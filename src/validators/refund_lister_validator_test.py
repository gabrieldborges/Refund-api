import pytest
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest
from .refund_lister_validator import refund_lister_validator


def query(**overrides) -> dict:
    base = {"page": 1, "per_page": 10, "name": None, "status": None, "sort": None, "order": None}
    base.update(overrides)
    return base


# All three are optional: leaving them out keeps today's behaviour.
def test_no_optional_parameter_is_valid():
    refund_lister_validator(HttpRequest(query=query()))


@pytest.mark.parametrize("status", ["pending", "approved", "rejected", "paid"])
def test_every_allowed_status_is_valid(status):
    refund_lister_validator(HttpRequest(query=query(status=status)))


@pytest.mark.parametrize("sort", ["created_at", "amount_in_cents", "name", "status"])
def test_every_sortable_field_is_valid(sort):
    refund_lister_validator(HttpRequest(query=query(sort=sort)))


@pytest.mark.parametrize("order", ["asc", "desc"])
def test_both_orders_are_valid(order):
    refund_lister_validator(HttpRequest(query=query(order=order)))


def test_unknown_status_raises():
    with pytest.raises(HttpUnprocessableEntityError):
        refund_lister_validator(HttpRequest(query=query(status="whatever")))


# The sort name becomes a lookup key for a real column, so anything outside the
# whitelist must be refused at the boundary.
def test_unknown_sort_field_raises():
    with pytest.raises(HttpUnprocessableEntityError):
        refund_lister_validator(HttpRequest(query=query(sort="password")))


def test_sql_looking_sort_value_raises():
    with pytest.raises(HttpUnprocessableEntityError):
        refund_lister_validator(HttpRequest(query=query(sort="id; DROP TABLE refunds")))


def test_unknown_order_raises():
    with pytest.raises(HttpUnprocessableEntityError):
        refund_lister_validator(HttpRequest(query=query(order="sideways")))
