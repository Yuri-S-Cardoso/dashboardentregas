import json
from zipfile import BadZipFile
from openpyxl.utils.exceptions import InvalidFileException
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from entregas.services.importacao import importar_excel


class Command(BaseCommand):
    help = "Importa as quatro abas em transação, preservando duplicados e edições manuais."

    def add_arguments(self, parser):
        parser.add_argument("arquivo")

    def handle(self, *args, **options):
        try:
            lote, criado = importar_excel(options["arquivo"])
        except (OSError, ValueError, ValidationError, BadZipFile, InvalidFileException) as erro:
            raise CommandError(f"Importação cancelada; nenhuma alteração foi gravada. {erro}") from erro
        if criado:
            self.stdout.write(self.style.SUCCESS(f"Importação #{lote.pk} concluída. SHA-256: {lote.sha256}"))
        else:
            self.stdout.write("Arquivo já importado. Nenhum registro criado, restaurado ou sobrescrito.")
        self.stdout.write(json.dumps(lote.resumo, ensure_ascii=False, indent=2))
        for aviso in lote.avisos:
            self.stdout.write(self.style.WARNING(aviso))
