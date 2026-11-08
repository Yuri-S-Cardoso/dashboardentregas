"""Lotes exercitados somente no banco de testes, inclusive falhas e reenvios."""
import csv
from datetime import date, time
from decimal import Decimal
from io import BytesIO, StringIO
import json
from unittest import skipUnless
from unittest.mock import patch
from uuid import uuid4
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook
from core.periodos import FiltroPeriodo
from entregas.models import Entrega, LoteEntrega
from entregas.services.importacao import importar_excel
from painel.dashboard import montar_dashboard
from painel.exportacao import exportar_csv, exportar_xlsx
from painel.models import Configuracao
from .test_importacao import EXCEL_REAL


class OperacoesLote:
    def setUp(self):
        self.client.force_login(self.usuario)
        self.url = reverse("entregas:lote")

    def dados(self, quantidade=1, **alteracoes):
        return {"chave": str(uuid4()), "data_padrao": "2026-10-22", "situacao_padrao": "Baixa realizada",
                "linhas": json.dumps([{"codigo": f"{i:010d}"} for i in range(quantidade)]), **alteracoes}

    def previa(self, dados, cliente=None):
        resposta = (cliente or self.client).post(self.url, {**dados, "acao": "prever"})
        self.assertEqual(resposta.status_code, 200, resposta.content.decode()[:1500])
        return {**dados, "acao": "salvar", "comprovante": resposta.context["form"]["comprovante"].value()}

    def salvar(self, dados, cliente=None):
        return (cliente or self.client).post(self.url, self.previa(dados, cliente))


