import hashlib
import shutil
from collections import Counter
from datetime import date, time, timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import skipUnless
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from openpyxl import load_workbook
from openpyxl.utils.datetime import MAC_EPOCH
from conferencia.models import EspelhoEmpresa, Pagamento
from core.models import Importacao
from entregas.models import Entrega
from entregas.services.conversoes import codigo_excel, data_excel, horario_excel, decimal_excel, duracao_excel
from entregas.services.importacao import ErroImportacao, importar_excel
from jornadas.models import Jornada
from painel.models import Configuracao
from painel.services import resumo_entregas
from .factories import workbook_teste

EXCEL_REAL = settings.BASE_DIR / "referencias" / "Conferencia_de_Entregas(3).xlsx"


class ConversoesTests(TestCase):
    def test_datas_numericas_texto_e_epoca_1904(self):
        self.assertEqual(data_excel(46310), date(2026, 10, 15))
        self.assertEqual(data_excel("15/10/2026"), date(2026, 10, 15))
        self.assertEqual(data_excel(1, MAC_EPOCH), date(1904, 1, 2))

    def test_horarios_numericos_incluindo_meia_noite(self):
        self.assertEqual(horario_excel(.5), time(12))
        self.assertEqual(horario_excel(0), time(0))
        self.assertEqual(horario_excel("17:04:59"), time(17, 4, 59))
        with self.assertRaises(ValueError):
            horario_excel(2)

    def test_duracao_fracao_de_dia(self):
        self.assertEqual(duracao_excel(.125), timedelta(hours=3))
        self.assertIsNone(duracao_excel(None))

    def test_decimal_preciso_sem_transformar_vazio_em_zero(self):
        self.assertIsNone(decimal_excel(None))
        self.assertEqual(decimal_excel(0), Decimal("0.00"))
        self.assertEqual(decimal_excel(67.59999999999999, 3), Decimal("67.600"))
        self.assertEqual(decimal_excel("1.234,56"), Decimal("1234.56"))
        with self.assertRaises(ValueError):
            decimal_excel("NaN")


