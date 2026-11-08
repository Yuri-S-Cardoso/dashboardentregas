from core.forms import FormularioModelo
from .models import Configuracao
from datetime import date
from zoneinfo import ZoneInfo
from django import forms
from django.http import QueryDict
from django.utils import timezone
from core.periodos import FiltroPeriodo, periodo_mes, periodo_quinzena, periodo_semana


class ConfiguracaoForm(FormularioModelo):
    class Meta:
        model = Configuracao
        fields = ["valor_por_baixa", "meta_diaria", "meta_semanal", "meta_mensal"]


class ConsultaConciliacaoForm(forms.Form):
    codigo = forms.CharField(label="Código contém", max_length=100, required=False)
    situacao_conciliacao = forms.ChoiceField(label="Situação conhecida", required=False, choices=[
        ("", "Todas"), ("recuperada", "Recuperadas"),
        ("insucesso_real", "Insucesso Real — sem baixa posterior"),
        ("concluida", "Concluídas sem insucesso"), ("revisao", "Exigem revisão"),
    ])


class FiltroPainelForm(forms.Form):
    periodo = forms.ChoiceField(label="Período", required=False, choices=[
        ("todos", "Todo o histórico"), ("intervalo", "Intervalo de datas"),
        ("dia", "Dia"), ("semana", "Semana"), ("mes", "Mês e ano"),
        ("quinzena", "Quinzena"),
    ])
    inicio = forms.DateField(label="Data inicial", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    fim = forms.DateField(label="Data final", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    dia = forms.DateField(label="Dia", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    semana = forms.DateField(label="Uma data da semana", required=False, widget=forms.DateInput(attrs={"type": "date"}), help_text="Selecione qualquer data: o período vai de domingo a sábado.")
    mes = forms.TypedChoiceField(label="Mês", required=False, coerce=int, empty_value=None, choices=[("", "Selecione"), *[(i, str(i).zfill(2)) for i in range(1, 13)]])
    ano = forms.IntegerField(label="Ano", required=False, min_value=1, max_value=9999)
    quinzena = forms.ChoiceField(label="Quinzena", required=False, choices=[("", "Selecione"), ("1", "01 a 15"), ("2", "16 ao fim do mês")])
    dias_projecao = forms.IntegerField(label="Dias com entregas no cenário", required=False, min_value=1, max_value=366, initial=5)

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            data = data.copy()
            if not data.get("periodo"):
                hoje = timezone.localtime(timezone.now(), ZoneInfo("America/Sao_Paulo")).date()
                data.update({"periodo": "mes", "mes": str(hoje.month), "ano": str(hoje.year)})
        super().__init__(data, *args, **kwargs)

    def parametros(self):
        """Consulta canônica: só campos válidos e pertinentes; nunca dados privados."""
        saida = QueryDict(mutable=True)
        if not self.is_valid():
            return saida
        dados = self.cleaned_data
        tipo = dados.get("periodo") or "todos"
        campos = {"intervalo": ("inicio", "fim"), "dia": ("dia",), "semana": ("semana",),
                  "mes": ("mes", "ano"), "quinzena": ("mes", "ano", "quinzena")}.get(tipo, ())
        saida["periodo"] = tipo
        for campo in campos:
            valor = dados[campo]
            # Salvar o domingo resolve a navegação semanal sem numeração ISO.
            if campo == "semana":
                valor = dados["filtro"].inicio
            saida[campo] = valor.isoformat() if isinstance(valor, date) else str(valor)
        if "dias_projecao" in self.data:
            saida["dias_projecao"] = str(dados["dias_projecao"])
        return saida

    def clean(self):
        dados = super().clean()
        tipo = dados.get("periodo") or "todos"
        necessarios = {
            "intervalo": ("inicio", "fim"), "dia": ("dia",), "semana": ("semana",),
            "mes": ("mes", "ano"), "quinzena": ("mes", "ano", "quinzena"),
        }.get(tipo, ())
        for campo in necessarios:
            if not dados.get(campo) and campo not in self.errors:
                self.add_error(campo, "Preencha este campo para o período escolhido.")
        if self.errors:
            return dados
        inicio = fim = None
        if tipo == "intervalo":
            inicio, fim = dados["inicio"], dados["fim"]
            if fim < inicio:
                self.add_error("fim", "A data final deve ser igual ou posterior à inicial.")
        elif tipo == "dia":
            inicio = fim = dados["dia"]
        elif tipo == "semana":
            inicio, fim = periodo_semana(dados["semana"])
        elif tipo in ("mes", "quinzena"):
            inicio, fim = periodo_mes(dados["ano"], dados["mes"])
            if tipo == "quinzena":
                inicio, fim = periodo_quinzena(inicio.replace(day=1 if dados["quinzena"] == "1" else 16))
        dados["filtro"] = FiltroPeriodo(inicio, fim)
        dados["dias_projecao"] = dados.get("dias_projecao") or 5
        return dados
