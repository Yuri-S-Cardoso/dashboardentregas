"""Widgets HTML e apresentação brasileira dos campos."""
from django import forms


class FormularioModelo(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            if isinstance(campo, forms.DateField):
                campo.widget = forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})
                campo.input_formats = ["%Y-%m-%d", "%d/%m/%Y"]
            elif isinstance(campo, forms.TimeField):
                campo.widget = forms.TimeInput(format="%H:%M:%S", attrs={"type": "time", "step": "1"})
            elif isinstance(campo, forms.DecimalField):
                campo.localize = True
                campo.widget = forms.TextInput(attrs={"inputmode": "decimal"})
                campo.widget.is_localized = True
            elif isinstance(campo.widget, forms.Textarea):
                campo.widget.attrs["rows"] = 3