class ImportacaoTests(TestCase):
    def setUp(self):
        self.pasta = TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        self.arquivo = Path(self.pasta.name) / "origem.xlsx"
        self.workbook = workbook_teste(self.arquivo)
        self.addCleanup(self.workbook.close)

    def test_importa_quatro_abas_pulando_formulas_e_datas_isoladas(self):
        lote, criado = importar_excel(self.arquivo)
        self.assertTrue(criado)
        self.assertEqual(lote.resumo["contagens"], {"entregas": 2, "espelhos": 1, "jornadas": 1, "pagamentos": 0, "datas_sem_jornada_ignoradas": 1})
        self.assertEqual(len(lote.resumo["abas_lidas"]), 4)

    def test_codigos_zeros_a_esquerda_duplicados_e_ordem(self):
        importar_excel(self.arquivo)
        registros = list(Entrega.objects.order_by("ordem_original"))
        self.assertEqual([r.codigo for r in registros], ["000123", "000123"])
        self.assertEqual([r.ordem_original for r in registros], [1, 2])
        self.assertEqual(registros[0].horario, time(12))
        self.assertEqual(registros[0].dados_origem["A"]["formato"], "000000")
        self.assertEqual(registros[0].linha_origem, 3)

    def test_reimportacao_mesmo_hash_preserva_edicao_e_exclusao(self):
        lote, _ = importar_excel(self.arquivo)
        registro = Entrega.objects.order_by("pk").first()
        registro.codigo = "EDITADO"
        registro.save()
        Entrega.objects.exclude(pk=registro.pk).delete()
        mesmo, criado = importar_excel(self.arquivo)
        self.assertFalse(criado)
        self.assertEqual(mesmo.pk, lote.pk)
        self.assertEqual(Entrega.objects.get().codigo, "EDITADO")
        self.assertEqual(Importacao.objects.count(), 1)

    def test_arquivo_renomeado_com_mesmo_hash_nao_duplica(self):
        importar_excel(self.arquivo)
        copia = self.arquivo.with_name("copia.xlsx")
        shutil.copyfile(self.arquivo, copia)
        self.assertFalse(importar_excel(copia)[1])
        self.assertEqual(Entrega.objects.count(), 2)

    def test_mesmo_nome_com_conteudo_alterado_bloqueia(self):
        importar_excel(self.arquivo)
        self.workbook["Minhas Entregas"]["A3"] = "alterado"
        self.workbook.save(self.arquivo)
        with self.assertRaises(ErroImportacao):
            importar_excel(self.arquivo)
        self.assertEqual(Entrega.objects.count(), 2)

    def test_erro_em_ultima_aba_reverte_todas_as_gravacoes(self):
        self.workbook["Jornada e Custos"]["G5"] = -1
        self.workbook.save(self.arquivo)
        with self.assertRaises(ErroImportacao):
            importar_excel(self.arquivo)
        for modelo in (Entrega, EspelhoEmpresa, Jornada, Pagamento, Importacao):
            self.assertEqual(modelo.objects.count(), 0)

    def test_layout_desconhecido_e_formula_de_entrada_rejeitados(self):
        self.workbook["Minhas Entregas"]["A2"] = "Mudou"
        self.workbook.save(self.arquivo)
        with self.assertRaises(ErroImportacao):
            importar_excel(self.arquivo)
        self.workbook["Minhas Entregas"]["A2"] = "Código"
        self.workbook["Minhas Entregas"]["B3"] = "=TODAY()"
        self.workbook.save(self.arquivo)
        with self.assertRaises(ErroImportacao):
            importar_excel(self.arquivo)
        self.assertFalse(Importacao.objects.exists())

    def test_pagamento_efetivo_independente_de_espelho(self):
        for coord, valor in {"T5": 46320, "U5": 46296, "V5": 46310, "W5": 160.15, "X5": "comprovante", "Y5": "recebido"}.items():
            self.workbook["Espelho da Empresa"][coord] = valor
        self.workbook.save(self.arquivo)
        importar_excel(self.arquivo)
        pagamento = Pagamento.objects.get()
        self.assertEqual(pagamento.valor_recebido, Decimal("160.15"))
        self.assertEqual(pagamento.inicio_quinzena, date(2026, 10, 1))
        self.assertEqual(pagamento.fim_quinzena, date(2026, 10, 15))

    def test_parametros_manuais_preservados_e_preco_importado_historico(self):
        Configuracao.objects.create(valor_por_baixa=Decimal("8.00"))
        lote, _ = importar_excel(self.arquivo)
        self.assertTrue(lote.avisos)
        self.assertEqual(Configuracao.atual().valor_por_baixa, Decimal("8.00"))
        self.assertEqual(Entrega.objects.first().valor_por_baixa, Decimal("5.00"))

    def test_espelho_incompleto_e_zero_explicito_preservados(self):
        self.workbook["Espelho da Empresa"]["E5"] = None
        self.workbook.save(self.arquivo)
        lote, _ = importar_excel(self.arquivo)
        self.assertIsNone(EspelhoEmpresa.objects.get().valor_empresa)
        self.assertEqual(EspelhoEmpresa.objects.get().insucessos, 0)
        self.assertEqual(Jornada.objects.get().outros_custos, Decimal("0.00"))
        self.assertIsNone(Jornada.objects.get().inicio_real)
        self.assertTrue(lote.avisos)

    def test_comando_arquivo_inexistente_explica_erro(self):
        with self.assertRaisesMessage(CommandError, "nenhuma alteração"):
            call_command("importar_excel", str(self.arquivo.with_name("inexistente.xlsx")))


