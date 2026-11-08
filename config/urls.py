from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

admin.site.site_header = "Conferência de Entregas"
admin.site.site_title = "Administração local"
admin.site.index_title = "Cadastros e importações"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("contas/entrar/", auth_views.LoginView.as_view(template_name="registration/login.html", redirect_authenticated_user=True), name="login"),
    path("contas/sair/", auth_views.LogoutView.as_view(), name="logout"),
    path("entregas/", include("entregas.urls")),
    path("espelho/", include("conferencia.urls")),
    path("jornadas/", include("jornadas.urls")),
    path("", include("painel.urls")),
]
