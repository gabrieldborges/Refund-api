"""One log line per request: method, route, status, duration.

Separate from RequestIdMiddleware on purpose — that one owns the id, this one
owns the record. Ordering matters and is asserted by the server module: the id
middleware must run FIRST, or this line would be written before an id exists.
"""
import logging
import time
from urllib.parse import parse_qsl, urlencode
from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger("api.access")

# Query parameters whose VALUE must never reach a log.
#
# `token` is not hypothetical. Item 22 serves files through signed URLs like
# /files/receipts/a3f2.png?token=eyJhbGciOi... — a working capability for as
# long as it lives. A log that records the raw query string is a credential
# leak with a timestamp on it, and the log usually outlives the token's five
# minutes by years.
SENSITIVE_QUERY_PARAMS = {"token", "password", "secret"}

MASK = "***"


def mask_query(query: str) -> str:
    """Replace sensitive values, keeping the parameter names visible.

    Names are kept because "a token was present" is useful when reading a log;
    the value is what must not be.
    """
    if not query:
        return ""

    # keep_blank_values so `?token=` does not silently disappear from the line.
    pairs = parse_qsl(query, keep_blank_values=True)
    # safe="*" so the mask reads as token=*** and not token=%2A%2A%2A. Noticed
    # by looking at the real output, not by reading the code.
    return urlencode(
        [(key, MASK if key.lower() in SENSITIVE_QUERY_PARAMS else value) for key, value in pairs],
        safe="*",
    )


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # An unhandled exception must still produce an access line, or the
            # requests that matter most are the ones missing from the log.
            # status 500 is what the client will receive from the handler
            # registered in server.py.
            self.__log(request, 500, started)
            raise

        self.__log(request, response.status_code, started)
        return response

    def __log(self, request, status: int, started: float) -> None:
        duration_ms = round((time.perf_counter() - started) * 1000, 1)

        # NEITHER THE BODY NOR THE HEADERS ARE LOGGED, anywhere. That is what
        # keeps passwords and the Authorization bearer out — masking only has
        # to cover the query string because the query string is the only
        # request content that gets recorded at all.
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query": mask_query(request.url.query),
                "status": status,
                "duration_ms": duration_ms,
            },
        )
