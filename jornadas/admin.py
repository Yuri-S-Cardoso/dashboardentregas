from django.contrib import admin
from core.admin import AdminOrigem
from .models import Jornada


@admin.register(Jornada)
class JornadaAdmin(AdminOrigem):
    list_display = ("data", "inicio_real", "fim_real", "odometro_inicial", "odometro_final", "litros_consumidos", "custo_combustivel")
