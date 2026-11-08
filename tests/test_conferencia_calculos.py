from datetime import date, time
from decimal import Decimal
from django.test import TestCase
from conferencia.models import EspelhoEmpresa, Pagamento
from conferencia.services import detectar_duplicidades
from core.periodos import FiltroPeriodo
from entregas.models import Entrega
from painel.dashboard import montar_dashboard


class ConferenciaCalculosTests(TestCase):
    def setUp(self):
        self.data = date(2026, 10, 15)
        for situacao in ["Baixa realizada", "Baixa realizada", "Insucesso"]:
            Entrega.objects.create(data=self.data, horario=time(12), codigo="mesmo", situacao=situacao, valor_por_baixa=Decimal("5.00"))

    def espelho(self, **dados):
        padrao = dict(data_competencia=self.data, baixas_pagas=2, insucessos=1, valor_empresa=Decimal("10.00"), documento="OS 1")
        return EspelhoEmpresa.objects.create(**{**padrao, **dados})

    def pagamento(self, valor, **dados):
        padrao = dict(data_pagamento=date(2026, 11, 1), inicio_quinzena=date(2026, 10, 1), fim_quinzena=date(2026, 10, 15), valor_recebido=Decimal(valor))
        return Pagamento.objects.create(**{**padrao, **dados})

    def test_conferencia_exata(self):
        self.espelho()
        dia = montar_dashboard()["auditoria"][0]
        self.assertEqual(dia["status"], "Conferido")
        self.assertEqual(dia["diferenca"], Decimal("0.00"))
        self.assertEqual(dia["diferenca_baixas"], 0)
        self.assertEqual(dia["diferenca_insucessos"], 0)

    def test_diferencas_quantidade_valor_e_ambas(self):
        registro = self.espelho()
        casos = [(1, 10, "Divergência de quantidade"), (2, 9, "Divergência de valor"), (1, 9, "Divergência de quantidade e valor")]
        for baixas, valor, status in casos:
            registro.baixas_pagas = baixas
            registro.valor_empresa = valor
            registro.save()
            dia = montar_dashboard()["auditoria"][0]
            self.assertEqual(dia["status"], status)
            self.assertEqual(dia["diferenca"], Decimal(10 - valor))
            self.assertEqual(dia["diferenca_baixas"], 2 - baixas)

    def test_sem_espelho_nao_gera_divergencia_ou_prejuizo(self):
        p = montar_dashboard()
        dia, quinzena = p["auditoria"][0], p["quinzenas"][0]
        self.assertEqual(dia["status"], "Aguardando espelho")
        self.assertIsNone(dia["diferenca"])
        self.assertIsNone(quinzena["diferenca"])
        self.assertIsNone(quinzena["saldo"])
        self.assertEqual(quinzena["status_pagamento"], "Sem pagamento registrado")

    def test_documentos_distintos_sao_agregados(self):
        self.espelho(baixas_pagas=1, insucessos=1, valor_empresa=5, documento="A")
        self.espelho(baixas_pagas=1, insucessos=0, valor_empresa=5, documento="B")
        dia = montar_dashboard()["auditoria"][0]
        self.assertEqual(dia["status"], "Conferido")
        self.assertEqual(dia["baixas_empresa"], 2)
        self.assertEqual(dia["valor_empresa"], Decimal("10.00"))
        self.assertEqual(len(dia["documentos"]), 2)

    def test_duplicidade_documental_normalizada_exige_revisao_sem_excluir(self):
        self.espelho(documento="  OS   1 ")
        self.espelho(documento="os 1")
        p = montar_dashboard()
        dia = p["auditoria"][0]
        self.assertEqual(dia["status"], "Revisar possível duplicidade")
        self.assertEqual(dia["valor_empresa_conhecido"], Decimal("20.00"))
        self.assertIsNone(dia["diferenca"])
        self.assertFalse(dia["confrontavel"])
        self.assertEqual(EspelhoEmpresa.objects.count(), 2)
        self.assertIsNone(p["quinzenas"][0]["saldo"])

    def test_documentos_vazios_identicos_alertam_mas_referencia_distinta_nao(self):
        self.espelho(documento="")
        self.espelho(documento="")
        self.assertTrue(montar_dashboard()["auditoria"][0]["duplicidades"])

    def test_mesmo_documento_em_competencias_distintas_nao_e_duplicado(self):
        primeiro = self.espelho()
        segundo = self.espelho(data_competencia=date(2026, 10, 16))
        self.assertEqual(detectar_duplicidades([primeiro, segundo]), [])

    def test_espelho_incompleto_preserva_valor_parcial_sem_confrontar(self):
        self.espelho()
        self.espelho(documento="OS 2", baixas_pagas=None, insucessos=0, valor_empresa=None)
        dia = montar_dashboard()["auditoria"][0]
        self.assertEqual(dia["status"], "Espelho incompleto")
        self.assertIsNone(dia["valor_empresa"])
        self.assertEqual(dia["valor_empresa_conhecido"], Decimal("10.00"))
        self.assertIsNone(dia["diferenca"])

    def test_espelho_sem_entregas_nao_e_conferido(self):
        self.espelho(data_competencia=date(2026, 10, 16))
        dia = montar_dashboard()["auditoria"][1]
        self.assertEqual(dia["status"], "Espelho sem entregas registradas")
        self.assertIsNone(dia["diferenca"])

    def test_quinzena_parcial_so_soma_diferencas_confrontaveis(self):
        self.espelho(valor_empresa=9)
        Entrega.objects.create(data=date(2026, 10, 14), horario=time(12), codigo="sem espelho", situacao="Baixa realizada", valor_por_baixa=Decimal("5.00"))
        q = montar_dashboard()["quinzenas"][0]
        self.assertEqual(q["receita"], Decimal("15.00"))
        self.assertEqual(q["diferenca"], Decimal("1.00"))
        self.assertEqual(q["datas_sem_espelho"], [date(2026, 10, 14)])
        self.assertEqual(q["datas_divergentes"], [self.data])
        self.assertFalse(q["informado_completo"])

    def test_pagamento_parcial_somado_por_competencia_mesmo_pago_outro_mes(self):
        self.espelho()
        self.pagamento("4.00")
        self.pagamento("3.00")
        q = montar_dashboard(FiltroPeriodo(date(2026, 10, 1), date(2026, 10, 15)))["quinzenas"][0]
        self.assertEqual(q["recebido"], Decimal("7.00"))
        self.assertEqual(q["saldo"], Decimal("3.00"))
        self.assertEqual(q["status_pagamento"], "Pagamento parcial")

    def test_pagamento_total_e_acima_do_informado(self):
        self.espelho()
        registro = self.pagamento("10.00")
        self.assertEqual(montar_dashboard()["quinzenas"][0]["status_pagamento"], "Pagamento conferido")
        registro.valor_recebido = Decimal("11.00")
        registro.save()
        q = montar_dashboard()["quinzenas"][0]
        self.assertEqual(q["saldo"], Decimal("-1.00"))
        self.assertEqual(q["status_pagamento"], "Recebido acima do informado")

    def test_zero_registrado_nao_se_confunde_com_ausencia(self):
        self.espelho()
        self.pagamento("0.00")
        q = montar_dashboard()["quinzenas"][0]
        self.assertEqual(q["recebido"], Decimal("0.00"))
        self.assertEqual(q["saldo"], Decimal("10.00"))
        self.assertEqual(q["status_pagamento"], "Pagamento parcial")

    def test_recorte_diario_nao_subtrai_pagamento_integral_de_base_parcial(self):
        self.espelho()
        self.pagamento("4.00")
        q = montar_dashboard(FiltroPeriodo(self.data, self.data))["quinzenas"][0]
        self.assertTrue(q["recorte_parcial"])
        self.assertEqual(q["recebido"], Decimal("4.00"))
        self.assertIsNone(q["saldo"])

    def test_pagamento_sem_espelho_nao_comprova_saldo(self):
        self.pagamento("4.00")
        q = montar_dashboard()["quinzenas"][0]
        self.assertIsNone(q["saldo"])
        self.assertIn("depende da conferência", q["status_pagamento"])

    def test_pagamento_fora_do_padrao_nao_e_rateado_automaticamente(self):
        self.pagamento("10.00", fim_quinzena=date(2026, 10, 31))
        p = montar_dashboard()
        self.assertEqual(len(p["pagamentos_sem_vinculo"]), 1)
        self.assertIsNone(p["quinzenas"][0]["recebido"])
