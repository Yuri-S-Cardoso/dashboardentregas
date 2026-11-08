"""Composição somente de leitura dos serviços, comum ao painel e à auditoria."""
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from conferencia.models import EspelhoEmpresa, Pagamento
from conferencia.services import conferir_data, agrupar_conferencia
from core.calculos import dividir
from core.periodos import FiltroPeriodo, periodo_mes, periodo_semana
from entregas.models import Entrega
from entregas.services.indicadores import totalizar_entregas
from entregas.services.conciliacao import INSUCESSO_REAL, RECUPERADA, conciliar_entregas
from jornadas.models import Jornada
from jornadas.services import calcular_jornada, consolidar_jornadas
from painel.models import Configuracao
from .metas import acompanhar_meta, projetar
from .taxas_tabelas import calcular_taxa_sucesso_tabela
from .faturamento import calcular_faturamento_quinzenal


def por_data(registros, campo="data"):
    grupos = defaultdict(list)
    for registro in registros:
        grupos[getattr(registro, campo)].append(registro)
    return grupos


def indicadores_principais(resumo, conciliacao):
    """Mesma fórmula operacional nos cards e em cada linha diária/semanal/mensal.

    A taxa combina ocorrências de baixa com pendências distintas. A população
    conciliada continua disponível separadamente, sem alterar seu cálculo.
    """
    baixas = resumo["baixas"]
    pendentes = conciliacao["insucessos_reais"]
    taxa = dividir(100 * baixas, baixas + pendentes)
    return {
        "total_encomendas": resumo["tentativas"],
        "entregas_concluidas": baixas,
        "total_com_insucesso": resumo["insucessos"],
        "insucessos_pendentes": pendentes,
        "entregas_recuperadas": conciliacao["recuperadas"],
        "faturamento": resumo["receita"],
        "taxa_sucesso": taxa,
        # O formatador genérico limita casas sem arredondar; só esta taxa exige
        # arredondamento explícito, sem mudar a apresentação financeira existente.
        "taxa_sucesso_arredondada": taxa.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if taxa is not None else None,
    }


def periodos_agrupados(dias, entregas, jornadas, tipo, meta, filtro):
    funcao = periodo_semana if tipo == "semana" else lambda dia: periodo_mes(dia.year, dia.month)
    chaves = sorted({funcao(d["data"]) for d in dias if d["tentativas"] or d["jornadas_quantidade"]})
    resultados = []
    for inicio, fim in chaves:
        selecionadas = [e for e in entregas if inicio <= e.data <= fim]
        movimento = {d["data"]: d for d in dias if inicio <= d["data"] <= fim}
        calculadas = [j for j in jornadas if inicio <= j["data"] <= fim]
        totais = totalizar_entregas(selecionadas)
        media = dividir(totais["receita"], totais["dias_com_entregas"])
        conciliadas = {
            "insucessos_reais": sum(d["indicadores_principais"]["insucessos_pendentes"] for d in movimento.values()),
            "recuperadas": sum(d["indicadores_principais"]["entregas_recuperadas"] for d in movimento.values()),
        }
        resultados.append({
            "inicio": inicio, "fim": fim,
            "rotulo": f"{inicio:%d/%m/%Y} a {fim:%d/%m/%Y}" if tipo == "semana" else f"{inicio:%m/%Y}",
            **totais, **consolidar_jornadas(calculadas, movimento),
            **acompanhar_meta(totais["receita"], meta),
            "media_receita_dia": media,
            "media_receita_dia_arredondada": media.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if media is not None else None,
            "indicadores_principais": indicadores_principais(totais, conciliadas),
            "recorte_parcial": not filtro.cobre(inicio, fim),
        })
    return resultados


