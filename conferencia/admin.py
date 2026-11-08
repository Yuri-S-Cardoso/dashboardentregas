from django.contrib import admin
from core.admin import AdminOrigem
from .models import EspelhoEmpresa, Pagamento


@admin.register(EspelhoEmpresa)
class EspelhoAdmin(AdminOrigem):
    list_display = ("data_competencia", "baixas_pagas", "insucessos", "valor_empresa", "documento", "vencimento")
    search_fields = ("documento",)


@admin.register(Pagamento)
class PagamentoAdmin(AdminOrigem):
    list_display = ("data_pagamento", "inicio_quinzena", "fim_quinzena", "valor_recebido", "comprovante")
