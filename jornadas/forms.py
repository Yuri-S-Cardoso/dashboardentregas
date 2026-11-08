from core.forms import FormularioModelo
from .models import Jornada


class JornadaForm(FormularioModelo):
    class Meta:
        model = Jornada
        fields = ["data", "inicio_real", "fim_real", "odometro_inicial", "odometro_final", "litros_consumidos", "custo_combustivel", "outros_custos", "janela_historica"]
