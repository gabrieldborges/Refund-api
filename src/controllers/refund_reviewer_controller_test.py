# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.errors.types.http_forbidden_error import HttpForbiddenError
from src.errors.types.http_not_found_error import HttpNotFoundError
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from .refund_reviewer_controller import RefundReviewerController


def build_unit_of_work(refund=None, insert_review=None):
    """Builds a UnitOfWork test double usable as `async with`."""
    unit_of_work = MagicMock()
    unit_of_work.refunds = MagicMock()
    unit_of_work.refunds.select_for_update = AsyncMock(return_value=refund)
    unit_of_work.refunds.update_status = AsyncMock()
    unit_of_work.reviews = MagicMock()
    unit_of_work.reviews.insert_review = insert_review or AsyncMock()
    unit_of_work.commit = AsyncMock()
    unit_of_work.__aenter__ = AsyncMock(return_value=unit_of_work)
    unit_of_work.__aexit__ = AsyncMock(return_value=None)
    return unit_of_work


@pytest.fixture
def pending_refund():
    return {"id": 1, "user_id": 7, "status": "pending", "name": "Almoço", "filename": "a.jpg"}


@pytest.mark.asyncio
async def test_admin_approves_a_pending_refund(pending_refund):
    unit_of_work = build_unit_of_work(refund=pending_refund)
    controller = RefundReviewerController(unit_of_work)

    response = await controller.review(
        refund_id=1, reviewer_id=9, role="admin", status="approved", reason=None
    )

    unit_of_work.refunds.update_status.assert_awaited_once_with(1, "approved")
    unit_of_work.reviews.insert_review.assert_awaited_once_with(
        refund_id=1, reviewer_id=9, from_status="pending", to_status="approved", reason=None
    )
    unit_of_work.commit.assert_awaited_once()
    assert response["attributes"]["status"] == "approved"


# BR-017: an admin may change their mind, and the history records where it came from.
@pytest.mark.asyncio
async def test_an_approved_refund_can_be_rejected_afterwards():
    unit_of_work = build_unit_of_work(refund={"id": 1, "user_id": 7, "status": "approved"})
    controller = RefundReviewerController(unit_of_work)

    await controller.review(
        refund_id=1, reviewer_id=9, role="admin", status="rejected", reason="Duplicado"
    )

    unit_of_work.reviews.insert_review.assert_awaited_once_with(
        refund_id=1, reviewer_id=9, from_status="approved", to_status="rejected", reason="Duplicado"
    )


# The role check runs BEFORE touching the database on purpose: a check that never
# queries cannot leak whether the id exists, so a standard user gets the same 403
# for a real id and for a made-up one (same reasoning as BR-013's 404).
@pytest.mark.asyncio
async def test_standard_user_is_forbidden_and_the_database_is_never_touched(pending_refund):
    unit_of_work = build_unit_of_work(refund=pending_refund)
    controller = RefundReviewerController(unit_of_work)

    with pytest.raises(HttpForbiddenError):
        await controller.review(
            refund_id=1, reviewer_id=7, role="standard", status="approved", reason=None
        )

    unit_of_work.refunds.select_for_update.assert_not_awaited()
    unit_of_work.__aenter__.assert_not_awaited()


# BR-016: whoever spends does not approve their own spending.
@pytest.mark.asyncio
async def test_admin_cannot_review_their_own_refund(pending_refund):
    unit_of_work = build_unit_of_work(refund=pending_refund)
    controller = RefundReviewerController(unit_of_work)

    with pytest.raises(HttpForbiddenError):
        await controller.review(
            refund_id=1, reviewer_id=7, role="admin", status="approved", reason=None
        )

    unit_of_work.refunds.update_status.assert_not_awaited()
    unit_of_work.reviews.insert_review.assert_not_awaited()
    unit_of_work.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_refund_raises_not_found():
    unit_of_work = build_unit_of_work(refund=None)
    controller = RefundReviewerController(unit_of_work)

    with pytest.raises(HttpNotFoundError):
        await controller.review(
            refund_id=999, reviewer_id=9, role="admin", status="approved", reason=None
        )

    unit_of_work.commit.assert_not_awaited()


