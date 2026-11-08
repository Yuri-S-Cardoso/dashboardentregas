from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from pathlib import Path
import sqlite3
from core.backups import criar_backup


class Command(BaseCommand):
    help = "Cria backup consistente em .local/backups e verifica integridade, tamanho e SHA-256."

    def handle(self, *args, **options):
        try:
            caminho, resultado = criar_backup(
                Path(settings.DATABASES["default"]["NAME"]), settings.BASE_DIR / ".local" / "backups"
            )
        except (OSError, ValueError, sqlite3.Error) as erro:
            raise CommandError(f"Backup não concluído: {erro}") from erro
        self.stdout.write(self.style.SUCCESS(f"Backup verificado: {caminho}"))
        self.stdout.write(f"Tamanho: {resultado['bytes']} bytes\nSHA-256: {resultado['sha256']}")
