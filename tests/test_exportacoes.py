import csv
from datetime import date, time, timedelta
from decimal import Decimal
from io import BytesIO, StringIO
import secrets
from unittest import skipUnless
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook
from core.periodos import FiltroPeriodo
from entregas.models import Entrega
from conferencia.models import EspelhoEmpresa, Pagamento
from jornadas.models import Jornada
from painel.exportacao import exportar_xlsx, exportar_csv, proteger_csv
from entregas.services.importacao import importar_excel
from .test_importacao import EXCEL_REAL


class ExportacoesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(username="exportacao_teste", password=secrets.token_urlsafe(24))
        for dia, situacao in [(15, "Baixa realizada"), (15, "Insucesso"), (20, "Baixa realizada")]:
            Entrega.objects.create(codigo="000123", data=date(2026, 10, dia), horario=time(12, 30, 45), situacao=situacao, valor_por_baixa=Decimal("5.00"))
        EspelhoEmpresa.objects.create(data_competencia=date(2026, 10, 15), baixas_pagas=1, insucessos=1, valor_empresa=Decimal("5.00"), documento="OS çã", observacoes="Entrega; conferida\ncom observação")
        Jornada.objects.create(data=date(2026, 10, 20), odometro_inicial=0, custo_combustivel=Decimal("13.54"), litros_consumidos=Decimal("2.093"), janela_historica=timedelta(hours=3, minutes=12))
        Pagamento.objects.create(data_pagamento=date(2026, 11, 1), inicio_quinzena=date(2026, 10, 1), fim_quinzena=date(2026, 10, 15), valor_recebido=Decimal("3.25"), comprovante="Comprovante á")

    def abrir(self, filtro=None):
        livro = load_workbook(BytesIO(exportar_xlsx(filtro or FiltroPeriodo())), data_only=False)
        self.addCleanup(livro.close)
        return livro

    def test_cinco_abas_dados_formatos_e_codigos_textuais(self):
        livro = self.abrir()
        self.assertEqual(livro.sheetnames, ["Minhas Entregas", "Espelhos da Empresa", "Jornadas e Custos", "Pagamentos", "Resumo de Indicadores"])
        aba = livro["Minhas Entregas"]
        self.assertEqual([aba.cell(linha, 1).value for linha in (6, 7, 8)], ["000123"] * 3)
        self.assertEqual(aba["A6"].data_type, "s")
        self.assertEqual(aba["A6"].number_format, "@")
        self.assertEqual(aba["B6"].value.date(), date(2026, 10, 15))
        self.assertEqual(aba["B6"].number_format, "dd/mm/yyyy")
        self.assertEqual(aba["C6"].value, time(12, 30, 45))
        self.assertEqual(aba["F6"].value, 5)
        self.assertIn("R$", aba["F6"].number_format)
        self.assertEqual(livro["Espelhos da Empresa"]["F6"].value, "OS çã")

    def test_jornadas_preservam_nulos_zeros_e_duracao(self):
        aba = self.abrir()["Jornadas e Custos"]
        self.assertEqual(aba["D6"].value, 0)
        self.assertIsNone(aba["E6"].value)
        self.assertIsNone(aba["F6"].value)
        self.assertIsNone(aba["I6"].value)
        self.assertEqual(Decimal(str(aba["G6"].value)), Decimal("2.093"))
        self.assertEqual(aba["J6"].value, timedelta(hours=3, minutes=12))

    def test_pagamento_por_competencia_e_filtro_nas_cinco_abas(self):
        filtro = FiltroPeriodo(date(2026, 10, 1), date(2026, 10, 15))
        livro = self.abrir(filtro)
        self.assertIsNone(livro["Jornadas e Custos"]["A6"].value)
        self.assertEqual(livro["Pagamentos"]["D6"].value, 3.25)
        self.assertEqual(livro["Minhas Entregas"]["A6"].value, "000123")
        self.assertEqual(livro["Minhas Entregas"]["A7"].value, "000123")
        self.assertIsNone(livro["Minhas Entregas"]["A8"].value)
        for aba in livro:
            self.assertIn("01/10/2026 a 15/10/2026", aba["A2"].value)
            self.assertIn("não é automaticamente compatível", aba["A3"].value.lower())

    def test_textos_de_formula_sao_strings_sem_formulas_no_xlsx(self):
        casos = ["=HYPERLINK(\"https://exemplo.invalid\")", "+1+1", "-2+3", "@SUM(A1)", "\t=1", " \ufeff=1"]
        for codigo in casos:
            Entrega.objects.create(codigo=codigo, data=date(2026, 10, 21), horario=time(12), situacao="Baixa realizada")
        livro = self.abrir()
        for aba in livro:
            self.assertFalse(any(c.data_type == "f" for linha in aba for c in linha))
        valores = [c.value for linha in livro["Minhas Entregas"] for c in linha if c.column == 1]
        for codigo in casos:
            self.assertIn(codigo, valores)

    def test_csv_utf8_bom_delimitador_dinheiro_e_codigos_repetidos(self):
        conteudo = exportar_csv(FiltroPeriodo())
        self.assertTrue(conteudo.startswith(b"\xef\xbb\xbf"))
        linhas = list(csv.reader(StringIO(conteudo.decode("utf-8-sig")), delimiter=";"))
        self.assertEqual(len(linhas), 4)
        self.assertEqual(linhas[0], ["Código", "Data", "Horário", "Situação", "Valor previsto (R$)"])
        self.assertEqual([l[0] for l in linhas[1:]], ["000123"] * 3)
        self.assertEqual(linhas[1][1:3], ["15/10/2026", "12:30:45"])
        self.assertEqual(linhas[1][4], "5,00")
        self.assertEqual(linhas[2][4], "0,00")

    def test_csv_bloqueia_formulas_apos_espacos_e_controles(self):
        for valor in ["=1", "+SUM(1)", "-1+1", "@SUM(1)", "\t=1", "\r=1", " \ufeff=1", "\v=1"]:
            with self.subTest(valor=valor):
                self.assertTrue(proteger_csv(valor).startswith("'"))
        self.assertEqual(proteger_csv("000123"), "000123")
        self.assertEqual(proteger_csv('çã;"teste"'), 'çã;"teste"')

    def test_csv_filtrado_e_caracteres_especiais(self):
        registro = Entrega.objects.order_by("pk").last()
        registro.codigo = 'ação;"teste"'
        registro.save()
        texto = exportar_csv(FiltroPeriodo(date(2026, 10, 20), date(2026, 10, 20))).decode("utf-8-sig")
        linhas = list(csv.reader(StringIO(texto), delimiter=";"))
        self.assertEqual(len(linhas), 2)
        self.assertEqual(linhas[1][0], 'ação;"teste"')

    def test_exportacoes_nao_contem_autenticacao_ou_snapshots_tecnicos(self):
        livro = self.abrir()
        texto = " ".join(str(c.value) for aba in livro for linha in aba for c in linha if c.value is not None)
        for termo in ["password", "secret_key", "session_key", "dados_origem", "sha256", "csrfmiddlewaretoken", self.usuario.password]:
            self.assertNotIn(termo, texto)

    def test_resumo_distingue_previsto_informado_e_recebido(self):
        aba = self.abrir()["Resumo de Indicadores"]
        valores = {aba.cell(linha, 1).value: aba.cell(linha, 2).value for linha in range(6, aba.max_row + 1)}
        self.assertEqual(valores["Faturamento previsto"], 10)
        self.assertEqual(valores["Informado conhecido"], 5)
        self.assertEqual(valores["Recebido registrado"], 3.25)
        self.assertIsNone(valores["Resultado líquido completo"])

    def test_rotas_autenticadas_somente_get_e_download_privado(self):
        for rota in ["painel:exportar_excel", "painel:exportar_csv"]:
            self.assertEqual(self.client.get(reverse(rota)).status_code, 302)
        self.client.force_login(self.usuario)
        for rota in ["painel:exportar_excel", "painel:exportar_csv"]:
            resposta = self.client.get(reverse(rota))
            self.assertEqual(resposta.status_code, 200)
            self.assertIn("attachment", resposta["Content-Disposition"])
            self.assertEqual(resposta["Cache-Control"], "private, no-store")
            self.assertEqual(self.client.post(reverse(rota)).status_code, 405)

    def test_filtro_invalido_retorna_400_sem_exportar_tudo(self):
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse("painel:exportar_excel"), {"periodo": "dia", "dia": "invalido"})
        self.assertContains(resposta, "Não foi possível exportar", status_code=400)
        self.assertNotIn("Content-Disposition", resposta)

    def test_exportacao_nao_modifica_registros(self):
        antes = list(Entrega.objects.values())
        exportar_xlsx(FiltroPeriodo())
        exportar_csv(FiltroPeriodo())
        self.assertEqual(antes, list(Entrega.objects.values()))


@skipUnless(EXCEL_REAL.exists(), "Planilha privada para validar os relatórios históricos.")
class ExportacoesHistoricasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        importar_excel(EXCEL_REAL)

    def test_csv_historico_preserva_169_e_770_reais(self):
        linhas = list(csv.reader(StringIO(exportar_csv(FiltroPeriodo()).decode("utf-8-sig")), delimiter=";"))[1:]
        self.assertEqual(len(linhas), 169)
        self.assertEqual(sum(Decimal(l[4].replace(",", ".")) for l in linhas), Decimal("770.00"))
        self.assertLess(len({l[0] for l in linhas}), 169)

    def test_xlsx_historico_reabre_e_filtro_de_quinzena_confere(self):
        livro = load_workbook(BytesIO(exportar_xlsx(FiltroPeriodo(date(2026, 10, 16), date(2026, 10, 31)))))
        self.addCleanup(livro.close)
        aba = livro["Minhas Entregas"]
        dados = list(aba.iter_rows(min_row=6, max_row=141, values_only=True))
        self.assertEqual(len(dados), 136)
        self.assertTrue(all(l[0] and l[1].day >= 16 for l in dados))
        self.assertEqual(sum(Decimal(str(l[5])) for l in dados), Decimal("610.00"))
