"""Importação atômica do layout analisado. Nunca escreve no workbook."""
import hashlib
from collections import Counter, defaultdict
from contextlib import ExitStack
from datetime import date, datetime, time, timedelta
from io import BytesIO
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import transaction
from openpyxl import load_workbook

from conferencia.models import EspelhoEmpresa, Pagamento
from core.models import Importacao
from entregas.models import Entrega
from jornadas.models import Jornada
from painel.models import Configuracao
from .conversoes import (
    codigo_excel, data_excel, decimal_excel, duracao_excel,
    horario_excel, inteiro_excel, vazio,
)

ABAS = ("Painel Geral", "Minhas Entregas", "Espelho da Empresa", "Jornada e Custos")
PARAMETROS = {"valor_por_baixa": "B5", "meta_diaria": "B6", "meta_semanal": "B7", "meta_mensal": "B8"}


class ErroImportacao(ValueError):
    """Falha legível que impede qualquer gravação parcial."""


def serializar(valor):
    if isinstance(valor, (datetime, date, time)):
        return valor.isoformat()
    if isinstance(valor, timedelta):
        return str(valor)
    return valor


def entrada(aba, linha, coluna):
    celula = aba[f"{coluna}{linha}"]
    if celula.data_type == "f":
        raise ErroImportacao(f"{aba.title}!{celula.coordinate}: fórmula em campo de entrada; confira a origem.")
    return None if vazio(celula.value) else celula.value


def tem_dados(aba, linha, colunas):
    return any(not vazio(aba[f"{c}{linha}"].value) and aba[f"{c}{linha}"].data_type != "f" for c in colunas)


def salvar(modelo, lote, aba, linha, campos, colunas):
    dados = {
        c: {"valor": serializar(aba[f"{c}{linha}"].value), "formato": aba[f"{c}{linha}"].number_format}
        for c in colunas
    }
    registro = modelo(importacao=lote, aba_origem=aba.title, linha_origem=linha, dados_origem=dados, **campos)
    try:
        registro.full_clean()
        registro.save()
    except (ValidationError, ValueError) as erro:
        raise ErroImportacao(f"{aba.title}, linha {linha}: {erro}") from erro
    return registro


def validar_layout(workbook):
    if set(workbook.sheetnames) != set(ABAS):
        raise ErroImportacao(f"Esperadas exatamente as quatro abas: {', '.join(ABAS)}.")
    cabecalhos = {
        "Painel Geral": {"A5": "Valor por baixa (R$)", "A6": "Meta diária (R$)", "A7": "Meta semanal (R$)", "A8": "Meta mensal (R$)"},
        "Minhas Entregas": {"A2": "Código", "B2": "Data", "C2": "Horário", "D2": "Situação"},
        "Espelho da Empresa": {"A4": "Data", "B4": "Baixas pagas", "C4": "Insucessos", "E4": "Valor empresa", "I4": "Vencimento", "J4": "Documento", "K4": "Observação", "T4": "Data pagamento", "U4": "Início quinzena", "V4": "Fim quinzena", "W4": "Valor recebido", "X4": "Comprovante", "Y4": "Observação"},
        "Jornada e Custos": {"A4": "Data", "B4": "Início real", "C4": "Fim real", "D4": "Odômetro inicial", "E4": "Odômetro final", "F4": "Litros consumidos", "G4": "Combustível (R$)", "H4": "Outros custos (R$)", "X4": "Janela observada histórica"},
    }
    for nome, esperados in cabecalhos.items():
        for coordenada, texto in esperados.items():
            if workbook[nome][coordenada].value != texto:
                raise ErroImportacao(f"Layout inesperado em {nome}!{coordenada}: esperado {texto!r}.")


