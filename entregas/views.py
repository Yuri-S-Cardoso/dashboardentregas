from django.urls import reverse_lazy
from core.views import ListaProtegida, CriarProtegido, EditarProtegido, ExcluirProtegido
from .forms import EntregaForm, FiltroEntregaForm
from .models import Entrega

CONTEXTO = {"titulo": "Minhas Entregas", "url_lista": "entregas:lista", "url_novo": "entregas:nova", "tabela": "entregas/tabela.html"}


class ListaEntregas(ListaProtegida):
    model = Entrega
    extra_context = CONTEXTO

    def get_queryset(self):
        self.filtro = FiltroEntregaForm(self.request.GET)
        registros = super().get_queryset()
        if not self.filtro.is_valid():
            return registros.none()
        for nome, valor in self.filtro.cleaned_data.items():
            if valor:
                registros = registros.filter(**{nome: valor})
        return registros

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        filtros = self.request.GET.copy()
        filtros.pop("page", None)
        contexto.update(filtro=self.filtro, filtros_query=filtros.urlencode())
        return contexto


class NovaEntrega(CriarProtegido):
    model = Entrega
    form_class = EntregaForm
    success_url = reverse_lazy("entregas:lista")
    extra_context = {**CONTEXTO, "titulo": "Cadastrar entrega"}


class EditarEntrega(EditarProtegido):
    model = Entrega
    form_class = EntregaForm
    success_url = reverse_lazy("entregas:lista")
    extra_context = {**CONTEXTO, "titulo": "Editar entrega"}


class ExcluirEntrega(ExcluirProtegido):
    model = Entrega
    success_url = reverse_lazy("entregas:lista")
    extra_context = CONTEXTO
