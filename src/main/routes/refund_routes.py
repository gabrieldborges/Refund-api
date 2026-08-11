from typing import Optional
from fastapi import APIRouter, Depends, Form, UploadFile, File, Query, Body
from fastapi.responses import JSONResponse
from src.views.http_types.http_request import HttpRequest
from src.main.composer.refund_creator_composer import refund_creator_composer
from src.main.composer.refund_lister_composer import refund_lister_composer
from src.main.composer.refund_summary_composer import refund_summary_composer
from src.main.composer.refund_finder_composer import refund_finder_composer
from src.main.composer.refund_deleter_composer import refund_deleter_composer
from src.main.composer.refund_reviewer_composer import refund_reviewer_composer
from src.main.composer.receipt_finder_composer import receipt_finder_composer
from src.main.composer.refund_payer_composer import refund_payer_composer
from src.main.composer.payment_receipt_finder_composer import payment_receipt_finder_composer
from src.main.composer.refund_review_lister_composer import refund_review_lister_composer
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
    # Kept as free-form str: refund_lister_validator whitelists these values,
    # so an invalid one gets this project's {"detail": "..."} 422 body instead
    # of FastAPI's native enum/regex error envelope.
    status: Optional[str] = Query(None),
    sort: Optional[str] = Query(None),
    order: Optional[str] = Query(None),
    # Typed as int so FastAPI's native validation rejects garbage, matching how
    # page and per_page already behave. Unlike `status`, there is no whitelist
    # to express, so this project's 422 envelope buys nothing here.
    user_id: Optional[int] = Query(None),
    token_info: dict = Depends(get_current_user),
):
    http_request = HttpRequest(
        query={"page": page, "per_page": per_page, "name": name,
               "status": status, "sort": sort, "order": order, "user_id": user_id},
        token_info=token_info,
    )
    view = refund_lister_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)


# DECLARED BEFORE "/{refund_id}", and the order is load-bearing: FastAPI matches
# in declaration order, so with the id route first the path "/refunds/summary"
# would be read as an id, fail int coercion and answer 422 — a defect that passes
# every unit test of the layers below and fails on first use.
@refund_routes.get("/summary")
async def summarize_refunds(
    months: int = Query(6, ge=1, le=12),
    # Typed as int so FastAPI rejects garbage, like the listing's user_id. Only an
    # admin's request is actually narrowed by it: for a standard user the
    # controller ignores it, since they are already locked to themselves.
    user_id: Optional[int] = Query(None),
    token_info: dict = Depends(get_current_user),
):
    http_request = HttpRequest(
        query={"months": months, "user_id": user_id},
        token_info=token_info,
    )
    view = refund_summary_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)


@refund_routes.patch("/{refund_id}/status")
async def review_refund(
    refund_id: int,
    body: dict = Body(...),
    token_info: dict = Depends(get_current_user),
):
    http_request = HttpRequest(
        path_params={"refund_id": refund_id},
        body=body,
        token_info=token_info,
    )
    view = refund_reviewer_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)


@refund_routes.get("/{refund_id}/receipt")
async def get_refund_receipt(
    refund_id: int,
    token_info: dict = Depends(get_current_user),
):
    http_request = HttpRequest(path_params={"refund_id": refund_id}, token_info=token_info)
    view = receipt_finder_composer()
    response = await view.handle(http_request)
    # Item 22: answers a short-lived signed URL, not the bytes. The browser
    # fetches the file directly — from this API's /files route with the local
    # backend, straight from the bucket with S3 — which is what lets an <img>
    # tag work at all, since it cannot send an Authorization header.
    return JSONResponse(content=response.body, status_code=response.status_code)


@refund_routes.post("/{refund_id}/payment")
async def pay_refund(
    refund_id: int,
    file: UploadFile = File(...),
    token_info: dict = Depends(get_current_user),
):
    content = await file.read()
    http_request = HttpRequest(
        path_params={"refund_id": refund_id},
        body={"filename": file.filename, "content": content},
        token_info=token_info,
    )
    view = refund_payer_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)


@refund_routes.get("/{refund_id}/payment-receipt")
async def get_payment_receipt(
    refund_id: int,
    token_info: dict = Depends(get_current_user),
):
    http_request = HttpRequest(path_params={"refund_id": refund_id}, token_info=token_info)
    view = payment_receipt_finder_composer()
    response = await view.handle(http_request)
    return JSONResponse(content=response.body, status_code=response.status_code)


@refund_routes.get("/{refund_id}/reviews")
async def list_refund_reviews(refund_id: int, token_info: dict = Depends(get_current_user)):
    http_request = HttpRequest(path_params={"refund_id": refund_id}, token_info=token_info)
    view = refund_review_lister_composer()
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