@skipUnless(EXCEL_REAL.exists(), "Excel privado não está disponível: testes históricos requerem o arquivo de referência.")
class HistoricoRealTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hash_antes = hashlib.sha256(EXCEL_REAL.read_bytes()).hexdigest()
        cls.lote, _ = importar_excel(EXCEL_REAL)

    def test_totais_historicos_por_data_e_situacao(self):
        esperados = {
            "2026-10-15": (33, 32, 1, "160.00"), "2026-10-16": (50, 48, 2, "240.00"),
            "2026-10-19": (36, 34, 2, "170.00"), "2026-10-20": (50, 40, 10, "200.00"),
        }
        self.assertEqual(set(self.lote.resumo["por_data"]), set(esperados))
        for dia, (tentativas, baixas, insucessos, receita) in esperados.items():
            with self.subTest(dia=dia):
                registros = Entrega.objects.filter(data=dia)
                self.assertEqual(registros.count(), tentativas)
                self.assertEqual(registros.filter(situacao="Baixa realizada").count(), baixas)
                self.assertEqual(registros.filter(situacao="Insucesso").count(), insucessos)
                self.assertEqual(sum(r.valor_previsto for r in registros), Decimal(receita))
        self.assertEqual(resumo_entregas(), {"tentativas": 169, "baixas": 154, "insucessos": 15, "receita": Decimal("770.00")})

    def test_espelho_real_preserva_campos(self):
        espelho = EspelhoEmpresa.objects.get()
        self.assertEqual(espelho.data_competencia, date(2026, 10, 15))
        self.assertEqual((espelho.baixas_pagas, espelho.insucessos, espelho.valor_empresa), (32, 1, Decimal("160.00")))
        self.assertEqual(espelho.documento, "OS 188674")
        self.assertEqual(espelho.vencimento, date(2026, 10, 25))
        self.assertIn("líquido R$ 160,00", espelho.observacoes)

    def test_jornadas_reais_preservam_financeiro_e_ausencias(self):
        self.assertEqual(Jornada.objects.count(), 4)
        jornada19 = Jornada.objects.get(data="2026-10-19")
        self.assertEqual(jornada19.quilometragem, Decimal("67.600"))
        self.assertEqual(jornada19.litros_consumidos, Decimal("3.762"))
        self.assertEqual(jornada19.custo_combustivel, Decimal("20.45"))
        self.assertIsNone(jornada19.outros_custos)
        jornada20 = Jornada.objects.get(data="2026-10-20")
        self.assertEqual(jornada20.custo_combustivel, Decimal("13.54"))
        self.assertEqual(jornada20.litros_consumidos, Decimal("2.093"))
        self.assertIsNone(jornada20.quilometragem)
        self.assertIsNone(jornada20.janela_historica)
        self.assertEqual(Jornada.objects.get(data="2026-10-15").janela_historica, timedelta(hours=3, minutes=12))
        self.assertEqual(Pagamento.objects.count(), 0)

    def test_todos_codigos_ordem_datas_horarios_e_situacoes_do_original(self):
        workbook = load_workbook(EXCEL_REAL, data_only=False)
        self.addCleanup(workbook.close)
        aba = workbook["Minhas Entregas"]
        codigos_excel = []
        for registro in Entrega.objects.all():
            linha = registro.linha_origem
            codigo = codigo_excel(aba[f"A{linha}"])
            codigos_excel.append(codigo)
            self.assertEqual(registro.codigo, codigo)
            self.assertEqual(registro.data, data_excel(aba[f"B{linha}"].value, workbook.epoch))
            self.assertEqual(registro.horario, horario_excel(aba[f"C{linha}"].value, workbook.epoch))
            self.assertEqual(registro.situacao, aba[f"D{linha}"].value)
            self.assertEqual(registro.ordem_original, linha - 2)
        contagem = Counter(codigos_excel)
        self.assertTrue(any(n > 1 for n in contagem.values()))
        self.assertEqual(contagem, Counter(Entrega.objects.values_list("codigo", flat=True)))

    def test_reimportacao_real_nao_duplica_e_arquivo_permanece_identico(self):
        self.assertFalse(importar_excel(EXCEL_REAL)[1])
        self.assertEqual(Entrega.objects.count(), 169)
        self.assertEqual(hashlib.sha256(EXCEL_REAL.read_bytes()).hexdigest(), self.hash_antes)
