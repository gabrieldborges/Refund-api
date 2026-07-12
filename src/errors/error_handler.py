from fastapi import HTTPException
from src.errors.types.http_bad_request_error import HttpBadRequestError
from src.errors.types.http_not_found_error import HttpNotFoundError
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.errors.types.http_unauthorized_error import HttpUnauthorizedError


def error_handler(error: Exception) -> HTTPException:
    if isinstance(error, (
        HttpBadRequestError, HttpNotFoundError, HttpUnprocessableEntityError, HttpUnauthorizedError
    )):
        raise HTTPException(
            status_code=error.status_code,
            detail=error.message
        )
    raise HTTPException(
        status_code=500,
        detail="Internal server error"
    )
