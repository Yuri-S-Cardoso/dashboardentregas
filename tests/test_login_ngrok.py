"""Regressão do login em HTTPS: política do navegador, CSRF e sessões completas."""
import json
import logging
import secrets
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from core.online_diagnostico import FiltroCsrfSeguro, contexto_seguro, categoria_csrf
from core.online_middleware import tentativas_login
from tests.test_online import AJUSTES_ONLINE, DOMINIO, EMAIL


@override_settings(**AJUSTES_ONLINE)
class LoginNgrokRegressaoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.senha = secrets.token_urlsafe(24)
        cls.usuario = get_user_model().objects.create_user(username="prova_login", password=cls.senha)

    def setUp(self):
        self.cliente = Client(enforce_csrf_checks=True)
        with tentativas_login.lock:
            tentativas_login.itens.clear()

    def headers(self, **extras):
        return {"HTTP_HOST": DOMINIO, "HTTP_X_ENTREGAS_HTTPS": "https", "entregas.email": EMAIL, **extras}

    def abrir(self, cliente=None, **headers):
        cliente = cliente or self.cliente
        resposta = cliente.get(reverse("login") + "?next=/", **(headers or self.headers()))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'name="csrfmiddlewaretoken"')
        return cliente.cookies[settings.CSRF_COOKIE_NAME].value

    def dados(self, token):
        return {"username": self.usuario.username, "password": self.senha, "csrfmiddlewaretoken": token, "next": "/"}

    def test_get_login_em_https_preserva_origem_para_formulario_do_navegador(self):
        self.abrir()
        resposta = self.cliente.get(reverse("login"), **self.headers())
        self.assertEqual(resposta["Referrer-Policy"], "same-origin")
        self.assertTrue(resposta.wsgi_request.is_secure())
        self.assertEqual(resposta.wsgi_request.get_host(), DOMINIO)
        self.assertEqual(settings.CSRF_TRUSTED_ORIGINS, ["https://" + DOMINIO])

    def test_post_login_cookie_sessao_painel_logout_e_nova_autenticacao(self):
        token = self.abrir()
        h = self.headers(HTTP_ORIGIN="https://" + DOMINIO, HTTP_REFERER="https://" + DOMINIO + "/contas/entrar/?next=/")
        self.assertEqual(self.cliente.post(reverse("login"), self.dados(token), **h).status_code, 302)
        sessao = self.cliente.cookies[settings.SESSION_COOKIE_NAME]
        self.assertTrue(sessao["secure"] and sessao["httponly"])
        self.assertEqual(sessao["samesite"], "Lax")
        self.assertEqual(self.cliente.get("/", **h).status_code, 200)
        novo_token = self.cliente.cookies[settings.CSRF_COOKIE_NAME].value
        self.assertNotEqual(token, novo_token)
        self.assertEqual(self.cliente.post(reverse("logout"), {"csrfmiddlewaretoken": novo_token}, **h).status_code, 302)
        self.assertEqual(self.cliente.get("/", **h).status_code, 302)
        token = self.abrir()
        self.assertEqual(self.cliente.post(reverse("login"), self.dados(token), **h).status_code, 302)
        self.assertEqual(self.cliente.get("/", **h).status_code, 200)

    def test_origin_null_continua_rejeitado_mesmo_com_token_valido(self):
        token = self.abrir()
        resposta = self.cliente.post(reverse("login"), self.dados(token), **self.headers(HTTP_ORIGIN="null"))
        self.assertEqual(resposta.status_code, 403)
        self.assertFalse(resposta.wsgi_request.user.is_authenticated)

    @override_settings(ONLINE_LOGIN_LIMITE=10)
    def test_sem_origin_requer_referer_https_da_origem_exata(self):
        token = self.abrir()
        dados = self.dados(token)
        self.assertEqual(self.cliente.post(reverse("login"), dados, **self.headers()).status_code, 403)
        for referer in ("http://" + DOMINIO + "/", "https://outro.ngrok-free.dev/"):
            self.assertEqual(self.cliente.post(reverse("login"), dados, **self.headers(HTTP_REFERER=referer)).status_code, 403)
        self.assertEqual(self.cliente.post(reverse("login"), dados,
            **self.headers(HTTP_REFERER="https://" + DOMINIO + "/contas/entrar/")).status_code, 302)

    def test_token_invalido_e_cookie_ausente_nao_criam_sessao(self):
        token = self.abrir()
        h = self.headers(HTTP_ORIGIN="https://" + DOMINIO)
        self.assertEqual(self.cliente.post(reverse("login"), self.dados("invalido"), **h).status_code, 403)
        outro = Client(enforce_csrf_checks=True)
        self.assertEqual(outro.post(reverse("login"), self.dados(token), **h).status_code, 403)
        self.assertNotIn(settings.SESSION_COOKIE_NAME, outro.cookies)

    def test_fluxo_local_completo_preservado(self):
        h = {"HTTP_HOST": "127.0.0.1:8000", "entregas.local": True}
        token = self.abrir(**h)
        self.assertFalse(self.cliente.cookies[settings.CSRF_COOKIE_NAME]["secure"])
        self.assertEqual(self.cliente.post(reverse("login"), self.dados(token), **h).status_code, 302)
        self.assertEqual(self.cliente.get("/", **h).status_code, 200)
        self.assertEqual(self.cliente.post(reverse("logout"), {"csrfmiddlewaretoken": self.cliente.cookies[settings.CSRF_COOKIE_NAME].value}, **h).status_code, 302)
        self.assertEqual(self.cliente.get("/", **h).status_code, 302)


