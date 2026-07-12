from fastapi import APIRouter, Depends, Form, UploadFile, File
from fastapi.responses import JSONResponse
from src.views.http_types.http_request import HttpRequest
from src.main.composer.refund_creator_composer import refund_creator_composer
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
