import pytest
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest
from .refund_summary_validator import refund_summary_validator


def _request(months):
    return HttpRequest(query={"months": months})


def test_a_month_count_inside_the_range_passes():
    for months in (1, 6, 12):
        refund_summary_validator(_request(months))


# The ceiling is what bounds the table scan, so exceeding it must be refused
# rather than silently clamped: a clamp would answer a different question than the
# one asked, without saying so.
def test_a_month_count_above_the_ceiling_raises():
    with pytest.raises(HttpUnprocessableEntityError) as error:
        refund_summary_validator(_request(13))

    assert "between 1 and 12" in str(error.value)


def test_zero_or_negative_months_raises():
    for months in (0, -1):
        with pytest.raises(HttpUnprocessableEntityError):
            refund_summary_validator(_request(months))


# An absent value means the route's own default was used, which is already inside
# the range — refusing it would reject a request that never named the parameter.
def test_an_absent_month_count_passes():
    refund_summary_validator(HttpRequest(query={}))
