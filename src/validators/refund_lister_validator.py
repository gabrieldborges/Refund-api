from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest

ALLOWED_STATUS_FILTERS = {"pending", "approved", "rejected", "paid"}
# These names are keys into RefundsRepository.SORTABLE_COLUMNS, never text
# interpolated into SQL. Refusing anything outside the set here is the first of
# two barriers; the dictionary lookup is the second.
SORTABLE_FIELDS = {"created_at", "amount_in_cents", "name", "status"}
ALLOWED_ORDERS = {"asc", "desc"}


def refund_lister_validator(http_request: HttpRequest) -> None:
    query = http_request.query

    status = query.get("status")
    if status is not None and status not in ALLOWED_STATUS_FILTERS:
        raise HttpUnprocessableEntityError(
            f"Status must be one of: {', '.join(sorted(ALLOWED_STATUS_FILTERS))}"
        )

    sort = query.get("sort")
    if sort is not None and sort not in SORTABLE_FIELDS:
        raise HttpUnprocessableEntityError(
            f"Sort must be one of: {', '.join(sorted(SORTABLE_FIELDS))}"
        )

    order = query.get("order")
    if order is not None and order not in ALLOWED_ORDERS:
        raise HttpUnprocessableEntityError(
            f"Order must be one of: {', '.join(sorted(ALLOWED_ORDERS))}"
        )
