import pytest
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest
from .refund_summary_validator import refund_summary_validator


def _request(year):
    return HttpRequest(query={"year": year})


def test_a_year_inside_the_range_passes():
    for year in (2000, 2026, 2100):
        refund_summary_validator(_request(year))


# The bounds keep an absurd value from reaching the repository, and from building
# an invalid datetime in the controller.
def test_a_year_outside_the_range_raises():
    for year in (1999, 2101, 0, -5):
        with pytest.raises(HttpUnprocessableEntityError) as error:
            refund_summary_validator(_request(year))
        assert "between 2000 and 2100" in str(error.value)


# An absent value means the client never named a year, and the controller uses the
# current one — refusing it would reject a request that asked for the default.
def test_an_absent_year_passes():
    refund_summary_validator(HttpRequest(query={}))
    refund_summary_validator(_request(None))
