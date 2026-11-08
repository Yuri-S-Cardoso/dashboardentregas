"""Conciliação derivada do histórico; não grava nem corrige registros financeiros."""
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal
from itertools import groupby

from core.calculos import dividir
from core.periodos import FiltroPeriodo

BAIXA = "Baixa realizada"
INSUCESSO = "Insucesso"
CONCLUIDA = "concluida"
RECUPERADA = "recuperada"
INSUCESSO_REAL = "insucesso_real"
REVISAO = "revisao"
ROTULOS = {
    CONCLUIDA: "Concluída",
    RECUPERADA: "Recuperada",
    INSUCESSO_REAL: "Sem baixa posterior registrada",
    REVISAO: "Identidade ou cronologia em revisão",
}


def ordem_registro(registro):
    """PK desempata a apresentação; nunca comprova a ordem de eventos empatados."""
    return registro.data, registro.horario or time.min, registro.pk or 0


def posterior(baixa, insucesso):
    """No mesmo dia, a recuperação exige dois horários conhecidos e distintos."""
    if baixa.data != insucesso.data:
        return baixa.data > insucesso.data
    return (baixa.horario is not None and insucesso.horario is not None
            and baixa.horario > insucesso.horario)


@dataclass(frozen=True)
class CicloConciliado:
    chave: str
    codigo: str
    ciclo: int
    primeira_tentativa: date
    primeiro_insucesso: date | None
    horario_primeiro_insucesso: time | None
    data_baixa: date | None
    horario_baixa: time | None
    ultima_tentativa: date
    tentativas: int
    baixas: int
    insucessos: int
    situacao: str
    motivos_revisao: tuple[str, ...]
    alertas_financeiros: tuple[str, ...]
    ids_registros: tuple[int, ...]
    receita_registrada: Decimal
    ocorrencias_identicas: int

    @property
    def rotulo(self):
        return ROTULOS[self.situacao]


def blocos_cronologicos(registros):
    """Hora ausente impede ordenar situações diferentes dentro daquele dia."""
    for _, grupo in groupby(registros, key=lambda r: r.data):
        dia = list(grupo)
        if any(r.horario is None for r in dia):
            yield dia
        else:
            for _, horario in groupby(dia, key=lambda r: r.horario):
                yield list(horario)


def ciclos_do_codigo(codigo, registros):
    """Baixa encerra ciclo; novo insucesso abre candidato, sem validar identidade.

    Não há prazo arbitrário para recuperação. Sem identificador de encomenda,
    retornos após baixa e baixas em datas diferentes pedem revisão de todo o
    código. Candidatos ambíguos ficam fora da taxa, visíveis na auditoria.
    """
    registros = sorted(registros, key=ordem_registro)
    ciclos, atual, encerrado, motivos = [], [], False, []
    if not codigo.strip():
        motivos.append("Código ausente: identidade não comprovada.")
    for bloco in blocos_cronologicos(registros):
        situacoes = {r.situacao for r in bloco}
        if not situacoes <= {BAIXA, INSUCESSO}:
            motivos.append("Situação desconhecida no histórico.")
        if {BAIXA, INSUCESSO} <= situacoes:
            motivos.append("Baixa e insucesso sem ordem comprovada no mesmo dia/horário.")
        if encerrado and INSUCESSO in situacoes:
            ciclos.append(atual)
            atual = []
            encerrado = False
            motivos.append("Insucesso posterior à baixa: possível reutilização do código.")
        atual.extend(bloco)
        encerrado = encerrado or BAIXA in situacoes
    if atual:
        ciclos.append(atual)
    if len({r.data for r in registros if r.situacao == BAIXA}) > 1:
        motivos.append("Baixas em datas diferentes: duplicidade ou reutilização a revisar.")
    motivos = tuple(dict.fromkeys(motivos))
    return [resumir_ciclo(codigo, numero, itens, motivos)
            for numero, itens in enumerate(ciclos, 1)]


