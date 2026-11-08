from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from .forms import FiltroPainelForm, ConsultaConciliacaoForm
from .exportacao import exportar_xlsx, exportar_csv, exportar_conciliacao_csv


@login_required
@require_GET
def baixar_relatorio(request, formato):
    form = FiltroPainelForm(request.GET)
    if not form.is_valid():
        return render(request, "painel/erro_exportacao.html", {"filtro": form}, status=400)
    try:
        filtro = form.cleaned_data["filtro"]
        dados = exportar_xlsx(filtro, form.cleaned_data["dias_projecao"]) if formato == "xlsx" else exportar_csv(filtro)
    except ValueError as erro:
        return render(request, "painel/erro_exportacao.html", {"erro": str(erro)}, status=400)
    mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if formato == "xlsx" else "text/csv; charset=utf-8"
    resposta = HttpResponse(dados, content_type=mime)
    resposta["Content-Disposition"] = f'attachment; filename="entregas_relatorio.{formato}"'
    resposta["Cache-Control"] = "private, no-store"
    resposta["Pragma"] = "no-cache"
    return resposta


@login_required
@require_GET
def baixar_conciliacao(request):
    form = FiltroPainelForm(request.GET)
    consulta = ConsultaConciliacaoForm(request.GET)
    periodo_valido, consulta_valida = form.is_valid(), consulta.is_valid()
    if not periodo_valido or not consulta_valida:
        return render(request, "painel/erro_exportacao.html",
                      {"filtro": form, "erro": "Corrija o período ou os campos da consulta."}, status=400)
    dados = exportar_conciliacao_csv(form.cleaned_data["filtro"],
                                   consulta.cleaned_data["situacao_conciliacao"], consulta.cleaned_data["codigo"])
    resposta = HttpResponse(dados, content_type="text/csv; charset=utf-8")
    resposta["Content-Disposition"] = 'attachment; filename="conciliacao_entregas.csv"'
    resposta["Cache-Control"] = "private, no-store"
    resposta["Pragma"] = "no-cache"
    return resposta
