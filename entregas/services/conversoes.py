"""Conversões explícitas: vazio é None; números do Excel usam sua época."""
import re
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from openpyxl.utils.datetime import from_excel, WINDOWS_EPOCH


def vazio(valor):
    return valor is None or isinstance(valor, str) and not valor.strip()


def decimal_excel(valor, casas=2):
    if vazio(valor):
        return None
    if isinstance(valor, bool):
        raise ValueError("Valor booleano não é um número válido.")
    if isinstance(valor, str):
        valor = valor.strip().replace("R$", "").replace(" ", "")
        if "," in valor:
            valor = valor.replace(".", "").replace(",", ".")
    try:
        numero = Decimal(str(valor))
        if not numero.is_finite():
            raise ValueError("Número não finito.")
        return numero.quantize(Decimal(1).scaleb(-casas), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError) as erro:
        raise ValueError(f"Número inválido: {valor!r}") from erro


def inteiro_excel(valor):
    if vazio(valor):
        return None
    numero = decimal_excel(valor, casas=8)
    if numero != numero.to_integral_value():
        raise ValueError("Quantidade deve ser inteira.")
    return int(numero)


def data_excel(valor, epoch=WINDOWS_EPOCH):
    if vazio(valor):
        return None
    if isinstance(valor, bool):
        raise ValueError("Data inválida.")
    if isinstance(valor, (int, float, Decimal)):
        valor = from_excel(float(valor), epoch=epoch)
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        for formato in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(valor.strip(), formato).date()
            except ValueError:
                pass
    raise ValueError(f"Data inválida: {valor!r}")


def horario_excel(valor, epoch=WINDOWS_EPOCH):
    if vazio(valor):
        return None
    if isinstance(valor, bool):
        raise ValueError("Horário inválido.")
    if isinstance(valor, (int, float, Decimal)):
        if not 0 <= valor < 1:
            raise ValueError("Horário numérico deve estar entre 0 e 1 dia.")
        valor = from_excel(float(valor), epoch=epoch)
    if isinstance(valor, datetime):
        valor = valor.time()
    if isinstance(valor, time):
        return valor
    if isinstance(valor, str):
        try:
            return time.fromisoformat(valor.strip())
        except ValueError:
            pass
    raise ValueError(f"Horário inválido: {valor!r}")


def duracao_excel(valor):
    if vazio(valor):
        return None
    if isinstance(valor, timedelta):
        return valor
    if isinstance(valor, time):
        return timedelta(hours=valor.hour, minutes=valor.minute, seconds=valor.second, microseconds=valor.microsecond)
    if isinstance(valor, (int, float, Decimal)) and not isinstance(valor, bool):
        # A fração de dia representa uma duração, não uma data/hora civil.
        return timedelta(microseconds=int((Decimal(str(valor)) * 86400000000).quantize(Decimal(1), rounding=ROUND_HALF_UP)))
    horario = horario_excel(valor)
    return duracao_excel(horario)


def codigo_excel(celula):
    valor = celula.value
    if vazio(valor):
        raise ValueError("Código de entrega ausente.")
    if isinstance(valor, str):
        return valor
    if isinstance(valor, (int, float, Decimal)) and not isinstance(valor, bool):
        numero = Decimal(str(valor))
        if not numero.is_finite() or numero != numero.to_integral_value():
            raise ValueError("Código numérico precisa ser inteiro; use texto para outras representações.")
        texto = str(int(numero))
        if re.fullmatch(r"0+", celula.number_format or ""):
            texto = texto.zfill(len(celula.number_format))
        return texto
    raise ValueError("Código deve ser textual ou numérico inteiro.")