@transaction.atomic
def importar_excel(caminho):
    """Mesmo SHA-256 é ignorado, inclusive após edição ou exclusão manual."""
    caminho = Path(caminho).resolve()
    conteudo = caminho.read_bytes()
    sha = hashlib.sha256(conteudo).hexdigest()
    existente = Importacao.objects.filter(sha256=sha).first()
    if existente:
        return existente, False
    if Importacao.objects.filter(nome_arquivo=caminho.name).exists():
        raise ErroImportacao("Já existe importação desse nome com conteúdo diferente. Nenhum dado foi alterado. Revise a origem antes de uma nova importação; substituição automática não é permitida.")

    with ExitStack() as pilha:
        workbook = load_workbook(BytesIO(conteudo), data_only=False)
        pilha.callback(workbook.close)
        # Caches são apenas evidência; não tratamos resultados auxiliares como dados reais.
        cache = load_workbook(BytesIO(conteudo), data_only=True)
        pilha.callback(cache.close)
        validar_layout(workbook)
        lote = Importacao.objects.create(nome_arquivo=caminho.name, caminho=str(caminho), sha256=sha)
        avisos = []
        totais = Counter()
        por_data = defaultdict(Counter)
        painel = workbook[ABAS[0]]
        parametros = {campo: decimal_excel(entrada(painel, int(coord[1:]), coord[0])) for campo, coord in PARAMETROS.items()}
        configuracao = Configuracao(**parametros)
        configuracao.full_clean()
        atual = Configuracao.objects.order_by("-pk").first()
        if atual is None:
            configuracao.save()
        elif any(getattr(atual, campo) != valor for campo, valor in parametros.items()):
            avisos.append("Os parâmetros atuais foram mantidos; os da planilha estão no resumo. O preço histórico das entregas usa o valor da planilha.")

        aba = workbook[ABAS[1]]
        for linha in range(3, aba.max_row + 1):
            if not tem_dados(aba, linha, "ABCD"):
                continue
            try:
                codigo = codigo_excel(aba[f"A{linha}"])
                if aba[f"A{linha}"].data_type == "f":
                    raise ValueError("Código não pode ser fórmula.")
                campos = {
                    "codigo": codigo,
                    "data": data_excel(entrada(aba, linha, "B"), workbook.epoch),
                    "horario": horario_excel(entrada(aba, linha, "C"), workbook.epoch),
                    "situacao": entrada(aba, linha, "D"),
                    "ordem_original": linha - 2,
                    "valor_por_baixa": parametros["valor_por_baixa"],
                }
                registro = salvar(Entrega, lote, aba, linha, campos, "ABCD")
            except (ValueError, TypeError) as erro:
                raise ErroImportacao(f"{aba.title}, linha {linha}: {erro}") from erro
            if aba[f"A{linha}"].data_type == "n" and len(codigo.lstrip("0")) > 15:
                avisos.append(f"{aba.title}!A{linha}: código numérico com mais de 15 dígitos; a precisão anterior do Excel não pode ser recuperada.")
            dados = por_data[registro.data.isoformat()]
            dados["tentativas"] += 1
            dados["baixas" if registro.situacao == Entrega.Situacao.BAIXA else "insucessos"] += 1
            totais["entregas"] += 1
            valor_cache = cache[aba.title][f"E{linha}"].value
            if not vazio(valor_cache) and decimal_excel(valor_cache) != registro.valor_previsto:
                avisos.append(f"{aba.title}!E{linha}: cache de receita difere da regra de baixa; fórmula/cache preservados como evidência no arquivo original.")

        aba = workbook[ABAS[2]]
        for linha in range(5, aba.max_row + 1):
            if tem_dados(aba, linha, "ABCEIJK"):
                campos = {
                    "data_competencia": data_excel(entrada(aba, linha, "A"), workbook.epoch),
                    "baixas_pagas": inteiro_excel(entrada(aba, linha, "B")),
                    "insucessos": inteiro_excel(entrada(aba, linha, "C")),
                    "valor_empresa": decimal_excel(entrada(aba, linha, "E")),
                    "vencimento": data_excel(entrada(aba, linha, "I"), workbook.epoch),
                    "documento": str(entrada(aba, linha, "J") or ""),
                    "observacoes": str(entrada(aba, linha, "K") or ""),
                }
                salvar(EspelhoEmpresa, lote, aba, linha, campos, "ABCEIJK")
                totais["espelhos"] += 1
                if any(campos[c] is None for c in ("baixas_pagas", "insucessos", "valor_empresa")):
                    avisos.append(f"{aba.title}, linha {linha}: espelho incompleto preservado com valores nulos.")
            if tem_dados(aba, linha, "TUVWXY"):
                campos = {
                    "data_pagamento": data_excel(entrada(aba, linha, "T"), workbook.epoch),
                    "inicio_quinzena": data_excel(entrada(aba, linha, "U"), workbook.epoch),
                    "fim_quinzena": data_excel(entrada(aba, linha, "V"), workbook.epoch),
                    "valor_recebido": decimal_excel(entrada(aba, linha, "W")),
                    "comprovante": str(entrada(aba, linha, "X") or ""),
                    "observacoes": str(entrada(aba, linha, "Y") or ""),
                }
                salvar(Pagamento, lote, aba, linha, campos, "TUVWXY")
                totais["pagamentos"] += 1

        aba = workbook[ABAS[3]]
        for linha in range(5, aba.max_row + 1):
            # A agenda tem 130 datas prontas. Data isolada não significa jornada.
            if not tem_dados(aba, linha, "BCDEFGHX"):
                if not vazio(aba[f"A{linha}"].value):
                    totais["datas_sem_jornada_ignoradas"] += 1
                continue
            campos = {
                "data": data_excel(entrada(aba, linha, "A"), workbook.epoch),
                "inicio_real": horario_excel(entrada(aba, linha, "B"), workbook.epoch),
                "fim_real": horario_excel(entrada(aba, linha, "C"), workbook.epoch),
                "odometro_inicial": decimal_excel(entrada(aba, linha, "D"), 3),
                "odometro_final": decimal_excel(entrada(aba, linha, "E"), 3),
                "litros_consumidos": decimal_excel(entrada(aba, linha, "F"), 3),
                "custo_combustivel": decimal_excel(entrada(aba, linha, "G")),
                "outros_custos": decimal_excel(entrada(aba, linha, "H")),
                "janela_historica": duracao_excel(entrada(aba, linha, "X")),
            }
            salvar(Jornada, lote, aba, linha, campos, "ABCDEFGHX")
            totais["jornadas"] += 1

        for dia, dados in por_data.items():
            dados["receita"] = str(parametros["valor_por_baixa"] * dados["baixas"])
        repetidos = Counter(Entrega.objects.filter(importacao=lote).values_list("codigo", flat=True))
        lote.resumo = {
            "abas_lidas": list(ABAS), "parametros_excel": {k: str(v) for k, v in parametros.items()},
            "contagens": {chave: totais[chave] for chave in ("entregas", "espelhos", "jornadas", "pagamentos", "datas_sem_jornada_ignoradas")},
            "por_data": dict(sorted(por_data.items())),
            "codigos_repetidos": {k: n for k, n in repetidos.items() if n > 1},
        }
        lote.avisos = avisos
        lote.save(update_fields=["resumo", "avisos"])
        return lote, True
