from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from core.models import RegistroOrigem


class EspelhoEmpresa(RegistroOrigem):
    data_competencia = models.DateField("data da competência", db_index=True)
    baixas_pagas = models.PositiveIntegerField("baixas pagas", null=True, blank=True)
    insucessos = models.PositiveIntegerField(null=True, blank=True)
    valor_empresa = models.DecimalField("valor da empresa (R$)", max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    vencimento = models.DateField(null=True, blank=True)
    documento = models.CharField("documento", max_length=255, blank=True)
    observacoes = models.TextField("observações", blank=True)

    class Meta(RegistroOrigem.Meta):
        ordering = ["-data_competencia", "pk"]
        verbose_name = "espelho da empresa"
        verbose_name_plural = "espelhos da empresa"
        constraints = RegistroOrigem.Meta.constraints + [models.CheckConstraint(
            condition=models.Q(valor_empresa__gte=0) | models.Q(valor_empresa__isnull=True),
            name="espelho_valor_positivo",
        )]

    def __str__(self):
        return f"Espelho · {self.data_competencia:%d/%m/%Y} · {self.documento}"


class Pagamento(RegistroOrigem):
    data_pagamento = models.DateField("data do pagamento")
    inicio_quinzena = models.DateField("início da quinzena")
    fim_quinzena = models.DateField("fim da quinzena")
    valor_recebido = models.DecimalField("valor recebido (R$)", max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    comprovante = models.CharField("referência do comprovante", max_length=255, blank=True)
    observacoes = models.TextField("observações", blank=True)

    class Meta(RegistroOrigem.Meta):
        ordering = ["-data_pagamento", "pk"]
        constraints = RegistroOrigem.Meta.constraints + [
            models.CheckConstraint(condition=models.Q(valor_recebido__gte=0), name="pagamento_valor_positivo"),
            models.CheckConstraint(condition=models.Q(fim_quinzena__gte=models.F("inicio_quinzena")), name="pagamento_periodo_valido"),
        ]

    def clean(self):
        super().clean()
        if self.inicio_quinzena and self.fim_quinzena and self.fim_quinzena < self.inicio_quinzena:
            raise ValidationError({"fim_quinzena": "O fim deve ser igual ou posterior ao início."})

    def __str__(self):
        return f"Pagamento · {self.data_pagamento:%d/%m/%Y} · R$ {self.valor_recebido}"
