from datetime import date, time, timedelta
from decimal import Decimal
from django.test import TestCase
from entregas.models import Entrega
from jornadas.models import Jornada
from jornadas.services import calcular_jornada
from painel.dashboard import montar_dashboard


class JornadasCalculosTests(TestCase):
    def movimento(self, data=date(2026, 10, 19), quantidade=2):
        for _ in range(quantidade):
            Entrega.objects.create(data=data, codigo="duplicado", horario=time(12), situacao="Baixa realizada", valor_por_baixa=Decimal("5.00"))

    def test_real_prioritario_historico_nao_soma(self):
        j = Jornada.objects.create(data=date(2026, 10, 19), inicio_real=time(13, 57), fim_real=time(20, 30), janela_historica=timedelta(hours=3))
        resultado = calcular_jornada(j)
        self.assertEqual(resultado["horas"], Decimal("6.55"))
        self.assertEqual(resultado["origem_duracao"], "Real")

    def test_jornada_ultrapassa_meia_noite(self):
        j = Jornada.objects.create(data=date(2026, 10, 19), inicio_real=time(23, 30), fim_real=time(1, 15))
        self.assertEqual(calcular_jornada(j)["horas"], Decimal("1.75"))

    def test_horarios_iguais_nao_dividem_por_zero(self):
        self.movimento()
        Jornada.objects.create(data=date(2026, 10, 19), inicio_real=time(12), fim_real=time(12))
        p = montar_dashboard()["resumo"]
        self.assertEqual(p["horas"], 0)
        self.assertIsNone(p["baixas_por_hora"])
        self.assertIsNone(p["ganho_por_hora"])

    def test_par_real_incompleto_usa_janela_rotulada(self):
        j = Jornada.objects.create(data=date(2026, 10, 19), inicio_real=time(12), janela_historica=timedelta(hours=2))
        r = calcular_jornada(j)
        self.assertEqual(r["origem_duracao"], "Histórica")
        self.assertEqual(r["horas"], 2)
        self.assertTrue(r["horario_incompleto"])

    def test_dia_sem_horas_bloqueia_taxa_global(self):
        self.movimento()
        self.movimento(date(2026, 10, 20))
        Jornada.objects.create(data=date(2026, 10, 19), inicio_real=time(12), fim_real=time(13))
        p = montar_dashboard()["resumo"]
        self.assertEqual(p["horas_reais"], 1)
        self.assertFalse(p["duracao_completa"])
        self.assertIsNone(p["ganho_por_hora"])
        self.assertEqual(p["dias_sem_jornada"], [date(2026, 10, 20)])

    def test_origens_mistas_ficam_separadas(self):
        self.movimento()
        self.movimento(date(2026, 10, 20))
        Jornada.objects.create(data=date(2026, 10, 19), inicio_real=time(12), fim_real=time(14))
        Jornada.objects.create(data=date(2026, 10, 20), janela_historica=timedelta(hours=1))
        p = montar_dashboard()["resumo"]
        self.assertEqual(p["horas_reais"], 2)
        self.assertEqual(p["horas_historicas"], 1)
        self.assertEqual(p["horas"], 3)
        self.assertEqual(p["origem_duracao"], "Mista: real e histórica")
        self.assertEqual(p["baixas_por_hora"], Decimal(4) / 3)

    def test_consumo_nao_mistura_litros_de_jornada_sem_km(self):
        self.movimento()
        Jornada.objects.create(data=date(2026, 10, 19), odometro_inicial=0, odometro_final=Decimal("67.600"), litros_consumidos=Decimal("3.762"), custo_combustivel=Decimal("20.45"))
        Jornada.objects.create(data=date(2026, 10, 20), odometro_inicial=0, litros_consumidos=Decimal("2.093"), custo_combustivel=Decimal("13.54"))
        p = montar_dashboard()["resumo"]
        self.assertEqual(p["litros"], Decimal("5.855"))
        self.assertEqual(p["consumo_km_l"], Decimal("67.600") / Decimal("3.762"))
        self.assertEqual(p["custo_por_km"], Decimal("20.45") / Decimal("67.600"))
        self.assertEqual(p["jornadas_consumo"], 1)
        self.assertEqual(p["combustivel"], Decimal("33.99"))
        self.assertFalse(p["km_completo"])
        self.assertIsNone(p["resultado_liquido"])

    def test_ausencia_de_custos_nao_gera_lucro(self):
        self.movimento()
        Jornada.objects.create(data=date(2026, 10, 19))
        p = montar_dashboard()["resumo"]
        self.assertIsNone(p["custos_conhecidos"])
        self.assertIsNone(p["resultado_parcial"])
        self.assertIsNone(p["resultado_liquido"])

    def test_custo_parcial_e_zero_explicito_com_resultado_completo(self):
        self.movimento()
        j = Jornada.objects.create(data=date(2026, 10, 19), custo_combustivel=Decimal("2.50"))
        p = montar_dashboard()["resumo"]
        self.assertEqual(p["resultado_parcial"], Decimal("7.50"))
        self.assertIsNone(p["resultado_liquido"])
        j.outros_custos = Decimal(0)
        j.save()
        p = montar_dashboard()["resumo"]
        self.assertTrue(p["custos_completos"])
        self.assertEqual(p["resultado_liquido"], Decimal("7.50"))
        self.assertEqual(p["margem_liquida"], Decimal("75"))

    def test_mesma_data_varias_jornadas_nao_duplica_receita_por_km(self):
        self.movimento()
        for _ in range(2):
            Jornada.objects.create(data=date(2026, 10, 19), odometro_inicial=0, odometro_final=10, litros_consumidos=1, custo_combustivel=1, outros_custos=0)
        p = montar_dashboard()["resumo"]
        self.assertEqual(p["km"], 20)
        self.assertEqual(p["receita_por_km"], Decimal("0.5"))
        self.assertEqual(p["custo_por_tentativa"], Decimal(1))

    def test_litros_zero_e_km_ausente_nao_criam_consumo(self):
        self.movimento()
        Jornada.objects.create(data=date(2026, 10, 19), odometro_inicial=0, litros_consumidos=0)
        p = montar_dashboard()["resumo"]
        self.assertIsNone(p["km"])
        self.assertIsNone(p["consumo_km_l"])
        self.assertIsNone(p["custo_por_km"])
        self.assertIsNone(p["receita_por_km"])
