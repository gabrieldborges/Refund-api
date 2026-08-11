import re
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest

MONTH_PATTERN = re.compile(r"^(\d{4})-(\d{2})$")
# Mesma faixa de ano de UC-017, pelo mesmo motivo: impedir um valor absurdo de
# construir uma data inválida no controller.
MIN_YEAR = 2000
MAX_YEAR = 2100


def refund_daily_counts_validator(http_request: HttpRequest) -> tuple[int, int]:
    """Valida `month` e devolve (ano, mês) já como inteiros.

    Devolve em vez de só validar porque quem valida o formato é quem já o quebrou em
    partes — deixar a view repetir o parse seria duas leituras da mesma string, e é
    assim que uma delas passa a aceitar o que a outra recusa.
    """
    month = http_request.query.get("month")

    if not isinstance(month, str) or not MONTH_PATTERN.match(month):
        raise HttpUnprocessableEntityError("Month must be in the format YYYY-MM")

    year_text, month_text = month.split("-")
    year, month_number = int(year_text), int(month_text)

    if not MIN_YEAR <= year <= MAX_YEAR:
        raise HttpUnprocessableEntityError(f"Year must be between {MIN_YEAR} and {MAX_YEAR}")

    if not 1 <= month_number <= 12:
        raise HttpUnprocessableEntityError("Month must be between 01 and 12")

    return year, month_number
