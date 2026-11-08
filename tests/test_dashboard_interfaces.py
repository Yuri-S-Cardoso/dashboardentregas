from datetime import date, time
from decimal import Decimal
import json
import re
import secrets
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from conferencia.models import EspelhoEmpresa
from entregas.models import Entrega
from jornadas.models import Jornada


class DashboardInterfacesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(username="painel_teste", password=secrets.token_urlsafe(24))
        for dia in [15, 16, 19, 20]:
            Entrega.objects.create(data=date(2026, 10, dia), horario=time(12), codigo="repetido", situacao="Baixa realizada", valor_por_baixa=Decimal("5.00"))
        EspelhoEmpresa.objects.create(data_competencia=date(2026, 10, 15), baixas_pagas=1, insucessos=0, valor_empresa=Decimal("5.00"), documento="OS teste")
        Jornada.objects.create(data=date(2026, 10, 19), inicio_real=time(12), fim_real=time(13))

    def test_rotas_protegidas_e_metodos_de_leitura(self):
        for nome in ["painel:inicio", "painel:auditoria"]:
            self.assertEqual(self.client.get(reverse(nome)).status_code, 302)
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.post(reverse("painel:auditoria")).status_code, 405)

    def test_todos_os_filtros_afetam_cards_series_e_auditoria(self):
        self.client.force_login(self.usuario)
        casos = [
            ({"periodo": "dia", "dia": "2026-10-15"}, 1),
            ({"periodo": "semana", "semana": "2026-10-19"}, 2),
            ({"periodo": "mes", "mes": "10", "ano": "2026"}, 4),
            ({"periodo": "quinzena", "mes": "10", "ano": "2026", "quinzena": "2"}, 3),
            ({"periodo": "intervalo", "inicio": "2026-10-16", "fim": "2026-10-19"}, 2),
        ]
        for parametros, esperado in casos:
            for rota in ["painel:inicio", "painel:auditoria"]:
                with self.subTest(parametros=parametros, rota=rota):
                    resposta = self.client.get(reverse(rota), parametros)
                    self.assertEqual(resposta.status_code, 200)
                    p = resposta.context["dashboard"]
                    self.assertEqual(p["resumo"]["tentativas"], esperado)
                    self.assertEqual(sum(d["tentativas"] for d in p["auditoria"]), esperado)
                    self.assertEqual(len(p["graficos"][1]["rotulos"]), esperado)

    def test_filtro_invalido_nao_mostra_historico_inteiro(self):
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse("painel:inicio"), {"periodo": "dia", "dia": "invalido"})
        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn("dashboard", resposta.context)
        self.assertContains(resposta, "Corrija os filtros")
        self.assertNotContains(resposta, 'id="dados-graficos"')

    def test_dados_graficos_json_coerentes_locais_e_nulos_preservados(self):
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse("painel:inicio"), {"periodo": "todos"})
        html = resposta.content.decode()
        dados = json.loads(re.search(r'<script id="dados-graficos" type="application/json">(.*?)</script>', html, re.S).group(1))
        self.assertEqual(len(dados), 7)
        self.assertEqual(dados[1]["series"][0]["valores"], ["5.00"] * 4)
        self.assertEqual(dados[5]["series"][1]["valores"], [None] * 4)
        self.assertContains(resposta, '/static/js/graficos.js')
        self.assertContains(resposta, "Ver tabela de valores", count=7)
        self.assertNotContains(resposta, "cdn.")
        self.assertContains(resposta, "Não informado")

    def test_auditoria_separa_previsto_informado_e_recebido(self):
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse("painel:auditoria"), {"periodo": "todos"})
        self.assertContains(resposta, "Conferido")
        self.assertContains(resposta, "Aguardando espelho")
        self.assertContains(resposta, "Sem pagamento registrado")
        self.assertContains(resposta, "não comprova inadimplência")

    def test_csrf_continua_ativo_na_nova_rota(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.usuario)
        self.assertContains(cliente.post(reverse("painel:auditoria"), {}), "Acesso não permitido", status_code=403)

    def test_projecao_usa_horizonte_informado(self):
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse("painel:inicio"), {"periodo": "todos", "dias_projecao": 10})
        projecao = resposta.context["dashboard"]["projecao"]
        self.assertEqual(projecao["dias_observados"], 4)
        self.assertEqual(projecao["receita_cenario"], Decimal("50.00"))

    def test_recorte_vazio_mostra_estado_vazio(self):
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse("painel:inicio"), {"periodo": "mes", "mes": 1, "ano": 2025})
        self.assertContains(resposta, "Nenhum registro encontrado no período")
        self.assertIsNone(resposta.context["dashboard"]["projecao"]["receita_cenario"])
