"""Provas locais das fronteiras online; nenhum destes testes abre túnel público."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from datetime import date
from io import BytesIO, StringIO
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from config.acesso_online import ConfiguracaoOnline, carregar_configuracao, gerar_politica, validar_dominio, validar_emails
from config.proxy_online import ProxyOnline
from core.online_middleware import TentativasLogin, tentativas_login
from entregas.models import Entrega, LoteEntrega
from scripts.iniciar_online import aplicacao_de_prova, executar_servicos, main
from scripts.ngrok_processos import InstalacaoNgrok, ProcessoNgrok, ambiente_ngrok, comando_tunel, validar_overlay

DOMINIO = "autorizado.ngrok-free.dev"
EMAIL = "permitido@example.com"
CONFIG = ConfiguracaoOnline(DOMINIO, (EMAIL,))
CHAVE = secrets.token_urlsafe(48)
MIDDLEWARE_ONLINE = ["core.online_middleware.CookiesOnlineMiddleware", "core.online_middleware.SegurancaOnlineMiddleware",
                     *[m for m in settings.MIDDLEWARE if m != "django.middleware.security.SecurityMiddleware"],
                     "core.online_middleware.LimitarLoginOnlineMiddleware"]
AJUSTES_ONLINE = dict(ALLOWED_HOSTS=["localhost", "127.0.0.1", DOMINIO], CSRF_TRUSTED_ORIGINS=["https://" + DOMINIO],
    SESSION_COOKIE_NAME="entregas_online_sessionid", CSRF_COOKIE_NAME="entregas_online_csrftoken",
    SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True, SESSION_COOKIE_HTTPONLY=True, CSRF_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax", CSRF_COOKIE_SAMESITE="Lax", SECURE_PROXY_SSL_HEADER=("HTTP_X_ENTREGAS_HTTPS", "https"),
    SECURE_SSL_REDIRECT=True, SECURE_HSTS_SECONDS=3600, SECURE_REFERRER_POLICY="same-origin", DEBUG=False,
    ONLINE_LOGIN_LIMITE=3, ONLINE_LOGIN_JANELA=60, MIDDLEWARE=MIDDLEWARE_ONLINE)


class ConfiguracaoOnlineTests(SimpleTestCase):
    def test_dominio_explicito_valido_e_rejeicao_de_curingas_urls_ips_e_outros_hosts(self):
        self.assertEqual(validar_dominio(DOMINIO), DOMINIO)
        for dominio in ("*", ".ngrok-free.dev", "*.ngrok-free.dev", "https://" + DOMINIO, DOMINIO + "/",
                        DOMINIO + ":443", DOMINIO + ".evil.com", "8.8.8.8", "exemplo.com", "ngrok-free.dev", "a\n.ngrok.dev"):
            with self.subTest(dominio=dominio), self.assertRaises(ValueError):
                validar_dominio(dominio)

    def test_lista_de_emails_nao_aceita_dominio_inteiro_curinga_ou_lista_vazia(self):
        self.assertEqual(validar_emails([EMAIL, EMAIL]), (EMAIL,))
        for emails in ([], ["*"], ["@gmail.com"], ["*@gmail.com"], "gmail.com", ["conta@"], [123]):
            with self.subTest(emails=emails), self.assertRaises(ValueError):
                validar_emails(emails)

    def test_revisao_e_validacao_vinculadas_a_dominio_emails_e_versao(self):
        with self.assertRaises(ValueError):
            CONFIG.exigir_ativacao_aprovada("3.35.0")
        identificador = CONFIG.identificador_validacao("3.35.0")
        aprovado = ConfiguracaoOnline(DOMINIO, (EMAIL,), True, identificador)
        aprovado.exigir_ativacao_aprovada("3.35.0")
        for configuracao, versao in ((aprovado, "3.36.0"),
                (ConfiguracaoOnline("outro.ngrok-free.dev", (EMAIL,), True, identificador), "3.35.0"),
                (ConfiguracaoOnline(DOMINIO, ("outro@example.com",), True, identificador), "3.35.0")):
            with self.assertRaises(ValueError):
                configuracao.exigir_ativacao_aprovada(versao)

    def test_arquivo_online_rejeita_credenciais_e_campos_inesperados(self):
        with TemporaryDirectory() as temp:
            arquivo = Path(temp) / "online.json"
            dados = dict(dominio=DOMINIO, emails_autorizados=[EMAIL], revisao_aprovada=False, validacao_externa_sha256="")
            arquivo.write_text(json.dumps(dados), encoding="utf-8")
            self.assertEqual(carregar_configuracao(arquivo), CONFIG)
            arquivo.write_text(json.dumps({**dados, "authtoken": "nao-e-uma-credencial"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                carregar_configuracao(arquivo)

    def test_politica_oauth_tem_negacao_explicita_e_remove_antes_de_adicionar(self):
        regras = gerar_politica(CONFIG, CHAVE)["on_http_request"]
        self.assertEqual(regras[0]["actions"], [{"type": "oauth", "config": {"provider": "google"}}])
        self.assertIn(EMAIL, regras[1]["expressions"][0])
        self.assertTrue(regras[1]["expressions"][0].startswith("!("))
        self.assertEqual(regras[1]["actions"][0]["type"], "deny")
        acoes = regras[2]["actions"]
        self.assertEqual([a["type"] for a in acoes], ["remove-headers", "add-headers"])
        self.assertIn("x-entregas-proxy-key", acoes[0]["config"]["headers"])
        self.assertEqual(acoes[1]["config"]["headers"]["host"], DOMINIO)
        self.assertNotIn("allow_domains", json.dumps(regras))

    def test_settings_online_reais_em_processo_novo_sem_contaminar_local(self):
        codigo = '''
import json
from django.conf import settings as s
print(json.dumps({'debug':s.DEBUG,'hosts':s.ALLOWED_HOSTS,'csrf':s.CSRF_TRUSTED_ORIGINS,
 'cookies':[s.SESSION_COOKIE_SECURE,s.CSRF_COOKIE_SECURE,s.SESSION_COOKIE_HTTPONLY,s.CSRF_COOKIE_HTTPONLY],
 'proxy':s.SECURE_PROXY_SSL_HEADER,'samesite':[s.SESSION_COOKIE_SAMESITE,s.CSRF_COOKIE_SAMESITE],
 'referrer':s.SECURE_REFERRER_POLICY,'csrf_filtro':s.LOGGING['handlers']['csrf_seguro']['filters']}))
'''
        ambiente = {**os.environ, "DJANGO_SETTINGS_MODULE": "config.settings_online", "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1",
                    "ENTREGAS_ONLINE_DOMINIO": DOMINIO, "ENTREGAS_ONLINE_EMAILS": json.dumps([EMAIL]), "ENTREGAS_ONLINE_PROXY_KEY": CHAVE}
        resultado = subprocess.run([sys.executable, "-c", codigo], env=ambiente, capture_output=True, text=True, timeout=20)
        self.assertEqual(resultado.returncode, 0)
        dados = json.loads(resultado.stdout)
        self.assertEqual(dados["hosts"], ["localhost", "127.0.0.1", DOMINIO])
        self.assertEqual(dados["csrf"], ["https://" + DOMINIO])
        self.assertEqual(dados["cookies"], [True] * 4)
        self.assertFalse(dados["debug"])
        self.assertEqual(dados["proxy"], ["HTTP_X_ENTREGAS_HTTPS", "https"])
        self.assertEqual(dados["samesite"], ["Lax", "Lax"])
        self.assertEqual(dados["referrer"], "same-origin")
        self.assertEqual(dados["csrf_filtro"], ["csrf_seguro"])
        self.assertFalse(settings.SESSION_COOKIE_SECURE)


class ProxyOnlineTests(SimpleTestCase):
    def chamar(self, host=DOMINIO, **alteracoes):
        vistos, status = {}, []

        def aplicacao(environ, responder):
            vistos.update(environ)
            responder("200 OK", [])
            return [b"ok"]

        environ = {"HTTP_HOST": host, "REMOTE_ADDR": "127.0.0.1", "wsgi.url_scheme": "http", **alteracoes}
        resposta = ProxyOnline(aplicacao, CONFIG, CHAVE)(environ, lambda codigo, headers: status.append(codigo))
        self.assertTrue(list(resposta))
        return status[0], vistos

    def test_proxy_autenticado_produz_https_e_descarta_credencial_e_forwarded(self):
        status, vistos = self.chamar(HTTP_X_ENTREGAS_PROXY_KEY=CHAVE, HTTP_X_ENTREGAS_OAUTH_EMAIL=EMAIL,
            HTTP_X_ENTREGAS_HTTPS="https", HTTP_X_FORWARDED_PROTO="http,https", HTTP_FORWARDED="proto=http",
            HTTP_X_FORWARDED_HOST="evil.com", HTTP_NGROK_AUTH_OAUTH_ACCESS_TOKEN="descartar")
        self.assertEqual(status, "200 OK")
        self.assertEqual(vistos["HTTP_X_ENTREGAS_HTTPS"], "https")
        self.assertEqual(vistos["entregas.email"], EMAIL)
        for campo in ("HTTP_X_ENTREGAS_PROXY_KEY", "HTTP_X_FORWARDED_PROTO", "HTTP_FORWARDED",
                      "HTTP_X_FORWARDED_HOST", "HTTP_NGROK_AUTH_OAUTH_ACCESS_TOKEN"):
            self.assertNotIn(campo, vistos)

    def test_cabecalhos_forjados_sem_chave_nao_autorizam_host_remoto(self):
        status, vistos = self.chamar(HTTP_X_ENTREGAS_OAUTH_EMAIL=EMAIL, HTTP_X_ENTREGAS_HTTPS="https", HTTP_X_FORWARDED_PROTO="https")
        self.assertEqual(status, "403 Forbidden")
        self.assertEqual(vistos, {})

    def test_chave_correta_com_outro_email_ou_http_e_negada(self):
        for email, protocolo in (("outro@example.com", "https"), (EMAIL, "http"), (EMAIL, "https,http")):
            with self.subTest(email=email, protocolo=protocolo):
                status, _ = self.chamar(HTTP_X_ENTREGAS_PROXY_KEY=CHAVE, HTTP_X_ENTREGAS_OAUTH_EMAIL=email, HTTP_X_ENTREGAS_HTTPS=protocolo)
                self.assertEqual(status, "403 Forbidden")

    def test_hosts_desconhecidos_rejeitados_inclusive_outra_conta_ngrok(self):
        for host in ("outro.ngrok-free.dev", "example.com", "127.0.0.1.evil.com", "user@localhost"):
            with self.subTest(host=host):
                self.assertEqual(self.chamar(host)[0], "400 Bad Request")

    def test_local_ignora_https_forjado_e_nao_exige_tunel(self):
        for host in ("127.0.0.1:8000", "localhost:8000"):
            status, vistos = self.chamar(host, HTTP_X_FORWARDED_PROTO="https", HTTP_X_ENTREGAS_HTTPS="https")
            self.assertEqual(status, "200 OK")
            self.assertTrue(vistos["entregas.local"])
            self.assertNotIn("HTTP_X_ENTREGAS_HTTPS", vistos)
            self.assertEqual(vistos["wsgi.url_scheme"], "http")

    def test_proxy_nao_pode_rebaixar_remoto_para_local_e_peer_deve_ser_loopback(self):
        self.assertEqual(self.chamar("localhost:8000", HTTP_X_ENTREGAS_PROXY_KEY=CHAVE, HTTP_X_ENTREGAS_OAUTH_EMAIL=EMAIL)[0], "403 Forbidden")
        self.assertEqual(self.chamar("localhost:8000", REMOTE_ADDR="192.168.1.10")[0], "403 Forbidden")


class LimiteLoginTests(SimpleTestCase):
    def test_limite_expira_e_reserva_atomica_impede_burst_paralelo(self):
        tempo = [0]
        limite = TentativasLogin(relogio=lambda: tempo[0])
        with ThreadPoolExecutor(max_workers=20) as executor:
            resultados = list(executor.map(lambda _: limite.reservar(["usuario", "email"], 5, 900), range(20)))
        self.assertEqual(resultados.count(0), 5)
        self.assertTrue(all(resultado == 900 for resultado in resultados if resultado))
        tempo[0] = 901
        self.assertEqual(limite.reservar(["usuario", "email"], 5, 900), 0)

    def test_limpeza_libera_as_tentativas(self):
        limite = TentativasLogin()
        limite.reservar(["a"], 1, 900)
        self.assertGreater(limite.reservar(["a"], 1, 900), 0)
        limite.limpar(["a"])
        self.assertEqual(limite.reservar(["a"], 1, 900), 0)


@override_settings(**AJUSTES_ONLINE)
class DjangoOnlineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.senha = secrets.token_urlsafe(24)
        cls.usuario = get_user_model().objects.create_user(username="online_teste", password=cls.senha)
        cls.entrega = Entrega.objects.create(codigo="original", data=date(2026, 10, 22), situacao="Baixa realizada")

    def setUp(self):
        self.cliente = Client(enforce_csrf_checks=True)
        with tentativas_login.lock:
            tentativas_login.itens.clear()

    def remoto(self, **extras):
        return {"HTTP_HOST": DOMINIO, "HTTP_X_ENTREGAS_HTTPS": "https", "entregas.email": EMAIL,
                "HTTP_ORIGIN": "https://" + DOMINIO, **extras}

    def token(self, cliente=None, **headers):
        cliente = cliente or self.cliente
        cliente.get(reverse("login"), **(headers or self.remoto()))
        if settings.CSRF_COOKIE_NAME not in cliente.cookies:
            cliente.get(reverse("entregas:lote"), **(headers or self.remoto()))
        return cliente.cookies[settings.CSRF_COOKIE_NAME].value

    def test_rotas_privadas_e_exportacoes_exigem_login_apos_oauth(self):
        for url in ("painel:inicio", "painel:auditoria", "entregas:lista", "entregas:nova", "entregas:lote",
                    "painel:exportar_excel", "painel:exportar_csv", "conferencia:espelhos", "jornadas:lista"):
            with self.subTest(url=url):
                resposta = self.cliente.get(reverse(url), **self.remoto())
                self.assertEqual(resposta.status_code, 302)
                self.assertIn(reverse("login"), resposta.url)

    def test_cookies_https_httponly_samesite_e_cabecalhos(self):
        self.token()
        csrf = self.cliente.cookies[settings.CSRF_COOKIE_NAME]
        self.assertTrue(csrf["secure"])
        self.assertTrue(csrf["httponly"])
        self.assertEqual(csrf["samesite"], "Lax")
        resposta = self.cliente.post(reverse("login"), {"username": self.usuario.username, "password": self.senha,
                "csrfmiddlewaretoken": csrf.value}, **self.remoto())
        self.assertEqual(resposta.status_code, 302)
        sessao = self.cliente.cookies[settings.SESSION_COOKIE_NAME]
        self.assertTrue(sessao["secure"])
        self.assertTrue(sessao["httponly"])
        self.assertEqual(sessao["samesite"], "Lax")
        self.assertEqual(resposta["X-Frame-Options"], "DENY")
        self.assertEqual(resposta["X-Content-Type-Options"], "nosniff")
        self.assertEqual(resposta["Referrer-Policy"], "same-origin")
        self.assertIn("max-age=3600", resposta["Strict-Transport-Security"])
        self.assertIn("no-store", resposta["Cache-Control"])

    def test_csrf_origem_exata_aceita_e_origem_desconhecida_rejeitada(self):
        self.cliente.force_login(self.usuario)
        token = self.token()
        dados = {"codigo": "nova", "data": "2026-10-22", "situacao": "Insucesso", "csrfmiddlewaretoken": token}
        url = reverse("entregas:nova")
        for origem in ("https://outro.ngrok-free.dev", "http://" + DOMINIO):
            self.assertEqual(self.cliente.post(url, dados, **self.remoto(HTTP_ORIGIN=origem)).status_code, 403)
        self.assertEqual(self.cliente.post(url, {k: v for k, v in dados.items() if k != "csrfmiddlewaretoken"}, **self.remoto()).status_code, 403)
        self.assertEqual(self.cliente.post(url, dados, **self.remoto()).status_code, 302)
        self.assertEqual(Entrega.objects.count(), 2)

    def test_acesso_autenticado_dashboard_auditoria_e_downloads(self):
        self.cliente.force_login(self.usuario)
        for url in ("painel:inicio", "painel:auditoria", "entregas:lista", "painel:exportar_excel", "painel:exportar_csv"):
            with self.subTest(url=url):
                self.assertEqual(self.cliente.get(reverse(url), **self.remoto()).status_code, 200)

    def test_cadastro_em_lote_https_e_reenvio_sem_duplicacao(self):
        self.cliente.force_login(self.usuario)
        token = self.token()
        pagina = self.cliente.get(reverse("entregas:lote"), **self.remoto())
        dados = {"data_padrao": "2026-10-22", "situacao_padrao": "Baixa realizada", "chave": pagina.context["form"]["chave"].value(),
                 "linhas": '[{"codigo":"000123"},{"codigo":"000123","situacao":"Insucesso"}]',
                 "csrfmiddlewaretoken": token, "acao": "prever"}
        previa = self.cliente.post(reverse("entregas:lote"), dados, **self.remoto())
        self.assertEqual(previa.status_code, 200)
        dados.update(acao="salvar", comprovante=previa.context["form"]["comprovante"].value())
        for _ in range(2):
            self.assertEqual(self.cliente.post(reverse("entregas:lote"), dados, **self.remoto()).status_code, 302)
        self.assertEqual(Entrega.objects.count(), 3)
        self.assertEqual(LoteEntrega.objects.count(), 1)

    def test_http_local_no_perfil_online_mantem_login_e_cookies_locais(self):
        headers = {"HTTP_HOST": "127.0.0.1:8000", "entregas.local": True}
        token = self.token(**headers)
        self.assertFalse(self.cliente.cookies[settings.CSRF_COOKIE_NAME]["secure"])
        resposta = self.cliente.post(reverse("login"), {"username": self.usuario.username, "password": self.senha,
                                                        "csrfmiddlewaretoken": token}, **headers)
        self.assertEqual(resposta.status_code, 302)
        self.assertFalse(self.cliente.cookies[settings.SESSION_COOKIE_NAME]["secure"])
        self.assertEqual(self.cliente.get(reverse("painel:inicio"), **headers).status_code, 200)

    def test_forca_bruta_login_e_admin_limitados(self):
        token = self.token()
        dados = {"username": self.usuario.username, "password": "senha_incorreta", "csrfmiddlewaretoken": token}
        for _ in range(3):
            self.assertEqual(self.cliente.post(reverse("login"), dados, **self.remoto()).status_code, 200)
        resposta = self.cliente.post(reverse("login"), dados, **self.remoto())
        self.assertEqual(resposta.status_code, 429)
        self.assertIn("Retry-After", resposta)
        self.assertEqual(self.cliente.post(reverse("admin:login"), dados, **self.remoto()).status_code, 429)

    def test_usuario_comum_logado_nao_contorna_limite_do_admin(self):
        self.cliente.force_login(self.usuario)
        token = self.token()
        dados = {"username": "admin_inexistente", "password": "senha_incorreta", "csrfmiddlewaretoken": token}
        for _ in range(3):
            self.assertEqual(self.cliente.post(reverse("admin:login"), dados, **self.remoto()).status_code, 200)
        self.assertEqual(self.cliente.post(reverse("admin:login"), dados, **self.remoto()).status_code, 429)

    def test_login_correto_remove_somente_bloqueios_correspondentes(self):
        token = self.token()
        dados = {"username": self.usuario.username, "password": "senha_incorreta", "csrfmiddlewaretoken": token}
        self.cliente.post(reverse("login"), dados, **self.remoto())
        dados["password"] = self.senha
        self.assertEqual(self.cliente.post(reverse("login"), dados, **self.remoto()).status_code, 302)
        self.assertEqual(tentativas_login.itens, {})


class ProcessosOnlineTests(SimpleTestCase):
    def test_dados_reais_nao_iniciam_sem_revisao_e_validacao(self):
        with TemporaryDirectory() as temp:
            arquivo = Path(temp) / "online.json"
            arquivo.write_text(json.dumps(dict(dominio=DOMINIO, emails_autorizados=[EMAIL], revisao_aprovada=False,
                                               validacao_externa_sha256="")), encoding="utf-8")
            with patch("scripts.iniciar_online.inspecionar_ngrok", return_value=InstalacaoNgrok(Path("ngrok.exe"), Path("privado.yml"), "3.35.0")), \
                    patch("waitress.create_server") as servidor, patch("django.setup") as django_setup, redirect_stdout(StringIO()):
                with self.assertRaisesRegex(ValueError, "Ativação com dados reais bloqueada"):
                    main(["--config", str(arquivo)])
                servidor.assert_not_called()
                django_setup.assert_not_called()

    def test_prova_nao_abre_sqlite_nem_retorna_dados_do_sistema(self):
        status = []
        with patch("sqlite3.connect", side_effect=AssertionError("A prova não pode abrir SQLite.")):
            corpo = b"".join(aplicacao_de_prova({}, lambda s, h: status.append(s)))
        self.assertEqual(status, ["200 OK"])
        self.assertIn("Nenhum dado do sistema", corpo.decode())

    def test_comando_somente_loopback_https_exato_politica_e_sem_inspecao(self):
        instalacao = InstalacaoNgrok(Path("ngrok.exe"), Path("privado.yml"), "3.35.0")
        comando = comando_tunel(instalacao, CONFIG, Path("agente.json"), Path("politica.json"))
        self.assertIn("http://127.0.0.1:8000", comando)
        self.assertIn("https://" + DOMINIO, comando)
        self.assertIn("--traffic-policy-file", comando)
        self.assertIn("--inspect=false", comando)
        self.assertNotIn("0.0.0.0", " ".join(comando))
        self.assertNotIn(CHAVE, " ".join(comando))
        with patch.dict(os.environ, {"NGROK_AUTHTOKEN": "nao-exibir", "NGROK_WEB_ADDR": "inseguro"}):
            self.assertFalse(any(k.startswith("NGROK_") for k in ambiente_ngrok()))

    def test_log_descarta_segredos_e_so_aceita_url_esperada(self):
        agente = ProcessoNgrok([], CONFIG.origem)
        agente.processo = MagicMock(stdout=StringIO(json.dumps({"msg": "started tunnel", "url": CONFIG.origem, "nao_registrar": CHAVE}) + "\n"))
        agente._ler_eventos()
        self.assertTrue(agente.pronto.is_set())
        self.assertNotIn(CHAVE, repr(agente.__dict__))
        agente.processo.stdout = StringIO(json.dumps({"msg": "started tunnel", "url": "https://outro.ngrok-free.dev"}) + "\n")
        agente._ler_eventos()
        self.assertTrue(agente.dominio_incorreto.is_set())

    def test_encerramento_termina_somente_processo_criado_e_aguarda(self):
        agente = ProcessoNgrok([], CONFIG.origem)
        agente.processo = MagicMock()
        agente.processo.poll.return_value = None
        agente.encerrar()
        agente.processo.terminate.assert_called_once()
        agente.processo.wait.assert_called_once_with(timeout=5)
        agente.processo.kill.assert_not_called()

    def test_queda_ngrok_nao_encerra_waitress_antes_do_encerramento_controlado(self):
        momentos = iter([0, 0, 0, 2])
        with patch("waitress.create_server") as criar, patch("scripts.iniciar_online.ProcessoNgrok") as classe, \
                patch("scripts.iniciar_online.Thread") as thread, patch("scripts.iniciar_online.monotonic", side_effect=momentos), \
                patch("scripts.iniciar_online.sleep"), redirect_stdout(StringIO()) as saida:
            thread.return_value.is_alive.return_value = True
            agente = classe.return_value
            agente.pronto.is_set.return_value = False
            agente.dominio_incorreto.is_set.return_value = False
            agente.processo.poll.return_value = 1
            agente.codigo_erro = "ERR_NGROK_727"
            executar_servicos(aplicacao_de_prova, [], CONFIG.origem, duracao=1)
            self.assertIn("Localhost continua ativo", saida.getvalue())
            self.assertEqual(criar.call_args.kwargs["listen"], "127.0.0.1:8000")
            criar.return_value.close.assert_called_once()
            criar.return_value.task_dispatcher.shutdown.assert_called_once_with(timeout=5)
            agente.encerrar.assert_called_once()

    def test_overlay_e_conferido_sem_passar_lista_ao_config_check(self):
        instalacao = InstalacaoNgrok(Path("ngrok.exe"), Path("privado.yml"), "3.35.0")
        with patch("scripts.ngrok_processos.subprocess.run", return_value=subprocess.CompletedProcess([], 0)) as executar:
            validar_overlay(instalacao, Path("agente.json"))
        self.assertEqual(executar.call_args.args[0][-1], "agente.json")

    def test_interrupcao_encerra_agente_e_servidor(self):
        with patch("waitress.create_server") as criar, patch("scripts.iniciar_online.ProcessoNgrok") as classe, \
                patch("scripts.iniciar_online.Thread"), redirect_stdout(StringIO()):
            classe.return_value.iniciar.side_effect = KeyboardInterrupt
            with self.assertRaises(KeyboardInterrupt):
                executar_servicos(aplicacao_de_prova, [], CONFIG.origem)
            classe.return_value.encerrar.assert_called_once()
            criar.return_value.close.assert_called_once()
