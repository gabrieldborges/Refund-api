import pytest
from fastapi import HTTPException
from src.errors.types.http_bad_request_error import HttpBadRequestError
from src.errors.types.http_forbidden_error import HttpForbiddenError
from src.errors.types.http_not_found_error import HttpNotFoundError
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from .error_handler import error_handler


# FOUND BY COVERAGE (Item 26). error_handler.py reported 82% with its line 17 —
# the unexpected-error path — never executed by any of 317 tests. It is the
# branch every view falls through to when something nobody predicted happens,
# and it had no test at all.
def test_an_unknown_error_becomes_a_generic_500():
    with pytest.raises(HTTPException) as raised:
        error_handler(RuntimeError("connection to db-prod-3 refused"))

    assert raised.value.status_code == 500
    assert raised.value.detail == "Internal server error"


# The message must stay generic. A driver exception carried through to the
# client would leak infrastructure detail — the same rule the 500 handler in
# server.py follows one layer up.
def test_the_original_message_is_not_leaked():
    with pytest.raises(HTTPException) as raised:
        error_handler(RuntimeError("host db-prod-3 port 5432"))

    assert "db-prod-3" not in str(raised.value.detail)


@pytest.mark.parametrize(
    "error,status",
    [
        (HttpBadRequestError("bad"), 400),
        (HttpForbiddenError("nope"), 403),
        (HttpNotFoundError("gone"), 404),
        (HttpUnprocessableEntityError("no"), 422),
    ],
)
def test_our_own_errors_keep_their_status_and_message(error, status):
    with pytest.raises(HTTPException) as raised:
        error_handler(error)

    assert raised.value.status_code == status
    assert raised.value.detail == error.message
