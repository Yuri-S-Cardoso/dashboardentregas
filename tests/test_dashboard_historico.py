from datetime import date
from decimal import Decimal
from unittest import skipUnless
from django.test import TestCase
from core.periodos import FiltroPeriodo
from entregas.services.importacao import importar_excel
from painel.dashboard import montar_dashboard
from .test_importacao import EXCEL_REAL


@skipUnless(EXCEL_REAL.exists(), "Excel privado necessário para as referências históricas da etapa 02.")
class DashboardHistoricoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        importar_excel(EXCEL_REAL)

    def test_totais_indicadores_e_intervalos_historicos(self):
        p = montar_dashboard()
        r = p["resumo"]
        self.assertEqual((r["tentativas"], r["baixas"], r["insucessos"], r["receita"]), (169, 154, 15, Decimal("770.00")))
        self.assertEqual(r["sucesso_percentual"], Decimal(15400) / 169)
        self.assertEqual(r["media_diaria_baixas"], Decimal("38.5"))
        self.assertEqual(r["melhores_dias"], [date(2026, 10, 16)])
        self.assertEqual(r["intervalos_quantidade"], 165)
        self.assertEqual(r["intervalo_medio_segundos"], Decimal(56146) / 165)
        self.assertEqual(p["projecao"]["receita_cenario"], Decimal("962.50"))

    def test_quinzenas_historicas_exatamente_como_solicitado(self):
        primeira, segunda = montar_dashboard()["quinzenas"]
        self.assertEqual(primeira["status"], "Conferido")
        self.assertEqual(primeira["diferenca"], Decimal("0.00"))
        self.assertEqual((primeira["baixas"], primeira["insucessos"], primeira["valor_empresa"]), (32, 1, Decimal("160.00")))
        self.assertEqual((segunda["tentativas"], segunda["baixas"], segunda["insucessos"], segunda["receita"]), (136, 122, 14, Decimal("610.00")))
        self.assertEqual(segunda["status"], "Aguardando espelho")
        self.assertIsNone(segunda["diferenca"])
        self.assertIsNone(segunda["saldo"])
        self.assertEqual(segunda["status_pagamento"], "Sem pagamento registrado")

    def test_jornadas_historicas_e_lucro_parcial(self):
        p = montar_dashboard()
        dias = {d["data"].day: d for d in p["diarios"]}
        self.assertEqual(dias[19]["horas"], Decimal("6.55"))
        self.assertEqual(dias[20]["horas"], Decimal("9.2"))
        self.assertEqual(dias[19]["km"], Decimal("67.600"))
        self.assertIsNone(dias[20]["km"])
        self.assertIsNone(dias[20]["consumo_km_l"])
        self.assertEqual(dias[19]["resultado_parcial"], Decimal("149.55"))
        self.assertEqual(dias[20]["resultado_parcial"], Decimal("186.46"))
        self.assertEqual(p["resumo"]["horas_reais"], Decimal("15.75"))
        self.assertEqual(p["resumo"]["resultado_parcial"], Decimal("736.01"))
        self.assertIsNone(p["resumo"]["resultado_liquido"])
        self.assertEqual(p["resumo"]["consumo_km_l"], Decimal("67.600") / Decimal("3.762"))

    def test_semanas_mes_e_graficos_usam_recorte(self):
        p = montar_dashboard()
        self.assertEqual([s["receita"] for s in p["semanas"]], [Decimal("400.00"), Decimal("370.00")])
        self.assertEqual(p["meses"][0]["receita"], Decimal("770.00"))
        self.assertEqual(p["meses"][0]["percentual_meta"], Decimal(77000) / 6000)
        p = montar_dashboard(FiltroPeriodo(date(2026, 10, 16), date(2026, 10, 31)))
        self.assertEqual(p["resumo"]["receita"], Decimal("610.00"))
        self.assertEqual(p["graficos"][1]["series"][0]["valores"], [Decimal("240.00"), Decimal("170.00"), Decimal("200.00")])
        self.assertEqual(p["graficos"][5]["series"][1]["valores"], [None, Decimal("20.45"), Decimal("13.54")])
