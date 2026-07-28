import pytest
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest
from .refund_reviewer_validator import refund_reviewer_validator


def valid_body(**overrides) -> dict:
    body = {"status": "approved", "reason": None}
    body.update(overrides)
    return body


def test_approving_without_a_reason_is_valid():
    refund_reviewer_validator(HttpRequest(body=valid_body()))


def test_rejecting_with_a_reason_is_valid():
    refund_reviewer_validator(
        HttpRequest(body=valid_body(status="rejected", reason="Comprovante ilegível"))
    )


# "pending" is a legal status of a refund but never a legal TARGET of a review:
# nothing returns to pending (BR-017).
def test_pending_is_not_an_acceptable_target_status():
    with pytest.raises(HttpUnprocessableEntityError):
        refund_reviewer_validator(HttpRequest(body=valid_body(status="pending")))


def test_unknown_status_raises():
    with pytest.raises(HttpUnprocessableEntityError):
        refund_reviewer_validator(HttpRequest(body=valid_body(status="whatever")))


# A rejection without justification is useless to whoever receives it.
def test_rejecting_without_a_reason_raises():
    with pytest.raises(HttpUnprocessableEntityError):
        refund_reviewer_validator(HttpRequest(body=valid_body(status="rejected", reason=None)))


def test_rejecting_with_a_blank_reason_raises():
    with pytest.raises(HttpUnprocessableEntityError):
        refund_reviewer_validator(HttpRequest(body=valid_body(status="rejected", reason="   ")))
