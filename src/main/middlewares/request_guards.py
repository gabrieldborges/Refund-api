"""Two edge guards: a size ceiling on request bodies, and response headers.

THE SIZE THREAT, from the model done before writing this. Every upload route
does `content = await file.read()` and the validators then check
`len(content) > max_file_size_bytes`. The 4MB limit is real — but it is
enforced AFTER the whole body is already in memory. A 2GB POST was buffered
before being refused, and since registration is open, anyone could get an
account and reach those routes.

This middleware refuses on Content-Length, before the route ever reads.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from src.configs.settings import settings
from src.errors.problem_details import problem_response
from src.main.middlewares.request_id import request_id_of


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        declared = request.headers.get("content-length")

        # KNOWN LIMIT, stated rather than left to be discovered: this reads the
        # DECLARED size. A chunked request sends no Content-Length and passes
        # through here, and the validators' own 4MB check is what catches it —
        # after buffering, which is the very thing this exists to prevent.
        # Closing that would mean wrapping the ASGI receive stream and counting
        # bytes as they arrive; worth doing the day something other than a
        # browser or curl posts here.
        if declared and int(declared) > settings.max_request_body_bytes:
            return problem_response(
                status=413,
                detail="Request body is too large",
                instance=request.url.path,
                request_id=request_id_of(request),
            )

        return await call_next(request)


# The one path whose whole purpose is to be embedded by our own page.
FILES_PREFIX = "/files/"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # nosniff: without it a browser may guess a response is HTML from its
        # bytes and run it. This API serves uploaded files, so a stored .png
        # that is really markup is precisely the case.
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        # Keeps a signed file URL — which carries a token in its query string —
        # out of the Referer header when a browser follows a link away.
        response.headers.setdefault("Referrer-Policy", "no-referrer")

        # FRAMING IS DECIDED PER PATH, and getting this wrong broke PDF
        # previews. X-Frame-Options: DENY was applied to every response,
        # including /files — and a PDF is rendered by <object>, which is
        # framing. Images kept working because <img> is not, so the bug looked
        # like "PDFs are broken" rather than "a header is too broad".
        #
        # SAMEORIGIN would not fix it: the file comes from the API's port and
        # the page from the frontend's, which are different origins. And with
        # STORAGE_BACKEND=s3 the file never passes through here at all, so the
        # two storage backends would behave differently — worse than the bug.
        #
        # So files get Content-Security-Policy instead, which unlike
        # X-Frame-Options can name WHO may embed: the same origins already
        # trusted to call the API. Everything else keeps the strictest answer,
        # in both the old header and the modern one.
        if request.url.path.startswith(FILES_PREFIX):
            allowed = " ".join(settings.cors_origins)
            response.headers.setdefault(
                "Content-Security-Policy", f"frame-ancestors 'self' {allowed}"
            )
        else:
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault("Content-Security-Policy", "frame-ancestors 'none'")

        return response
