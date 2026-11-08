from core.forms import FormularioModelo
from .models import EspelhoEmpresa, Pagamento


class EspelhoForm(FormularioModelo):
    class Meta:
        model = EspelhoEmpresa
        fields = ["data_competencia", "baixas_pagas", "insucessos", "valor_empresa", "vencimento", "documento", "observacoes"]


class PagamentoForm(FormularioModelo):
    class Meta:
        model = Pagamento
        fields = ["data_pagamento", "inicio_quinzena", "fim_quinzena", "valor_recebido", "comprovante", "observacoes"]
