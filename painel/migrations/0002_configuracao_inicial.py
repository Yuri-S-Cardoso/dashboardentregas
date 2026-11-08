from decimal import Decimal
from django.db import migrations


def configurar(apps, schema_editor):
    Configuracao = apps.get_model("painel", "Configuracao")
    if not Configuracao.objects.exists():
        Configuracao.objects.create(
            valor_por_baixa=Decimal("5.00"), meta_diaria=Decimal("300.00"),
            meta_semanal=Decimal("1500.00"), meta_mensal=Decimal("6000.00"),
        )


class Migration(migrations.Migration):
    dependencies = [("painel", "0001_initial")]
    operations = [migrations.RunPython(configurar, reverse_code=migrations.RunPython.noop)]
