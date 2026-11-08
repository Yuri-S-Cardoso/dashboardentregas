from django.contrib import admin
from .models import Importacao


class AdminOrigem(admin.ModelAdmin):
    readonly_fields = (
        "importacao", "aba_origem", "linha_origem", "dados_origem",
        "criado_em", "atualizado_em",
    )


@admin.register(Importacao)
class ImportacaoAdmin(admin.ModelAdmin):
    list_display = ("nome_arquivo", "sha256", "criada_em")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
