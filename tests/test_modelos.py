from datetime import date, time, timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from conferencia.forms import EspelhoForm, PagamentoForm
from conferencia.models import EspelhoEmpresa, Pagamento
from entregas.forms import EntregaForm
from entregas.models import Entrega
from jornadas.forms import JornadaForm
from jornadas.models import Jornada
from painel.models import Configuracao
from painel.services import resumo_entregas


class ModelosTests(TestCase):
    def entrega(self, **campos):
        dados = dict(codigo="00123", data=date(2026, 10, 15), horario=time(12), situacao=Entrega.Situacao.BAIXA)
        return Entrega.objects.create(**{**dados, **campos})

    def test_codigo_repetido_mesmo_dia_e_permitido(self):
        um, dois = self.entrega(), self.entrega()
        self.assertNotEqual(um.pk, dois.pk)
        self.assertEqual(um.codigo, "00123")

    def test_situacao_invalida_rejeitada_no_modelo_e_banco(self):
        registro = self.entrega()
        registro.situacao = "Outra"
        with self.assertRaises(ValidationError):
            registro.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            registro.save()

    def test_preco_historico_nao_muda_com_configuracao(self):
        antiga = self.entrega()
        Configuracao.objects.create(valor_por_baixa=Decimal("6.50"))
        nova = self.entrega()
        antiga.refresh_from_db()
        self.assertEqual(antiga.valor_previsto, Decimal("5.00"))
        self.assertEqual(nova.valor_previsto, Decimal("6.50"))
        self.assertEqual(resumo_entregas()["receita"], Decimal("11.50"))

    def test_insucesso_nao_gera_receita(self):
        self.assertEqual(self.entrega(situacao=Entrega.Situacao.INSUCESSO).valor_previsto, Decimal("0.00"))

    def test_configuracao_cria_versoes_e_impede_edicao_da_antiga(self):
        atual = Configuracao.atual()
        atual.meta_diaria = Decimal("400.00")
        with self.assertRaises(ValueError):
            atual.save()
        self.assertEqual(Configuracao.atual().meta_diaria, Decimal("300.00"))

    def test_valores_negativos_sao_invalidos(self):
        objetos = [
            Configuracao(meta_diaria=Decimal("-1")),
            Jornada(data=date.today(), custo_combustivel=Decimal("-0.01")),
            EspelhoEmpresa(data_competencia=date.today(), valor_empresa=Decimal("-1")),
            Pagamento(data_pagamento=date.today(), inicio_quinzena=date.today(), fim_quinzena=date.today(), valor_recebido=Decimal("-1")),
        ]
        for objeto in objetos:
            with self.subTest(modelo=type(objeto).__name__), self.assertRaises(ValidationError):
                objeto.full_clean()

    def test_jornada_vazia_preserva_nulos_e_zero_explicito(self):
        jornada = Jornada.objects.create(data=date(2026, 10, 20), odometro_inicial=0, custo_combustivel=Decimal("13.54"))
        jornada.refresh_from_db()
        self.assertIsNone(jornada.odometro_final)
        self.assertIsNone(jornada.quilometragem)
        self.assertIsNone(jornada.outros_custos)
        self.assertIsNone(jornada.inicio_real)
        self.assertEqual(jornada.odometro_inicial, Decimal("0.000"))

    def test_odometros_invertidos_e_duracao_negativa_invalidos(self):
        for campos in [dict(odometro_inicial=10, odometro_final=9), dict(janela_historica=timedelta(seconds=-1))]:
            with self.subTest(campos=campos), self.assertRaises(ValidationError):
                Jornada(data=date.today(), **campos).full_clean()

    def test_pagamento_periodo_invertido_invalido(self):
        form = PagamentoForm(data={"data_pagamento": "2026-10-21", "inicio_quinzena": "2026-10-16", "fim_quinzena": "2026-10-15", "valor_recebido": "160,00"})
        self.assertFalse(form.is_valid())
        self.assertIn("fim_quinzena", form.errors)

    def test_multiplos_espelhos_por_competencia(self):
        for _ in range(2):
            EspelhoEmpresa.objects.create(data_competencia=date(2026, 10, 15))
        self.assertEqual(EspelhoEmpresa.objects.count(), 2)

    def test_formularios_aceitam_decimal_brasileiro_e_brancos(self):
        form = JornadaForm(data={"data": "2026-10-20", "custo_combustivel": "1.234,56", "odometro_inicial": "0", "litros_consumidos": "3,762"})
        self.assertTrue(form.is_valid(), form.errors)
        jornada = form.save()
        self.assertEqual(jornada.custo_combustivel, Decimal("1234.56"))
        self.assertEqual(jornada.litros_consumidos, Decimal("3.762"))
        self.assertIsNone(jornada.outros_custos)
        espelho = EspelhoForm(data={"data_competencia": "2026-10-15"})
        self.assertTrue(espelho.is_valid(), espelho.errors)
        self.assertIsNone(espelho.save().valor_empresa)

    def test_entrega_campos_obrigatorios(self):
        form = EntregaForm(data={"codigo": "001"})
        self.assertFalse(form.is_valid())
        self.assertEqual(set(form.errors), {"data", "situacao"})
