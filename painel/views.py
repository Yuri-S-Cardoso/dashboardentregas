from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView, FormView
from .forms import ConfiguracaoForm
from .models import Configuracao
from .forms import FiltroPainelForm, ConsultaConciliacaoForm
from .dashboard import montar_dashboard
from entregas.services.conciliacao import filtrar_ciclos


@method_decorator(never_cache, name="dispatch")
class Inicio(LoginRequiredMixin, TemplateView):
    """Recalcula a leitura a cada consulta e impede reutilização HTTP de resultados."""
    template_name = "painel/inicio.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        form = FiltroPainelForm(self.request.GET)
        contexto.update(filtro=form, filtros_query=form.parametros().urlencode())
        if form.is_valid():
            dashboard = montar_dashboard(form.cleaned_data["filtro"], form.cleaned_data["dias_projecao"])
            contexto.update(dashboard=dashboard, resumo=dashboard["resumo"])
        return contexto


class Auditoria(Inicio):
    template_name = "conferencia/auditoria.html"


class Conciliacao(Inicio):
    """Lista autenticada da população conciliada, sem edição do histórico."""
    template_name = "painel/conciliacao.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        consulta = ConsultaConciliacaoForm(self.request.GET)
        contexto["consulta"] = consulta
        contexto["pagina"] = None
        parametros_filtro = contexto["filtro"].parametros()
        contexto["campos_filtro"] = list(parametros_filtro.items())
        if "dashboard" in contexto and consulta.is_valid():
            ciclos = filtrar_ciclos(contexto["dashboard"]["conciliacao"]["ciclos"],
                                   consulta.cleaned_data["situacao_conciliacao"], consulta.cleaned_data["codigo"])
            contexto["pagina"] = Paginator(ciclos, 30).get_page(self.request.GET.get("pagina"))
        parametros = self.request.GET.copy()
        parametros.pop("pagina", None)
        for nome, valor in parametros_filtro.items():
            parametros[nome] = valor
        contexto["consulta_query"] = parametros.urlencode()
        return contexto


class Configuracoes(LoginRequiredMixin, FormView):
    template_name = "painel/configuracoes.html"
    form_class = ConfiguracaoForm
    success_url = reverse_lazy("painel:configuracoes")

    def get_initial(self):
        atual = Configuracao.atual()
        return {campo: getattr(atual, campo) for campo in self.form_class.Meta.fields}

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Nova configuração salva. Os valores históricos das entregas foram preservados.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "versoes": Configuracao.objects.order_by("-pk")[:10], "titulo": "Configurações"}
