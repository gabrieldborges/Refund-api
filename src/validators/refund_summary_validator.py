from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest

# O piso é o ano em que o produto pode ter dado: antes disso não existia. O teto
# impede um ano absurdo produzir um datetime inválido no controller. Não é
# formatação — é o que limita a janela que a consulta varre.
MIN_YEAR = 2000
MAX_YEAR = 2100


def refund_summary_validator(http_request: HttpRequest) -> None:
    year = http_request.query.get("year")

    # None significa que o cliente não pediu ano nenhum, e o controller usa o
    # corrente — recusar aqui rejeitaria uma requisição que nunca nomeou o campo.
    if year is None:
        return

    if not isinstance(year, int) or not MIN_YEAR <= year <= MAX_YEAR:
        raise HttpUnprocessableEntityError(f"Year must be between {MIN_YEAR} and {MAX_YEAR}")
