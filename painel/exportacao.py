"""Relatórios de saída; não são entradas do importador original de quatro abas."""
import csv
from dataclasses import dataclass
from io import BytesIO, StringIO
from decimal import Decimal
import re
from django.db import transaction
from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from conferencia.models import EspelhoEmpresa, Pagamento
from core.calculos import somar_conhecidos
from entregas.models import Entrega
from entregas.services.conciliacao import filtrar_ciclos
from jornadas.models import Jornada
from .dashboard import montar_dashboard

FORMATOS = {
    "texto": "@", "data": "dd/mm/yyyy", "hora": "hh:mm:ss",
    "dinheiro": '"R$" #,##0.00', "decimal": "0.000", "inteiro": "0",
    "duracao": "[h]:mm:ss",
    "percentual": "0.00",
}


@dataclass(frozen=True)
class Coluna:
    titulo: str
    campo: str
    tipo: str = "texto"


def texto_excel(valor):
    texto = str(valor)
    if len(texto) > 32767:
        raise ValueError("Um campo de texto excede 32.767 caracteres, limite de uma célula Excel. Nenhum dado foi alterado.")
    return ILLEGAL_CHARACTERS_RE.sub("\ufffd", texto)


def proteger_csv(valor):
    """Excel reinterpreta texto ao abrir CSV: neutraliza prefixos de fórmula."""
    texto = str(valor)
    significativo = re.sub(r"^[\s\x00-\x1f\ufeff]+", "", texto)
    if significativo.startswith(("=", "+", "-", "@")) or texto.startswith(("\t", "\r", "\n")):
        return "'" + texto
    return texto


def preencher(celula, valor, tipo="texto"):
    if valor is None:
        return
    if tipo == "texto" or isinstance(valor, str):
        celula.value = texto_excel(valor)
        # Evita inferência de fórmulas, inclusive =HYPERLINK e referências DDE.
        celula.data_type = "s"
    else:
        celula.value = valor
    celula.number_format = FORMATOS[tipo]
    celula.alignment = Alignment(vertical="top", wrap_text=tipo == "texto")


def nova_aba(workbook, titulo, filtro, colunas):
    aba = workbook.create_sheet(titulo)
    for linha, texto in enumerate([
        titulo, "Filtro aplicado: " + filtro.descricao,
        "Relatório de saída. Não é automaticamente compatível com o importador original. Ausência é célula vazia.",
    ], 1):
        preencher(aba.cell(linha, 1), texto)
    for numero, coluna in enumerate(colunas, 1):
        celula = aba.cell(5, numero)
        preencher(celula, coluna.titulo)
        celula.fill = PatternFill("solid", fgColor="153E59")
        celula.font = Font(color="FFFFFF", bold=True)
        aba.column_dimensions[get_column_letter(numero)].width = 24 if coluna.tipo == "texto" else 21
    aba.freeze_panes = "A6"
    aba.sheet_view.showGridLines = False
    return aba


def escrever_registros(aba, colunas, registros):
    linha = 6
    for registro in registros:
        for numero, coluna in enumerate(colunas, 1):
            preencher(aba.cell(linha, numero), getattr(registro, coluna.campo), coluna.tipo)
        linha += 1
    aba.auto_filter.ref = f"A5:{get_column_letter(len(colunas))}{max(5, linha - 1)}"
    return linha + 1


def total(aba, linha, titulo, valor, tipo="dinheiro"):
    preencher(aba.cell(linha, 1), titulo)
    preencher(aba.cell(linha, 2), valor, tipo)
    aba.cell(linha, 1).font = Font(bold=True)


def registros_periodo(filtro):
    pagamentos = Pagamento.objects.all()
    if filtro.inicio:
        pagamentos = pagamentos.filter(fim_quinzena__gte=filtro.inicio)
    if filtro.fim:
        pagamentos = pagamentos.filter(inicio_quinzena__lte=filtro.fim)
    return (
        list(filtro.aplicar(Entrega.objects.all()).order_by("data", "ordem_original", "pk")),
        list(filtro.aplicar(EspelhoEmpresa.objects.all(), "data_competencia").order_by("data_competencia", "pk")),
        list(filtro.aplicar(Jornada.objects.all()).order_by("data", "pk")),
        list(pagamentos.order_by("inicio_quinzena", "data_pagamento", "pk")),
    )


