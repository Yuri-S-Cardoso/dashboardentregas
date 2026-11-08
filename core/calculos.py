"""Aritmética de relatórios: Decimal e ausência explícita de dados."""
from decimal import Decimal, ROUND_HALF_UP

ZERO = Decimal("0")
CENTAVO = Decimal("0.01")


def dinheiro(valor):
    return Decimal(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def dividir(numerador, denominador):
    if numerador is None or denominador is None or denominador <= 0:
        return None
    return Decimal(numerador) / Decimal(denominador)


def somar_conhecidos(valores):
    """Retorna None quando não existe sequer um valor informado, preservando zero."""
    informados = [valor for valor in valores if valor is not None]
    return sum(informados, ZERO) if informados else None


def segundos_duracao(duracao):
    return Decimal(duracao.days * 86400 + duracao.seconds) + Decimal(duracao.microseconds) / 1000000


def segundos_horario(horario):
    return Decimal(horario.hour * 3600 + horario.minute * 60 + horario.second) + Decimal(horario.microsecond) / 1000000
