from datetime import date, time
from decimal import Decimal
from types import SimpleNamespace
from django.test import SimpleTestCase, TestCase
from core.periodos import FiltroPeriodo, periodo_mes, periodo_quinzena, periodo_semana
from entregas.services.indicadores import intervalos_entregas
from painel.forms import FiltroPainelForm
from painel.metas import acompanhar_meta, projetar
from painel.dashboard import montar_dashboard
from entregas.models import Entrega
from painel.models import Configuracao


class PeriodosTests(SimpleTestCase):
    def test_quinzenas_fevereiro_e_meses_30_31_dias(self):
        for ano, mes, ultimo in [(2024, 2, 29), (2026, 2, 28), (2026, 4, 30), (2026, 10, 31), (2026, 12, 31)]:
            with self.subTest(ano=ano, mes=mes):
                self.assertEqual(periodo_quinzena(date(ano, mes, 15)), (date(ano, mes, 1), date(ano, mes, 15)))
                self.assertEqual(periodo_quinzena(date(ano, mes, 16)), (date(ano, mes, 16), date(ano, mes, ultimo)))
                self.assertEqual(periodo_mes(ano, mes)[1].day, ultimo)

    def test_semana_civil_pode_atravessar_ano(self):
        self.assertEqual(periodo_semana(date(2021, 1, 1)), (date(2020, 12, 27), date(2021, 1, 2)))

    def test_todos_os_filtros_resolvem_periodo(self):
        casos = [
            ({"periodo": "todos"}, (None, None)),
            ({"periodo": "dia", "dia": "2026-10-15"}, (date(2026, 10, 15), date(2026, 10, 15))),
            ({"periodo": "intervalo", "inicio": "2026-10-15", "fim": "2026-10-20"}, (date(2026, 10, 15), date(2026, 10, 20))),
            ({"periodo": "semana", "semana": "2026-10-19"}, (date(2026, 10, 18), date(2026, 10, 24))),
            ({"periodo": "mes", "mes": 2, "ano": 2024}, (date(2024, 2, 1), date(2024, 2, 29))),
            ({"periodo": "quinzena", "mes": 10, "ano": 2026, "quinzena": "2"}, (date(2026, 10, 16), date(2026, 10, 31))),
        ]
        for dados, esperado in casos:
            with self.subTest(dados=dados):
                form = FiltroPainelForm(dados)
                self.assertTrue(form.is_valid(), form.errors)
                filtro = form.cleaned_data["filtro"]
                self.assertEqual((filtro.inicio, filtro.fim), esperado)

    def test_filtros_invalidos_nao_inventam_periodo(self):
        casos = [
            {"periodo": "dia"}, {"periodo": "quinzena", "mes": 10, "ano": 2026},
            {"periodo": "intervalo", "inicio": "2026-10-20", "fim": "2026-10-15"},
            {"periodo": "semana", "semana": "2026-W54"},
            {"periodo": "semana", "semana": "2026-43"},
            {"periodo": "mes", "mes": 13, "ano": 2026},
            {"dias_projecao": 0}, {"periodo": "dia", "dia": "2026-02-29"},
        ]
        for dados in casos:
            with self.subTest(dados=dados):
                self.assertFalse(FiltroPainelForm(dados).is_valid())

    def test_intervalos_ordenados_sem_misturar_datas_ou_duplicar_horarios(self):
        registros = [SimpleNamespace(data=date(2026, 10, dia), horario=hora) for dia, hora in [
            (15, time(13)), (15, time(12)), (15, time(12, 30)),
            (15, time(12, 30)), (16, time(23)), (16, None),
        ]]
        resultado = intervalos_entregas(registros)
        self.assertEqual(resultado["intervalos_quantidade"], 2)
        self.assertEqual(resultado["intervalo_medio_segundos"], Decimal(1800))

    def test_intervalo_ausente_com_um_horario_por_dia(self):
        registros = [SimpleNamespace(data=date(2026, 10, d), horario=time(12)) for d in [15, 16]]
        self.assertIsNone(intervalos_entregas(registros)["intervalo_medio_segundos"])

    def test_metas_sem_divisao_por_zero_e_projecao_condicional(self):
        self.assertIsNone(acompanhar_meta(Decimal("10"), Decimal("0"))["percentual_meta"])
        self.assertEqual(acompanhar_meta(Decimal("350"), Decimal("300"))["faltante_meta"], 0)
        resultado = projetar(Decimal("770.00"), 4, 5)
        self.assertEqual(resultado["media_receita_dia"], Decimal("192.50"))
        self.assertEqual(resultado["receita_cenario"], Decimal("962.50"))
        self.assertIsNone(projetar(Decimal(0), 0, 5)["receita_cenario"])


