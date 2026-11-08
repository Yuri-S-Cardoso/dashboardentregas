from django.urls import path
from . import views

app_name = "conferencia"
urlpatterns = [
    path("", views.ListaEspelhos.as_view(), name="espelhos"),
    path("novo/", views.NovoEspelho.as_view(), name="novo_espelho"),
    path("<int:pk>/editar/", views.EditarEspelho.as_view(), name="editar_espelho"),
    path("pagamentos/", views.ListaPagamentos.as_view(), name="pagamentos"),
    path("pagamentos/novo/", views.NovoPagamento.as_view(), name="novo_pagamento"),
    path("pagamentos/<int:pk>/editar/", views.EditarPagamento.as_view(), name="editar_pagamento"),
]
