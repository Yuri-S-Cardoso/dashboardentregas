"""Segurança somente do perfil online, com exceção HTTP restrita ao loopback."""
import hashlib
import hmac
from math import ceil
from threading import Lock
from time import monotonic
from django.conf import settings
from django.http import HttpResponse
from django.middleware.security import SecurityMiddleware


class SegurancaOnlineMiddleware(SecurityMiddleware):
    def process_request(self, request):
        if request.META.get("entregas.local") is True:
            return None
        return super().process_request(request)


class CookiesOnlineMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        resposta = self.get_response(request)
        if request.META.get("entregas.local") is True:
            for nome in (settings.SESSION_COOKIE_NAME, settings.CSRF_COOKIE_NAME):
                if nome in resposta.cookies:
                    resposta.cookies[nome]["secure"] = False
        else:
            resposta["Cache-Control"] = "private, no-store"
            resposta["Pragma"] = "no-cache"
        return resposta


class TentativasLogin:
    """Contador limitado, atômico entre workers; reiniciar o processo o reinicia."""
    def __init__(self, relogio=monotonic):
        self.relogio, self.lock, self.itens = relogio, Lock(), {}

    def reservar(self, chaves, limite, janela):
        agora = self.relogio()
        with self.lock:
            self.itens = {chave: valor for chave, valor in self.itens.items() if valor[1] > agora}
            bloqueios = [self.itens[chave][1] - agora for chave in chaves
                         if chave in self.itens and self.itens[chave][0] >= limite]
            if bloqueios or len(self.itens) >= 5000:
                return max(1, ceil(max(bloqueios, default=janela)))
            for chave in chaves:
                contador, fim = self.itens.get(chave, (0, agora + janela))
                self.itens[chave] = (contador + 1, fim)
        return 0

    def limpar(self, chaves):
        with self.lock:
            for chave in chaves:
                self.itens.pop(chave, None)


tentativas_login = TentativasLogin()


class LimitarLoginOnlineMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (request.method != "POST" or request.path not in ("/contas/entrar/", "/admin/login/")
                or request.META.get("entregas.local") is True
                or (request.path == "/contas/entrar/" and request.user.is_authenticated)):
            return self.get_response(request)
        # Não registra usuário, e-mail, senha, IP ou corpo da requisição em logs.
        valores = ["usuario:" + request.POST.get("username", "").strip().casefold()[:254],
                   "identidade:" + request.META.get("entregas.email", "")]
        chaves = [hmac.new(settings.SECRET_KEY.encode(), valor.encode(), hashlib.sha256).hexdigest() for valor in valores]
        espera = tentativas_login.reservar(chaves, settings.ONLINE_LOGIN_LIMITE, settings.ONLINE_LOGIN_JANELA)
        if espera:
            resposta = HttpResponse("Muitas tentativas de acesso. Aguarde antes de tentar novamente.", status=429,
                                    content_type="text/plain; charset=utf-8")
            resposta["Retry-After"] = str(espera)
            return resposta
        resposta = self.get_response(request)
        if (resposta.status_code in (302, 303) and request.user.is_authenticated
                and request.user.get_username().casefold() == request.POST.get("username", "").strip().casefold()):
            tentativas_login.limpar(chaves)
        return resposta
