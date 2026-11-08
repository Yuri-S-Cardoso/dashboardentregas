"""Horas, distâncias e custos com coberturas explícitas e conjuntos compatíveis."""
from collections import defaultdict
from core.calculos import ZERO, dividir, segundos_duracao, segundos_horario, somar_conhecidos


def calcular_jornada(jornada):
    """Real tem prioridade; duração histórica só é usada na ausência do par real."""
    segundos, origem = None, "Não informado"
    if jornada.inicio_real is not None and jornada.fim_real is not None:
        segundos = segundos_horario(jornada.fim_real) - segundos_horario(jornada.inicio_real)
        if segundos < 0:
            segundos += 86400
        origem = "Real"
    elif jornada.janela_historica is not None:
        segundos = segundos_duracao(jornada.janela_historica)
        origem = "Histórica"
    custo = somar_conhecidos([jornada.custo_combustivel, jornada.outros_custos])
    return {
        "id": jornada.pk, "data": jornada.data, "segundos": segundos,
        "horas": dividir(segundos, 3600), "origem_duracao": origem,
        "km": jornada.quilometragem, "litros": jornada.litros_consumidos,
        "combustivel": jornada.custo_combustivel, "outros": jornada.outros_custos,
        "custos_conhecidos": custo,
        "custos_completos": jornada.custo_combustivel is not None and jornada.outros_custos is not None,
        "horario_incompleto": (jornada.inicio_real is None) != (jornada.fim_real is None),
    }


def consolidar_jornadas(jornadas, movimento):
    """Movimento contém os totais de entregas por data do mesmo recorte.

    Totais conhecidos nunca completam lacunas com zero. Taxas de horas exigem
    cobertura de todas as datas operacionais. Consumo e taxas por KM usam apenas
    pares comparáveis; receitas são vinculadas à data, nunca repetidas por jornada.
    """
    jornadas = list(jornadas)
    por_dia = defaultdict(list)
    for jornada in jornadas:
        por_dia[jornada["data"]].append(jornada)
    dias_com_entregas = {dia for dia, dados in movimento.items() if dados["tentativas"]}
    cobertura = dias_com_entregas <= set(por_dia)
    relevante = bool(dias_com_entregas or jornadas)
    duracao_completa = relevante and cobertura and all(j["segundos"] is not None for j in jornadas)
    custos_completos = relevante and cobertura and all(j["custos_completos"] for j in jornadas)
    km_completo = relevante and cobertura and all(j["km"] is not None for j in jornadas)
    reais = somar_conhecidos(j["segundos"] for j in jornadas if j["origem_duracao"] == "Real")
    historicas = somar_conhecidos(j["segundos"] for j in jornadas if j["origem_duracao"] == "Histórica")
    segundos = somar_conhecidos(j["segundos"] for j in jornadas)
    horas = dividir(segundos, 3600)
    origem = "Mista: real e histórica" if reais is not None and historicas is not None else "Real" if reais is not None else "Histórica" if historicas is not None else "Não informado"
    receita = sum((d["receita"] for d in movimento.values()), ZERO)
    baixas = sum(d["baixas"] for d in movimento.values())
    custos = somar_conhecidos(j["custos_conhecidos"] for j in jornadas)

    consumo = [j for j in jornadas if j["km"] is not None and j["litros"] is not None and j["litros"] > 0]
    km_consumo = somar_conhecidos(j["km"] for j in consumo)
    litros_consumo = somar_conhecidos(j["litros"] for j in consumo)
    custos_km = [j for j in jornadas if j["km"] is not None and j["custos_conhecidos"] is not None]
    dias_km = {dia for dia, itens in por_dia.items() if all(j["km"] is not None for j in itens)}
    receita_km = sum((d["receita"] for dia, d in movimento.items() if dia in dias_km), ZERO)
    km_receita = somar_conhecidos(j["km"] for dia, itens in por_dia.items() if dia in dias_km for j in itens)
    dias_custo = dias_com_entregas & {j["data"] for j in jornadas if j["custos_conhecidos"] is not None}
    custo_com_entregas = somar_conhecidos(j["custos_conhecidos"] for j in jornadas if j["data"] in dias_custo)
    tentativas_custo = sum(movimento[dia]["tentativas"] for dia in dias_custo)
    return {
        "horas": horas, "horas_reais": dividir(reais, 3600),
        "horas_historicas": dividir(historicas, 3600), "segundos": segundos,
        "origem_duracao": origem, "duracao_completa": duracao_completa,
        "baixas_por_hora": dividir(baixas, horas) if duracao_completa else None,
        "ganho_por_hora": dividir(receita, horas) if duracao_completa else None,
        "km": somar_conhecidos(j["km"] for j in jornadas), "km_completo": km_completo,
        "litros": somar_conhecidos(j["litros"] for j in jornadas),
        "litros_completo": relevante and cobertura and all(j["litros"] is not None for j in jornadas),
        "consumo_km_l": dividir(km_consumo, litros_consumo),
        "consumo_completo": relevante and cobertura and bool(jornadas) and len(consumo) == len(jornadas),
        "km_consumo": km_consumo, "litros_consumo": litros_consumo,
        "jornadas_consumo": len(consumo), "jornadas_quantidade": len(jornadas),
        "combustivel": somar_conhecidos(j["combustivel"] for j in jornadas),
        "combustivel_completo": relevante and cobertura and all(j["combustivel"] is not None for j in jornadas),
        "outros_custos": somar_conhecidos(j["outros"] for j in jornadas),
        "custos_conhecidos": custos, "custos_completos": custos_completos,
        "custo_por_tentativa": dividir(custo_com_entregas, tentativas_custo),
        "tentativas_com_custos": tentativas_custo,
        "custo_por_km": dividir(somar_conhecidos(j["custos_conhecidos"] for j in custos_km), somar_conhecidos(j["km"] for j in custos_km)),
        "receita_por_km": dividir(receita_km, km_receita),
        "resultado_parcial": receita - custos if custos is not None else None,
        "resultado_liquido": receita - custos if custos_completos else None,
        "margem_liquida": dividir(100 * (receita - custos), receita) if custos_completos else None,
        "dias_sem_jornada": sorted(dias_com_entregas - set(por_dia)),
    }
