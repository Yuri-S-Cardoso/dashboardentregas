from datetime import timedelta
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from core.models import RegistroOrigem


class Jornada(RegistroOrigem):
    data = models.DateField(db_index=True)
    inicio_real = models.TimeField("início real", null=True, blank=True)
    fim_real = models.TimeField("fim real", null=True, blank=True)
    odometro_inicial = models.DecimalField("odômetro inicial (km)", max_digits=12, decimal_places=3, null=True, blank=True, validators=[MinValueValidator(0)])
    odometro_final = models.DecimalField("odômetro final (km)", max_digits=12, decimal_places=3, null=True, blank=True, validators=[MinValueValidator(0)])
    litros_consumidos = models.DecimalField("litros consumidos", max_digits=10, decimal_places=3, null=True, blank=True, validators=[MinValueValidator(0)])
    custo_combustivel = models.DecimalField("combustível (R$)", max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    outros_custos = models.DecimalField("outros custos (R$)", max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    janela_historica = models.DurationField("janela observada histórica", null=True, blank=True, validators=[MinValueValidator(timedelta(0))], help_text="Formato: HH:MM:SS. Não substitui os horários reais.")

    class Meta(RegistroOrigem.Meta):
        ordering = ["-data", "pk"]
        constraints = RegistroOrigem.Meta.constraints + [models.CheckConstraint(
            condition=models.Q(**{f"{campo}__gte": 0}) | models.Q(**{f"{campo}__isnull": True}),
            name=f"jornada_{campo}_positivo",
        ) for campo in ("odometro_inicial", "odometro_final", "litros_consumidos", "custo_combustivel", "outros_custos")] + [
            models.CheckConstraint(condition=models.Q(odometro_final__gte=models.F("odometro_inicial")) | models.Q(odometro_inicial__isnull=True) | models.Q(odometro_final__isnull=True), name="jornada_odometros_validos")
        ]

    def clean(self):
        super().clean()
        if self.odometro_inicial is not None and self.odometro_final is not None and self.odometro_final < self.odometro_inicial:
            raise ValidationError({"odometro_final": "O odômetro final não pode ser menor que o inicial."})

    @property
    def quilometragem(self):
        if self.odometro_inicial is None or self.odometro_final is None:
            return None
        return self.odometro_final - self.odometro_inicial

    def __str__(self):
        return f"Jornada · {self.data:%d/%m/%Y}"
