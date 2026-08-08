"""RFC 9457 error envelope.

Every error this API returns has the same shape, served as
application/problem+json:

    {"type", "title", "status", "detail", "instance", "request_id"}

Before this there were two shapes — a string `detail` for our business errors
and a list of objects for FastAPI's own validation failures — and the frontend
carried a function whose only job was to tell them apart.

WHY `detail` STAYS A STRING. It is a string in the RFC too, which is what makes
this migration have no broken moment: a client reading `.detail` keeps working,
including for validation errors that used to arrive as a list. Field-level
information moves to the `errors` extension instead of overloading `detail`.

WHY `type` IS about:blank FOR NOW. The RFC uses that value to mean "no
machine-readable code beyond the status". Inventing nineteen codes with no
consumer asking for one would be abstraction ahead of need; the field exists
and a specific code can be filled in the day a client actually branches on it.
"""
from http import HTTPStatus
from typing import Optional
from fastapi.responses import JSONResponse
from src.main.middlewares.request_id import REQUEST_ID_HEADER


# The RFC's own value for "there is no more specific type than the status".
DEFAULT_TYPE = "about:blank"

MEDIA_TYPE = "application/problem+json"


def problem_response(
    status: int,
    detail: str,
    instance: str,
    request_id: str,
    errors: Optional[list] = None,
) -> JSONResponse:
    """Build the response. `errors` is the RFC extension for per-field detail."""
    try:
        title = HTTPStatus(status).phrase
    except ValueError:
        # A status outside the registry should not turn an error response into
        # a second, different error.
        title = "Error"

    body = {
        "type": DEFAULT_TYPE,
        "title": title,
        "status": status,
        "detail": detail,
        "instance": instance,
        # An extension, not part of the RFC's core fields. It is what makes a
        # 500 reportable: without it a user says "it broke" and nothing ties
        # that to a log line. Item 24 will reuse this same id in the logs
        # rather than minting its own.
        "request_id": request_id,
    }
    if errors:
        body["errors"] = errors

    # The header is set HERE rather than left to RequestIdMiddleware, and the
    # reason was measured: on a 500 the exception travels up PAST that
    # middleware before Starlette's outermost layer invokes the handler, so
    # `call_next` never returns and the header never gets added. The body had
    # the id and the header did not — on exactly the response where someone
    # would most want to copy it. Setting it on the response itself makes it
    # independent of middleware ordering.
    return JSONResponse(
        status_code=status,
        content=body,
        media_type=MEDIA_TYPE,
        headers={REQUEST_ID_HEADER: request_id},
    )
