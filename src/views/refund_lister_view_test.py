# pylint: disable=w0621
from unittest.mock import MagicMock, AsyncMock
import pytest
from fastapi import HTTPException
from src.views.http_types.http_request import HttpRequest
from .refund_lister_view import RefundListerView


@pytest.fixture
def mock_controller():
    controller = MagicMock()
    controller.list = AsyncMock(
        return_value={"type": "Refund", "count": 0, "total": 0, "page": 1, "per_page": 10, "total_pages": 0, "attributes": []}
    )
    return controller


# Happy path: query params + token info are correctly unpacked and forwarded to the controller.
@pytest.mark.asyncio
async def test_refund_lister_view_forwards_query_and_token_info_to_the_controller(mock_controller):
    http_request = HttpRequest(
        query={"page": 2, "per_page": 20, "name": "Ana"},
        token_info={"user_id": 7, "role": "standard"},
    )
    view = RefundListerView(mock_controller)

    response = await view.handle(http_request)

    assert response.status_code == 200
    mock_controller.list.assert_awaited_once_with(
        page=2, per_page=20, name="Ana", user_id=7, role="standard",
        status=None, sort=None, order=None, filter_user_id=None
    )


# When "name" is absent from the query dict, the view must pass None, not raise a KeyError.
@pytest.mark.asyncio
async def test_refund_lister_view_defaults_name_to_none_when_absent(mock_controller):
    http_request = HttpRequest(
        query={"page": 1, "per_page": 10},
        token_info={"user_id": 7, "role": "admin"},
    )
    view = RefundListerView(mock_controller)

    await view.handle(http_request)

    mock_controller.list.assert_awaited_once_with(
        page=1, per_page=10, name=None, user_id=7, role="admin",
        status=None, sort=None, order=None, filter_user_id=None
    )


# The three new query parameters (status, sort, order) must reach the controller as kwargs.
@pytest.mark.asyncio
async def test_the_new_query_parameters_reach_the_controller(mock_controller):
    view = RefundListerView(mock_controller)
    http_request = HttpRequest(
        query={"page": 1, "per_page": 10, "name": None,
               "status": "pending", "sort": "name", "order": "asc"},
        token_info={"user_id": 7, "role": "admin"},
    )

    await view.handle(http_request)

    assert mock_controller.list.await_args.kwargs["status"] == "pending"
    assert mock_controller.list.await_args.kwargs["sort"] == "name"
    assert mock_controller.list.await_args.kwargs["order"] == "asc"


# The "user_id" query param (Task 10) must reach the controller as filter_user_id,
# the name the controller's authorization rule expects.
@pytest.mark.asyncio
async def test_the_user_id_query_parameter_reaches_the_controller_as_filter_user_id(mock_controller):
    view = RefundListerView(mock_controller)
    http_request = HttpRequest(
        query={"page": 1, "per_page": 10, "name": None,
               "status": None, "sort": None, "order": None, "user_id": 3},
        token_info={"user_id": 7, "role": "admin"},
    )

    await view.handle(http_request)

    assert mock_controller.list.await_args.kwargs["filter_user_id"] == 3


# The validator runs before the controller: an invalid sort must be refused with
# 422 and never reach the query.
@pytest.mark.asyncio
async def test_invalid_sort_short_circuits_before_the_controller(mock_controller):
    view = RefundListerView(mock_controller)
    http_request = HttpRequest(
        query={"page": 1, "per_page": 10, "name": None,
               "status": None, "sort": "password", "order": None},
        token_info={"user_id": 7, "role": "admin"},
    )

    with pytest.raises(HTTPException) as exception_info:
        await view.handle(http_request)

    assert exception_info.value.status_code == 422
    mock_controller.list.assert_not_awaited()
