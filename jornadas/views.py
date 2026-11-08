from django.urls import reverse_lazy
from core.views import ListaProtegida, CriarProtegido, EditarProtegido
from .forms import JornadaForm
from .models import Jornada

CONTEXTO = {"titulo": "Jornada e Custos", "url_lista": "jornadas:lista", "url_novo": "jornadas:nova", "tabela": "jornadas/tabela.html"}


class ListaJornadas(ListaProtegida):
    model = Jornada
    extra_context = CONTEXTO


class NovaJornada(CriarProtegido):
    form_class = JornadaForm
    success_url = reverse_lazy("jornadas:lista")
    extra_context = {**CONTEXTO, "titulo": "Cadastrar jornada"}


class EditarJornada(EditarProtegido):
    model = Jornada
    form_class = JornadaForm
    success_url = reverse_lazy("jornadas:lista")
    extra_context = {**CONTEXTO, "titulo": "Editar jornada"}
