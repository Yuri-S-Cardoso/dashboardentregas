"""Produtividade sem deduplicação e intervalos cronológicos dentro de cada dia."""
from collections import defaultdict
from core.calculos import ZERO, dividir, segundos_horario


def intervalos_entregas(entregas):
    por_dia = defaultdict(list)
    for entrega in entregas:
        if entrega.horario is not None:
            por_dia[entrega.data].append(segundos_horario(entrega.horario))
    intervalos = []
    for horarios in por_dia.values():
        horarios.sort()
        intervalos.extend(fim - inicio for inicio, fim in zip(horarios, horarios[1:]) if fim > inicio)
    return {
        "intervalos_quantidade": len(intervalos),
        "intervalos_segundos": sum(intervalos, ZERO),
        "intervalo_medio_segundos": dividir(sum(intervalos, ZERO), len(intervalos)),
    }


def totalizar_entregas(entregas):
    entregas = list(entregas)
    baixas = sum(e.situacao == "Baixa realizada" for e in entregas)
    dias = len({e.data for e in entregas})
    return {
        "tentativas": len(entregas), "baixas": baixas,
        "insucessos": sum(e.situacao == "Insucesso" for e in entregas),
        "receita": sum((e.valor_previsto for e in entregas), ZERO),
        "sucesso_percentual": dividir(100 * baixas, len(entregas)),
        "dias_com_entregas": dias,
        "media_diaria_baixas": dividir(baixas, dias),
        **intervalos_entregas(entregas),
    }
