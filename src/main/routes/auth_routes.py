from fastapi import APIRouter
from fastapi.responses import JSONResponse
from src.views.http_types.http_request import HttpRequest
from src.main.composer.user_register_composer import user_register_composer
from src.main.composer.user_login_composer import user_login_composer
from src.validators.user_register_validator import UserRegisterValidator
from src.validators.user_login_validator import UserLoginValidator

auth_routes = APIRouter(prefix="/auth", tags=["Auth"])


@auth_routes.post("/register")
async def register_user(body: UserRegisterValidator):
    http_request = HttpRequest(body=dict(body))
    view = user_register_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)


@auth_routes.post("/login")
async def login_user(body: UserLoginValidator):
    http_request = HttpRequest(body=dict(body))
    view = user_login_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)
