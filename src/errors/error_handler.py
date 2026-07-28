from fastapi import HTTPException
from src.errors.types.http_bad_request_error import HttpBadRequestError
from src.errors.types.http_forbidden_error import HttpForbiddenError
from src.errors.types.http_not_found_error import HttpNotFoundError
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError


def error_handler(error: Exception) -> HTTPException:
    if isinstance(
        error,
        (HttpBadRequestError, HttpForbiddenError, HttpNotFoundError, HttpUnprocessableEntityError),
    ):
        raise HTTPException(
            status_code=error.status_code,
            detail=error.message
        )
    raise HTTPException(
        status_code=500,
        detail="Internal server error"
    )
