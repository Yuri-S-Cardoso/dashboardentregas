"""Contrato explícito dos cards: registros, conciliação distinta e taxa mista."""
import csv
from datetime import date, datetime, time
from decimal import Decimal
from io import BytesIO, StringIO
import json
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook

from core.periodos import FiltroPeriodo
from entregas.models import Entrega
from painel.exportacao import exportar_csv, exportar_xlsx
from tests.test_dashboard_situacao_real import CardsEncomendas

BAIXA = "Baixa realizada"
INSUCESSO = "Insucesso"


class LeituraIndicadores:
    def setUp(self):
        self.client.force_login(self.usuario)

    def ler(self, esperado, params=None):
        resposta = self.client.get(reverse("painel:inicio"), params or {"periodo": "todos"})
        self.assertEqual(resposta.status_code, 200)
        painel = resposta.context["dashboard"]
        indicadores = painel["indicadores_principais"]
        campos = ("total_encomendas", "entregas_concluidas", "total_com_insucesso",
                  "insucessos_pendentes", "entregas_recuperadas")
        self.assertEqual(tuple(indicadores[c] for c in campos), esperado)
        self.assertEqual(indicadores["total_encomendas"],
                         indicadores["entregas_concluidas"] + indicadores["total_com_insucesso"])
        self.assertIn("no-store", resposta["Cache-Control"])
        return resposta, painel


