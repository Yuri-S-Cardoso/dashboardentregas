"""Configuração explícita do acesso online; nunca lê ou retorna authtokens."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

# Revisão 2 inclui a política de referência compatível com CSRF em HTTPS.
VERSAO_POLITICA = 2
DOMINIO_NGROK = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+ngrok(?:-free)?\.(?:app|dev|io)\Z")
EMAIL = re.compile(r"[a-z0-9._%+\-]+@[a-z0-9](?:[a-z0-9.\-]*[a-z0-9])?\.[a-z]{2,63}\Z")
CHAVE_PROXY = re.compile(r"[A-Za-z0-9_-]{43,128}\Z")


def validar_dominio(valor):
    if not isinstance(valor, str) or len(valor) > 253 or not DOMINIO_NGROK.fullmatch(valor):
        raise ValueError("Informe somente o domínio ngrok autorizado, em minúsculas, sem https://, porta, caminho ou curinga.")
    return valor


def validar_emails(valores):
    if (not isinstance(valores, list) or not 1 <= len(valores) <= 20
            or any(not isinstance(email, str) or len(email) > 254 or not EMAIL.fullmatch(email) for email in valores)):
        raise ValueError("Informe uma lista explícita de e-mails Google autorizados em minúsculas; domínio inteiro e curingas não são aceitos.")
    return tuple(sorted(set(valores)))


@dataclass(frozen=True)
class ConfiguracaoOnline:
    dominio: str
    emails: tuple[str, ...]
    revisao_aprovada: bool = False
    validacao_externa_sha256: str = ""

    @property
    def origem(self):
        return "https://" + self.dominio

    def identificador_validacao(self, versao_ngrok):
        dados = {"dominio": self.dominio, "emails": self.emails,
                 "politica": VERSAO_POLITICA, "ngrok": versao_ngrok}
        return hashlib.sha256(json.dumps(dados, sort_keys=True).encode()).hexdigest()

    def exigir_ativacao_aprovada(self, versao_ngrok):
        if not self.revisao_aprovada or self.validacao_externa_sha256 != self.identificador_validacao(versao_ngrok):
            raise ValueError("Ativação com dados reais bloqueada: revise o relatório e valide OAuth/e-mail/HTTPS com --testar-protecao. Registre a aprovação da configuração atual no arquivo privado; não desative as proteções.")


def carregar_configuracao(caminho):
    try:
        arquivo = Path(caminho)
        if arquivo.stat().st_size > 16384:
            raise ValueError
        dados = json.loads(arquivo.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        raise ValueError("Configuração online ausente ou inválida. Consulte docs/ACESSO_NGROK.md e .local/ngrok_online.json.") from None
    campos = {"dominio", "emails_autorizados", "revisao_aprovada", "validacao_externa_sha256"}
    if (not isinstance(dados, dict) or set(dados) != campos or type(dados["revisao_aprovada"]) is not bool
            or not isinstance(dados["validacao_externa_sha256"], str)):
        raise ValueError("A configuração online deve conter somente domínio, e-mails e os dois campos de aprovação do exemplo. Não inclua credenciais.")
    return ConfiguracaoOnline(validar_dominio(dados["dominio"]), validar_emails(dados["emails_autorizados"]),
                              dados["revisao_aprovada"], dados["validacao_externa_sha256"])


def gerar_politica(configuracao, chave_proxy):
    """OAuth, lista exata e cabeçalhos autenticados; nunca aceita só 'conta Google'."""
    if not CHAVE_PROXY.fullmatch(chave_proxy):
        raise ValueError("A credencial temporária do proxy não foi inicializada corretamente.")
    return {"on_http_request": [
        {"actions": [{"type": "oauth", "config": {"provider": "google"}}]},
        {"expressions": ["!(actions.ngrok.oauth.identity.email in " + json.dumps(configuracao.emails) + ")"],
         "actions": [{"type": "deny", "config": {"status_code": 403}}]},
        {"actions": [
            {"type": "remove-headers", "config": {"headers": [
                "forwarded", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "x-forwarded-port",
                "x-entregas-proxy-key", "x-entregas-oauth-email", "x-entregas-https"]}},
            {"type": "add-headers", "config": {"headers": {
                "host": configuracao.dominio, "x-entregas-proxy-key": chave_proxy,
                "x-entregas-oauth-email": "${actions.ngrok.oauth.identity.email}", "x-entregas-https": "https"}}},
        ]},
    ]}
