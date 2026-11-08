from django import forms
from core.forms import FormularioModelo
from .models import Entrega


class EntregaForm(FormularioModelo):
    class Meta:
        model = Entrega
        fields = ["codigo", "data", "horario", "situacao"]


class FiltroEntregaForm(forms.Form):
    data = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), input_formats=["%Y-%m-%d", "%d/%m/%Y"])
    situacao = forms.ChoiceField(label="Situação", required=False, choices=[("", "Todas as situações"), *Entrega.Situacao.choices])
