from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from src.configs.settings import settings
from src.errors.problem_details import problem_response
from src.main.middlewares.rate_limit import client_identity, rate_limiter
from src.main.middlewares.request_id import request_id_of
from src.views.http_types.http_request import HttpRequest
from src.main.composer.user_register_composer import user_register_composer
from src.main.composer.user_login_composer import user_login_composer
from src.validators.user_register_validator import UserRegisterValidator
from src.validators.user_login_validator import UserLoginValidator

auth_routes = APIRouter(prefix="/auth", tags=["Auth"])


def too_many_attempts(request: Request):
    """The 429, built once so both endpoints answer identically.

    Returns a problem document like every other error (ADR-005), including the
    Retry-After header, which is the one thing a client can act on.
    """
    return problem_response(
        status=429,
        detail="Too many attempts. Try again later.",
        instance=request.url.path,
        request_id=request_id_of(request),
    )


# Rate limited because it answers "Email already registered" — useful to a
# person, and exactly what /login refuses to reveal. Keeping the message and
# capping the rate was the decision (ADR-009): enumerating ten emails stays
# possible, ten thousand does not.
@auth_routes.post("/register")
async def register_user(body: UserRegisterValidator, request: Request):
    if not rate_limiter.allow(
        "register",
        client_identity(request),
        settings.register_rate_limit,
        settings.rate_limit_window_seconds,
    ):
        return too_many_attempts(request)

    http_request = HttpRequest(body=dict(body))
    view = user_register_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)


# The classic target, and doubly so here: bcrypt makes every attempt expensive
# for the SERVER, so an unlimited login is a CPU exhaustion vector as well as a
# credential one.
#
# Counted per client address, NOT per email. Limiting by email would let anyone
# lock a known victim out of their own account by burning the allowance on
# purpose — trading a brute-force risk for a denial-of-service one.
@auth_routes.post("/login")
async def login_user(body: UserLoginValidator, request: Request):
    if not rate_limiter.allow(
        "login",
        client_identity(request),
        settings.login_rate_limit,
        settings.rate_limit_window_seconds,
    ):
        return too_many_attempts(request)

    http_request = HttpRequest(body=dict(body))
    view = user_login_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)
