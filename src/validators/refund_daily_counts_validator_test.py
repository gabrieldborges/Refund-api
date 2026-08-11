import pytest
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest
from .refund_daily_counts_validator import refund_daily_counts_validator


def _request(month):
    return HttpRequest(query={"month": month})


# It returns the parsed parts, so the view never re-reads the string. Two readings
# of one format is how one of them ends up accepting what the other refuses.
def test_it_returns_the_year_and_month_as_integers():
    assert refund_daily_counts_validator(_request("2026-08")) == (2026, 8)


def test_a_malformed_month_raises():
    for month in ("2026-8", "2026/08", "202608", "agosto", "", "2026-08-01"):
        with pytest.raises(HttpUnprocessableEntityError):
            refund_daily_counts_validator(_request(month))


def test_a_missing_month_raises():
    with pytest.raises(HttpUnprocessableEntityError):
        refund_daily_counts_validator(HttpRequest(query={}))


def test_a_year_outside_the_range_raises():
    for month in ("1999-08", "2101-08"):
        with pytest.raises(HttpUnprocessableEntityError) as error:
            refund_daily_counts_validator(_request(month))
        assert "between 2000 and 2100" in str(error.value)


# "2026-13" matches the pattern but is not a month — the regex checks shape, and this
# checks meaning.
def test_a_month_number_outside_one_to_twelve_raises():
    for month in ("2026-00", "2026-13", "2026-99"):
        with pytest.raises(HttpUnprocessableEntityError) as error:
            refund_daily_counts_validator(_request(month))
        assert "between 01 and 12" in str(error.value)


def test_the_edges_of_the_range_pass():
    assert refund_daily_counts_validator(_request("2000-01")) == (2000, 1)
    assert refund_daily_counts_validator(_request("2100-12")) == (2100, 12)
