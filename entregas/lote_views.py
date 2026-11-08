"""Prévia e confirmação autenticadas; GET e prévia nunca criam entregas."""
import json
import logging
from urllib.parse import urlencode
from uuid import uuid4
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .lote_forms import CabecalhoLoteForm, LIMITE_LINHAS, validar_linhas
from .models import Entrega, LoteEntrega
from .services.lote import ConflitoLote, assinatura_conteudo, salvar_lote

logger = logging.getLogger(__name__)
SALT_PREVIA = "entregas.previa-lote.v1"


def contexto_grade(request, formulario, linhas, **extras):
    return {"titulo": "Adicionar Entregas em Lote", "form": formulario,
            "linhas_iniciais": linhas, "erros_linhas": [], "limite": LIMITE_LINHAS,
            "rascunho_chave": f"entregas:lote:v1:{request.user.pk}",
            "enviado": request.method == "POST", **extras}


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def adicionar_lote(request):
    if request.method == "GET":
        padroes = CabecalhoLoteForm({"data_padrao": request.GET.get("data", timezone.localdate().isoformat()),
                                   "situacao_padrao": request.GET.get("situacao", Entrega.Situacao.BAIXA),
                                   "chave": uuid4(), "linhas": "[]"})
        if padroes.is_valid():
            data, situacao = padroes.cleaned_data["data_padrao"], padroes.cleaned_data["situacao_padrao"]
        else:
            data, situacao = timezone.localdate(), Entrega.Situacao.BAIXA
        formulario = CabecalhoLoteForm(initial={"data_padrao": data, "situacao_padrao": situacao,
                                               "chave": uuid4(), "linhas": "[]"})
        return render(request, "entregas/lote.html", contexto_grade(request, formulario, []))

    formulario = CabecalhoLoteForm(request.POST)
    valido = formulario.is_valid()
    linhas = formulario.cleaned_data.get("linhas", [])
    contexto = contexto_grade(request, formulario, linhas)
    if not valido:
        return render(request, "entregas/lote.html", contexto, status=400)
    dados = formulario.cleaned_data
    validas, erros = validar_linhas(linhas, dados["data_padrao"], dados["situacao_padrao"])
    contexto["erros_linhas"] = erros
    if erros or not validas:
        formulario.add_error(None, "Corrija as linhas destacadas. Nenhuma entrega foi salva." if erros
                             else "Preencha ao menos um código. Nenhuma entrega foi salva.")
        return render(request, "entregas/lote.html", contexto, status=400)
    if request.POST.get("acao") == "editar":
        return render(request, "entregas/lote.html", contexto)

    conteudo = {"usuario": request.user.pk, "chave": str(dados["chave"]),
                "sha256": assinatura_conteudo(validas, dados["data_padrao"], dados["situacao_padrao"])}
    if request.POST.get("acao") == "salvar":
        try:
            if signing.loads(dados["comprovante"], salt=SALT_PREVIA, max_age=86400) != conteudo:
                raise signing.BadSignature
        except signing.BadSignature:
            formulario.add_error(None, "Confira novamente a prévia antes de confirmar este lote. Nenhum registro foi salvo.")
            return render(request, "entregas/lote.html", contexto, status=400)
        try:
            recibo, novo = salvar_lote(request.user, dados["chave"], validas, dados["data_padrao"], dados["situacao_padrao"])
        except ConflitoLote as erro:
            formulario.add_error(None, str(erro))
            return render(request, "entregas/lote.html", contexto, status=409)
        except (DatabaseError, ValidationError):
            logger.exception("Não foi possível concluir o lote de entregas.")
            formulario.add_error(None, "Não foi possível gravar o lote. Nada foi salvo parcialmente. Seus dados continuam na grade; confira a conexão e tente novamente.")
            return render(request, "entregas/lote.html", contexto, status=503)
        messages.success(request, f"{recibo.quantidade} entregas salvas com sucesso." if novo
                         else f"Este lote de {recibo.quantidade} entregas já estava salvo. O reenvio não criou registros.")
        return redirect("entregas:lote_sucesso", pk=recibo.pk)

    formulario = CabecalhoLoteForm(initial={**request.POST.dict(), "linhas": json.dumps(linhas),
                                           "comprovante": signing.dumps(conteudo, salt=SALT_PREVIA)})
    baixas = sum(linha["situacao"] == Entrega.Situacao.BAIXA for linha in validas)
    contexto.update(form=formulario, previa=validas, quantidade=len(validas), baixas=baixas,
                    insucessos=len(validas) - baixas)
    return render(request, "entregas/lote.html", contexto)


@login_required
@never_cache
@require_http_methods(["GET"])
def lote_sucesso(request, pk):
    recibo = get_object_or_404(LoteEntrega, pk=pk, usuario=request.user)
    proximo = reverse("entregas:lote") + "?" + urlencode({"data": recibo.data_padrao.isoformat(), "situacao": recibo.situacao_padrao})
    return render(request, "entregas/lote_sucesso.html", {
        "titulo": "Lote salvo", "recibo": recibo, "proximo_lote": proximo,
        "rascunho_chave": f"entregas:lote:v1:{request.user.pk}",
    })