@transaction.atomic
def exportar_xlsx(filtro, dias_projecao=5):
    entregas, espelhos, jornadas, pagamentos = registros_periodo(filtro)
    painel = montar_dashboard(filtro, dias_projecao)
    workbook = Workbook()
    workbook.remove(workbook.active)
    especificacoes = [
        ("Minhas Entregas", entregas, [
            Coluna("Código", "codigo"), Coluna("Data", "data", "data"),
            Coluna("Horário", "horario", "hora"), Coluna("Situação", "situacao"),
            Coluna("Valor por baixa preservado", "valor_por_baixa", "dinheiro"),
            Coluna("Valor previsto", "valor_previsto", "dinheiro"),
        ]),
        ("Espelhos da Empresa", espelhos, [
            Coluna("Competência", "data_competencia", "data"), Coluna("Baixas pagas", "baixas_pagas", "inteiro"),
            Coluna("Insucessos", "insucessos", "inteiro"), Coluna("Valor informado", "valor_empresa", "dinheiro"),
            Coluna("Vencimento", "vencimento", "data"), Coluna("Documento", "documento"), Coluna("Observações", "observacoes"),
        ]),
        ("Jornadas e Custos", jornadas, [
            Coluna("Data", "data", "data"), Coluna("Início real", "inicio_real", "hora"), Coluna("Fim real", "fim_real", "hora"),
            Coluna("Odômetro inicial", "odometro_inicial", "decimal"), Coluna("Odômetro final", "odometro_final", "decimal"),
            Coluna("KM conhecido", "quilometragem", "decimal"), Coluna("Litros", "litros_consumidos", "decimal"),
            Coluna("Combustível", "custo_combustivel", "dinheiro"), Coluna("Outros custos", "outros_custos", "dinheiro"),
            Coluna("Janela histórica", "janela_historica", "duracao"),
        ]),
        ("Pagamentos", pagamentos, [
            Coluna("Data do pagamento", "data_pagamento", "data"), Coluna("Início da quinzena", "inicio_quinzena", "data"),
            Coluna("Fim da quinzena", "fim_quinzena", "data"), Coluna("Valor efetivamente recebido", "valor_recebido", "dinheiro"),
            Coluna("Comprovante", "comprovante"), Coluna("Observações", "observacoes"),
        ]),
    ]
    for titulo, registros, colunas in especificacoes:
        aba = nova_aba(workbook, titulo, filtro, colunas)
        linha = escrever_registros(aba, colunas, registros)
        total(aba, linha, "Registros", len(registros), "inteiro")
        if titulo == "Minhas Entregas":
            total(aba, linha + 1, "Total previsto", painel["resumo"]["receita"])
            total(aba, linha + 2, "Ocorrências de baixa", painel["resumo"]["baixas"], "inteiro")
            total(aba, linha + 3, "Insucesso Total", painel["resumo"]["insucessos"], "inteiro")
        elif titulo == "Espelhos da Empresa":
            total(aba, linha + 1, "Informado conhecido", somar_conhecidos(e.valor_empresa for e in registros))
        elif titulo == "Jornadas e Custos":
            total(aba, linha + 1, "Combustível conhecido", painel["resumo"]["combustivel"])
            total(aba, linha + 2, "KM conhecido (pode ser parcial)", painel["resumo"]["km"], "decimal")
        elif titulo == "Pagamentos":
            total(aba, linha + 1, "Total recebido registrado", somar_conhecidos(p.valor_recebido for p in registros))
    aba = nova_aba(workbook, "Resumo de Indicadores", filtro, [Coluna("Indicador", ""), Coluna("Valor", ""), Coluna("Observação", "")])
    linhas = [
        ("Tentativas", painel["resumo"]["tentativas"], "inteiro", "Todos os registros, inclusive códigos repetidos."),
        ("Ocorrências de baixa", painel["resumo"]["baixas"], "inteiro", "Por data efetiva; base financeira preservada."),
        ("Insucesso Total", painel["resumo"]["insucessos"], "inteiro", "Todas as ocorrências na data registrada."),
        ("Sucesso por tentativa (%)", painel["resumo"]["sucesso_percentual"], "decimal", "Ocorrências de baixa / tentativas do período × 100."),
        ("Faturamento previsto", painel["resumo"]["receita"], "dinheiro", "Não é pagamento efetivo."),
        ("Informado conhecido", somar_conhecidos(e.valor_empresa for e in espelhos), "dinheiro", "Pode estar incompleto ou exigir revisão documental."),
        ("Recebido registrado", somar_conhecidos(p.valor_recebido for p in pagamentos), "dinheiro", "Competências sobrepostas ao filtro; não há rateio."),
        ("Horas reais", painel["resumo"]["horas_reais"], "decimal", ""),
        ("Horas históricas", painel["resumo"]["horas_historicas"], "decimal", "Não somadas a um par real na mesma jornada."),
        ("KM conhecido", painel["resumo"]["km"], "decimal", "Pode ser parcial."),
        ("Consumo comparável km/L", painel["resumo"]["consumo_km_l"], "decimal", "Somente jornadas com KM e litros válidos."),
        ("Custos conhecidos", painel["resumo"]["custos_conhecidos"], "dinheiro", "Campos ausentes não foram preenchidos com zero."),
        ("Resultado parcial", painel["resumo"]["resultado_parcial"], "dinheiro", "Não é lucro definitivo quando há despesas ausentes."),
        ("Resultado líquido completo", painel["resumo"]["resultado_liquido"], "dinheiro", "Exige cobertura completa de custos."),
        ("Dias observados", painel["projecao"]["dias_observados"], "inteiro", "Dias com entregas."),
        ("Projeção condicional", painel["projecao"]["receita_cenario"], "dinheiro", f"Cenário para {dias_projecao} dias com entregas; sem garantia de continuidade."),
    ]
    conciliacao = painel["conciliacao"]
    referencia = conciliacao["referencia"].strftime("%d/%m/%Y") if conciliacao["referencia"] else "sem registros"
    nota = ("Primeira tentativa no filtro; resultado conhecido até " + referencia
            + ". Inclui baixas posteriores ao período. Identidades conflitantes ficam fora dos indicadores por encomenda distinta desta auditoria.")
    for titulo, campo, tipo in [
        ("Entregas identificadas", "entregas_identificadas", "inteiro"),
        ("Baixas realizadas — entregas distintas", "concluidas", "inteiro"),
        ("Entregas com insucesso", "com_insucesso", "inteiro"),
        ("Entregas recuperadas", "recuperadas", "inteiro"),
        ("Insucesso Real — sem baixa posterior registrada", "insucessos_reais", "inteiro"),
        ("Sucesso por encomenda distinta (%)", "sucesso_percentual", "decimal"),
        ("Códigos em revisão", "codigos_em_revisao", "inteiro"),
        ("Ciclos com alerta financeiro", "alertas_financeiros", "inteiro"),
        ("Conclusões após o período", "concluidas_apos_periodo", "inteiro"),
    ]:
        linhas.append((titulo, conciliacao[campo], tipo, nota))
    linhas.append(("Taxa de Sucesso (%)", painel["indicadores_principais"]["taxa_sucesso"], "percentual",
                   "Ocorrências de baixa do período / (ocorrências de baixa do período + pendências distintas da população iniciada no período) × 100. "
                   + "Referência da conciliação: " + referencia
                   + ". Base mista; as baixas registradas permanecem no numerador mesmo se a identidade exigir revisão."))
    if painel["conciliacao_ate_fim"] is not None:
        for titulo, campo in [("Concluídas até o fim do período", "concluidas"),
                              ("Insucesso Real até o fim do período", "insucessos_reais")]:
            linhas.append((titulo, painel["conciliacao_ate_fim"][campo], "inteiro",
                           "Fotografia sem consultar registros posteriores ao fim do filtro."))
    for quinzena in painel["quinzenas"]:
        prefixo = f"{quinzena['inicio']:%d/%m/%Y} a {quinzena['fim']:%d/%m/%Y}"
        for titulo, campo, nota in [
            ("Previsto", "receita", quinzena["status"]), ("Informado conhecido", "valor_empresa", quinzena["status"]),
            ("Diferença confrontável", "diferenca", "Somente competências confrontáveis."),
            ("Recebido da quinzena", "recebido", quinzena["status_pagamento"]),
            ("Saldo do informado", "saldo", "Bloqueado em recorte parcial ou sem dados suficientes."),
        ]:
            linhas.append((prefixo + " · " + titulo, quinzena[campo], "dinheiro", nota))
    for numero, (titulo, valor, tipo, nota) in enumerate(linhas, 6):
        preencher(aba.cell(numero, 1), titulo)
        preencher(aba.cell(numero, 2), valor, tipo)
        preencher(aba.cell(numero, 3), nota)
    aba.column_dimensions["A"].width = 53
    aba.column_dimensions["C"].width = 65
    arquivo = BytesIO()
    workbook.save(arquivo)
    workbook.close()
    return arquivo.getvalue()


