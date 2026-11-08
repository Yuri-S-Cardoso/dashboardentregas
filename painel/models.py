"""Cada alteração cria uma versão; entregas guardam o preço da sua criação."""
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models


def valor_baixa_atual():
    return Configuracao.atual().valor_por_baixa


class Configuracao(models.Model):
    valor_por_baixa = models.DecimalField("valor por baixa (R$)", max_digits=10, decimal_places=2, default=Decimal("5.00"), validators=[MinValueValidator(0)])
    meta_diaria = models.DecimalField("meta diária (R$)", max_digits=12, decimal_places=2, default=Decimal("300.00"), validators=[MinValueValidator(0)])
    meta_semanal = models.DecimalField("meta semanal (R$)", max_digits=12, decimal_places=2, default=Decimal("1500.00"), validators=[MinValueValidator(0)])
    meta_mensal = models.DecimalField("meta mensal (R$)", max_digits=12, decimal_places=2, default=Decimal("6000.00"), validators=[MinValueValidator(0)])
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "configuração"
        verbose_name_plural = "configurações"
        constraints = [models.CheckConstraint(
            condition=models.Q(**{f"{campo}__gte": 0}), name=f"config_{campo}_positivo"
        ) for campo in ("valor_por_baixa", "meta_diaria", "meta_semanal", "meta_mensal")]

    @classmethod
    def atual(cls):
        return cls.objects.order_by("-pk").first() or cls()

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValueError("Configurações históricas são imutáveis. Crie uma nova versão.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Versão {self.pk or 'inicial'} · R$ {self.valor_por_baixa}/baixa"
