"""Agregação de apresentação: mês completo e suas duas quinzenas civis."""
from zoneinfo import ZoneInfo

from django.utils import timezone

from core.periodos import periodo_mes
from entregas.services.indicadores import totalizar_entregas


def calcular_faturamento_quinzenal(historico, filtro):
    """Usa o mês do filtro único; histórico/múltiplos meses usam o mês vigente.

    Reutiliza a receita prevista e os preços históricos do totalizador aprovado.
    A lista completa já carregada permite mostrar o mês inteiro mesmo se o filtro
    for diário/semanal/quinzenal, sem mudar os demais indicadores ou exportações.
    """
    if (filtro.inicio and filtro.fim
            and (filtro.inicio.year, filtro.inicio.month) == (filtro.fim.year, filtro.fim.month)):
        referencia = filtro.inicio
    else:
        referencia = timezone.localtime(timezone.now(), ZoneInfo("America/Sao_Paulo")).date()
    inicio, fim = periodo_mes(referencia.year, referencia.month)
    mensais = [e for e in historico if inicio <= e.data <= fim]
    return {
        "inicio": inicio, "fim": fim, "rotulo": f"{inicio:%m/%Y}",
        "mensal": totalizar_entregas(mensais)["receita"],
        "primeira_quinzena": totalizar_entregas([e for e in mensais if e.data.day <= 15])["receita"],
        "segunda_quinzena": totalizar_entregas([e for e in mensais if e.data.day >= 16])["receita"],
    }
