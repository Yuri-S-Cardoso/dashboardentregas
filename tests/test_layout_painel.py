"""Contrato do painel civil, conciliação global e medidas de conjuntos comparáveis."""
import csv
from datetime import date, datetime, time, timedelta, timezone as utc
from decimal import Decimal
from html.parser import HTMLParser
from io import StringIO
import json
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from core.periodos import FiltroPeriodo, periodo_semana
from conferencia.models import EspelhoEmpresa
from entregas.models import Entrega
from jornadas.models import Jornada
from painel.dashboard import montar_dashboard
from painel.forms import FiltroPainelForm
from tests.test_dashboard_situacao_real import CardsEncomendas

B = "Baixa realizada"
I = "Insucesso"


class TabelasPainel(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tabelas = []
        self.tabela = self.linha = self.celula = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.tabela = []
        elif tag == "tr" and self.tabela is not None:
            self.linha = []
        elif tag in ("th", "td") and self.linha is not None:
            self.celula = ""

    def handle_data(self, texto):
        if self.celula is not None:
            self.celula += texto + " "

    def handle_endtag(self, tag):
        if tag in ("th", "td") and self.celula is not None:
            self.linha.append(" ".join(self.celula.split()))
            self.celula = None
        elif tag == "tr" and self.linha is not None:
            self.tabela.append(self.linha)
            self.linha = None
        elif tag == "table" and self.tabela is not None:
            self.tabelas.append(self.tabela)
            self.tabela = None


class CalendarioCivilTests(SimpleTestCase):
    def test_domingo_sabado_mes_e_ano(self):
        for dia, inicio, fim in [
            ("2026-10-29", "2026-10-25", "2026-10-31"),
            ("2026-11-01", "2026-11-01", "2026-11-07"),
            ("2021-01-01", "2020-12-27", "2021-01-02"),
            ("2026-10-01", "2026-09-27", "2026-10-03"),
        ]:
            with self.subTest(dia=dia):
                self.assertEqual(periodo_semana(date.fromisoformat(dia)),
                                 (date.fromisoformat(inicio), date.fromisoformat(fim)))

    def test_limites_representaveis_do_calendario(self):
        self.assertEqual(periodo_semana(date.min)[0], date.min)
        self.assertEqual(periodo_semana(date.max)[1], date.max)

    def test_filtro_semanal_por_data_e_consulta_canonica(self):
        f = FiltroPainelForm({"periodo": "semana", "semana": "2026-10-29", "senha": "privado", "dia": "2026-10-15"})
        self.assertTrue(f.is_valid(), f.errors)
        self.assertEqual(f.cleaned_data["filtro"], FiltroPeriodo(date(2026, 10, 25), date(2026, 10, 31)))
        self.assertEqual(f.parametros().urlencode(), "periodo=semana&semana=2026-10-25")

    def test_filtro_iso_antigo_nao_se_converte_silenciosamente(self):
        f = FiltroPainelForm({"periodo": "semana", "semana": "2026-W43"})
        self.assertFalse(f.is_valid())
        self.assertIn("semana", f.errors)

    def test_mes_padrao_usa_sao_paulo_mesmo_com_utc_no_mes_seguinte(self):
        for hora, mes in [(1, 10), (3, 11)]:
            with self.subTest(hora=hora), patch("painel.forms.timezone.now", return_value=datetime(2026, 11, 1, hora, tzinfo=utc.utc)):
                f = FiltroPainelForm({})
                self.assertTrue(f.is_valid())
                self.assertEqual(f.cleaned_data["filtro"].inicio, date(2026, mes, 1))
                self.assertEqual(f.parametros()["mes"], str(mes))


class LayoutPainelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(username="layout_painel_teste")

    def setUp(self):
        self.client.force_login(self.usuario)

    def entrega(self, codigo, dia, situacao=B, valor="5.00", horario=time(10)):
        return Entrega.objects.create(codigo=codigo, data=date.fromisoformat(dia), situacao=situacao,
                                      horario=horario, valor_por_baixa=Decimal(valor))

    def pagina(self, params=None):
        r = self.client.get(reverse("painel:inicio"), params if params is not None else {"periodo": "todos"})
        self.assertEqual(r.status_code, 200)
        return r

    @patch("painel.forms.timezone.now", return_value=datetime(2026, 10, 31, 15, tzinfo=utc.utc))
    def test_default_mes_historico_explicito_e_exportacoes_coerentes(self, _):
        for mes in (9, 10, 11):
            self.entrega(str(mes), f"2026-{mes:02}-01")
        r = self.pagina({})
        self.assertEqual(r.context["dashboard"]["indicadores_principais"]["total_encomendas"], 1)
        self.assertEqual(r.context["filtros_query"], "periodo=mes&mes=10&ano=2026")
        self.assertEqual(self.pagina().context["resumo"]["tentativas"], 3)
        auditoria = self.client.get(reverse("painel:auditoria"))
        self.assertEqual(auditoria.context["resumo"]["tentativas"], 1)
        for params, quantidade in [({}, 1), ({"periodo": "todos"}, 3)]:
            csv_bytes = self.client.get(reverse("painel:exportar_csv"), params).content
            linhas = list(csv.reader(StringIO(csv_bytes.decode("utf-8-sig")), delimiter=";"))
            self.assertEqual(len(linhas) - 1, quantidade)

    def test_menu_links_filtrados_e_ausencia_de_dados_privados(self):
        r = self.pagina({"periodo": "semana", "semana": "2026-10-29", "token": "NAO_PROPAGAR"})
        html = r.content.decode()
        self.assertIn('data-menu-painel', html)
        self.assertIn('aria-controls="opcoes-painel"', html)
        self.assertIn('data-fechar-painel', html)
        for texto in ("Filtrar período", "Exportar relatórios", "Conferência Financeira"):
            self.assertIn(texto, html)
        for rota in ("painel:auditoria", "painel:exportar_excel", "painel:exportar_csv"):
            self.assertIn(reverse(rota) + "?periodo=semana&amp;semana=2026-10-25", html)
        self.assertIn(reverse("painel:exportar_excel") + "?periodo=todos", html)
        self.assertNotIn("NAO_PROPAGAR", html)
        self.assertEqual(self.client.get(reverse("painel:auditoria"), r.context["filtro"].parametros()).status_code, 200)

    def test_nove_cards_ordem_secoes_e_colunas_exatas(self):
        self.entrega("b", "2026-10-29")
        r = self.pagina({"periodo": "mes", "mes": "10", "ano": "2026"})
        html = r.content.decode()
        self.assertEqual(len(CardsEncomendas(html).cards), 9)
        self.assertEqual(CardsEncomendas(html).cards["Faturamento Mensal"], "R$ 5,00")
        for texto in ("<h2>Horas e produtividade</h2>", "Finanças do período", "Faturamento e metas por dia", "Ganho médio por baixa", "Falta para meta", "Origem das horas"):
            self.assertNotIn(texto, html)
        ordem = [html.index(x) for x in ('<h1>Painel Geral', 'id="indicadores-encomendas"', 'id="titulo-dias"', 'id="titulo-semanas"', 'id="titulo-meses"', 'id="titulo-graficos"', 'id="auditoria-operacional"')]
        self.assertEqual(ordem, sorted(ordem))
        tabelas = TabelasPainel(html).tabelas
        self.assertEqual(tabelas[0][0], ["Data", "Faturamento", "Taxa de Sucesso", "Total de entregas", "Baixas realizadas", "Total de insucessos", "Horas trabalhadas", "KM rodados", "KM/L"])
        colunas = ["Período", "Faturamento", "Média de receita por dia", "Taxa de Sucesso", "Total de entregas", "Baixas realizadas", "Insucessos pendentes", "Horas trabalhadas", "KM rodados", "Gasto com combustível", "Litros", "Média de KM/L"]
        self.assertEqual(tabelas[1][0], colunas)
        self.assertEqual(tabelas[2][0], colunas)
        self.assertEqual([len(t[1]) for t in tabelas[:3]], [9, 12, 12])
        self.assertGreaterEqual(html.count('scope="col"'), 33)
        self.assertIn('aria-labelledby="titulo-semanas"', html)

    def test_mes_sem_dados_mantem_menu_cards_e_denominador_ausente(self):
        r = self.pagina({"periodo": "mes", "mes": 1, "ano": 2025})
        self.assertEqual(CardsEncomendas(r.content.decode()).cards["Taxa de Sucesso"], "Não informado")
        self.assertIn("Nenhum registro", r.content.decode())

    def test_espelho_isolado_nao_vira_dia_com_entrega(self):
        EspelhoEmpresa.objects.create(data_competencia=date(2026, 10, 29), documento="Somente espelho")
        r = self.pagina()
        self.assertEqual(r.context["dashboard"]["dias_operacionais"], [])
        self.assertEqual(TabelasPainel(r.content.decode()).tabelas[0][1], ["Sem dados no período."])

    def test_taxa_mista_mesma_em_todas_as_tabelas_com_arredondamento(self):
        self.entrega("b", "2026-10-29")
        for i in range(5):
            self.entrega(f"p{i}", "2026-10-29", I)
        p = self.pagina().context["dashboard"]
        for linha in [p, *p["diarios"], *p["semanas"], *p["meses"]]:
            self.assertEqual(linha["indicadores_principais"]["taxa_sucesso_arredondada"], Decimal("16.67"))
            self.assertEqual(linha["indicadores_principais"]["insucessos_pendentes"], 5)
        tabelas = TabelasPainel(self.pagina().content.decode()).tabelas
        self.assertEqual([t[1][i] for t, i in zip(tabelas[:3], [2, 3, 3])], ["16,67%"] * 3)

    def test_repeticoes_financeiras_e_insucessos_mantidos_por_data(self):
        self.entrega("r", "2026-10-26", I)
        self.entrega("r", "2026-10-27", I)
        self.entrega("r", "2026-10-28", B, "7.00")
        self.entrega("r", "2026-10-28", B, "8.00", time(11))
        antes = list(Entrega.objects.values())
        p = montar_dashboard()
        self.assertEqual([d["tentativas"] for d in p["diarios"]], [1, 1, 2])
        self.assertEqual([d["insucessos"] for d in p["diarios"]], [1, 1, 0])
        self.assertEqual([d["receita"] for d in p["diarios"]], [0, 0, 15])
        self.assertEqual([d["indicadores_principais"]["entregas_recuperadas"] for d in p["diarios"]], [1, 0, 0])
        for d in (p, *p["diarios"], *p["semanas"], *p["meses"]):
            self.assertEqual(d["indicadores_principais"]["insucessos_pendentes"], 0)
        self.assertEqual(p["semanas"][0]["media_receita_dia"], 5)
        self.assertEqual(list(Entrega.objects.values()), antes)

    def test_semana_recalcula_razao_e_nao_media_das_taxas_diarias(self):
        for dia, baixas, pendentes in [(26, 1, 5), (27, 3, 1)]:
            for i in range(baixas):
                self.entrega(f"b{dia}-{i}", f"2026-10-{dia}")
            for i in range(pendentes):
                self.entrega(f"p{dia}-{i}", f"2026-10-{dia}", I)
        p = montar_dashboard()
        self.assertEqual([d["indicadores_principais"]["taxa_sucesso_arredondada"] for d in p["diarios"]], [Decimal("16.67"), Decimal("75.00")])
        for linha in (p, *p["semanas"], *p["meses"]):
            self.assertEqual(linha["indicadores_principais"]["taxa_sucesso_arredondada"], Decimal("40.00"))
        self.assertEqual(p["semanas"][0]["media_receita_dia"], 10)

    def test_nova_media_monetaria_arredonda_so_apresentacao(self):
        for dia in range(25, 31):
            self.entrega(str(dia), f"2026-10-{dia}", B if dia == 25 else I, "1.00")
        p = montar_dashboard()
        for linha in (*p["semanas"], *p["meses"]):
            self.assertEqual(linha["media_receita_dia"], Decimal(1) / 6)
            self.assertEqual(linha["media_receita_dia_arredondada"], Decimal("0.17"))
        self.assertEqual(p["resumo"]["receita"], 1)
        self.assertIn("R$ 0,17", TabelasPainel(self.pagina().content.decode()).tabelas[1][1][2])

    def test_recuperacao_dia_semana_mes_seguinte_sem_deslocar_receita(self):
        for codigo, inicio, fim in [("dia", "2026-10-26", "2026-10-27"), ("semana", "2026-10-24", "2026-10-25"), ("mes", "2026-10-31", "2026-11-01")]:
            self.entrega(codigo, inicio, I)
            self.entrega(codigo, fim)
        p = montar_dashboard(FiltroPeriodo(date(2026, 10, 1), date(2026, 10, 31)))
        self.assertEqual((p["resumo"]["tentativas"], p["resumo"]["receita"]), (5, 10))
        self.assertEqual(p["indicadores_principais"]["entregas_recuperadas"], 3)
        self.assertEqual(p["conciliacao"]["recuperadas_apos_periodo"], 1)
        for d in [p, *p["diarios"], *p["semanas"], *p["meses"]]:
            self.assertEqual(d["indicadores_principais"]["insucessos_pendentes"], 0)
        self.assertEqual([s["rotulo"] for s in p["semanas"]], ["18/10/2026 a 24/10/2026", "25/10/2026 a 31/10/2026"])
        novembro = montar_dashboard(FiltroPeriodo(date(2026, 11, 1), date(2026, 11, 30)))
        self.assertEqual(novembro["resumo"]["receita"], 5)
        self.assertEqual(novembro["indicadores_principais"]["entregas_recuperadas"], 0)

    def test_pendencia_atribuida_uma_vez_ao_dia_inicial(self):
        self.entrega("p", "2026-10-31", I)
        self.entrega("p", "2026-11-01", I)
        p = montar_dashboard()
        self.assertEqual([d["indicadores_principais"]["insucessos_pendentes"] for d in p["diarios"]], [1, 0])
        for linhas in (p["semanas"], p["meses"]):
            self.assertEqual([d["indicadores_principais"]["insucessos_pendentes"] for d in linhas], [1, 0])
            self.assertEqual([d["indicadores_principais"]["taxa_sucesso"] for d in linhas], [0, None])

    def test_semana_transano_e_media_por_dias_com_registros(self):
        for i, dia in enumerate(["2026-12-27", "2026-12-31", "2027-01-01", "2027-01-02", "2027-01-03"]):
            self.entrega(str(i), dia, valor="6.00")
        self.entrega("i", "2027-01-01", I)
        Jornada.objects.create(data=date(2026, 12, 28), janela_historica=timedelta(hours=1))
        p = montar_dashboard()
        self.assertEqual([s["tentativas"] for s in p["semanas"]], [5, 1])
        self.assertEqual([s["receita"] for s in p["semanas"]], [24, 6])
        self.assertEqual([s["media_receita_dia"] for s in p["semanas"]], [6, 6])
        self.assertEqual([m["tentativas"] for m in p["meses"]], [2, 4])
        self.assertEqual(sum(s["tentativas"] for s in p["semanas"]), 6)

    def test_lote_recupera_mes_anterior_e_exclusao_reabre_tabelas(self):
        self.entrega("r", "2026-10-31", I)
        filtro = {"periodo": "mes", "mes": 10, "ano": 2026}
        self.assertEqual(self.pagina(filtro).context["dashboard"]["semanas"][0]["indicadores_principais"]["insucessos_pendentes"], 1)
        dados = {"chave": str(uuid4()), "data_padrao": "2026-11-01", "situacao_padrao": B, "linhas": json.dumps([{"codigo": "r", "horario": "11:00"}])}
        url = reverse("entregas:lote")
        previa = self.client.post(url, {**dados, "acao": "prever"})
        dados.update(acao="salvar", comprovante=previa.context["form"]["comprovante"].value())
        self.assertEqual(self.client.post(url, dados).status_code, 302)
        p = self.pagina(filtro).context["dashboard"]
        for d in [p, *p["diarios"], *p["semanas"], *p["meses"]]:
            self.assertEqual(d["indicadores_principais"]["insucessos_pendentes"], 0)
        self.assertEqual(p["resumo"]["receita"], 0)
        baixa = Entrega.objects.get(situacao=B)
        self.assertEqual(self.client.post(reverse("entregas:excluir", args=[baixa.pk])).status_code, 302)
        self.assertEqual(self.pagina(filtro).context["dashboard"]["meses"][0]["indicadores_principais"]["insucessos_pendentes"], 1)

    def test_tanque_cheio_zero_real_prioritario_e_consumo_ponderado(self):
        for dia in (26, 27):
            self.entrega(str(dia), f"2026-10-{dia}")
        Jornada.objects.create(data=date(2026, 10, 26), inicio_real=time(10), fim_real=time(12), janela_historica=timedelta(hours=8), odometro_inicial=0, odometro_final=100, litros_consumidos=2, custo_combustivel=Decimal("34.55"))
        Jornada.objects.create(data=date(2026, 10, 27), janela_historica=timedelta(hours=3), odometro_inicial=0, odometro_final=60, litros_consumidos=6, custo_combustivel=24)
        p = montar_dashboard()
        for d in (p["resumo"], *p["semanas"], *p["meses"]):
            self.assertEqual((d["horas"], d["km"], d["litros"], d["consumo_km_l"], d["combustivel"]), (5, 160, 8, 20, Decimal("58.55")))
            self.assertTrue(d["duracao_completa"])
            self.assertTrue(d["consumo_completo"])
            self.assertTrue(d["combustivel_completo"])
        self.assertEqual(p["resumo"]["horas_reais"], 2)
        self.assertEqual(p["resumo"]["horas_historicas"], 3)
        self.assertEqual([d["consumo_km_l"] for d in p["diarios"]], [50, 10])

    def test_cobertura_parcial_nao_mistura_litros_e_km_incompativeis(self):
        for dia in (26, 27, 28, 29):
            self.entrega(str(dia), f"2026-10-{dia}")
        Jornada.objects.create(data=date(2026, 10, 26), odometro_inicial=0, odometro_final=100, litros_consumidos=2, custo_combustivel=30, janela_historica=timedelta(hours=2))
        Jornada.objects.create(data=date(2026, 10, 27), odometro_inicial=0, odometro_final=60)
        Jornada.objects.create(data=date(2026, 10, 28), litros_consumidos=3)
        p = montar_dashboard()
        for d in (p["resumo"], *p["semanas"], *p["meses"]):
            self.assertEqual((d["km"], d["litros"], d["consumo_km_l"], d["combustivel"], d["horas"]), (160, 5, 50, 30, 2))
            for campo in ("km_completo", "litros_completo", "consumo_completo", "combustivel_completo", "duracao_completa"):
                self.assertFalse(d[campo], campo)
        self.assertIn("Parcial", self.pagina().content.decode())
        self.assertIsNone(p["diarios"][-1]["km"])
        self.assertIsNone(p["diarios"][-1]["consumo_km_l"])

    def test_horas_zero_e_litros_zero_nao_sao_ausencia_nem_divisao_por_zero(self):
        self.entrega("b", "2026-10-29")
        Jornada.objects.create(data=date(2026, 10, 29), inicio_real=time(12), fim_real=time(12), odometro_inicial=0, odometro_final=0, litros_consumidos=0, custo_combustivel=0)
        d = montar_dashboard()["diarios"][0]
        self.assertEqual((d["horas"], d["km"], d["litros"], d["combustivel"]), (0, 0, 0, 0))
        self.assertIsNone(d["consumo_km_l"])
        self.assertTrue(d["duracao_completa"])
