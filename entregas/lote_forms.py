"""Validação do transporte e de todas as linhas antes da gravação do lote."""
import json
from django import forms
from .models import Entrega

LIMITE_LINHAS = 500


class CabecalhoLoteForm(forms.Form):
    data_padrao = forms.DateField(label="Data padrão do lote", input_formats=["%Y-%m-%d", "%d/%m/%Y"],
                                 widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}))
    situacao_padrao = forms.ChoiceField(label="Situação padrão", choices=Entrega.Situacao.choices)
    chave = forms.UUIDField(widget=forms.HiddenInput)
    linhas = forms.CharField(widget=forms.HiddenInput, max_length=250000)
    comprovante = forms.CharField(widget=forms.HiddenInput, required=False, max_length=1000)

    def clean_linhas(self):
        try:
            linhas = json.loads(self.cleaned_data["linhas"])
        except (ValueError, TypeError) as erro:
            raise forms.ValidationError("Não foi possível ler a grade. Os dados não foram salvos.") from erro
        campos = {"codigo", "data", "horario", "situacao"}
        if (not isinstance(linhas, list) or len(linhas) > LIMITE_LINHAS
                or any(not isinstance(linha, dict) or set(linha) - campos
                       or any(not isinstance(valor, str) for valor in linha.values()) for linha in linhas)):
            raise forms.ValidationError(f"Envie uma grade de até {LIMITE_LINHAS} linhas com campos de texto.")
        return linhas


class LinhaLoteForm(forms.Form):
    codigo = forms.CharField(label="Código", max_length=100)
    data = forms.DateField(input_formats=["%Y-%m-%d", "%d/%m/%Y"])
    horario = forms.TimeField(label="Horário", required=False, input_formats=["%H:%M", "%H:%M:%S"])
    situacao = forms.ChoiceField(label="Situação", choices=Entrega.Situacao.choices)


def linha_vazia(linha, situacao_padrao):
    return (not any(linha.get(campo, "").strip() for campo in ("codigo", "data", "horario"))
            and linha.get("situacao", "").strip() in ("", situacao_padrao))


def validar_linhas(linhas, data_padrao, situacao_padrao):
    """Mantém números da grade e erros por campo, incluindo linhas sem código."""
    validas, erros = [], []
    for numero, linha in enumerate(linhas, 1):
        if linha_vazia(linha, situacao_padrao):
            continue
        dados = {**linha, "data": linha.get("data", "").strip() or data_padrao.isoformat(),
                 "situacao": linha.get("situacao", "").strip() or situacao_padrao}
        formulario = LinhaLoteForm(dados)
        if formulario.is_valid():
            validas.append(formulario.cleaned_data)
        else:
            erros.append({"linha": numero, "campos": dict(formulario.errors)})
    return validas, erros
