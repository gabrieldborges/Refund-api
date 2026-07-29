# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from .refund_creator_controller import RefundCreatorController


# Fake repository: insert_refund just returns id 1, no database involved.
@pytest.fixture
def mock_repository():
    mock_repo = MagicMock()
    mock_repo.insert_refund = AsyncMock(return_value=1)
    # create() re-reads the written row after insert, so the fixture needs to
    # provide it too (real shape: status from the DB default, nested requester).
    mock_repo.select_refund_by_id = AsyncMock(
        return_value={
            "id": 1, "name": "Ana Silva", "category": "food", "amount_in_cents": 4590,
            "filename": "uuid-generated-name.jpg", "status": "pending", "created_at": None,
            "user": {"id": 7, "name": "Ana Silva", "avatar_filename": None},
        }
    )
    return mock_repo


# Fake storage: save() returns a fixed "already saved" filename, no real disk I/O.
@pytest.fixture
def mock_storage():
    mock_storage_instance = MagicMock()
    mock_storage_instance.save = MagicMock(return_value="uuid-generated-name.jpg")
    return mock_storage_instance


# Happy path: the receipt gets saved, the amount is converted to cents, and the
# refund is persisted tied to the given user_id.
@pytest.mark.asyncio
async def test_create_saves_the_receipt_and_persists_the_refund(mock_repository, mock_storage):
    refund_data = {
        "name": "Ana Silva", "category": "food", "amount": 45.90,
        "filename": "receipt.jpg", "content_type": "image/jpeg", "content": b"bytes",
    }
    controller = RefundCreatorController(mock_repository, mock_storage)

    response = await controller.create(refund_data, user_id=7)

    mock_storage.save.assert_called_once_with("receipt.jpg", b"bytes")
    mock_repository.insert_refund.assert_awaited_once()

    inserted = mock_repository.insert_refund.await_args.args[0]
    assert inserted["user_id"] == 7
    assert inserted["filename"] == "uuid-generated-name.jpg"
    # 45.90 reais -> 4590 cents (see the money-as-cents rule from the Refund entity).
    assert inserted["amount_in_cents"] == 4590

    assert response["type"] == "Refund"
    assert response["attributes"]["id"] == 1


# Security: the refund must always be tied to the authenticated user's id (the
# controller's own user_id parameter), never to anything the client might send in
# the form body — even if a "user_id" key were to sneak into refund_data.
@pytest.mark.asyncio
async def test_create_always_uses_the_authenticated_user_id(mock_repository, mock_storage):
    refund_data = {
        "name": "Ana Silva", "category": "food", "amount": 10,
        "filename": "r.png", "content_type": "image/png", "content": b"x",
        "user_id": 999,
    }
    controller = RefundCreatorController(mock_repository, mock_storage)

    await controller.create(refund_data, user_id=7)

    inserted = mock_repository.insert_refund.await_args.args[0]
    assert inserted["user_id"] == 7


# The create response must match what GET returns, including status and the
# nested user. Building it from the input dict instead would give three
# different shapes for the same resource — and the frontend reuses one schema
# for all three.
@pytest.mark.asyncio
async def test_create_returns_the_row_it_wrote(mock_repository, mock_storage):
    mock_repository.select_refund_by_id = AsyncMock(
        return_value={
            "id": 1, "name": "Almoço", "category": "food", "amount_in_cents": 1000,
            "filename": "a.jpg", "status": "pending", "created_at": None,
            "user": {"id": 7, "name": "Gabriel", "avatar_filename": None},
        }
    )
    controller = RefundCreatorController(mock_repository, mock_storage)

    response = await controller.create(
        {"name": "Almoço", "category": "food", "amount": 10.0, "filename": "a.jpg", "content": b"x"},
        user_id=7,
    )

    mock_repository.select_refund_by_id.assert_awaited_once_with(1)
    assert response["attributes"]["status"] == "pending"
    assert response["attributes"]["user"]["name"] == "Gabriel"


# The create response is the first response a client sees for a refund; the
# stored filename must not leak here either — same contract as list and detail.
@pytest.mark.asyncio
async def test_create_response_hides_filename_and_exposes_has_avatar(mock_repository, mock_storage):
    mock_repository.select_refund_by_id = AsyncMock(
        return_value={
            "id": 1, "name": "Almoço", "category": "food", "amount_in_cents": 1000,
            "filename": "a.jpg", "status": "pending", "created_at": None,
            "user": {"id": 7, "name": "Gabriel", "avatar_filename": "foto.png"},
        }
    )
    controller = RefundCreatorController(mock_repository, mock_storage)

    response = await controller.create(
        {"name": "Almoço", "category": "food", "amount": 10.0, "filename": "a.jpg", "content": b"x"},
        user_id=7,
    )

    assert "filename" not in response["attributes"]
    assert response["attributes"]["user"]["has_avatar"] is True
    assert "avatar_filename" not in response["attributes"]["user"]