@transaction.atomic
def montar_dashboard(filtro=None, dias_projecao=5):
    filtro = filtro or FiltroPeriodo()
    # A população depende da primeira tentativa, mesmo fora do recorte financeiro.
    historico = list(Entrega.objects.all().order_by("data", "horario", "pk"))
    entregas = [e for e in historico if filtro.contem(e.data)]
    conciliacao = conciliar_entregas(historico, filtro)
    # A conciliação já consultou TODO o histórico. Cada pendência/recuperação é
    # atribuída uma vez à data inicial, sem mover ocorrências ou receitas.
    pendentes = Counter(c.primeira_tentativa for c in conciliacao["ciclos"] if c.situacao == INSUCESSO_REAL)
    recuperadas = Counter(c.primeira_tentativa for c in conciliacao["ciclos"] if c.situacao == RECUPERADA)
    ate_fim = None
    if filtro.fim and conciliacao["referencia"] and filtro.fim < conciliacao["referencia"]:
        ate_fim = conciliar_entregas(historico, filtro, data_referencia=filtro.fim)
    espelhos = list(filtro.aplicar(EspelhoEmpresa.objects.all(), "data_competencia").order_by("data_competencia", "pk"))
    jornadas = list(filtro.aplicar(Jornada.objects.all()).order_by("data", "pk"))
    pagamentos_qs = Pagamento.objects.all()
    # Pagamentos são vinculados pela competência, mesmo se recebidos em outro mês.
    if filtro.inicio:
        pagamentos_qs = pagamentos_qs.filter(fim_quinzena__gte=filtro.inicio)
    if filtro.fim:
        pagamentos_qs = pagamentos_qs.filter(inicio_quinzena__lte=filtro.fim)
    pagamentos = list(pagamentos_qs)
    configuracao = Configuracao.atual()
    entregas_dia, espelhos_dia = por_data(entregas), por_data(espelhos, "data_competencia")
    jornadas_calculadas = [calcular_jornada(j) for j in jornadas]
    jornadas_dia = defaultdict(list)
    for jornada in jornadas_calculadas:
        jornadas_dia[jornada["data"]].append(jornada)
    datas = sorted(set(entregas_dia) | set(espelhos_dia) | set(jornadas_dia))
    diarios, auditoria = [], []
    for data in datas:
        movimento = totalizar_entregas(entregas_dia[data])
        diarios.append({
            "data": data, **movimento,
            **consolidar_jornadas(jornadas_dia[data], {data: movimento}),
            **acompanhar_meta(movimento["receita"], configuracao.meta_diaria),
            "indicadores_principais": indicadores_principais(movimento, {
                "insucessos_reais": pendentes[data], "recuperadas": recuperadas[data],
            }),
        })
        if movimento["tentativas"] or espelhos_dia[data]:
            auditoria.append(conferir_data(data, movimento, espelhos_dia[data]))
    resumo = totalizar_entregas(entregas)
    resumo.update(consolidar_jornadas(jornadas_calculadas, {d["data"]: d for d in diarios}))
    resumo["ganho_medio_baixa"] = dividir(resumo["receita"], resumo["baixas"])
    ativos = [d for d in diarios if d["tentativas"]]
    melhor = max((d["baixas"] for d in ativos), default=None)
    resumo["melhores_dias"] = [d["data"] for d in ativos if d["baixas"] == melhor]
    resumo["melhor_dia_baixas"] = melhor
    quinzenas, pagamentos_sem_vinculo = agrupar_conferencia(auditoria, pagamentos, filtro)
    resultado = {
        "resumo": resumo, "diarios": diarios,
        "dias_operacionais": [d for d in diarios if d["tentativas"] or d["jornadas_quantidade"]],
        "auditoria": auditoria,
        "semanas": periodos_agrupados(diarios, entregas, jornadas_calculadas, "semana", configuracao.meta_semanal, filtro),
        "meses": periodos_agrupados(diarios, entregas, jornadas_calculadas, "mes", configuracao.meta_mensal, filtro),
        "quinzenas": quinzenas, "pagamentos_sem_vinculo": pagamentos_sem_vinculo,
        "jornadas": jornadas_calculadas, "configuracao": configuracao,
        "projecao": projetar(resumo["receita"], resumo["dias_com_entregas"], dias_projecao),
        "periodo": filtro, "tem_dados": bool(datas or pagamentos),
        "conciliacao": conciliacao, "conciliacao_ate_fim": ate_fim,
        "indicadores_principais": indicadores_principais(resumo, conciliacao),
        "faturamento_quinzenal": calcular_faturamento_quinzenal(historico, filtro),
    }
    # Apenas a nova coluna usa população distinta; os campos aprovados acima
    # permanecem intactos, inclusive indicadores principais, receitas e gráficos.
    for grupo in ("diarios", "semanas", "meses"):
        for linha in resultado[grupo]:
            inicio = linha.get("data", linha.get("inicio"))
            fim = linha.get("data", linha.get("fim"))
            # Mantém o recorte aplicado nas demais colunas da linha.
            inicio = max(inicio, filtro.inicio) if filtro.inicio else inicio
            fim = min(fim, filtro.fim) if filtro.fim else fim
            linha["taxa_sucesso_tabela"] = calcular_taxa_sucesso_tabela(
                inicio, fim, conciliacao["referencia"], historico=historico,
            )
    from .graficos import dados_graficos
    resultado["graficos"] = dados_graficos(resultado)
    return resultado
