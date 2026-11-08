"""Metas da versão selecionada e cenários condicionais, sem escala presumida."""
from core.calculos import dividir, dinheiro


def acompanhar_meta(receita, meta):
    return {
        "meta": meta, "percentual_meta": dividir(100 * receita, meta),
        "faltante_meta": max(meta - receita, 0),
    }


def projetar(receita, dias_observados, dias_cenario):
    media = dividir(receita, dias_observados)
    return {
        "dias_observados": dias_observados, "dias_cenario": dias_cenario,
        "media_receita_dia": media,
        "receita_cenario": dinheiro(media * dias_cenario) if media is not None else None,
        "metodologia": "Receita média por dia com entregas × dias com entregas do cenário. Não presume dias de trabalho, receita em dias sem registros ou continuidade da média.",
    }