class CadastroLoteTests(OperacoesLote, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(username="operador_lote")
        cls.original = Entrega.objects.create(codigo="original", data=date(2026, 10, 15), horario=time(12),
                                              situacao="Baixa realizada", valor_por_baixa=Decimal("5.00"))

    def test_get_data_atual_grade_e_acesso_direto_na_lista(self):
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context["form"]["data_padrao"].value(), timezone.localdate())
        self.assertContains(resposta, "Adicionar 20 Linhas")
        self.assertContains(resposta, "inputmode=\"numeric\"")
        self.assertContains(self.client.get(reverse("entregas:lista")), self.url)
        self.assertEqual(Entrega.objects.count(), 1)
        self.assertEqual(LoteEntrega.objects.count(), 0)

    def test_cadastro_de_1_50_100_e_200_em_transacao(self):
        for quantidade in (1, 50, 100, 200):
            with self.subTest(quantidade=quantidade):
                antes = Entrega.objects.count()
                resposta = self.salvar(self.dados(quantidade))
                self.assertEqual(resposta.status_code, 302)
                self.assertEqual(Entrega.objects.count() - antes, quantidade)
                self.assertEqual(LoteEntrega.objects.order_by("pk").last().quantidade, quantidade)

    def test_previa_valida_nao_grava_nada(self):
        dados = self.dados(50)
        self.previa(dados)
        self.assertEqual(Entrega.objects.count(), 1)
        self.assertEqual(LoteEntrega.objects.count(), 0)

    def test_data_padrao_e_data_individual_brasileira(self):
        dados = self.dados(linhas=json.dumps([{"codigo": "0001"}, {"codigo": "0002", "data": "23/10/2026"}]))
        self.assertEqual(self.salvar(dados).status_code, 302)
        self.assertEqual(Entrega.objects.get(codigo="0001").data, date(2026, 10, 22))
        self.assertEqual(Entrega.objects.get(codigo="0002").data, date(2026, 10, 23))

    def test_situacao_padrao_e_alteracao_individual(self):
        dados = self.dados(situacao_padrao="Insucesso", linhas=json.dumps([
            {"codigo": "a"}, {"codigo": "b", "situacao": "Baixa realizada"}]))
        self.assertEqual(self.salvar(dados).status_code, 302)
        self.assertEqual(Entrega.objects.get(codigo="a").valor_previsto, Decimal("0.00"))
        self.assertEqual(Entrega.objects.get(codigo="b").valor_previsto, Decimal("5.00"))

    def test_horarios_opcionais_reais_e_meia_noite(self):
        dados = self.dados(linhas=json.dumps([{"codigo": "sem"}, {"codigo": "meia-noite", "horario": "00:00"},
                                           {"codigo": "com", "horario": "17:04:59"}]))
        self.assertEqual(self.salvar(dados).status_code, 302)
        self.assertIsNone(Entrega.objects.get(codigo="sem").horario)
        self.assertEqual(Entrega.objects.get(codigo="meia-noite").horario, time(0))
        self.assertEqual(Entrega.objects.get(codigo="com").horario, time(17, 4, 59))

    def test_zeros_a_esquerda_codigos_repetidos_e_novo_lote_legitimo(self):
        dados = self.dados(linhas=json.dumps([{"codigo": "000123"}, {"codigo": "000123"}]))
        self.salvar(dados)
        self.salvar({**dados, "chave": str(uuid4())})
        self.assertEqual(Entrega.objects.filter(codigo="000123").count(), 4)

    def test_linhas_vazias_ignoradas_sem_fundir_codigos(self):
        dados = self.dados(linhas=json.dumps([{}, {"codigo": ""}, {"codigo": "a"},
            {"codigo": " ", "horario": "", "data": "", "situacao": "Baixa realizada"}]))
        self.salvar(dados)
        self.assertEqual(Entrega.objects.count(), 2)
        self.assertEqual(LoteEntrega.objects.get().quantidade, 1)

    def test_lote_completamente_vazio_nao_grava(self):
        resposta = self.client.post(self.url, {**self.dados(linhas="[{}]"), "acao": "prever"})
        self.assertContains(resposta, "Preencha ao menos um código", status_code=400)
        self.assertEqual(LoteEntrega.objects.count(), 0)

    def test_linhas_incompletas_e_invalidas_preservam_toda_a_digitacao(self):
        linhas = [{"codigo": "000123"}, {"horario": "12:00"}, {"codigo": "data", "data": "31/02/2026"},
                  {"codigo": "hora", "horario": "25:70"}, {"codigo": "sit", "situacao": "outra"}]
        resposta = self.client.post(self.url, {**self.dados(linhas=json.dumps(linhas)), "acao": "prever"})
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(resposta.context["linhas_iniciais"], linhas)
        self.assertEqual([erro["linha"] for erro in resposta.context["erros_linhas"]], [2, 3, 4, 5])
        self.assertEqual(Entrega.objects.count(), 1)
        self.assertEqual(LoteEntrega.objects.count(), 0)

    def test_transporte_rejeita_numeros_objetos_e_limites_sem_perder_banco(self):
        for linhas in ('[{"codigo": 123}]', '{}', '[null]', 'invalido', json.dumps([{}] * 501),
                       json.dumps([{"codigo": "x" * 101}])):
            with self.subTest(linhas=linhas[:60]):
                resposta = self.client.post(self.url, {**self.dados(linhas=linhas), "acao": "prever"})
                self.assertEqual(resposta.status_code, 400)
        self.assertEqual(Entrega.objects.count(), 1)

    def test_salvamento_exige_previa_e_revalida_linhas(self):
        dados = self.dados()
        resposta = self.client.post(self.url, {**dados, "acao": "salvar"})
        self.assertEqual(resposta.status_code, 400)
        confirmado = self.previa(dados)
        confirmado["linhas"] = '[{"codigo":"alterado"}]'
        self.assertEqual(self.client.post(self.url, confirmado).status_code, 400)
        self.assertEqual(Entrega.objects.count(), 1)

    def test_duplo_envio_mesma_chave_nao_duplica_inclusive_apos_reiniciar_cliente(self):
        dados = self.previa(self.dados(50))
        primeira = self.client.post(self.url, dados)
        outro_cliente = Client()
        outro_cliente.force_login(self.usuario)
        segunda = outro_cliente.post(self.url, dados)
        self.assertEqual(primeira.url, segunda.url)
        self.assertEqual(Entrega.objects.count(), 51)
        self.assertEqual(LoteEntrega.objects.count(), 1)

    def test_mesma_chave_com_conteudo_diferente_produz_conflito(self):
        dados = self.dados()
        self.salvar(dados)
        modificado = self.previa({**dados, "linhas": '[{"codigo":"outro"}]'})
        self.assertEqual(self.client.post(self.url, modificado).status_code, 409)
        self.assertEqual(Entrega.objects.count(), 2)

    def test_falha_de_gravacao_reverte_entregas_e_recibo_e_permite_tentar_novamente(self):
        dados = self.previa(self.dados(50))

        def falhar(registros, **kwargs):
            registros[0].save()
            raise IntegrityError("Falha de teste após gravar uma linha")

        with patch("entregas.services.lote.Entrega.objects.bulk_create", side_effect=falhar), patch("entregas.lote_views.logger.exception"):
            resposta = self.client.post(self.url, dados)
        self.assertEqual(resposta.status_code, 503)
        self.assertEqual(len(resposta.context["linhas_iniciais"]), 50)
        self.assertEqual(Entrega.objects.count(), 1)
        self.assertEqual(LoteEntrega.objects.count(), 0)
        self.assertEqual(self.client.post(self.url, dados).status_code, 302)
        self.assertEqual(Entrega.objects.count(), 51)

    def test_unicidade_do_recibo_no_banco_sem_unicidade_de_codigo(self):
        self.salvar(self.dados())
        recibo = LoteEntrega.objects.get()
        with self.assertRaises(IntegrityError), transaction.atomic():
            LoteEntrega.objects.create(usuario=self.usuario, chave=recibo.chave, sha256=recibo.sha256,
                quantidade=1, data_padrao=recibo.data_padrao, situacao_padrao=recibo.situacao_padrao)

    def test_preco_vigente_snapshot_historico_e_insucesso_zero(self):
        Configuracao.objects.create(valor_por_baixa=Decimal("7.25"))
        dados = self.previa(self.dados(linhas=json.dumps([{"codigo": "nova"}, {"codigo": "falha", "situacao": "Insucesso"}])))
        self.client.post(self.url, dados)
        Configuracao.objects.create(valor_por_baixa=Decimal("9.00"))
        self.client.post(self.url, dados)
        self.assertEqual(Entrega.objects.get(codigo="nova").valor_por_baixa, Decimal("7.25"))
        self.assertEqual(Entrega.objects.get(codigo="falha").valor_previsto, Decimal("0.00"))
        self.original.refresh_from_db()
        self.assertEqual(self.original.valor_por_baixa, Decimal("5.00"))
        self.assertEqual(Entrega.objects.count(), 3)

    def test_autenticacao_csrf_e_recibo_restrito_ao_usuario(self):
        anonimo = Client()
        for metodo in (anonimo.get, anonimo.post):
            resposta = metodo(self.url)
            self.assertEqual(resposta.status_code, 302)
            self.assertIn(reverse("login"), resposta.url)
        protegido = Client(enforce_csrf_checks=True)
        protegido.force_login(self.usuario)
        self.assertEqual(protegido.post(self.url, self.dados()).status_code, 403)
        protegido.get(self.url)
        dados = {**self.dados(), "csrfmiddlewaretoken": protegido.cookies["csrftoken"].value}
        resposta = self.salvar(dados, protegido)
        self.assertEqual(resposta.status_code, 302)
        outro = get_user_model().objects.create_user(username="outro_lote")
        self.client.force_login(outro)
        self.assertEqual(self.client.get(resposta.url).status_code, 404)
        self.assertEqual(anonimo.get(resposta.url).status_code, 302)

    def test_confirmacao_e_novo_lote_conservam_padroes_e_mudam_chave(self):
        dados = self.dados(data_padrao="2026-11-03", situacao_padrao="Insucesso")
        resposta = self.client.get(self.salvar(dados).url)
        self.assertContains(resposta, "1 entregas salvas")
        seguinte = self.client.get(resposta.context["proximo_lote"])
        self.assertEqual(seguinte.context["form"]["data_padrao"].value(), date(2026, 11, 3))
        self.assertEqual(seguinte.context["form"]["situacao_padrao"].value(), "Insucesso")
        self.assertNotEqual(str(seguinte.context["form"]["chave"].value()), dados["chave"])

    def test_individual_cria_e_edita_entrega_do_lote_sem_inventar_horario(self):
        self.salvar(self.dados(linhas='[{"codigo":"000123"}]'))
        entrega = Entrega.objects.get(codigo="000123")
        dados = {"codigo": "corrigido", "data": "2026-10-22", "horario": "", "situacao": "Insucesso"}
        self.assertEqual(self.client.post(reverse("entregas:editar", args=[entrega.pk]), dados).status_code, 302)
        entrega.refresh_from_db()
        self.assertIsNone(entrega.horario)
        self.assertEqual(entrega.codigo, "corrigido")
        self.assertEqual(self.client.post(reverse("entregas:nova"), dados).status_code, 302)

    def test_integracao_imediata_lista_dashboard_auditoria_e_exportacoes(self):
        dados = self.dados(linhas=json.dumps([{"codigo": "000001"}, {"codigo": "000002", "situacao": "Insucesso"}]))
        self.salvar(dados)
        filtro = FiltroPeriodo(date(2026, 10, 22), date(2026, 10, 22))
        dashboard = montar_dashboard(filtro)
        for conjunto in ([dashboard["resumo"]], dashboard["diarios"], dashboard["semanas"], dashboard["meses"]):
            self.assertEqual(conjunto[0]["tentativas"], 2)
            self.assertEqual(conjunto[0]["receita"], Decimal("5.00"))
        self.assertEqual(dashboard["auditoria"][0]["receita"], Decimal("5.00"))
        self.assertIsNone(dashboard["resumo"]["intervalo_medio_segundos"])
        self.assertContains(self.client.get(reverse("entregas:lista"), {"data": "2026-10-22"}), "000001")
        for url in ("painel:inicio", "painel:auditoria"):
            self.assertEqual(self.client.get(reverse(url), {"periodo": "dia", "dia": "2026-10-22"}).status_code, 200)
        livro = load_workbook(BytesIO(exportar_xlsx(filtro)))
        try:
            self.assertEqual(livro["Minhas Entregas"]["A6"].value, "000001")
            self.assertIsNone(livro["Minhas Entregas"]["C6"].value)
        finally:
            livro.close()
        linhas = list(csv.reader(StringIO(exportar_csv(filtro).decode("utf-8-sig")), delimiter=";"))
        self.assertEqual(linhas[1][:4], ["000001", "22/10/2026", "", "Baixa realizada"])


@skipUnless(EXCEL_REAL.exists(), "Excel privado necessário para a preservação histórica.")
class LoteHistoricoTests(OperacoesLote, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(username="historico_lote")
        importar_excel(EXCEL_REAL)

    def test_preserva_todas_as_169_linhas_historicas_ao_adicionar_100(self):
        anteriores = list(Entrega.objects.order_by("pk").values())
        self.assertEqual(len(anteriores), 169)
        self.salvar(self.dados(100))
        depois = list(Entrega.objects.filter(pk__in=[linha["id"] for linha in anteriores]).order_by("pk").values())
        self.assertEqual(anteriores, depois)
        self.assertEqual(Entrega.objects.count(), 269)
