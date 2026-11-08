"""Reconsulta do painel após operações reais de cadastro, lote, edição e exclusão."""
from datetime import date, time
from decimal import Decimal
from html.parser import HTMLParser
import json
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from entregas.models import Entrega
from painel.models import Configuracao

BAIXA = "Baixa realizada"
INSUCESSO = "Insucesso"


class CardsEncomendas(HTMLParser):
    """Lê os resultados apresentados ao operador, sem capturar formulários."""
    def __init__(self, html):
        super().__init__()
        self.nivel = 0
        self.campo = None
        self.card = {}
        self.cards = {}
        self.auditoria_recolhida = False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "details" and attrs.get("id") == "auditoria-operacional":
            self.auditoria_recolhida = "open" not in attrs
        if tag == "div" and attrs.get("id") == "indicadores-encomendas":
            self.nivel = 1
        elif self.nivel and tag == "div":
            self.nivel += 1
        if self.nivel and tag == "article":
            self.card = {"titulo": "", "valor": ""}
        if self.nivel and tag in ("h3", "strong"):
            self.campo = "titulo" if tag == "h3" else "valor"

    def handle_data(self, data):
        if self.nivel and self.campo:
            self.card[self.campo] += data

    def handle_endtag(self, tag):
        if self.nivel and tag == "article":
            self.cards[self.card["titulo"].strip()] = self.card["valor"].strip()
        if tag in ("h3", "strong"):
            self.campo = None
        if self.nivel and tag == "div":
            self.nivel -= 1


class DashboardSituacaoRealTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(username="situacao_real_teste")

    def setUp(self):
        self.client.force_login(self.usuario)

    def criar(self, codigo="000123", dia="2026-10-20", situacao=INSUCESSO, horario=time(10), valor="3.00"):
        return Entrega.objects.create(codigo=codigo, data=date.fromisoformat(dia), horario=horario,
                                      situacao=situacao, valor_por_baixa=Decimal(valor))

    def painel(self, parametros=None, **headers):
        resposta = self.client.get(reverse("painel:inicio"), parametros or {"periodo": "todos"}, **headers)
        self.assertEqual(resposta.status_code, 200)
        c = resposta.context["dashboard"]["conciliacao"]
        self.assertEqual(c["entregas_identificadas"], c["concluidas"] + c["insucessos_reais"])
        self.assertEqual(c["com_insucesso"], c["recuperadas"] + c["insucessos_reais"])
        self.assertIn("no-store", resposta["Cache-Control"])
        return resposta, c

    def totais(self, esperado, parametros=None):
        resposta, c = self.painel(parametros)
        campos = ("entregas_identificadas", "concluidas", "com_insucesso", "insucessos_reais", "recuperadas")
        self.assertEqual(tuple(c[campo] for campo in campos), esperado)
        return resposta

    def cadastrar_baixa(self, dia="2026-10-21", codigo="000123"):
        resposta = self.client.post(reverse("entregas:nova"), {
            "codigo": codigo, "data": dia, "horario": "11:00:00", "situacao": BAIXA,
        })
        self.assertEqual(resposta.status_code, 302)
        return Entrega.objects.order_by("pk").last()

    def test_cards_priorizam_seis_indicadores_e_tres_faturamentos(self):
        self.criar()
        resposta = self.totais((1, 0, 1, 1, 0))
        cards = CardsEncomendas(resposta.content.decode())
        self.assertEqual(cards.cards, {"Total de encomendas": "1", "Entregas concluídas": "0",
                                     "Total com insucesso": "1", "Insucessos pendentes": "1",
                                     "Entregas recuperadas": "0", "Taxa de Sucesso": "0,00%",
                                     "Faturamento Mensal": "R$ 0,00", "Faturamento 1ª Quinzena": "R$ 0,00",
                                     "Faturamento 2ª Quinzena": "R$ 0,00"})
        self.assertTrue(cards.auditoria_recolhida)
        antes_auditoria = resposta.content.decode().split('id="auditoria-operacional"')[0]
        self.assertNotIn("<h3>Sucesso por tentativa</h3>", antes_auditoria)
        self.assertNotIn("<h3>Ocorrências de baixa</h3>", antes_auditoria)
        self.assertNotContains(resposta, "Finanças do período")
        self.assertContains(resposta, "Jornada e Custos")

    def test_cadastro_individual_resolve_pendente_na_proxima_consulta(self):
        falha = self.criar()
        original = Entrega.objects.values().get(pk=falha.pk)
        resposta_anterior = self.totais((1, 0, 1, 1, 0))
        self.cadastrar_baixa()
        resposta = self.totais((1, 1, 1, 0, 1))
        self.assertEqual(Entrega.objects.values().get(pk=falha.pk), original)
        self.assertEqual(Entrega.objects.count(), 2)
        self.assertEqual(resposta_anterior.context["dashboard"]["conciliacao"]["concluidas"], 0)
        self.assertEqual(CardsEncomendas(resposta.content.decode()).cards["Taxa de Sucesso"], "100,00%")

    def test_dois_insucessos_e_baixa_nao_duplicam_total_com_insucesso(self):
        self.criar()
        self.criar(dia="2026-10-21")
        self.totais((1, 0, 1, 1, 0))
        self.cadastrar_baixa("2026-10-22")
        resposta = self.totais((1, 1, 1, 0, 1))
        self.assertEqual(resposta.context["resumo"]["insucessos"], 2)

    def test_cadastro_em_lote_recalcula_apos_confirmacao_e_reenvio(self):
        self.criar()
        self.totais((1, 0, 1, 1, 0))
        dados = {"chave": str(uuid4()), "data_padrao": "2026-10-21", "situacao_padrao": BAIXA,
                 "linhas": json.dumps([{"codigo": "000123", "horario": "11:00"}])}
        previa = self.client.post(reverse("entregas:lote"), {**dados, "acao": "prever"})
        self.assertEqual(previa.status_code, 200)
        self.totais((1, 0, 1, 1, 0))
        dados.update(acao="salvar", comprovante=previa.context["form"]["comprovante"].value())
        for _ in range(2):
            self.assertEqual(self.client.post(reverse("entregas:lote"), dados).status_code, 302)
            self.totais((1, 1, 1, 0, 1))
            self.assertEqual(Entrega.objects.count(), 2)

    def test_exclusao_da_baixa_reabre_pendente_sem_cache(self):
        falha = self.criar()
        baixa = self.cadastrar_baixa()
        self.totais((1, 1, 1, 0, 1))
        self.assertEqual(self.client.post(reverse("entregas:excluir", args=[baixa.pk])).status_code, 302)
        self.totais((1, 0, 1, 1, 0))
        self.assertTrue(Entrega.objects.filter(pk=falha.pk, situacao=INSUCESSO).exists())

    def test_edicao_da_situacao_da_baixa_reabre_pendente(self):
        self.criar()
        baixa = self.cadastrar_baixa()
        self.totais((1, 1, 1, 0, 1))
        resposta = self.client.post(reverse("entregas:editar", args=[baixa.pk]), {
            "codigo": baixa.codigo, "data": "2026-10-21", "horario": "11:00", "situacao": INSUCESSO})
        self.assertEqual(resposta.status_code, 302)
        self.totais((1, 0, 1, 1, 0))

    def test_edicao_do_codigo_da_baixa_recalcula_as_duas_encomendas(self):
        self.criar()
        baixa = self.cadastrar_baixa()
        self.totais((1, 1, 1, 0, 1))
        resposta = self.client.post(reverse("entregas:editar", args=[baixa.pk]), {
            "codigo": "outra", "data": "2026-10-21", "horario": "11:00", "situacao": BAIXA})
        self.assertEqual(resposta.status_code, 302)
        self.totais((2, 1, 1, 1, 0))

    def test_edicao_da_data_para_antes_do_insucesso_exige_revisao(self):
        self.criar()
        baixa = self.cadastrar_baixa()
        self.totais((1, 1, 1, 0, 1))
        resposta = self.client.post(reverse("entregas:editar", args=[baixa.pk]), {
            "codigo": baixa.codigo, "data": "2026-10-19", "horario": "11:00", "situacao": BAIXA})
        self.assertEqual(resposta.status_code, 302)
        resposta = self.totais((0, 0, 0, 0, 0))
        self.assertEqual(resposta.context["dashboard"]["conciliacao"]["codigos_em_revisao"], 1)
        self.assertContains(resposta, "Necessita revisão")

    def test_exclusao_do_insucesso_remove_so_classificacao_de_recuperada(self):
        falha = self.criar()
        self.cadastrar_baixa()
        self.totais((1, 1, 1, 0, 1))
        self.assertEqual(self.client.post(reverse("entregas:excluir", args=[falha.pk])).status_code, 302)
        self.totais((1, 1, 0, 0, 0))

    def test_filtros_incluem_baixa_em_outra_quinzena_e_mes(self):
        self.criar(dia="2026-10-15")
        parametros = [
            {"periodo": "todos"}, {"periodo": "dia", "dia": "2026-10-15"},
            {"periodo": "semana", "semana": "2026-10-15"},
            {"periodo": "mes", "mes": 10, "ano": 2026},
            {"periodo": "quinzena", "mes": 10, "ano": 2026, "quinzena": 1},
            {"periodo": "intervalo", "inicio": "2026-10-14", "fim": "2026-10-15"},
        ]
        for params in parametros:
            self.totais((1, 0, 1, 1, 0), params)
        self.cadastrar_baixa("2026-11-01")
        for params in parametros:
            with self.subTest(params=params):
                resposta = self.totais((1, 1, 1, 0, 1), params)
                if params["periodo"] != "todos":
                    self.assertEqual(resposta.context["resumo"]["receita"], 0)
                    self.assertEqual(resposta.context["dashboard"]["conciliacao"]["concluidas_apos_periodo"], 1)
                    self.assertContains(resposta, "incluindo baixas posteriores ao período")
        novembro = self.totais((0, 0, 0, 0, 0), {"periodo": "mes", "mes": 11, "ano": 2026})
        self.assertEqual(novembro.context["resumo"]["receita"], 5)

    def test_baixa_na_segunda_quinzena_atualiza_primeira_quinzena(self):
        self.criar(dia="2026-10-15")
        params = {"periodo": "quinzena", "mes": 10, "ano": 2026, "quinzena": 1}
        self.totais((1, 0, 1, 1, 0), params)
        self.cadastrar_baixa("2026-10-16")
        resposta = self.totais((1, 1, 1, 0, 1), params)
        self.assertEqual(resposta.context["resumo"]["receita"], 0)

    def test_baixas_repetidas_contam_uma_conclusao_e_preservam_receitas(self):
        self.criar()
        self.criar(dia="2026-10-21", situacao=BAIXA, horario=time(10), valor="5.00")
        self.criar(dia="2026-10-21", situacao=BAIXA, horario=time(11), valor="7.00")
        resposta = self.totais((1, 1, 1, 0, 1))
        self.assertEqual(resposta.context["resumo"]["receita"], 12)
        self.assertEqual(resposta.context["resumo"]["ganho_medio_baixa"], 6)
        self.assertEqual(resposta.context["dashboard"]["conciliacao"]["alertas_financeiros"], 1)
        self.assertEqual(Entrega.objects.count(), 3)
        self.assertContains(resposta, "ciclo(s) com alerta financeiro")

    def test_precos_historicos_nao_mudam_ao_reconsultar_ou_editar(self):
        falha = self.criar(valor="3.00")
        Configuracao.objects.create(valor_por_baixa=Decimal("7.00"))
        baixa = self.cadastrar_baixa()
        resposta = self.totais((1, 1, 1, 0, 1))
        self.assertEqual(resposta.context["resumo"]["receita"], 7)
        dados = {"codigo": baixa.codigo, "data": "2026-10-21", "horario": "12:00", "situacao": BAIXA}
        self.assertEqual(self.client.post(reverse("entregas:editar", args=[baixa.pk]), dados).status_code, 302)
        self.totais((1, 1, 1, 0, 1))
        baixa.refresh_from_db()
        falha.refresh_from_db()
        self.assertEqual((falha.valor_por_baixa, baixa.valor_por_baixa), (Decimal("3.00"), Decimal("7.00")))

    def test_grafico_exclusivo_concilia_com_cards_e_nao_desloca_financas(self):
        self.criar(codigo="direta", dia="2026-10-19", situacao=BAIXA, valor="5.00")
        self.criar()
        self.criar(dia="2026-10-21", situacao=BAIXA, valor="7.00")
        self.criar(codigo="pendente")
        self.criar(codigo="pendente", horario=time(11))
        resposta = self.totais((3, 2, 2, 1, 1))
        graficos = resposta.context["dashboard"]["graficos"]
        self.assertEqual(graficos[0]["rotulos"], ["19/10/2026", "20/10/2026"])
        self.assertEqual([s["valores"] for s in graficos[0]["series"]], [[1, 0], [0, 1], [0, 1]])
        self.assertEqual(sum(sum(s["valores"]) for s in graficos[0]["series"]), 3)
        self.assertEqual(graficos[1]["series"][0]["valores"], [Decimal("5.00"), Decimal("0.00"), Decimal("7.00")])

    def test_reutilizacao_fica_em_revisao_e_fora_do_grafico(self):
        self.criar(dia="2026-10-01", situacao=BAIXA)
        self.criar(dia="2026-11-01")
        resposta = self.totais((0, 0, 0, 0, 0))
        self.assertEqual(resposta.context["dashboard"]["conciliacao"]["ciclos_em_revisao"], 2)
        self.assertEqual(resposta.context["dashboard"]["graficos"][0]["rotulos"], [])
        self.assertContains(resposta, "Necessita revisão")

    def test_paginas_de_resultado_impedem_cache_http(self):
        self.criar()
        for nome in ("painel:inicio", "painel:auditoria", "painel:conciliacao"):
            resposta = self.client.get(reverse(nome), HTTP_IF_NONE_MATCH='"anterior"')
            self.assertEqual(resposta.status_code, 200)
            for valor in ("no-cache", "no-store", "must-revalidate", "private"):
                self.assertIn(valor, resposta["Cache-Control"])

    def test_desktop_e_mobile_recebem_mesmos_cards_e_vazio_sem_taxa_inventada(self):
        for agente in ("Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Mozilla/5.0 (Linux; Android 14; Mobile)"):
            resposta, _ = self.painel(HTTP_USER_AGENT=agente)
            cards = CardsEncomendas(resposta.content.decode()).cards
            self.assertEqual(len(cards), 9)
            self.assertEqual(cards["Total de encomendas"], "0")
            self.assertEqual(cards["Taxa de Sucesso"], "Não informado")
            self.assertContains(resposta, '/static/css/responsivo.css')
