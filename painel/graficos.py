"""Somente dados calculados no servidor. Decimal é serializado como texto."""
from collections import defaultdict

from entregas.services.conciliacao import CONCLUIDA, RECUPERADA, INSUCESSO_REAL


def situacoes_por_primeira_tentativa(conciliacao):
    """Três grupos exclusivos de encomendas; recuperadas são parte das concluídas.

    Cada data representa o início da encomenda, com o resultado atual conhecido.
    Casos em revisão ficam separados; receitas continuam nas séries por data real.
    """
    grupos = defaultdict(lambda: {"concluidas_sem_insucesso": 0, "pendentes": 0, "recuperadas": 0})
    campos = {CONCLUIDA: "concluidas_sem_insucesso", INSUCESSO_REAL: "pendentes", RECUPERADA: "recuperadas"}
    for ciclo in conciliacao["ciclos"]:
        if ciclo.situacao in campos:
            grupos[ciclo.primeira_tentativa][campos[ciclo.situacao]] += 1
    return [{"data": dia, **valores} for dia, valores in sorted(grupos.items())]


def dados_graficos(painel):
    dias = [d for d in painel["diarios"] if d["tentativas"] or d["jornadas_quantidade"]]
    encomendas = situacoes_por_primeira_tentativa(painel["conciliacao"])
    def grafico(chave, titulo, linhas, campo_rotulo, series, unidade="numero"):
        return {
            "id": chave, "titulo": titulo, "unidade": unidade,
            "rotulos": [campo_rotulo(linha) for linha in linhas],
            "series": [{"nome": nome, "valores": [linha[campo] for linha in linhas]} for nome, campo in series],
            "tabela": [{"rotulo": campo_rotulo(linha), "valores": [linha[campo] for nome, campo in series]} for linha in linhas],
        }
    return [
        grafico("situacoes", "Situação atual por início da encomenda", encomendas,
                lambda d: d["data"].strftime("%d/%m/%Y"),
                [("Concluídas sem insucesso", "concluidas_sem_insucesso"),
                 ("Pendentes", "pendentes"), ("Recuperadas", "recuperadas")]),
        grafico("receita-dia", "Faturamento diário", dias, lambda d: d["data"].strftime("%d/%m/%Y"), [("Previsto", "receita")], "reais"),
        grafico("receita-semana", "Faturamento semanal", painel["semanas"], lambda d: d["rotulo"], [("Previsto", "receita")], "reais"),
        grafico("receita-mes", "Faturamento mensal", painel["meses"], lambda d: d["rotulo"], [("Previsto", "receita")], "reais"),
        grafico("metas", "Meta diária versus faturamento", dias, lambda d: d["data"].strftime("%d/%m/%Y"), [("Previsto", "receita"), ("Meta diária", "meta")], "reais"),
        grafico("custos", "Custos conhecidos versus faturamento", dias, lambda d: d["data"].strftime("%d/%m/%Y"), [("Previsto", "receita"), ("Custos conhecidos (podem ser parciais)", "custos_conhecidos")], "reais"),
        grafico("produtividade", "Ocorrências de baixa por hora com duração válida", dias, lambda d: f'{d["data"]:%d/%m/%Y} · {d["origem_duracao"]}', [("Ocorrências de baixa/h", "baixas_por_hora")]),
    ]
