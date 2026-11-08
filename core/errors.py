from django.shortcuts import render


def csrf_failure(request, reason=""):
    """Mensagem em português sem expor detalhes internos da validação CSRF."""
    return render(request, "403.html", status=403)
