"""Fronteira WSGI: autentica o proxy antes de alcançar qualquer rota Django."""
import hmac
import re

HOST_LOCAL = re.compile(r"(?:localhost|127\.0\.0\.1)(?::[0-9]{1,5})?\Z")


class ProxyOnline:
    def __init__(self, application, configuracao, chave):
        self.application, self.configuracao, self.chave = application, configuracao, chave

    @staticmethod
    def rejeitar(start_response, status):
        corpo = "Acesso não permitido.\n".encode()
        start_response(status, [("Content-Type", "text/plain; charset=utf-8"),
                                ("Content-Length", str(len(corpo))), ("Cache-Control", "no-store"),
                                ("X-Frame-Options", "DENY"), ("X-Content-Type-Options", "nosniff")])
        return [corpo]

    def __call__(self, environ, start_response):
        host = environ.get("HTTP_HOST", "").lower()
        chave = environ.pop("HTTP_X_ENTREGAS_PROXY_KEY", "")
        email = environ.pop("HTTP_X_ENTREGAS_OAUTH_EMAIL", "").lower()
        protocolo = environ.pop("HTTP_X_ENTREGAS_HTTPS", "")
        # Descarta inclusive listas forjadas 'https,http'; nunca usa o primeiro XFP.
        for nome in list(environ):
            if nome == "HTTP_FORWARDED" or nome.startswith(("HTTP_X_FORWARDED_", "HTTP_NGROK_AUTH_")):
                environ.pop(nome)
        environ["entregas.local"] = False
        environ.pop("entregas.email", None)
        environ["wsgi.url_scheme"] = "http"
        if environ.get("REMOTE_ADDR") != "127.0.0.1":
            return self.rejeitar(start_response, "403 Forbidden")
        if HOST_LOCAL.fullmatch(host):
            if chave or email:
                return self.rejeitar(start_response, "403 Forbidden")
            environ["entregas.local"] = True
        elif host in (self.configuracao.dominio, self.configuracao.dominio + ":443"):
            if (not hmac.compare_digest(chave.encode(), self.chave.encode())
                    or email not in self.configuracao.emails or protocolo != "https"):
                return self.rejeitar(start_response, "403 Forbidden")
            # Só este código produz o sinal HTTPS que settings_online confia.
            environ["HTTP_X_ENTREGAS_HTTPS"] = "https"
            environ["entregas.email"] = email
        else:
            return self.rejeitar(start_response, "400 Bad Request")
        return self.application(environ, start_response)
