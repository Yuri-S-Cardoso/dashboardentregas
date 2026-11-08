"""Cópias consistentes por API SQLite; nunca copia um arquivo aberto diretamente."""
from contextlib import closing
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
from uuid import uuid4
from zoneinfo import ZoneInfo

TABELAS_OBRIGATORIAS = {
    "entregas_entrega", "conferencia_espelhoempresa", "conferencia_pagamento",
    "jornadas_jornada", "painel_configuracao", "core_importacao", "django_migrations",
}


def sha256_arquivo(caminho):
    with Path(caminho).open("rb") as arquivo:
        return hashlib.file_digest(arquivo, "sha256").hexdigest()


def conectar_leitura(caminho):
    return sqlite3.connect(Path(caminho).resolve().as_uri() + "?mode=ro", uri=True, timeout=20)


def verificar_backup(caminho, conferir_manifesto=True):
    caminho = Path(caminho).resolve()
    if not caminho.is_file():
        raise ValueError("O arquivo de banco não foi encontrado.")
    with closing(conectar_leitura(caminho)) as banco:
        if banco.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("A verificação de integridade do SQLite falhou.")
        tabelas = {linha[0] for linha in banco.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not TABELAS_OBRIGATORIAS <= tabelas:
            raise ValueError("O arquivo não contém as tabelas esperadas do sistema de entregas.")
    resultado = {"arquivo": caminho.name, "bytes": caminho.stat().st_size, "sha256": sha256_arquivo(caminho), "integridade": "ok"}
    manifesto = caminho.with_suffix(caminho.suffix + ".json")
    if conferir_manifesto and manifesto.exists():
        esperado = json.loads(manifesto.read_text(encoding="utf-8"))
        if resultado["sha256"] != esperado["sha256"] or resultado["bytes"] != esperado["bytes"]:
            raise ValueError("O arquivo diverge do tamanho ou SHA-256 registrado no manifesto.")
    return resultado


def copiar_sqlite(origem, destino):
    """SQLite coordena a leitura com conexões ativas e inclui dados confirmados."""
    origem, destino = Path(origem).resolve(), Path(destino).resolve()
    if origem == destino or not origem.is_file() or destino.exists():
        raise ValueError("Origem ausente ou destino já existente; nenhuma substituição foi feita.")
    with closing(conectar_leitura(origem)) as fonte, closing(sqlite3.connect(destino)) as copia:
        fonte.backup(copia, pages=256, sleep=0.05)
    return verificar_backup(destino, conferir_manifesto=False)


def criar_backup(origem, diretorio):
    origem, diretorio = Path(origem).resolve(), Path(diretorio).resolve()
    if not origem.is_file():
        raise ValueError("O banco de origem não existe; nenhum banco vazio foi criado.")
    diretorio.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(diretorio).free < origem.stat().st_size * 2 + 10485760:
        raise ValueError("Espaço insuficiente: mantenha pelo menos duas vezes o banco e 10 MB livres.")
    agora = datetime.now(ZoneInfo("America/Sao_Paulo"))
    nome = f"entregas_{agora:%Y%m%d_%H%M%S_%f}_{uuid4().hex[:8]}.sqlite3"
    destino = diretorio / nome
    temporario = destino.with_suffix(".incompleto")
    copiar_sqlite(origem, temporario)
    temporario.rename(destino)
    resultado = verificar_backup(destino, conferir_manifesto=False)
    resultado["criado_em"] = agora.isoformat()
    destino.with_suffix(destino.suffix + ".json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino, resultado
