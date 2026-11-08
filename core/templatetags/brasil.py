from django import template
from django.utils.formats import number_format
from decimal import Decimal, ROUND_HALF_UP

register = template.Library()


@register.filter
def reais(valor):
    if valor is None:
        return "Não informado"
    return f"R$ {number_format(valor, decimal_pos=2, use_l10n=True)}"


@register.filter
def numero(valor):
    if valor is None:
        return "Não informado"
    return number_format(valor, decimal_pos=3, use_l10n=True)


@register.filter
def indicador(valor):
    return "Não informado" if valor is None else number_format(valor, decimal_pos=2, use_l10n=True)


@register.filter
def duracao(valor):
    if valor is None:
        return "Não informado"
    segundos = int(Decimal(valor).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    return f"{segundos // 3600:02d}:{segundos % 3600 // 60:02d}:{segundos % 60:02d}"
