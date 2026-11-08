"""Diagnóstico CSRF por categorias; nunca serializa requisições ou segredos."""
import json
import logging
from urllib.parse import urlsplit
from django.conf import settings
from django.core.exceptions import DisallowedHost


def contexto_seguro(request):
    """Inspeciona o estado efetivo sem guardar valores de cookies ou cabeçalhos."""
    try:
        host = request.get_host()
    except DisallowedHost:
        host = "rejeitado"
    permitido = host.split(":", 1)[0] in settings.ALLOWED_HOSTS
    origem = request.META.get("HTTP_ORIGIN")
    mesma_origem = ("https://" if request.is_secure() else "http://") + host
    origem_classe = ("ausente" if origem is None else "null" if origem == "null"
                     else "mesma_origem" if origem == mesma_origem else "outra")
    referer = request.META.get("HTTP_REFERER")
    referencia = "ausente"
    if referer is not None:
        try:
            partes = urlsplit(referer)
            referencia = ("mesma_origem_https" if partes.scheme == "https" and partes.netloc == host
                          else "http" if partes.scheme == "http" else "outra")
        except ValueError:
            referencia = "invalida"
    return {
        "metodo": request.method if request.method in ("GET", "POST", "HEAD") else "outro",
        "rota": request.path if request.path in ("/", "/contas/entrar/", "/contas/sair/") else "outra",
        "is_secure": request.is_secure(), "host": host if permitido else "rejeitado",
        "origin_classe": origem_classe, "referer_classe": referencia,
        "cookie_csrf_presente": settings.CSRF_COOKIE_NAME in request.COOKIES,
        "cookie_sessao_presente": settings.SESSION_COOKIE_NAME in request.COOKIES,
        "proxy_validado": bool(request.META.get("entregas.email")),
    }


def categoria_csrf(reason):
    """Converte os motivos Django em uma enumeração fechada, sem interpolação."""
    if not isinstance(reason, str):
        return "csrf_rejeitado"
    for prefixo, categoria in (
        ("Origin checking failed", "origem_nao_confiavel"),
        ("Referer checking failed - no Referer.", "referer_ausente"),
        ("Referer checking failed - Referer is malformed.", "referer_invalido"),
        ("Referer checking failed - Referer is insecure", "referer_http"),
        ("Referer checking failed", "referer_nao_confiavel"),
        ("CSRF cookie not set.", "cookie_csrf_ausente"),
        ("CSRF cookie", "cookie_csrf_invalido"),
        ("CSRF token missing.", "token_csrf_ausente"),
        ("CSRF token", "token_csrf_invalido"),
    ):
        if reason.startswith(prefixo):
            return categoria
    return "csrf_rejeitado"


class FiltroCsrfSeguro(logging.Filter):
    def filter(self, record):
        if getattr(record, "csrf_sanitizado", False):
            return True
        reason = record.args[0] if isinstance(record.args, tuple) and record.args else ""
        request = getattr(record, "request", None)
        dados = {"evento": "csrf_rejeitado", "motivo": categoria_csrf(reason)}
        if request is not None:
            dados.update(contexto_seguro(request))
        record.msg, record.args = json.dumps(dados, ensure_ascii=True), ()
        record.exc_info = record.exc_text = record.stack_info = None
        record.__dict__.pop("request", None)
        record.csrf_sanitizado = True
        return True


def configuracao_logs_csrf():
    """Substitui o motivo bruto do Django por diagnóstico sanitizado no console."""
    return {
        "version": 1, "disable_existing_loggers": False,
        "filters": {"csrf_seguro": {"()": "core.online_diagnostico.FiltroCsrfSeguro"}},
        "formatters": {"mensagem": {"format": "%(message)s"}},
        "handlers": {"csrf_seguro": {"class": "logging.StreamHandler", "formatter": "mensagem",
                                    "filters": ["csrf_seguro"]}},
        "loggers": {"django.security.csrf": {"handlers": ["csrf_seguro"], "level": "WARNING", "propagate": False}},
    }