class IndicadoresBancoTests(TestCase):
    def criar(self, data, situacao="Baixa realizada", valor="5.00", codigo="repetido"):
        return Entrega.objects.create(data=data, horario=time(12), codigo=codigo, situacao=situacao, valor_por_baixa=Decimal(valor))

    def test_agregacao_semana_mes_ano_e_codigos_repetidos(self):
        self.criar(date(2026, 10, 15))
        self.criar(date(2026, 10, 16), "Insucesso")
        self.criar(date(2026, 10, 19), valor="6.50")
        self.criar(date(2026, 11, 1), valor="7.00")
        p = montar_dashboard()
        self.assertEqual(p["resumo"]["tentativas"], 4)
        self.assertEqual(p["resumo"]["baixas"], 3)
        self.assertEqual(p["resumo"]["receita"], Decimal("18.50"))
        self.assertEqual([m["receita"] for m in p["meses"]], [Decimal("11.50"), Decimal("7.00")])
        self.assertEqual(p["semanas"][0]["tentativas"], 2)
        self.assertEqual(p["resumo"]["sucesso_percentual"], Decimal("75"))
        self.assertIsNone(p["resumo"]["ganho_por_hora"])

    def test_preco_historico_e_meta_da_versao_atual(self):
        antiga = self.criar(date(2026, 10, 15))
        configuracao = Configuracao.objects.create(valor_por_baixa=Decimal("8.00"), meta_diaria=Decimal("400.00"))
        Entrega.objects.create(data=date(2026, 10, 16), horario=time(12), codigo="novo", situacao="Baixa realizada")
        p = montar_dashboard()
        antiga.refresh_from_db()
        self.assertEqual(p["resumo"]["receita"], Decimal("13.00"))
        self.assertEqual(antiga.valor_por_baixa, Decimal("5.00"))
        self.assertEqual(p["configuracao"].pk, configuracao.pk)
        self.assertEqual(p["diarios"][0]["meta"], Decimal("400.00"))

    def test_recorte_filtra_todas_as_series_e_melhor_dia(self):
        self.criar(date(2026, 10, 15))
        self.criar(date(2026, 10, 20), valor="8.00")
        p = montar_dashboard(FiltroPeriodo(date(2026, 10, 20), date(2026, 10, 20)))
        self.assertEqual(p["resumo"]["receita"], Decimal("8.00"))
        self.assertEqual(p["resumo"]["melhores_dias"], [date(2026, 10, 20)])
        self.assertEqual(p["semanas"][0]["receita"], Decimal("8.00"))
        self.assertEqual(p["meses"][0]["receita"], Decimal("8.00"))
        self.assertTrue(p["semanas"][0]["recorte_parcial"])
        self.assertEqual(p["graficos"][1]["series"][0]["valores"], [Decimal("8.00")])

    def test_periodo_vazio_nao_gera_taxas_ou_projecao(self):
        p = montar_dashboard()
        self.assertFalse(p["tem_dados"])
        for campo in ["sucesso_percentual", "media_diaria_baixas", "intervalo_medio_segundos", "baixas_por_hora", "ganho_por_hora", "ganho_medio_baixa", "consumo_km_l", "resultado_liquido"]:
            self.assertIsNone(p["resumo"][campo], campo)
        self.assertIsNone(p["projecao"]["receita_cenario"])
        self.assertTrue(all(not g["rotulos"] for g in p["graficos"]))
