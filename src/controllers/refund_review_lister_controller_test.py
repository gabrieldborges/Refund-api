# pylint: disable=w0621
# Also disables duplicate-code: review_rows below repeats the same review dict
# shape as the row._mapping fixture in refund_reviews_repository_test.py — one
# is the controller-level view of a review, the other the raw repository row
# it's built from. They coincide because the fields really are identical, not
# because the tests should share a fixture across unrelated layers.
# pylint: disable=duplicate-code
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.errors.types.http_not_found_error import HttpNotFoundError
from .refund_review_lister_controller import RefundReviewListerController


def build_controller(refund, reviews):
    refunds_repository = MagicMock()
    refunds_repository.select_refund_by_id = AsyncMock(return_value=refund)
    reviews_repository = MagicMock()
    reviews_repository.select_by_refund_id = AsyncMock(return_value=reviews)
    return RefundReviewListerController(refunds_repository, reviews_repository)


@pytest.fixture
def refund():
    return {"id": 1, "status": "rejected", "user": {"id": 7, "name": "Ana", "avatar_filename": None}}


@pytest.fixture
def review_rows():
    return [
        {
            "from_status": "pending",
            "to_status": "approved",
            "reason": None,
            "created_at": datetime(2026, 7, 30, 10, 0, 0),
            "reviewer_id": 1,
            "reviewer_name": "Gabriel",
        }
    ]


# Closing the loop this cycle exists for: the requester reads why their refund
# was rejected, and who decided.
@pytest.mark.asyncio
async def test_owner_reads_their_own_history(refund, review_rows):
    controller = build_controller(refund, review_rows)

    response = await controller.list(refund_id=1, user_id=7, role="standard")

    assert response["count"] == 1
    assert response["attributes"][0]["reviewer"] == {"id": 1, "name": "Gabriel"}
    assert response["attributes"][0]["created_at"] == "2026-07-30T10:00:00"


@pytest.mark.asyncio
async def test_admin_reads_someone_elses_history(refund, review_rows):
    controller = build_controller(refund, review_rows)

    response = await controller.list(refund_id=1, user_id=99, role="admin")

    assert response["count"] == 1


# A refund nobody has decided yet is not an error: it has an empty history.
@pytest.mark.asyncio
async def test_a_never_decided_refund_has_an_empty_history(refund):
    controller = build_controller({**refund, "status": "pending"}, [])

    response = await controller.list(refund_id=1, user_id=7, role="standard")

    assert response["count"] == 0
    assert response["attributes"] == []


@pytest.mark.asyncio
async def test_someone_elses_refund_is_not_found(refund, review_rows):
    controller = build_controller(refund, review_rows)

    with pytest.raises(HttpNotFoundError, match="Refund not found"):
        await controller.list(refund_id=1, user_id=99, role="standard")


@pytest.mark.asyncio
async def test_unknown_refund_is_not_found():
    controller = build_controller(None, [])

    with pytest.raises(HttpNotFoundError, match="Refund not found"):
        await controller.list(refund_id=1, user_id=7, role="standard")
