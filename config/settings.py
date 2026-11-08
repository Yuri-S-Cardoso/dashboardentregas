"""Configuração local: não publicar este servidor na internet."""
import os
import secrets
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
from .rede import hosts_permitidos

BASE_DIR = Path(__file__).resolve().parent.parent


def chave_local():
    """Cria um segredo aleatório persistente fora do código versionável."""
    pasta = BASE_DIR / ".local"
    pasta.mkdir(exist_ok=True)
    arquivo = pasta / "secret_key"
    try:
        with arquivo.open("x", encoding="utf-8") as destino:
            destino.write(secrets.token_urlsafe(64))
    except FileExistsError:
        pass
    return arquivo.read_text(encoding="utf-8").strip()


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or chave_local()
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
try:
    ALLOWED_HOSTS = hosts_permitidos(os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]"))
except ValueError as erro:
    raise ImproperlyConfigured(str(erro)) from erro

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "core", "painel", "entregas", "conferencia", "jornadas",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3",
    "OPTIONS": {"timeout": 20},
}}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = True
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
WHITENOISE_ALLOW_ALL_ORIGINS = False
WHITENOISE_MAX_AGE = 0
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "painel:inicio"
LOGOUT_REDIRECT_URL = "login"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_FAILURE_VIEW = "core.errors.csrf_failure"
X_FRAME_OPTIONS = "DENY"
