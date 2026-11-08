"""Conciliação por competência, sem deduplicação ou inadimplência presumida."""
from collections import defaultdict
import unicodedata
from core.calculos import ZERO, somar_conhecidos
from core.periodos import FiltroPeriodo, periodo_quinzena


def normalizar_documento(texto):
    return " ".join(unicodedata.normalize("NFKC", texto or "").casefold().split())


def detectar_duplicidades(espelhos):
    """Mesmo documento na competência, ou conteúdo idêntico sem referência.

    É um alerta para revisão: todos os registros permanecem visíveis e somados
    nos valores conhecidos, mas não confirmam divergência nem saldo automaticamente.
    """
    grupos = defaultdict(list)
    for espelho in espelhos:
        documento = normalizar_documento(espelho.documento)
        chave = ("documento", documento) if documento else (
            "sem_documento", espelho.baixas_pagas, espelho.insucessos,
            espelho.valor_empresa, espelho.vencimento, normalizar_documento(espelho.observacoes),
        )
        grupos[(espelho.data_competencia, chave)].append(espelho.pk)
    return [ids for ids in grupos.values() if len(ids) > 1]


def soma_integral(registros, campo):
    valores = [getattr(r, campo) for r in registros]
    return sum(valores, ZERO) if valores and all(v is not None for v in valores) else None


def conferir_data(data, movimento, espelhos):
    espelhos = list(espelhos)
    duplicidades = detectar_duplicidades(espelhos)
    baixas = soma_integral(espelhos, "baixas_pagas")
    insucessos = soma_integral(espelhos, "insucessos")
    valor = soma_integral(espelhos, "valor_empresa")
    completo = bool(espelhos) and all(v is not None for v in (baixas, insucessos, valor))
    tem_entregas = movimento["tentativas"] > 0
    confrontavel = tem_entregas and completo and not duplicidades
    diferenca_baixas = movimento["baixas"] - baixas if confrontavel else None
    diferenca_insucessos = movimento["insucessos"] - insucessos if confrontavel else None
    diferenca = movimento["receita"] - valor if confrontavel else None
    if duplicidades:
        status = "Revisar possível duplicidade"
    elif not espelhos:
        status = "Aguardando espelho" if tem_entregas else "Sem entregas ou espelho"
    elif not tem_entregas:
        status = "Espelho sem entregas registradas"
    elif not completo:
        status = "Espelho incompleto"
    else:
        quantidade = diferenca_baixas != 0 or diferenca_insucessos != 0
        financeiro = diferenca != 0
        status = "Divergência de quantidade e valor" if quantidade and financeiro else "Divergência de quantidade" if quantidade else "Divergência de valor" if financeiro else "Conferido"
    return {
        "data": data, **movimento, "baixas_empresa": baixas,
        "insucessos_empresa": insucessos, "valor_empresa": valor,
        "valor_empresa_conhecido": somar_conhecidos(e.valor_empresa for e in espelhos),
        "diferenca_baixas": diferenca_baixas, "diferenca_insucessos": diferenca_insucessos,
        "diferenca": diferenca, "confrontavel": confrontavel, "status": status,
        "tem_espelho": bool(espelhos), "espelho_completo": completo,
        "duplicidades": duplicidades,
        "documentos": [{"id": e.pk, "referencia": e.documento, "origem": e.origem} for e in espelhos],
    }


def conferir_quinzena(inicio, fim, dias, pagamentos, filtro=None):
    filtro = filtro or FiltroPeriodo()
    dias = [d for d in dias if inicio <= d["data"] <= fim and (d["tentativas"] or d["tem_espelho"])]
    pagamentos = [p for p in pagamentos if p.inicio_quinzena == inicio and p.fim_quinzena == fim]
    confrontaveis = [d for d in dias if d["confrontavel"]]
    sem_espelho = [d["data"] for d in dias if d["tentativas"] and not d["tem_espelho"]]
    divergencias = [d["data"] for d in dias if d["status"].startswith("Divergência")]
    completos = bool(dias) and all(d["confrontavel"] for d in dias)
    recorte_parcial = not filtro.cobre(inicio, fim)
    if not dias:
        status = "Sem dados de conferência"
    elif any(d["duplicidades"] for d in dias):
        status = "Revisar possível duplicidade"
    elif divergencias:
        status = "Divergências encontradas"
    elif any(d["status"] == "Espelho sem entregas registradas" for d in dias):
        status = "Espelho sem entregas registradas"
    elif any(d["status"] == "Espelho incompleto" for d in dias):
        status = "Espelho incompleto"
    elif sem_espelho:
        status = "Conferência parcial" if confrontaveis else "Aguardando espelho"
    else:
        status = "Conferido"
    informado = somar_conhecidos(d["valor_empresa_conhecido"] for d in dias)
    recebido = somar_conhecidos(p.valor_recebido for p in pagamentos)
    saldo = informado - recebido if completos and not recorte_parcial and recebido is not None else None
    if not pagamentos:
        pagamento_status = "Sem pagamento registrado"
    elif saldo is None:
        pagamento_status = "Pagamento registrado; saldo depende da conferência completa"
    elif saldo > 0:
        pagamento_status = "Pagamento parcial"
    elif saldo < 0:
        pagamento_status = "Recebido acima do informado"
    else:
        pagamento_status = "Pagamento conferido"
    return {
        "inicio": inicio, "fim": fim, "dias": dias,
        "tentativas": sum(d["tentativas"] for d in dias),
        "baixas": sum(d["baixas"] for d in dias), "insucessos": sum(d["insucessos"] for d in dias),
        "receita": sum((d["receita"] for d in dias), ZERO),
        "valor_empresa": informado, "informado_completo": completos,
        "diferenca": somar_conhecidos(d["diferenca"] for d in confrontaveis),
        "competencias_confrontaveis": len(confrontaveis), "competencias_total": len(dias),
        "recebido": recebido, "pagamentos_quantidade": len(pagamentos),
        "saldo": saldo, "status_pagamento": pagamento_status, "status": status,
        "datas_sem_espelho": sem_espelho, "datas_divergentes": divergencias,
        "recorte_parcial": recorte_parcial,
    }


def agrupar_conferencia(dias, pagamentos, filtro=None):
    chaves = {periodo_quinzena(d["data"]) for d in dias if d["tentativas"] or d["tem_espelho"]}
    sem_vinculo = []
    for pagamento in pagamentos:
        chave = periodo_quinzena(pagamento.inicio_quinzena)
        if chave == (pagamento.inicio_quinzena, pagamento.fim_quinzena):
            chaves.add(chave)
        else:
            sem_vinculo.append(pagamento)
    return [conferir_quinzena(*chave, dias, pagamentos, filtro) for chave in sorted(chaves)], sem_vinculo
