# pylint: disable=duplicate-code
# The binary Response block below mirrors get_refund_receipt in
# refund_routes.py; a shared helper would be more machinery than two lines
# of route glue are worth.
from fastapi import APIRouter, Depends, UploadFile, File, Response
from fastapi.responses import JSONResponse
from src.views.http_types.http_request import HttpRequest
from src.main.composer.avatar_uploader_composer import avatar_uploader_composer
from src.main.composer.avatar_remover_composer import avatar_remover_composer
from src.main.composer.avatar_finder_composer import avatar_finder_composer
from src.main.composer.refund_stats_finder_composer import refund_stats_finder_composer
from src.main.middlewares.auth_jwt import get_current_user

user_routes = APIRouter(prefix="/users", tags=["Users"])


@user_routes.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    token_info: dict = Depends(get_current_user),
):
    content = await file.read()
    http_request = HttpRequest(
        body={"filename": file.filename, "content": content},
        token_info=token_info,
    )
    view = avatar_uploader_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)


@user_routes.delete("/me/avatar")
async def remove_avatar(token_info: dict = Depends(get_current_user)):
    http_request = HttpRequest(token_info=token_info)
    view = avatar_remover_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)


@user_routes.get("/{user_id}/avatar", response_class=Response)
async def get_user_avatar(
    user_id: int,
    token_info: dict = Depends(get_current_user),  # pylint: disable=unused-argument
):
    # token_info is unused here on purpose: get_current_user's only job in this
    # route is to require authentication, not to authorize by identity.
    http_request = HttpRequest(path_params={"user_id": user_id})
    view = avatar_finder_composer()
    response = await view.handle(http_request)
    return Response(
        content=response.body["content"],
        media_type=response.body["media_type"],
        status_code=response.status_code,
    )


@user_routes.get("/{user_id}/refund-stats")
async def get_refund_stats(user_id: int, token_info: dict = Depends(get_current_user)):
    http_request = HttpRequest(path_params={"user_id": user_id}, token_info=token_info)
    view = refund_stats_finder_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)
