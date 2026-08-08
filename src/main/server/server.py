from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from src.configs.settings import settings
from src.errors.problem_details import problem_response
from src.models.entities import users, refunds, refund_reviews  # pylint: disable=unused-import
from src.main.middlewares.request_id import RequestIdMiddleware, request_id_of
from src.main.routes.auth_routes import auth_routes
from src.main.routes.refund_routes import refund_routes
from src.main.routes.user_routes import user_routes
from src.main.routes.file_routes import file_routes


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # The schema is owned by Alembic migrations (`alembic upgrade head`), not by
    # the application boot. Keeping metadata.create_all here would silently mask
    # a migration that was never applied: it creates missing tables and ignores
    # missing columns, so the app would start against a half-updated schema.
    yield


app = FastAPI(lifespan=lifespan)

# Was hardcoded to http://localhost:5173, which meant no deployed frontend
# could ever reach this API. Settings validates the value and refuses a
# wildcard or a localhost origin when ENVIRONMENT=production, so the insecure
# configuration is impossible rather than merely discouraged.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Uploaded files are NOT served statically: the UUID filenames would be
# capability URLs, granting anyone who ever saw a link permanent access even
# after losing access to the refund. They go through authenticated routes
# instead (GET /refunds/{id}/receipt and GET /users/{id}/avatar).

app.add_middleware(RequestIdMiddleware)


# Three handlers, one envelope (RFC 9457). Registering them here rather than
# changing the 38 places that raise is the point: error_handler and every
# controller keep raising exactly what they raised before, and the FORMAT is
# decided in one place.
# Registered on STARLETTE's HTTPException, not FastAPI's. FastAPI's subclasses
# it, so this covers both — while the reverse does not: the router raises the
# Starlette one for an unknown path, and registering the subclass let those
# 404s escape with the old {"detail": ...} shape. Found by asking the running
# API for a route that does not exist, not by reading the code.
@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(request: Request, exc: StarletteHTTPException):
    # exc.detail is a string everywhere in this project. str() is a guard, not
    # a conversion anyone should rely on: it keeps a stray non-string from
    # producing a body that contradicts the contract.
    return problem_response(
        status=exc.status_code,
        detail=str(exc.detail),
        instance=request.url.path,
        request_id=request_id_of(request),
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    # This is the shape that used to arrive as a LIST under `detail` and forced
    # the frontend to branch. Now `detail` is a sentence like every other error
    # and the per-field information lives in the `errors` extension, where a
    # form can actually use it.
    errors = [
        {
            # loc is ("body", "amount") — the last element is the field. The
            # first is the location kind, which a client does not need.
            "field": ".".join(str(part) for part in error["loc"][1:]) or str(error["loc"][0]),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    detail = errors[0]["message"] if errors else "Validation failed"

    return problem_response(
        status=422,
        detail=detail,
        instance=request.url.path,
        request_id=request_id_of(request),
        errors=errors,
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):  # pylint: disable=unused-argument
    # The message stays deliberately generic — an unexpected failure must not
    # leak a stack trace or a database message to the client. The request_id is
    # what makes it actionable: the user can quote it and it will match a log
    # line once Item 24 lands.
    return problem_response(
        status=500,
        detail="Internal server error",
        instance=request.url.path,
        request_id=request_id_of(request),
    )


app.include_router(auth_routes)
app.include_router(refund_routes)
app.include_router(user_routes)
# Only used by the local storage backend; with S3 the browser never comes here.
app.include_router(file_routes)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
