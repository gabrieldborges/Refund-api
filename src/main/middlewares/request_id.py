"""Gives every request an id, for correlating an error with a log line.

The id is put on request.state (where the exception handlers read it) and
echoed in the X-Request-Id response header — the header as well as the body
because a client can read it even when the response is not JSON, and because
that is where tooling looks for it.

The id is GENERATED HERE, never taken from an incoming header. Trusting a
client-supplied value would let anyone choose what appears in our logs, which
is how log forging works. Item 24 can revisit that if real cross-service
correlation ever needs it — with validation, not by trusting the header.
"""
import uuid
from starlette.middleware.base import BaseHTTPMiddleware


REQUEST_ID_HEADER = "X-Request-Id"


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


def request_id_of(request) -> str:
    """Read the id a request was given.

    Falls back to a literal rather than raising: an error response missing its
    correlation id is a small loss, and an exception handler that itself
    crashes is a large one.
    """
    return getattr(request.state, "request_id", "unknown")
