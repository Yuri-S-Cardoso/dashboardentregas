from django.urls import path
from . import views
from . import lote_views

app_name = "entregas"
urlpatterns = [
    path("", views.ListaEntregas.as_view(), name="lista"),
    path("nova/", views.NovaEntrega.as_view(), name="nova"),
    path("lote/", lote_views.adicionar_lote, name="lote"),
    path("lote/salvo/<int:pk>/", lote_views.lote_sucesso, name="lote_sucesso"),
    path("<int:pk>/editar/", views.EditarEntrega.as_view(), name="editar"),
    path("<int:pk>/excluir/", views.ExcluirEntrega.as_view(), name="excluir"),
]
