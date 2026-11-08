from django.urls import path
from . import views

app_name = "jornadas"
urlpatterns = [
    path("", views.ListaJornadas.as_view(), name="lista"),
    path("nova/", views.NovaJornada.as_view(), name="nova"),
    path("<int:pk>/editar/", views.EditarJornada.as_view(), name="editar"),
]
