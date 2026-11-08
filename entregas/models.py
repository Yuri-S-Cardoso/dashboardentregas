from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from core.models import RegistroOrigem
from painel.models import valor_baixa_atual


class Entrega(RegistroOrigem):
    class Situacao(models.TextChoices):
        BAIXA = "Baixa realizada", "Baixa realizada"
        INSUCESSO = "Insucesso", "Insucesso"

    codigo = models.CharField("código", max_length=100, db_index=True)
    data = models.DateField(db_index=True)
    horario = models.TimeField("horário", null=True, blank=True)
    situacao = models.CharField("situação", max_length=20, choices=Situacao.choices)
    ordem_original = models.PositiveIntegerField(null=True, blank=True, editable=False)
    valor_por_baixa = models.DecimalField(
        "valor por baixa preservado (R$)", max_digits=10, decimal_places=2,
        default=valor_baixa_atual, validators=[MinValueValidator(0)], editable=False,
    )

    class Meta(RegistroOrigem.Meta):
        ordering = ["-data", "ordem_original", "pk"]
        constraints = RegistroOrigem.Meta.constraints + [
            models.CheckConstraint(condition=models.Q(valor_por_baixa__gte=0), name="entrega_valor_positivo"),
            models.CheckConstraint(condition=models.Q(situacao__in=["Baixa realizada", "Insucesso"]), name="entrega_situacao_valida"),
        ]

    @property
    def valor_previsto(self):
        return self.valor_por_baixa if self.situacao == self.Situacao.BAIXA else Decimal("0.00")

    def __str__(self):
        return f"{self.codigo} · {self.data:%d/%m/%Y}"


class LoteEntrega(models.Model):
    """Recibo transacional de uma solicitação, sem impor unicidade aos códigos."""
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    chave = models.UUIDField()
    sha256 = models.CharField(max_length=64)
    quantidade = models.PositiveIntegerField()
    data_padrao = models.DateField()
    situacao_padrao = models.CharField(max_length=20, choices=Entrega.Situacao.choices)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["usuario", "chave"], name="entrega_lote_usuario_chave_unica")]
