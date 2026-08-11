from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest

# The ceiling is the only thing bounding how much of the table this endpoint
# scans, so it is a business limit and not a formatting detail. Twelve months also
# happens to be the most that fits a readable axis.
MIN_MONTHS = 1
MAX_MONTHS = 12


def refund_summary_validator(http_request: HttpRequest) -> None:
    months = http_request.query.get("months")

    # None means the route's default was used, which is already inside the range.
    if months is None:
        return

    if not isinstance(months, int) or not MIN_MONTHS <= months <= MAX_MONTHS:
        raise HttpUnprocessableEntityError(
            f"Months must be between {MIN_MONTHS} and {MAX_MONTHS}"
        )
