from django.contrib import admin
from .models import Configuracao


@admin.register(Configuracao)
class ConfiguracaoAdmin(admin.ModelAdmin):
    list_display = ("id", "criada_em", "valor_por_baixa", "meta_diaria", "meta_semanal", "meta_mensal")
    readonly_fields = ("criada_em",)

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
