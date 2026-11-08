"""Faturamento mensal/quinzenal com preços históricos e escopo de mês explícito."""
from copy import deepcopy
from datetime import date, datetime, timezone as utc
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook

from core.periodos import FiltroPeriodo, periodo_mes
from entregas.models import Entrega
from painel.dashboard import montar_dashboard
from painel.faturamento import calcular_faturamento_quinzenal
from painel.models import Configuracao
from tests.test_dashboard_situacao_real import CardsEncomendas


class CardsFaturamentoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(username="cards_faturamento_teste")

    def setUp(self):
        self.client.force_login(self.usuario)

    def entrega(self, dia, valor="5.00", situacao="Baixa realizada", codigo=None):
        return Entrega.objects.create(data=dia, codigo=codigo or str(Entrega.objects.count()),
                                      situacao=situacao, valor_por_baixa=Decimal(valor))

    def faturamento(self, ano, mes):
        return montar_dashboard(FiltroPeriodo(*periodo_mes(ano, mes)))["faturamento_quinzenal"]

    def test_31_30_dias_e_fevereiros_com_fronteiras_15_16(self):
        for ano, mes, ultimo in [(2026, 1, 31), (2026, 4, 30), (2026, 2, 28), (2024, 2, 29)]:
            with self.subTest(ano=ano, mes=mes):
                for dia, valor in [(1, "1.25"), (15, "2.50"), (16, "4.75"), (ultimo, "8.50")]:
                    self.entrega(date(ano, mes, dia), valor)
                f = self.faturamento(ano, mes)
                self.assertEqual(f["fim"], date(ano, mes, ultimo))
                self.assertEqual(f["primeira_quinzena"], Decimal("3.75"))
                self.assertEqual(f["segunda_quinzena"], Decimal("13.25"))
                self.assertEqual(f["mensal"], Decimal("17.00"))
                self.assertEqual(f["mensal"], f["primeira_quinzena"] + f["segunda_quinzena"])

    def test_fevereiro_separa_anos_e_nao_inclui_janeiro_marco(self):
        for dia in [date(2026, 1, 31), date(2026, 3, 1), date(2025, 2, 1)]:
            self.entrega(dia, "100.00")
        self.entrega(date(2026, 2, 28), "7.25")
        f = self.faturamento(2026, 2)
        self.assertEqual((f["mensal"], f["primeira_quinzena"], f["segunda_quinzena"]), (Decimal("7.25"), 0, Decimal("7.25")))

    def test_precos_historicos_insucessos_e_baixas_repetidas(self):
        self.entrega(date(2026, 11, 15), "3.50", codigo="mesmo")
        self.entrega(date(2026, 11, 16), "7.25", codigo="mesmo")
        self.entrega(date(2026, 11, 16), "7.25", codigo="mesmo")
        self.entrega(date(2026, 11, 16), "99.00", "Insucesso")
        Configuracao.objects.create(valor_por_baixa=Decimal("50.00"))
        antes = list(Entrega.objects.values())
        f = self.faturamento(2026, 11)
        self.assertEqual((f["mensal"], f["primeira_quinzena"], f["segunda_quinzena"]), (18, Decimal("3.50"), Decimal("14.50")))
        self.assertEqual(antes, list(Entrega.objects.values()))

    def test_mes_sem_baixas_exibe_zero_sem_inventar_receita(self):
        self.entrega(date(2026, 11, 1), "5.00", "Insucesso")
        self.assertEqual(self.faturamento(2026, 11)["mensal"], 0)
        f = self.faturamento(2026, 12)
        self.assertEqual((f["mensal"], f["primeira_quinzena"], f["segunda_quinzena"]), (0, 0, 0))

    def test_mes_completo_em_filtros_dia_semana_quinzena_intervalo(self):
        self.entrega(date(2026, 10, 1), "3.00")
        self.entrega(date(2026, 10, 15), "4.00")
        self.entrega(date(2026, 10, 16), "6.00")
        self.entrega(date(2026, 10, 31), "7.00")
        for inicio, fim in [(15, 15), (11, 17), (1, 15), (16, 31), (14, 17)]:
            with self.subTest(inicio=inicio, fim=fim):
                p = montar_dashboard(FiltroPeriodo(date(2026, 10, inicio), date(2026, 10, fim)))
                f = p["faturamento_quinzenal"]
                self.assertEqual((f["mensal"], f["primeira_quinzena"], f["segunda_quinzena"]), (20, 7, 13))
                esperado = sum(e.valor_previsto for e in Entrega.objects.filter(data__day__gte=inicio, data__day__lte=fim))
                self.assertEqual(p["resumo"]["receita"], esperado)
                self.assertEqual(p["indicadores_principais"]["faturamento"], esperado)

    @patch("painel.faturamento.timezone.now", return_value=datetime(2026, 11, 7, 15, tzinfo=utc.utc))
    def test_historico_e_varios_meses_usam_mes_vigente(self, _):
        self.entrega(date(2026, 10, 31), "100.00")
        self.entrega(date(2026, 11, 1), "3.00")
        self.entrega(date(2026, 11, 30), "7.00")
        for filtro in [FiltroPeriodo(), FiltroPeriodo(date(2026, 10, 25), date(2026, 11, 2))]:
            with self.subTest(filtro=filtro):
                f = montar_dashboard(filtro)["faturamento_quinzenal"]
                self.assertEqual(f["rotulo"], "11/2026")
                self.assertEqual((f["mensal"], f["primeira_quinzena"], f["segunda_quinzena"]), (10, 3, 7))

    @patch("painel.faturamento.timezone.now", return_value=datetime(2027, 1, 1, 1, tzinfo=utc.utc))
    def test_fuso_sao_paulo_na_virada_do_mes_e_ano(self, _):
        self.entrega(date(2026, 12, 31), "5.00")
        self.entrega(date(2027, 1, 1), "100.00")
        f = montar_dashboard()["faturamento_quinzenal"]
        self.assertEqual(f["rotulo"], "12/2026")
        self.assertEqual((f["mensal"], f["primeira_quinzena"], f["segunda_quinzena"]), (5, 0, 5))

    def test_agregacao_sem_consultas_adicionais_ou_mutacao(self):
        self.entrega(date(2026, 11, 15))
        self.entrega(date(2026, 11, 16), "7.00")
        historico = list(Entrega.objects.all())
        antes = [deepcopy({f.attname: getattr(e, f.attname) for f in e._meta.concrete_fields}) for e in historico]
        with self.assertNumQueries(0):
            f = calcular_faturamento_quinzenal(historico, FiltroPeriodo(*periodo_mes(2026, 11)))
        self.assertEqual(f["mensal"], 12)
        self.assertEqual([{f.attname: getattr(e, f.attname) for f in e._meta.concrete_fields} for e in historico], antes)

    def test_dados_aprovados_independentes_dos_novos_cards(self):
        self.entrega(date(2026, 11, 1), "5.00", "Insucesso", "r")
        self.entrega(date(2026, 11, 16), "7.00", codigo="r")
        filtro = FiltroPeriodo(*periodo_mes(2026, 11))
        with patch("painel.dashboard.calcular_faturamento_quinzenal", return_value={}):
            aprovado = montar_dashboard(filtro)
        atual = montar_dashboard(filtro)
        aprovado.pop("faturamento_quinzenal")
        atual.pop("faturamento_quinzenal")
        self.assertEqual(atual, aprovado)

    def test_recalcula_na_proxima_consulta_apos_cadastro_edicao_exclusao(self):
        e = self.entrega(date(2026, 11, 15))
        self.assertEqual(self.faturamento(2026, 11)["primeira_quinzena"], 5)
        e.data = date(2026, 11, 16)
        e.save()
        f = self.faturamento(2026, 11)
        self.assertEqual((f["primeira_quinzena"], f["segunda_quinzena"]), (0, 5))
        e.delete()
        self.assertEqual(self.faturamento(2026, 11)["mensal"], 0)

    def test_nove_cards_com_tres_financeiros_juntos_e_referencia(self):
        self.entrega(date(2026, 11, 1), "3.00")
        self.entrega(date(2026, 11, 16), "7.00")
        r = self.client.get(reverse("painel:inicio"), {"periodo": "dia", "dia": "2026-11-01"})
        html = r.content.decode()
        cards = CardsEncomendas(html).cards
        self.assertEqual(len(cards), 9)
        self.assertEqual(list(cards)[-3:], ["Faturamento Mensal", "Faturamento 1ª Quinzena", "Faturamento 2ª Quinzena"])
        self.assertEqual(list(cards.values())[-3:], ["R$ 10,00", "R$ 3,00", "R$ 7,00"])
        self.assertEqual(cards["Total de encomendas"], "1")
        self.assertEqual(html.count('class="cartao card-faturamento"'), 3)
        self.assertIn("11/2026 · mês completo", html)
        self.assertIn("16 a 30/11/2026", html)
        self.assertGreaterEqual(html.count("Receita prevista; não representa pagamento recebido."), 3)

    def test_exportacoes_continuam_no_periodo_filtrado(self):
        self.entrega(date(2026, 11, 1), "3.00")
        self.entrega(date(2026, 11, 16), "7.00")
        params = {"periodo": "dia", "dia": "2026-11-01"}
        r = self.client.get(reverse("painel:exportar_excel"), params)
        self.assertEqual(r.status_code, 200)
        livro = load_workbook(BytesIO(r.content))
        try:
            valores = {l[0]: l[1] for l in livro["Resumo de Indicadores"].iter_rows(min_row=6, values_only=True)}
            self.assertEqual(valores["Faturamento previsto"], 3)
            self.assertEqual(len(livro.sheetnames), 5)
        finally:
            livro.close()
        csv = self.client.get(reverse("painel:exportar_csv"), params).content.decode("utf-8-sig")
        self.assertIn("01/11/2026", csv)
        self.assertNotIn("16/11/2026", csv)
