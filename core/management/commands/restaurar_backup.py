"""Restauração interativa: nunca utilizada automaticamente no banco real."""
from pathlib import Path
import os
import sqlite3
from tempfile import TemporaryDirectory
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from core.backups import copiar_sqlite, criar_backup, verificar_backup
from core.locks import trava_exclusiva


class Command(BaseCommand):
    help = "Testa um backup isoladamente, preserva o banco atual e exige confirmação para restaurar. Servidor deve estar encerrado."

    def add_arguments(self, parser):
        parser.add_argument("arquivo")

    def handle(self, *args, **options):
        banco = Path(settings.DATABASES["default"]["NAME"]).resolve()
        selecionado = Path(options["arquivo"]).resolve()
        pasta_local = settings.BASE_DIR / ".local"
        pasta_testes = pasta_local / "restauracoes"
        pasta_testes.mkdir(parents=True, exist_ok=True)
        try:
            with trava_exclusiva(pasta_local / "servidor.lock"):
                if selecionado == banco:
                    raise ValueError("Selecione um backup diferente do banco em uso.")
                info = verificar_backup(selecionado)
                connections.close_all()
                if any(Path(str(banco) + sufixo).exists() for sufixo in ("-wal", "-shm", "-journal")):
                    raise ValueError("Existem arquivos de transação do SQLite. Feche todos os acessos; não remova esses arquivos manualmente.")
                with TemporaryDirectory(prefix="teste_", dir=pasta_testes) as temporario:
                    pasta = Path(temporario).resolve()
                    assert pasta.is_relative_to(pasta_testes.resolve())
                    candidato = pasta / "restaurado.sqlite3"
                    copiar_sqlite(selecionado, candidato)
                    protegido, _ = criar_backup(banco, pasta_local / "backups")
                    self.stdout.write(f"Backup selecionado: {selecionado}\nSHA-256: {info['sha256']}\nCópia atual preservada em: {protegido}")
                    self.stdout.write("A cópia isolada foi aberta e passou pela integridade. Encerre TODOS os servidores e acessos SQLite antes de confirmar.")
                    try:
                        resposta = input("Para substituir o banco atual, digite RESTAURAR: ")
                    except EOFError:
                        resposta = ""
                    if resposta != "RESTAURAR":
                        self.stdout.write("Cancelado. O banco atual não foi substituído.")
                        return
                    os.replace(candidato, banco)
                    verificar_backup(banco, conferir_manifesto=False)
                    self.stdout.write(self.style.SUCCESS("Banco restaurado e verificado. Inicie o sistema novamente."))
        except (OSError, ValueError, RuntimeError, sqlite3.Error) as erro:
            raise CommandError(f"Restauração não concluída: {erro}") from erro
