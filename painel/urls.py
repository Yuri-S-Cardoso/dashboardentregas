from django.urls import path
from .views import Inicio, Configuracoes, Auditoria, Conciliacao
from .export_views import baixar_relatorio, baixar_conciliacao

app_name = "painel"
urlpatterns = [
    path("", Inicio.as_view(), name="inicio"),
    path("auditoria/", Auditoria.as_view(), name="auditoria"),
    path("conciliacao/", Conciliacao.as_view(), name="conciliacao"),
    path("conciliacao/csv/", baixar_conciliacao, name="exportar_conciliacao"),
    path("exportar/excel/", baixar_relatorio, {"formato": "xlsx"}, name="exportar_excel"),
    path("exportar/csv/", baixar_relatorio, {"formato": "csv"}, name="exportar_csv"),
    path("configuracoes/", Configuracoes.as_view(), name="configuracoes"),
]
