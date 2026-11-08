"""Views reutilizáveis: acesso autenticado e alterações apenas por POST."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, UpdateView, DeleteView, ListView


class ListaProtegida(LoginRequiredMixin, ListView):
    template_name = "core/lista.html"
    paginate_by = 50


class CriarProtegido(LoginRequiredMixin, CreateView):
    template_name = "core/formulario.html"

    def form_valid(self, form):
        resposta = super().form_valid(form)
        messages.success(self.request, "Registro salvo com sucesso.")
        return resposta


class EditarProtegido(LoginRequiredMixin, UpdateView):
    template_name = "core/formulario.html"

    def form_valid(self, form):
        resposta = super().form_valid(form)
        messages.success(self.request, "Registro atualizado com sucesso.")
        return resposta


class ExcluirProtegido(LoginRequiredMixin, DeleteView):
    template_name = "core/confirmar_exclusao.html"

    def form_valid(self, form):
        resposta = super().form_valid(form)
        messages.success(self.request, "Registro excluído.")
        return resposta