class IndicadoresReferenciaTests(LeituraIndicadores, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(username="referencia_indicadores_teste")
        itens = []

        def adicionar(codigo, situacao, dia, horario):
            itens.append(Entrega(codigo=codigo, situacao=situacao, data=date(2026, 10, dia),
                                 horario=horario, valor_por_baixa=Decimal("5.00")))

        for i in range(528):
            adicionar(f"B{i:04}", BAIXA, 21, time(10))
        for i in range(33):
            adicionar(f"R{i:04}", INSUCESSO, 20, time(10))
            adicionar(f"R{i:04}", BAIXA, 21, time(11))
        for i in range(18):
            adicionar(f"P{i:04}", INSUCESSO, 20, time(10))
        for i in range(6):
            adicionar(f"P{i:04}", INSUCESSO, 20, time(11))
        adicionar("B0000", BAIXA, 21, time(12))
        Entrega.objects.bulk_create(itens)

    def test_referencia_619_562_57_18_33_e_taxa_9690(self):
        resposta, p = self.ler((619, 562, 57, 18, 33), {"periodo": "mes", "mes": "10", "ano": "2026"})
        self.assertEqual(CardsEncomendas(resposta.content.decode()).cards, {
            "Total de encomendas": "619", "Entregas concluídas": "562",
            "Total com insucesso": "57", "Insucessos pendentes": "18",
            "Entregas recuperadas": "33", "Taxa de Sucesso": "96,90%", "Faturamento Mensal": "R$ 2.810,00",
            "Faturamento 1ª Quinzena": "R$ 0,00", "Faturamento 2ª Quinzena": "R$ 2.810,00",
        })
        self.assertEqual(p["indicadores_principais"]["taxa_sucesso"], Decimal(56200) / 580)
        self.assertEqual(p["indicadores_principais"]["taxa_sucesso_arredondada"], Decimal("96.90"))
        self.assertNotEqual(p["indicadores_principais"]["taxa_sucesso"], p["conciliacao"]["sucesso_percentual"])
        self.assertEqual(p["conciliacao"]["entregas_identificadas"], 579)

    def test_baixas_repetidas_permanecem_no_card_e_na_receita(self):
        _, p = self.ler((619, 562, 57, 18, 33))
        self.assertEqual(p["conciliacao"]["concluidas"], 561)
        self.assertEqual(p["conciliacao"]["alertas_financeiros"], 1)
        self.assertEqual(p["resumo"]["receita"], Decimal("2810.00"))
        self.assertEqual(Entrega.objects.filter(codigo="B0000").count(), 2)

    def test_valores_sao_recalculados_se_referencia_muda_para_618(self):
        duplicada = Entrega.objects.get(codigo="B0000", horario=time(12))
        self.assertEqual(self.client.post(reverse("entregas:excluir", args=[duplicada.pk])).status_code, 302)
        resposta, p = self.ler((618, 561, 57, 18, 33))
        self.assertEqual(CardsEncomendas(resposta.content.decode()).cards["Taxa de Sucesso"], "96,89%")
        self.assertEqual(p["resumo"]["receita"], Decimal("2805.00"))

    def test_baixa_individual_acrescenta_registro_e_resolve_pendencia(self):
        self.ler((619, 562, 57, 18, 33))
        original = Entrega.objects.values().get(codigo="P0006")
        resposta = self.client.post(reverse("entregas:nova"), {
            "codigo": "P0006", "data": "2026-10-22", "horario": "12:00", "situacao": BAIXA})
        self.assertEqual(resposta.status_code, 302)
        _, p = self.ler((620, 563, 57, 17, 34))
        self.assertEqual(Entrega.objects.values().get(pk=original["id"]), original)
        self.assertEqual(p["resumo"]["receita"], 2815)

    def test_editar_situacao_da_baixa_atualiza_ocorrencias_e_conciliacao(self):
        baixa = Entrega.objects.get(codigo="R0000", situacao=BAIXA)
        self.ler((619, 562, 57, 18, 33))
        resposta = self.client.post(reverse("entregas:editar", args=[baixa.pk]), {
            "codigo": baixa.codigo, "data": "2026-10-21", "horario": "11:00", "situacao": INSUCESSO})
        self.assertEqual(resposta.status_code, 302)
        resposta, _ = self.ler((619, 561, 58, 19, 32))
        self.assertEqual(CardsEncomendas(resposta.content.decode()).cards["Taxa de Sucesso"], "96,72%")

    def test_excluir_baixa_atualiza_total_e_reabre_pendencia(self):
        baixa = Entrega.objects.get(codigo="R0001", situacao=BAIXA)
        self.ler((619, 562, 57, 18, 33))
        self.assertEqual(self.client.post(reverse("entregas:excluir", args=[baixa.pk])).status_code, 302)
        self.ler((618, 561, 57, 19, 32))

    def test_lote_editado_na_previa_confirmado_e_reenviado_sem_duplicar(self):
        dados = {"chave": str(uuid4()), "data_padrao": "2026-10-22", "situacao_padrao": INSUCESSO,
                 "linhas": json.dumps([{"codigo": "P0007"}, {"codigo": "P0008"}])}
        url = reverse("entregas:lote")
        self.assertEqual(self.client.post(url, {**dados, "acao": "prever"}).status_code, 200)
        self.assertEqual(self.client.post(url, {**dados, "acao": "editar"}).status_code, 200)
        self.ler((619, 562, 57, 18, 33))
        dados["situacao_padrao"] = BAIXA
        previa = self.client.post(url, {**dados, "acao": "prever"})
        self.assertEqual(previa.status_code, 200)
        dados.update(acao="salvar", comprovante=previa.context["form"]["comprovante"].value())
        for _ in range(2):
            self.assertEqual(self.client.post(url, dados).status_code, 302)
            _, p = self.ler((621, 564, 57, 16, 35))
            self.assertEqual(p["resumo"]["receita"], 2820)

    def test_exportacoes_preservam_financas_e_distinguem_os_dois_percentuais(self):
        antes = list(Entrega.objects.values())
        self.ler((619, 562, 57, 18, 33))
        livro = load_workbook(BytesIO(exportar_xlsx(FiltroPeriodo())))
        self.addCleanup(livro.close)
        self.assertEqual(len(livro.sheetnames), 5)
        linhas = {r[0]: r[1] for r in livro["Resumo de Indicadores"].iter_rows(min_row=6, values_only=True)}
        self.assertAlmostEqual(linhas["Taxa de Sucesso (%)"], 562 / (562 + 18) * 100)
        celula_taxa = next(r[1] for r in livro["Resumo de Indicadores"].iter_rows(min_row=6) if r[0].value == "Taxa de Sucesso (%)")
        self.assertEqual(celula_taxa.number_format, "0.00")
        self.assertAlmostEqual(linhas["Sucesso por encomenda distinta (%)"], 561 / (561 + 18) * 100)
        self.assertEqual(linhas["Faturamento previsto"], 2810)
        registros = [r for r in livro["Minhas Entregas"].iter_rows(min_row=6, values_only=True) if isinstance(r[1], datetime)]
        self.assertEqual(len(registros), 619)
        self.assertEqual(sum(r[5] for r in registros), 2810)
        csv_linhas = list(csv.reader(StringIO(exportar_csv(FiltroPeriodo()).decode("utf-8-sig")), delimiter=";"))
        self.assertEqual(len(csv_linhas), 620)
        self.assertEqual(antes, list(Entrega.objects.values()))


class IndicadoresPopulacoesTests(LeituraIndicadores, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(username="populacoes_indicadores_teste")

    def criar(self, situacao=INSUCESSO, dia="2026-10-15", horario=time(10), codigo="000123"):
        return Entrega.objects.create(codigo=codigo, data=date.fromisoformat(dia), horario=horario,
                                      situacao=situacao, valor_por_baixa=Decimal("5.00"))

    def test_varios_insucessos_inflam_so_ocorrencias_e_nao_pendencias(self):
        self.criar()
        self.criar(horario=time(11))
        resposta, _ = self.ler((2, 0, 2, 1, 0))
        self.assertEqual(CardsEncomendas(resposta.content.decode()).cards["Taxa de Sucesso"], "0,00%")

    def test_dois_insucessos_e_baixas_repetidas_recuperam_uma_so_encomenda(self):
        self.criar()
        self.criar(horario=time(11))
        self.criar(BAIXA, "2026-10-16")
        self.criar(BAIXA, "2026-10-16", horario=time(11))
        self.ler((4, 2, 2, 0, 1))

    def test_todos_os_filtros_contam_ocorrencias_e_consultam_baixa_futura(self):
        self.criar()
        self.criar(BAIXA, "2026-11-01")
        filtros = [
            {"periodo": "dia", "dia": "2026-10-15"},
            {"periodo": "semana", "semana": "2026-10-15"},
            {"periodo": "mes", "mes": 10, "ano": 2026},
            {"periodo": "quinzena", "mes": 10, "ano": 2026, "quinzena": 1},
            {"periodo": "intervalo", "inicio": "2026-10-14", "fim": "2026-10-15"},
        ]
        for params in filtros:
            with self.subTest(params=params):
                resposta, p = self.ler((1, 0, 1, 0, 1), params)
                self.assertIsNone(p["indicadores_principais"]["taxa_sucesso"])
                self.assertEqual(p["resumo"]["receita"], 0)
                self.assertContains(resposta, "Os três primeiros cards contam registros")
                self.assertContains(resposta, "Referência da conciliação")
        self.ler((2, 1, 1, 0, 1), {"periodo": "todos"})

    def test_baixa_na_quinzena_seguinte_nao_e_contada_na_primeira(self):
        self.criar()
        self.criar(BAIXA, "2026-10-16")
        _, p = self.ler((1, 0, 1, 0, 1), {"periodo": "quinzena", "mes": 10, "ano": 2026, "quinzena": 1})
        self.assertEqual(p["resumo"]["receita"], 0)
        self.ler((1, 1, 0, 0, 0), {"periodo": "quinzena", "mes": 10, "ano": 2026, "quinzena": 2})

    def test_baixa_no_mes_seguinte_mantem_receita_na_data_efetiva(self):
        self.criar(dia="2026-10-31")
        self.criar(BAIXA, "2026-11-01")
        self.ler((1, 0, 1, 0, 1), {"periodo": "mes", "mes": 10, "ano": 2026})
        resposta, p = self.ler((1, 1, 0, 0, 0), {"periodo": "mes", "mes": 11, "ano": 2026})
        self.assertEqual(p["resumo"]["receita"], 5)
        self.assertEqual(CardsEncomendas(resposta.content.decode()).cards["Taxa de Sucesso"], "100,00%")

    def test_baixa_antiga_nao_resolve_falha_posterior_mas_conta_como_registro(self):
        self.criar(BAIXA, "2026-10-14")
        self.criar()
        resposta, p = self.ler((2, 1, 1, 0, 0))
        self.assertEqual(p["conciliacao"]["codigos_em_revisao"], 1)
        self.assertEqual(p["indicadores_principais"]["taxa_sucesso"], 100)
        self.assertContains(resposta, "Necessita revisão")
        self.assertContains(resposta, "seus registros permanecem nos três primeiros cards")

    def test_codigos_com_zeros_nao_sao_fundidos(self):
        self.criar(codigo="000123")
        self.criar(BAIXA, "2026-10-16", codigo="123")
        resposta, _ = self.ler((2, 1, 1, 1, 0))
        self.assertEqual(CardsEncomendas(resposta.content.decode()).cards["Taxa de Sucesso"], "50,00%")

    def test_sem_registros_denominador_zero_permanece_nao_informado(self):
        resposta, p = self.ler((0, 0, 0, 0, 0))
        self.assertIsNone(p["indicadores_principais"]["taxa_sucesso"])
        self.assertEqual(CardsEncomendas(resposta.content.decode()).cards["Taxa de Sucesso"], "Não informado")

    def test_horario_ausente_no_mesmo_dia_mantem_alerta_e_ocorrencias(self):
        self.criar(horario=None)
        self.criar(BAIXA)
        resposta, p = self.ler((2, 1, 1, 0, 0))
        self.assertEqual(p["conciliacao"]["codigos_em_revisao"], 1)
        self.assertContains(resposta, "Necessita revisão")
