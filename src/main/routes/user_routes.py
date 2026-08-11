# pylint: disable=duplicate-code
from typing import Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import JSONResponse
from src.views.http_types.http_request import HttpRequest
from src.main.composer.avatar_uploader_composer import avatar_uploader_composer
from src.main.composer.avatar_remover_composer import avatar_remover_composer
from src.main.composer.avatar_finder_composer import avatar_finder_composer
from src.main.composer.refund_stats_finder_composer import refund_stats_finder_composer
from src.main.composer.user_lister_composer import user_lister_composer
from src.main.composer.user_finder_composer import user_finder_composer
from src.main.middlewares.auth_jwt import get_current_user

user_routes = APIRouter(prefix="/users", tags=["Users"])


@user_routes.get("")
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    name: Optional[str] = Query(None),
    token_info: dict = Depends(get_current_user),
):
    # No sort/order parameters: the order is fixed at name ASC in the repository.
    # That is also why this slice has no validator — there is no whitelist to
    # express, and these bounds are already FastAPI's job.
    http_request = HttpRequest(
        query={"page": page, "per_page": per_page, "name": name},
        token_info=token_info,
    )
    view = user_lister_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)


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


@user_routes.get("/{user_id}/avatar")
async def get_user_avatar(
    user_id: int,
    token_info: dict = Depends(get_current_user),  # pylint: disable=unused-argument
):
    # token_info is unused here on purpose: get_current_user's only job in this
    # route is to require authentication, not to authorize by identity.
    http_request = HttpRequest(path_params={"user_id": user_id})
    view = avatar_finder_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)


@user_routes.get("/{user_id}/refund-stats")
async def get_refund_stats(user_id: int, token_info: dict = Depends(get_current_user)):
    http_request = HttpRequest(path_params={"user_id": user_id}, token_info=token_info)
    view = refund_stats_finder_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)


# Declared AFTER the two /{user_id}/... routes above. FastAPI matches in
# declaration order, and while "/{user_id}" cannot swallow "/{user_id}/avatar"
# (the path segment count differs), keeping the most specific first is the habit
# that stays correct when a future route is genuinely ambiguous. Tests assert the
# two older routes still reach their own composers.
@user_routes.get("/{user_id}")
async def get_user(user_id: int, token_info: dict = Depends(get_current_user)):
    http_request = HttpRequest(path_params={"user_id": user_id}, token_info=token_info)
    view = user_finder_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)