# Repeating the current decision is not a state change, and writing
# "approved -> approved" would pollute the audit trail with an event that never
# happened.
@pytest.mark.asyncio
async def test_repeating_the_current_decision_raises():
    unit_of_work = build_unit_of_work(refund={"id": 1, "user_id": 7, "status": "approved"})
    controller = RefundReviewerController(unit_of_work)

    with pytest.raises(HttpUnprocessableEntityError):
        await controller.review(
            refund_id=1, reviewer_id=9, role="admin", status="approved", reason=None
        )

    unit_of_work.reviews.insert_review.assert_not_awaited()
    unit_of_work.refunds.update_status.assert_not_awaited()


# BR-017 (amended): "paid" is terminal because the money already moved — no
# review may revert it, even to a different target than the current status.
@pytest.mark.asyncio
async def test_a_paid_refund_cannot_be_reverted_to_approved():
    unit_of_work = build_unit_of_work(refund={"id": 1, "user_id": 7, "status": "paid"})
    controller = RefundReviewerController(unit_of_work)

    with pytest.raises(HttpUnprocessableEntityError):
        await controller.review(
            refund_id=1, reviewer_id=9, role="admin", status="approved", reason=None
        )

    unit_of_work.refunds.update_status.assert_not_awaited()
    unit_of_work.reviews.insert_review.assert_not_awaited()
    unit_of_work.commit.assert_not_awaited()


# Same rule, other target: "paid" is terminal regardless of which decision is
# being attempted.
@pytest.mark.asyncio
async def test_a_paid_refund_cannot_be_reverted_to_rejected():
    unit_of_work = build_unit_of_work(refund={"id": 1, "user_id": 7, "status": "paid"})
    controller = RefundReviewerController(unit_of_work)

    with pytest.raises(HttpUnprocessableEntityError):
        await controller.review(
            refund_id=1, reviewer_id=9, role="admin", status="rejected", reason="Duplicado"
        )

    unit_of_work.refunds.update_status.assert_not_awaited()
    unit_of_work.reviews.insert_review.assert_not_awaited()
    unit_of_work.commit.assert_not_awaited()


# THE test of this cycle: if the history insert fails, the status change must not
# survive. Without the UnitOfWork the UPDATE would have committed on its own and
# there would be no way to assert this.
@pytest.mark.asyncio
async def test_the_transaction_is_not_committed_when_the_review_insert_fails(pending_refund):
    failing_insert = AsyncMock(side_effect=RuntimeError("history insert exploded"))
    unit_of_work = build_unit_of_work(refund=pending_refund, insert_review=failing_insert)
    controller = RefundReviewerController(unit_of_work)

    with pytest.raises(RuntimeError):
        await controller.review(
            refund_id=1, reviewer_id=9, role="admin", status="approved", reason=None
        )

    # commit never ran, and __aexit__ received the exception — which is what
    # triggers the rollback proven in unit_of_work_test.py.
    unit_of_work.commit.assert_not_awaited()
    assert unit_of_work.__aexit__.await_args[0][0] is RuntimeError


# I1: payment_filename joined the refunds table this cycle, and this
# controller spreads the raw select_for_update row (**refund) instead of
# going through serialize_refund. Without an explicit exclusion, the new
# column would leak into a response UC-007 documents as diverging in exactly
# three points from the shared shape — silently making it four.
@pytest.mark.asyncio
async def test_payment_filename_is_not_exposed_in_the_response(pending_refund):
    refund = {**pending_refund, "payment_filename": None}
    unit_of_work = build_unit_of_work(refund=refund)
    controller = RefundReviewerController(unit_of_work)

    response = await controller.review(
        refund_id=1, reviewer_id=9, role="admin", status="approved", reason=None
    )

    assert "payment_filename" not in response["attributes"]
