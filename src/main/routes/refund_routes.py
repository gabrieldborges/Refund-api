from typing import Optional
from fastapi import APIRouter, Depends, Form, UploadFile, File, Query
from fastapi.responses import JSONResponse
from src.views.http_types.http_request import HttpRequest
from src.main.composer.refund_creator_composer import refund_creator_composer
from src.main.composer.refund_lister_composer import refund_lister_composer
from src.main.composer.refund_finder_composer import refund_finder_composer
from src.main.composer.refund_deleter_composer import refund_deleter_composer
from src.main.middlewares.auth_jwt import get_current_user

refund_routes = APIRouter(prefix="/refunds", tags=["Refunds"])


@refund_routes.post("")
async def create_refund(
    name: str = Form(...),
    amount: float = Form(...),
    category: str = Form(...),
    file: UploadFile = File(...),
    token_info: dict = Depends(get_current_user),
):
    content = await file.read()
    http_request = HttpRequest(
        body={
            "name": name,
            "amount": amount,
            "category": category,
            "filename": file.filename,
            "content_type": file.content_type,
            "content": content,
        },
        token_info=token_info,
    )
    view = refund_creator_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)


@refund_routes.get("")
async def list_refunds(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    name: Optional[str] = Query(None),
    token_info: dict = Depends(get_current_user),
):
    http_request = HttpRequest(
        query={"page": page, "per_page": per_page, "name": name},
        token_info=token_info,
    )
    view = refund_lister_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)


@refund_routes.get("/{refund_id}")
async def get_refund(refund_id: int, token_info: dict = Depends(get_current_user)):
    http_request = HttpRequest(path_params={"refund_id": refund_id}, token_info=token_info)
    view = refund_finder_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)


@refund_routes.delete("/{refund_id}")
async def delete_refund(refund_id: int, token_info: dict = Depends(get_current_user)):
    http_request = HttpRequest(path_params={"refund_id": refund_id}, token_info=token_info)
    view = refund_deleter_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)
