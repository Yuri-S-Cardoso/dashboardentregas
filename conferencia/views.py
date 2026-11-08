from django.urls import reverse_lazy
from core.views import ListaProtegida, CriarProtegido, EditarProtegido
from .models import EspelhoEmpresa, Pagamento
from .forms import EspelhoForm, PagamentoForm

ESPELHO = {"titulo": "Espelho da Empresa", "url_lista": "conferencia:espelhos", "url_novo": "conferencia:novo_espelho", "tabela": "conferencia/espelhos_tabela.html"}
PAGAMENTO = {"titulo": "Pagamentos recebidos", "url_lista": "conferencia:pagamentos", "url_novo": "conferencia:novo_pagamento", "tabela": "conferencia/pagamentos_tabela.html"}


class ListaEspelhos(ListaProtegida):
    model = EspelhoEmpresa
    extra_context = ESPELHO


class NovoEspelho(CriarProtegido):
    form_class = EspelhoForm
    success_url = reverse_lazy("conferencia:espelhos")
    extra_context = {**ESPELHO, "titulo": "Cadastrar espelho"}


class EditarEspelho(EditarProtegido):
    model = EspelhoEmpresa
    form_class = EspelhoForm
    success_url = reverse_lazy("conferencia:espelhos")
    extra_context = {**ESPELHO, "titulo": "Editar espelho"}


class ListaPagamentos(ListaProtegida):
    model = Pagamento
    extra_context = PAGAMENTO


class NovoPagamento(CriarProtegido):
    form_class = PagamentoForm
    success_url = reverse_lazy("conferencia:pagamentos")
    extra_context = {**PAGAMENTO, "titulo": "Cadastrar pagamento"}


class EditarPagamento(EditarProtegido):
    model = Pagamento
    form_class = PagamentoForm
    success_url = reverse_lazy("conferencia:pagamentos")
    extra_context = {**PAGAMENTO, "titulo": "Editar pagamento"}
