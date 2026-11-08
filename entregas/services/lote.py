"""Gravação integral e recibo de reenvio na mesma transação do SQLite."""
import hashlib
import json
from django.db import transaction
from django.core.serializers.json import DjangoJSONEncoder
from painel.models import valor_baixa_atual
from entregas.models import Entrega, LoteEntrega


class ConflitoLote(ValueError):
    pass


def assinatura_conteudo(linhas, data_padrao, situacao_padrao):
    dados = {"linhas": linhas, "data_padrao": data_padrao, "situacao_padrao": situacao_padrao}
    texto = json.dumps(dados, cls=DjangoJSONEncoder, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


@transaction.atomic
def salvar_lote(usuario, chave, linhas, data_padrao, situacao_padrao):
    """Repetir a chave confirma o recibo; mudar os códigos exige um novo lote."""
    resumo = assinatura_conteudo(linhas, data_padrao, situacao_padrao)
    recibo, novo = LoteEntrega.objects.get_or_create(usuario=usuario, chave=chave, defaults={
        "sha256": resumo, "quantidade": len(linhas), "data_padrao": data_padrao,
        "situacao_padrao": situacao_padrao,
    })
    if not novo:
        if recibo.sha256 != resumo:
            raise ConflitoLote("Este lote já foi salvo com outros dados. Confira Minhas Entregas antes de começar outro lote.")
        return recibo, False
    # A mesma regra do cadastro individual; lê o preço vigente uma vez por lote.
    valor = valor_baixa_atual()
    registros = [Entrega(**linha, valor_por_baixa=valor) for linha in linhas]
    for registro in registros:
        registro.full_clean(validate_unique=False, validate_constraints=False)
    Entrega.objects.bulk_create(registros, batch_size=100)
    return recibo, True