@transaction.atomic
def exportar_csv(filtro):
    arquivo = StringIO(newline="")
    escritor = csv.writer(arquivo, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    escritor.writerow(["Código", "Data", "Horário", "Situação", "Valor previsto (R$)"])
    registros = filtro.aplicar(Entrega.objects.all()).order_by("data", "ordem_original", "pk")
    for entrega in registros:
        escritor.writerow([
            proteger_csv(entrega.codigo), entrega.data.strftime("%d/%m/%Y"),
            entrega.horario.strftime("%H:%M:%S") if entrega.horario is not None else "", proteger_csv(entrega.situacao),
            f"{entrega.valor_previsto:.2f}".replace(".", ","),
        ])
    return arquivo.getvalue().encode("utf-8-sig")


@transaction.atomic
def exportar_conciliacao_csv(filtro, situacao="", codigo=""):
    """Tabela derivada, separada do CSV original de ocorrências e sem fórmulas."""
    conciliacao = montar_dashboard(filtro)["conciliacao"]
    ciclos = filtrar_ciclos(conciliacao["ciclos"], situacao, codigo)
    arquivo = StringIO(newline="")
    escritor = csv.writer(arquivo, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    escritor.writerow(["Código", "Ciclo candidato", "Primeira tentativa", "Primeiro insucesso",
                       "Horário primeiro insucesso", "Tentativas", "Ocorrências de insucesso",
                       "Ocorrências de baixa", "Baixa posterior / conclusão", "Horário da baixa",
                       "Situação final conhecida", "Motivos de revisão", "Alertas financeiros",
                       "Receita registrada (R$)", "IDs dos registros", "Resultado conhecido até",
                       "População: primeira tentativa no período"])
    def data(valor):
        return valor.strftime("%d/%m/%Y") if valor is not None else ""
    def hora(valor):
        return valor.strftime("%H:%M:%S") if valor is not None else ""
    for ciclo in ciclos:
        valores = [ciclo.codigo, ciclo.ciclo, data(ciclo.primeira_tentativa), data(ciclo.primeiro_insucesso),
                   hora(ciclo.horario_primeiro_insucesso), ciclo.tentativas, ciclo.insucessos, ciclo.baixas,
                   data(ciclo.data_baixa), hora(ciclo.horario_baixa), ciclo.rotulo,
                   " | ".join(ciclo.motivos_revisao), " | ".join(ciclo.alertas_financeiros),
                   f"{ciclo.receita_registrada:.2f}".replace(".", ","),
                   ", ".join(map(str, ciclo.ids_registros)), data(conciliacao["referencia"]), filtro.descricao]
        escritor.writerow([proteger_csv(valor) for valor in valores])
    return arquivo.getvalue().encode("utf-8-sig")
