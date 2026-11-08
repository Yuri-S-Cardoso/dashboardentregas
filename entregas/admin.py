from django.contrib import admin
from core.admin import AdminOrigem
from .models import Entrega


@admin.register(Entrega)
class EntregaAdmin(AdminOrigem):
    list_display = ("codigo", "data", "horario", "situacao", "valor_por_baixa", "ordem_original")
    list_filter = ("situacao", "data")
    search_fields = ("codigo",)
    readonly_fields = AdminOrigem.readonly_fields + ("valor_por_baixa", "ordem_original")
