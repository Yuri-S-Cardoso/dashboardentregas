from decimal import Decimal
from django.db.models import Count, Q, Sum
from entregas.models import Entrega


def resumo_entregas():
    """Resumo básico de todo o histórico, usando preços preservados."""
    resumo = Entrega.objects.aggregate(
        tentativas=Count("id"),
        baixas=Count("id", filter=Q(situacao=Entrega.Situacao.BAIXA)),
        insucessos=Count("id", filter=Q(situacao=Entrega.Situacao.INSUCESSO)),
        receita=Sum("valor_por_baixa", filter=Q(situacao=Entrega.Situacao.BAIXA)),
    )
    resumo["receita"] = (resumo["receita"] or Decimal("0.00")).quantize(Decimal("0.01"))
    return resumo
