"""Períodos civis inclusivos, semanas de domingo a sábado e quinzenas."""
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta


def periodo_mes(ano, mes):
    return date(ano, mes, 1), date(ano, mes, monthrange(ano, mes)[1])


def periodo_semana(dia):
    # date.min não possui o domingo anterior representável.
    inicio = dia - timedelta(days=min((dia.weekday() + 1) % 7, (dia - date.min).days))
    return inicio, min(date.max, inicio + timedelta(days=min(6, (date.max - inicio).days)))


def periodo_quinzena(dia):
    inicio, fim = periodo_mes(dia.year, dia.month)
    return (inicio, dia.replace(day=15)) if dia.day <= 15 else (dia.replace(day=16), fim)


@dataclass(frozen=True)
class FiltroPeriodo:
    inicio: date | None = None
    fim: date | None = None

    def aplicar(self, queryset, campo="data"):
        if self.inicio:
            queryset = queryset.filter(**{f"{campo}__gte": self.inicio})
        if self.fim:
            queryset = queryset.filter(**{f"{campo}__lte": self.fim})
        return queryset

    def contem(self, dia):
        return (self.inicio is None or dia >= self.inicio) and (self.fim is None or dia <= self.fim)

    def cobre(self, inicio, fim):
        return (self.inicio is None or self.inicio <= inicio) and (self.fim is None or self.fim >= fim)

    @property
    def descricao(self):
        if self.inicio is None and self.fim is None:
            return "Todo o histórico"
        return f"{self.inicio:%d/%m/%Y} a {self.fim:%d/%m/%Y}"
