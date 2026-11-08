"""Perfil separado: o inicializador local continua usando config.settings."""
import json
import os
from django.core.exceptions import ImproperlyConfigured
from .settings import *  # noqa: F403
from .acesso_online import CHAVE_PROXY, validar_dominio, validar_emails
from core.online_diagnostico import configuracao_logs_csrf

try:
    ONLINE_DOMINIO = validar_dominio(os.environ.get("ENTREGAS_ONLINE_DOMINIO", ""))
    ONLINE_EMAILS = validar_emails(json.loads(os.environ.get("ENTREGAS_ONLINE_EMAILS", "[]")))
    ONLINE_PROXY_KEY = os.environ.get("ENTREGAS_ONLINE_PROXY_KEY", "")
    if not CHAVE_PROXY.fullmatch(ONLINE_PROXY_KEY):
        raise ValueError
except (ValueError, TypeError):
    raise ImproperlyConfigured("Use o inicializador online com domínio, lista de e-mails e proxy controlado; não habilite este perfil isoladamente.") from None

DEBUG = False
ALLOWED_HOSTS = ["localhost", "127.0.0.1", ONLINE_DOMINIO]
CSRF_TRUSTED_ORIGINS = ["https://" + ONLINE_DOMINIO]
SESSION_COOKIE_NAME = "entregas_online_sessionid"
CSRF_COOKIE_NAME = "entregas_online_csrftoken"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_DOMAIN = None
SECURE_PROXY_SSL_HEADER = ("HTTP_X_ENTREGAS_HTTPS", "https")
USE_X_FORWARDED_HOST = False
USE_X_FORWARDED_PORT = False
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
# Permite validar formulários da própria origem sem enviar referência a terceiros.
# no-referrer faz navegadores enviarem Origin: null em POST de navegação.
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
ONLINE_LOGIN_LIMITE = 5
ONLINE_LOGIN_JANELA = 900
LOGGING = configuracao_logs_csrf()
MIDDLEWARE = [
    "core.online_middleware.CookiesOnlineMiddleware",
    "core.online_middleware.SegurancaOnlineMiddleware",
    *[m for m in MIDDLEWARE if m != "django.middleware.security.SecurityMiddleware"],  # noqa: F405
    "core.online_middleware.LimitarLoginOnlineMiddleware",
]
