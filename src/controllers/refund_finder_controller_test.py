# pylint: disable=w0621
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.errors.types.http_not_found_error import HttpNotFoundError
from .refund_finder_controller import RefundFinderController


@pytest.fixture
def mock_repository():
    mock_repo = MagicMock()
    mock_repo.select_refund_by_id = AsyncMock(
        return_value={
            "id": 1, "name": "Ana", "category": "food", "amount_in_cents": 1000,
            "status": "pending", "created_at": None,
            "user": {"id": 7, "name": "Ana", "avatar_filename": None},
        }
    )
    return mock_repo


@pytest.mark.asyncio
async def test_owner_can_find_their_own_refund(mock_repository):
    controller = RefundFinderController(mock_repository)

    response = await controller.find(refund_id=1, user_id=7, role="standard")

    assert response["attributes"]["id"] == 1


@pytest.mark.asyncio
async def test_admin_can_find_any_refund(mock_repository):
    controller = RefundFinderController(mock_repository)

    response = await controller.find(refund_id=1, user_id=999, role="admin")

    assert response["attributes"]["id"] == 1


# Security: a standard user trying to reach someone else's refund gets the same
# "not found" error as a truly missing id — the API never confirms the id exists.
@pytest.mark.asyncio
async def test_standard_user_cannot_find_someone_elses_refund(mock_repository):
    controller = RefundFinderController(mock_repository)

    with pytest.raises(HttpNotFoundError):
        await controller.find(refund_id=1, user_id=999, role="standard")


@pytest.mark.asyncio
async def test_missing_refund_raises_not_found():
    mock_repo = MagicMock()
    mock_repo.select_refund_by_id = AsyncMock(return_value=None)
    controller = RefundFinderController(mock_repo)

    with pytest.raises(HttpNotFoundError):
        await controller.find(refund_id=999, user_id=7, role="standard")


# Same datetime-serialization rule as RefundListerController: a raw datetime from the
# database would otherwise break JSON encoding at the HTTP boundary.
@pytest.mark.asyncio
async def test_created_at_is_serialized_to_an_iso_string():
    raw_datetime = datetime(2026, 7, 12, 10, 30, 0)
    mock_repo = MagicMock()
    mock_repo.select_refund_by_id = AsyncMock(
        return_value={
            "id": 1, "name": "Ana", "category": "food", "amount_in_cents": 1000,
            "status": "pending", "created_at": raw_datetime,
            "user": {"id": 7, "name": "Ana", "avatar_filename": None},
        }
    )
    controller = RefundFinderController(mock_repo)

    response = await controller.find(refund_id=1, user_id=7, role="standard")

    assert response["attributes"]["created_at"] == raw_datetime.isoformat()


# The detail response must carry status: it is what lets the frontend tell a
# pending refund from a decided one. It flows through serialize_refund, which
# lists status explicitly — this test is here so a future refactor cannot drop
# it silently.
@pytest.mark.asyncio
async def test_detail_response_includes_the_status(mock_repository):
    mock_repository.select_refund_by_id = AsyncMock(
        return_value={
            "id": 1, "name": "Ana", "category": "food", "amount_in_cents": 1000,
            "status": "approved", "filename": "a.jpg", "created_at": None,
            "user": {"id": 7, "name": "Ana", "avatar_filename": None},
        }
    )
    controller = RefundFinderController(mock_repository)

    response = await controller.find(refund_id=1, user_id=7, role="standard")

    assert response["attributes"]["status"] == "approved"


# The detail response is where the client used to build /receipts/{filename};
# now it fetches the file from GET /refunds/{id}/receipt instead, so the
# storage filename must not leak here, and the avatar becomes a boolean flag.
@pytest.mark.asyncio
async def test_detail_response_hides_filename_and_exposes_has_avatar(mock_repository):
    mock_repository.select_refund_by_id = AsyncMock(
        return_value={
            "id": 1, "name": "Ana", "category": "food", "amount_in_cents": 1000,
            "status": "approved", "filename": "a.jpg", "created_at": None,
            "user": {"id": 7, "name": "Ana", "avatar_filename": "foto.png"},
        }
    )
    controller = RefundFinderController(mock_repository)

    response = await controller.find(refund_id=1, user_id=7, role="standard")

    assert "filename" not in response["attributes"]
    assert response["attributes"]["user"]["has_avatar"] is True
    assert "avatar_filename" not in response["attributes"]["user"]
