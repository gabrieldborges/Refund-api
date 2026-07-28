import pytest
from fastapi import HTTPException
from src.errors.types.http_forbidden_error import HttpForbiddenError
from .error_handler import error_handler


# A forbidden error must surface as HTTP 403 with its own message, not collapse
# into the generic 500 that error_handler applies to unknown exceptions.
def test_forbidden_error_becomes_a_403_response():
    with pytest.raises(HTTPException) as exception_info:
        error_handler(HttpForbiddenError("Only administrators can review refunds"))

    assert exception_info.value.status_code == 403
    assert exception_info.value.detail == "Only administrators can review refunds"
