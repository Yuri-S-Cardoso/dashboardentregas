"""Taxa por população iniciada nas tabelas, com preservação do dashboard aprovado."""
from copy import deepcopy
from datetime import date, time, timedelta
from decimal import Decimal
import json
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse

from core.periodos import FiltroPeriodo
from entregas.models import Entrega
from jornadas.models import Jornada
from painel.dashboard import montar_dashboard
from painel.taxas_tabelas import calcular_taxa_sucesso_tabela
from tests.test_dashboard_situacao_real import CardsEncomendas
from tests.test_layout_painel import TabelasPainel

B, I = "Baixa realizada", "Insucesso"


class TaxasTabelasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(username="taxas_tabelas_teste")

    def setUp(self):
        self.client.force_login(self.usuario)

    def entrega(self, codigo, dia, situacao=I, hora=time(10), valor="5.00"):
        return Entrega.objects.create(codigo=codigo, data=date.fromisoformat(dia), situacao=situacao,
                                      horario=hora, valor_por_baixa=Decimal(valor))

    def taxa(self, inicio="2026-10-22", fim=None, referencia=None, **kwargs):
        return calcular_taxa_sucesso_tabela(date.fromisoformat(inicio), date.fromisoformat(fim or inicio),
                                           date.fromisoformat(referencia) if referencia else None, **kwargs)

    def test_referencia_62_entre_64_e_335_entre_345(self):
        registros = []

        def adicionar(codigo, dia, situacao, hora=time(10)):
            registros.append(Entrega(codigo=codigo, data=date(2026, 10, dia), situacao=situacao,
                                     horario=hora, valor_por_baixa=Decimal("5.00")))

        for n in range(43):
            adicionar(f"direta{n}", 22, B)
        for n in range(19):
            adicionar(f"recuperada{n}", 22, I)
            adicionar(f"recuperada{n}", 23, B)
        adicionar("recuperada0", 22, I, time(11))
        for n in range(2):
            adicionar(f"pendente22-{n}", 22, I)
        for n in range(273):
            adicionar(f"outra{n}", 19, B)
        adicionar("outra0", 19, B, time(11))
        for n in range(8):
            adicionar(f"pendente20-{n}", 20, I)
        Entrega.objects.bulk_create(registros)
        dia = self.taxa()
        semana = self.taxa("2026-10-18", "2026-10-24")
        self.assertEqual((dia["concluidas"], dia["encomendas_identificadas"], dia["taxa_sucesso_arredondada"]), (62, 64, Decimal("96.88")))
        self.assertEqual((semana["concluidas"], semana["encomendas_identificadas"], semana["taxa_sucesso_arredondada"]), (335, 345, Decimal("97.10")))
        p = montar_dashboard()
        d = next(d for d in p["diarios"] if d["data"] == date(2026, 10, 22))
        self.assertEqual((d["tentativas"], d["baixas"], d["insucessos"], d["receita"]), (65, 43, 22, 215))
        self.assertEqual(d["indicadores_principais"]["taxa_sucesso_arredondada"], Decimal("95.56"))
        self.assertEqual(d["taxa_sucesso_tabela"]["taxa_sucesso_arredondada"], Decimal("96.88"))

    def test_recuperacao_no_dia_seguinte_nao_move_baixa_ou_receita(self):
        self.entrega("r", "2026-10-22")
        self.entrega("r", "2026-10-23", B)
        p = montar_dashboard()
        self.assertEqual([d["taxa_sucesso_tabela"]["taxa_sucesso_arredondada"] for d in p["diarios"]], [100, None])
        self.assertEqual([d["receita"] for d in p["diarios"]], [0, 5])
        self.assertEqual([d["baixas"] for d in p["diarios"]], [0, 1])
        self.assertEqual([d["insucessos"] for d in p["diarios"]], [1, 0])
        self.assertEqual(p["diarios"][0]["indicadores_principais"]["taxa_sucesso"], None)

    def test_recuperacao_na_semana_seguinte_domingo_sabado(self):
        self.entrega("r", "2026-10-24")
        self.entrega("r", "2026-10-25", B)
        p = montar_dashboard()
        self.assertEqual([s["rotulo"] for s in p["semanas"]], ["18/10/2026 a 24/10/2026", "25/10/2026 a 31/10/2026"])
        self.assertEqual([s["taxa_sucesso_tabela"]["taxa_sucesso"] for s in p["semanas"]], [100, None])
        self.assertEqual([s["receita"] for s in p["semanas"]], [0, 5])

    def test_recuperacao_no_mes_seguinte_com_filtro_anterior(self):
        self.entrega("r", "2026-10-31")
        self.entrega("r", "2026-11-01", B)
        p = montar_dashboard(FiltroPeriodo(date(2026, 10, 1), date(2026, 10, 31)))
        self.assertEqual(p["meses"][0]["taxa_sucesso_tabela"]["taxa_sucesso"], 100)
        self.assertIsNone(p["indicadores_principais"]["taxa_sucesso"])
        self.assertEqual((p["resumo"]["receita"], p["resumo"]["baixas"], p["resumo"]["insucessos"]), (0, 0, 1))

    def test_referencia_inclusiva_nao_considera_baixa_futura_ao_corte(self):
        self.entrega("r", "2026-10-22")
        self.entrega("r", "2026-10-23", B)
        antes = self.taxa(referencia="2026-10-22")
        depois = self.taxa(referencia="2026-10-23")
        self.assertEqual((antes["concluidas"], antes["pendentes"], antes["taxa_sucesso"]), (0, 1, 0))
        self.assertEqual((depois["concluidas"], depois["pendentes"], depois["taxa_sucesso"]), (1, 0, 100))

    def test_tentativas_e_baixas_repetidas_nao_inflam_populacao(self):
        self.entrega("r", "2026-10-22")
        self.entrega("r", "2026-10-22", hora=time(11))
        self.entrega("r", "2026-10-23", B)
        self.entrega("r", "2026-10-23", B, time(11), "7.00")
        self.entrega("p", "2026-10-22")
        t = self.taxa()
        self.assertEqual((t["concluidas"], t["pendentes"], t["encomendas_identificadas"], t["taxa_sucesso"]), (1, 1, 2, 50))
        p = montar_dashboard()
        self.assertEqual(p["resumo"]["receita"], 12)
        self.assertEqual(p["indicadores_principais"]["taxa_sucesso_arredondada"], Decimal("66.67"))
        self.assertEqual(p["meses"][0]["taxa_sucesso_tabela"]["taxa_sucesso"], 50)

    def test_zeros_a_esquerda_sao_identidades_distintas(self):
        self.entrega("000123", "2026-10-22", B)
        self.entrega("123", "2026-10-22")
        self.assertEqual(self.taxa()["taxa_sucesso"], 50)

    def test_baixa_anterior_nao_resolve_insucesso_posterior(self):
        self.entrega("reuso", "2026-10-21", B)
        self.entrega("reuso", "2026-10-22")
        t = self.taxa()
        self.assertEqual(t["encomendas_identificadas"], 0)
        self.assertGreater(t["ciclos_em_revisao"], 0)
        self.assertIsNone(t["taxa_sucesso"])

    def test_ambiguidades_excluidas_sem_remover_ocorrencias(self):
        self.entrega("empate", "2026-10-22", B)
        self.entrega("empate", "2026-10-22", I)
        self.entrega("valida", "2026-10-22", B)
        p = montar_dashboard()
        t = p["diarios"][0]["taxa_sucesso_tabela"]
        self.assertEqual((t["encomendas_identificadas"], t["concluidas"], t["pendentes"], t["taxa_sucesso"]), (1, 1, 0, 100))
        self.assertEqual(t["ciclos_em_revisao"], 1)
        self.assertEqual((p["resumo"]["tentativas"], p["resumo"]["baixas"], p["resumo"]["receita"]), (3, 2, 10))

    def test_periodo_sem_populacao_e_jornada_isolada(self):
        Jornada.objects.create(data=date(2026, 10, 22), janela_historica=timedelta(hours=2))
        self.assertIsNone(self.taxa()["taxa_sucesso"])
        p = montar_dashboard()
        for linha in (*p["diarios"], *p["semanas"], *p["meses"]):
            self.assertEqual(linha["taxa_sucesso_tabela"]["encomendas_identificadas"], 0)
            self.assertIsNone(linha["taxa_sucesso_tabela"]["taxa_sucesso_arredondada"])
            self.assertEqual(linha["horas"], 2)

    def test_populacao_nao_inclui_encomenda_iniciada_antes_do_recorte(self):
        self.entrega("r", "2026-10-21")
        self.entrega("r", "2026-10-22", B)
        self.entrega("p", "2026-10-22")
        self.assertEqual((self.taxa()["encomendas_identificadas"], self.taxa()["taxa_sucesso"]), (1, 0))
        p = montar_dashboard(FiltroPeriodo(date(2026, 10, 22), date(2026, 10, 22)))
        self.assertEqual(p["indicadores_principais"]["taxa_sucesso"], 50)
        for linha in (*p["diarios"], *p["semanas"], *p["meses"]):
            self.assertEqual(linha["taxa_sucesso_tabela"]["taxa_sucesso"], 0)
            self.assertEqual(linha["receita"], 5)

    def test_periodo_invertido_rejeitado_sem_gravar(self):
        with self.assertRaises(ValueError):
            self.taxa("2026-10-23", "2026-10-22")
        self.assertEqual(Entrega.objects.count(), 0)

    def test_historico_fornecido_nao_faz_consultas_ou_muta_registros(self):
        self.entrega("r", "2026-10-22")
        self.entrega("r", "2026-10-23", B)
        historico = list(Entrega.objects.all())
        def campos():
            return [{f.attname: getattr(e, f.attname) for f in e._meta.concrete_fields} for e in historico]
        originais = deepcopy(campos())
        with self.assertNumQueries(0):
            t = self.taxa(historico=historico)
        self.assertEqual(t["taxa_sucesso"], 100)
        self.assertEqual(campos(), originais)

    def test_dashboard_aprovado_nao_depende_da_nova_taxa(self):
        self.entrega("r", "2026-10-22")
        self.entrega("r", "2026-10-23", B)
        self.entrega("p", "2026-10-22")
        Jornada.objects.create(data=date(2026, 10, 22), odometro_inicial=0, odometro_final=100,
                               litros_consumidos=2, custo_combustivel=30, janela_historica=timedelta(hours=2))
        antes = list(Entrega.objects.values())
        with patch("painel.dashboard.calcular_taxa_sucesso_tabela", return_value={}):
            sem_nova_taxa = montar_dashboard()
        atual = montar_dashboard()

        def anterior(v):
            if isinstance(v, dict):
                return {k: anterior(item) for k, item in v.items() if k != "taxa_sucesso_tabela"}
            if isinstance(v, list):
                return [anterior(item) for item in v]
            return v

        self.assertEqual(anterior(atual), anterior(sem_nova_taxa))
        self.assertEqual(atual["indicadores_principais"]["taxa_sucesso"], 50)
        self.assertEqual(atual["diarios"][0]["taxa_sucesso_tabela"]["taxa_sucesso"], 50)
        self.assertEqual(list(Entrega.objects.values()), antes)

    def test_somente_celulas_de_taxa_mudam_com_card_preservado(self):
        self.entrega("r", "2026-10-22")
        self.entrega("r", "2026-10-23", B)
        self.entrega("r", "2026-10-23", B, time(11))
        self.entrega("p", "2026-10-22")
        r = self.client.get(reverse("painel:inicio"), {"periodo": "todos"})
        p = r.context["dashboard"]
        legado = deepcopy(p)
        for grupo in ("diarios", "semanas", "meses"):
            for linha in legado[grupo]:
                linha["taxa_sucesso_tabela"] = linha["indicadores_principais"]
        html_anterior = render_to_string("painel/inicio.html", {"dashboard": legado, "resumo": legado["resumo"]})
        html_atual = r.content.decode()
        self.assertEqual(CardsEncomendas(html_anterior).cards, CardsEncomendas(html_atual).cards)
        self.assertEqual(CardsEncomendas(html_atual).cards["Taxa de Sucesso"], "66,67%")
        antes, depois = TabelasPainel(html_anterior).tabelas[:3], TabelasPainel(html_atual).tabelas[:3]
        alteradas = 0
        for i, (a, d) in enumerate(zip(antes, depois)):
            self.assertEqual(a[0], d[0])
            self.assertEqual(len(a), len(d))
            coluna = 2 if i == 0 else 3
            for la, ld in zip(a[1:], d[1:]):
                self.assertEqual(la[:coluna] + la[coluna + 1:], ld[:coluna] + ld[coluna + 1:])
                alteradas += la[coluna] != ld[coluna]
        self.assertGreater(alteradas, 0)
        self.assertEqual(depois[1][1][3], "50,00%")
        self.assertIn("considerando recuperações posteriores", html_atual)

    def test_lote_e_exclusao_recalculam_sem_cache(self):
        self.entrega("r", "2026-10-31")
        filtro = FiltroPeriodo(date(2026, 10, 1), date(2026, 10, 31))
        self.assertEqual(montar_dashboard(filtro)["meses"][0]["taxa_sucesso_tabela"]["taxa_sucesso"], 0)
        dados = {"chave": str(uuid4()), "data_padrao": "2026-11-01", "situacao_padrao": B,
                 "linhas": json.dumps([{"codigo": "r", "horario": "11:00"}])}
        url = reverse("entregas:lote")
        previa = self.client.post(url, {**dados, "acao": "prever"})
        self.assertEqual(montar_dashboard(filtro)["meses"][0]["taxa_sucesso_tabela"]["taxa_sucesso"], 0)
        dados.update(acao="salvar", comprovante=previa.context["form"]["comprovante"].value())
        self.assertEqual(self.client.post(url, dados).status_code, 302)
        p = montar_dashboard(filtro)
        self.assertEqual(p["meses"][0]["taxa_sucesso_tabela"]["taxa_sucesso"], 100)
        self.assertIsNone(p["indicadores_principais"]["taxa_sucesso"])
        baixa = Entrega.objects.get(situacao=B)
        self.assertEqual(self.client.post(reverse("entregas:excluir", args=[baixa.pk])).status_code, 302)
        self.assertEqual(montar_dashboard(filtro)["meses"][0]["taxa_sucesso_tabela"]["taxa_sucesso"], 0)
