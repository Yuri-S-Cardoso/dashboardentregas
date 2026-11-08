"""Workbooks sintéticos mínimos para testar erros, sem simular o histórico real."""
from datetime import date
from openpyxl import Workbook
from openpyxl.utils.datetime import to_excel
from entregas.services.importacao import ABAS, PARAMETROS


def workbook_teste(caminho):
    workbook = Workbook()
    workbook.remove(workbook.active)
    for nome in ABAS:
        workbook.create_sheet(nome)
    painel = workbook[ABAS[0]]
    for coord, texto in {"A5": "Valor por baixa (R$)", "A6": "Meta diária (R$)", "A7": "Meta semanal (R$)", "A8": "Meta mensal (R$)"}.items():
        painel[coord] = texto
    for coord, valor in zip(PARAMETROS.values(), [5, 300, 1500, 6000]):
        painel[coord] = valor
    entregas = workbook[ABAS[1]]
    entregas.append(["Título"])
    entregas.append(["Código", "Data", "Horário", "Situação", "Valor previsto"])
    entregas.append([123, to_excel(date(2026, 10, 15)), .5, "Baixa realizada", "=5"])
    entregas["A3"].number_format = "000000"
    entregas.append(["000123", to_excel(date(2026, 10, 15)), .75, "Insucesso", "=0"])
    entregas["E5"] = '=IF(A5="","",5)'
    empresa = workbook[ABAS[2]]
    empresa.append(["Título"])
    empresa.append(["Instruções"])
    empresa.append([])
    empresa.append([
        "Data", "Baixas pagas", "Insucessos", "Total empresa", "Valor empresa", "R$/baixa",
        "Início quinzena", "Fim quinzena", "Vencimento", "Documento", "Observação",
        "Minhas baixas", "Meus insucessos", "Meu valor", "Dif. baixas", "Dif. insucessos", "Dif. valor", "Resultado", "",
        "Data pagamento", "Início quinzena", "Fim quinzena", "Valor recebido", "Comprovante", "Observação",
    ])
    empresa["A5"] = to_excel(date(2026, 10, 15))
    empresa["B5"] = 1
    empresa["C5"] = 0
    empresa["E5"] = 5
    empresa["J5"] = "Documento de teste"
    jornada = workbook[ABAS[3]]
    jornada.append(["Título"])
    jornada.append(["Instruções"])
    jornada.append([])
    jornada.append([
        "Data", "Início real", "Fim real", "Odômetro inicial", "Odômetro final", "Litros consumidos", "Combustível (R$)", "Outros custos (R$)",
        *["Auxiliar"] * 15, "Janela observada histórica",
    ])
    jornada["A5"] = to_excel(date(2026, 10, 15))
    jornada["D5"] = 0
    jornada["E5"] = 67.59999999999999
    jornada["F5"] = 3.762
    jornada["G5"] = 20.45
    jornada["H5"] = 0
    jornada["X5"] = .125
    jornada["A6"] = to_excel(date(2026, 10, 16))
    jornada["I6"] = "=0"
    workbook.save(caminho)
    return workbook