@override_settings(**AJUSTES_ONLINE)
class DiagnosticoCsrfSeguroTests(SimpleTestCase):
    def test_log_nao_contem_valores_sensiveis_nem_urls_da_requisicao(self):
        segredo = secrets.token_urlsafe(36)
        req = RequestFactory().post("/contas/entrar/?segredo=" + segredo,
            {"username": segredo, "password": segredo, "csrfmiddlewaretoken": segredo},
            HTTP_HOST=DOMINIO, HTTP_X_ENTREGAS_HTTPS="https", HTTP_ORIGIN="https://" + segredo + ".example.com",
            HTTP_REFERER="https://" + DOMINIO + "/?token=" + segredo,
            HTTP_COOKIE=settings.CSRF_COOKIE_NAME + "=" + segredo, HTTP_X_ENTREGAS_PROXY_KEY=segredo)
        reason = "Origin checking failed - https://" + segredo + ".example.com does not match any trusted origins."
        record = logging.LogRecord("django.security.csrf", logging.WARNING, __file__, 0,
            "Forbidden (%s): %s", (reason, req.path), None)
        record.request = req
        filtro = FiltroCsrfSeguro()
        self.assertTrue(filtro.filter(record))
        self.assertTrue(filtro.filter(record))
        self.assertNotIn(segredo, repr(record.__dict__))
        dados = json.loads(record.getMessage())
        self.assertEqual(dados["motivo"], "origem_nao_confiavel")
        self.assertEqual(dados["referer_classe"], "mesma_origem_https")
        self.assertTrue(dados["is_secure"])

    def test_referer_malformado_host_rejeitado_e_motivo_desconhecido_sao_sanitizados(self):
        req = RequestFactory().get("/nao-registrar-este-caminho", HTTP_HOST="fora.example.com", HTTP_REFERER="https://[")
        dados = contexto_seguro(req)
        self.assertEqual(dados["host"], "rejeitado")
        self.assertEqual(dados["rota"], "outra")
        self.assertEqual(dados["referer_classe"], "invalida")
        self.assertEqual(categoria_csrf("motivo nao reconhecido com segredo"), "csrf_rejeitado")
