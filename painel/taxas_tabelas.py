"""Taxa exclusiva das tabelas; não altera os indicadores operacionais aprovados."""
from decimal import Decimal, ROUND_HALF_UP

from core.periodos import FiltroPeriodo
from entregas.models import Entrega
from entregas.services.conciliacao import conciliar_entregas


def calcular_taxa_sucesso_tabela(inicio, fim, referencia, *, historico=None):
    """Concluídas / população distinta iniciada no intervalo, até a referência.

    A conciliação recebe o histórico completo, incluindo tentativas anteriores
    ao intervalo e recuperações posteriores. Identidade, cronologia e exclusão
    de ambiguidades são decididas exclusivamente pelo serviço existente.
    O dashboard fornece a mesma lista já lida na sua transação, evitando novas
    consultas por linha. Sem lista explícita, a função faz uma leitura própria.
    """
    if inicio > fim:
        raise ValueError("O início do período deve ser igual ou anterior ao fim.")
    if historico is None:
        historico = Entrega.objects.all().order_by("data", "horario", "pk")
    conciliacao = conciliar_entregas(historico, FiltroPeriodo(inicio, fim), data_referencia=referencia)
    taxa = conciliacao["sucesso_percentual"]
    return {
        "encomendas_identificadas": conciliacao["entregas_identificadas"],
        "concluidas": conciliacao["concluidas"],
        "pendentes": conciliacao["insucessos_reais"],
        "ciclos_em_revisao": conciliacao["ciclos_em_revisao"],
        "referencia": conciliacao["referencia"],
        "taxa_sucesso": taxa,
        "taxa_sucesso_arredondada": taxa.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if taxa is not None else None,
    }