def resumir_ciclo(codigo, numero, registros, motivos):
    insucessos = [r for r in registros if r.situacao == INSUCESSO]
    baixas = [r for r in registros if r.situacao == BAIXA]
    # Uma baixa anterior/empatada nunca resolve um insucesso. Datas distintas
    # bastam mesmo sem hora; no mesmo dia a ordem precisa estar comprovada.
    baixa = next((b for b in baixas if all(posterior(b, i) for i in insucessos)), None)
    primeiro = insucessos[0] if insucessos else None
    situacao = (REVISAO if motivos else RECUPERADA if baixa and insucessos
                else CONCLUIDA if baixa else INSUCESSO_REAL)
    alertas = []
    if len(baixas) > 1:
        alertas.append("Múltiplas baixas no ciclo; conferir a receita registrada sem ajuste automático.")
    if motivos and baixas:
        alertas.append("Identidade em revisão com receita registrada; conferir documentos.")
    identicas = Counter((r.data, r.horario, r.situacao, r.valor_por_baixa) for r in registros)
    return CicloConciliado(
        chave=f"{registros[0].pk}:{numero}", codigo=codigo, ciclo=numero,
        primeira_tentativa=registros[0].data,
        primeiro_insucesso=primeiro.data if primeiro else None,
        horario_primeiro_insucesso=primeiro.horario if primeiro else None,
        data_baixa=baixa.data if baixa else None,
        horario_baixa=baixa.horario if baixa else None,
        ultima_tentativa=registros[-1].data, tentativas=len(registros),
        baixas=len(baixas), insucessos=len(insucessos), situacao=situacao,
        motivos_revisao=motivos, alertas_financeiros=tuple(alertas),
        ids_registros=tuple(r.pk for r in registros),
        receita_registrada=sum((r.valor_previsto for r in registros), Decimal("0.00")),
        ocorrencias_identicas=sum(qtd - 1 for qtd in identicas.values()),
    )


def conciliar_entregas(registros, filtro=None, data_referencia=None):
    """Seleciona pela primeira tentativa do ciclo e consulta o histórico até o corte.

    O filtro de população nunca é aplicado antes da identificação dos ciclos.
    A data de referência é inclusiva; sem corte usa o último registro disponível.
    Código é texto exato, sem conversão numérica ou remoção de zeros à esquerda.
    """
    filtro = filtro or FiltroPeriodo()
    grupos = defaultdict(list)
    for registro in registros:
        if data_referencia is None or registro.data <= data_referencia:
            # Não agrupa registros sem código como se fossem uma entrega única.
            chave = (registro.codigo, registro.pk if not registro.codigo.strip() else None)
            grupos[chave].append(registro)
    todos = [ciclo for (codigo, _), itens in grupos.items()
             for ciclo in ciclos_do_codigo(codigo, itens)]
    ciclos = sorted((c for c in todos if filtro.contem(c.primeira_tentativa)),
                    key=lambda c: (c.primeira_tentativa, c.codigo, c.ciclo, c.chave))
    validos = [c for c in ciclos if c.situacao != REVISAO]
    concluidas = sum(c.situacao in (CONCLUIDA, RECUPERADA) for c in validos)
    insucessos = sum(c.situacao == INSUCESSO_REAL for c in validos)
    referencia = data_referencia or max((c.ultima_tentativa for c in todos), default=None)
    return {
        "ciclos": ciclos, "referencia": referencia,
        "entregas_identificadas": len(validos),
        "codigos": len({c.codigo for c in ciclos}),
        "concluidas": concluidas, "insucessos_reais": insucessos,
        "com_insucesso": sum(c.insucessos > 0 for c in validos),
        "recuperadas": sum(c.situacao == RECUPERADA for c in validos),
        "sucesso_percentual": dividir(100 * concluidas, concluidas + insucessos),
        "codigos_em_revisao": len({c.codigo for c in ciclos if c.situacao == REVISAO}),
        "ciclos_em_revisao": len(ciclos) - len(validos),
        "alertas_financeiros": sum(bool(c.alertas_financeiros) for c in ciclos),
        "tentativas_populacao": sum(c.tentativas for c in ciclos),
        "ocorrencias_adicionais": sum(c.tentativas - 1 for c in ciclos),
        "ocorrencias_identicas": sum(c.ocorrencias_identicas for c in ciclos),
        "concluidas_apos_periodo": sum(bool(filtro.fim and c.data_baixa and c.data_baixa > filtro.fim)
                                       for c in validos),
        "recuperadas_apos_periodo": sum(bool(filtro.fim and c.data_baixa and c.data_baixa > filtro.fim
                                             and c.situacao == RECUPERADA) for c in validos),
    }


def filtrar_ciclos(ciclos, situacao="", codigo=""):
    """Consulta por situação e trecho textual do código, sem mudar os indicadores."""
    return [c for c in ciclos if (not situacao or c.situacao == situacao)
            and (not codigo or codigo.casefold() in c.codigo.casefold())]
