# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.errors.types.http_forbidden_error import HttpForbiddenError
from src.errors.types.http_not_found_error import HttpNotFoundError
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from .refund_payer_controller import RefundPayerController


def build_unit_of_work(affected=1):
    """Builds a UnitOfWork test double usable as `async with`."""
    unit_of_work = MagicMock()
    unit_of_work.refunds = MagicMock()
    unit_of_work.refunds.mark_as_paid = AsyncMock(return_value=affected)
    unit_of_work.reviews = MagicMock()
    unit_of_work.reviews.insert_review = AsyncMock()
    unit_of_work.commit = AsyncMock()
    unit_of_work.__aenter__ = AsyncMock(return_value=unit_of_work)
    unit_of_work.__aexit__ = AsyncMock(return_value=None)
    return unit_of_work


def build_repository(refund):
    """Repository double whose reads return the nested-user shape."""
    repository = MagicMock()
    repository.select_refund_by_id = AsyncMock(return_value=refund)
    return repository


@pytest.fixture
def approved_refund():
    return {
        "id": 1,
        "name": "Almoço",
        "category": "food",
        "amount_in_cents": 12000,
        "status": "approved",
        "created_at": None,
        "filename": "a.jpg",
        "user": {"id": 7, "name": "Ana", "avatar_filename": None},
    }


@pytest.fixture
def paid_refund(approved_refund):
    return {**approved_refund, "status": "paid"}


@pytest.mark.asyncio
async def test_admin_pays_an_approved_refund(approved_refund, paid_refund):
    unit_of_work = build_unit_of_work()
    repository = build_repository(approved_refund)
    # The re-read after commit must show the new status, so the second call
    # returns the paid row.
    repository.select_refund_by_id = AsyncMock(side_effect=[approved_refund, paid_refund])
    storage = MagicMock()
    storage.save = MagicMock(return_value="stored.pdf")
    controller = RefundPayerController(unit_of_work, repository, storage)

    response = await controller.pay(
        refund_id=1, payer_id=9, role="admin", filename="proof.pdf", content=b"x"
    )

    unit_of_work.refunds.mark_as_paid.assert_awaited_once_with(1, "stored.pdf")
    unit_of_work.reviews.insert_review.assert_awaited_once_with(
        refund_id=1, reviewer_id=9, from_status="approved", to_status="paid", reason=None
    )
    unit_of_work.commit.assert_awaited_once()
    assert response["attributes"]["status"] == "paid"
    # The response uses the shared serializer, so the requester is nested and
    # no filename leaks — unlike the PATCH /status response.
    assert response["attributes"]["user"] == {"id": 7, "name": "Ana", "has_avatar": False}
    assert "filename" not in response["attributes"]
    assert "payment_filename" not in response["attributes"]


# The role check runs BEFORE touching the database on purpose: a check that
# never queries cannot leak whether the id exists, so a standard user gets the
# same 403 for a real id and for a made-up one.
@pytest.mark.asyncio
async def test_standard_user_is_forbidden_and_the_database_is_never_touched(approved_refund):
    unit_of_work = build_unit_of_work()
    repository = build_repository(approved_refund)
    storage = MagicMock()
    controller = RefundPayerController(unit_of_work, repository, storage)

    with pytest.raises(HttpForbiddenError):
        await controller.pay(
            refund_id=1, payer_id=9, role="standard", filename="proof.pdf", content=b"x"
        )

    repository.select_refund_by_id.assert_not_awaited()
    storage.save.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_refund_is_not_found():
    unit_of_work = build_unit_of_work()
    repository = build_repository(None)
    controller = RefundPayerController(unit_of_work, repository, MagicMock())

    with pytest.raises(HttpNotFoundError):
        await controller.pay(
            refund_id=1, payer_id=9, role="admin", filename="proof.pdf", content=b"x"
        )


# BR-016 extended to payment: an admin already cannot approve their own refund,
# so being able to pay it would be a hole in the same rule.
@pytest.mark.asyncio
async def test_admin_cannot_pay_their_own_refund(approved_refund):
    unit_of_work = build_unit_of_work()
    repository = build_repository(approved_refund)
    storage = MagicMock()
    controller = RefundPayerController(unit_of_work, repository, storage)

    with pytest.raises(HttpForbiddenError):
        await controller.pay(
            refund_id=1, payer_id=7, role="admin", filename="proof.pdf", content=b"x"
        )

    # The exception alone would not catch a guard that ran after the file was
    # written: a bare MagicMock's save() succeeds silently, so this assertion
    # is what actually pins the ownership check ahead of the file write.
    storage.save.assert_not_called()


# Only an approved refund can be paid: pending has not been decided and
# rejected owes nothing.
@pytest.mark.asyncio
async def test_a_refund_that_is_not_approved_cannot_be_paid(approved_refund):
    unit_of_work = build_unit_of_work()
    repository = build_repository({**approved_refund, "status": "pending"})
    storage = MagicMock()
    controller = RefundPayerController(unit_of_work, repository, storage)

    with pytest.raises(HttpUnprocessableEntityError):
        await controller.pay(
            refund_id=1, payer_id=9, role="admin", filename="proof.pdf", content=b"x"
        )

    # The file is only written once every guard has passed.
    storage.save.assert_not_called()


# The race the conditional UPDATE closes: another admin paid between our guard
# read and our write. The file we already wrote must not survive the failure.
@pytest.mark.asyncio
async def test_a_lost_race_deletes_the_file_it_had_written(approved_refund):
    unit_of_work = build_unit_of_work(affected=0)
    repository = build_repository(approved_refund)
    storage = MagicMock()
    storage.save = MagicMock(return_value="stored.pdf")
    storage.delete = MagicMock()
    controller = RefundPayerController(unit_of_work, repository, storage)

    with pytest.raises(HttpUnprocessableEntityError):
        await controller.pay(
            refund_id=1, payer_id=9, role="admin", filename="proof.pdf", content=b"x"
        )

    storage.delete.assert_called_once_with("stored.pdf")
    unit_of_work.commit.assert_not_awaited()
    unit_of_work.reviews.insert_review.assert_not_awaited()


# I2: a lock timeout (PostgreSQL 55P03 lock_not_available, reachable through
# the engine's global 3s lock_timeout from Task 2 when RefundReviewerController
# holds the same row with select_for_update) fails INSIDE the transaction,
# after the file was already written. The file must not be orphaned, and the
# original exception must survive untouched — it is not "not approved", so it
# must not be laundered into a 422.
@pytest.mark.asyncio
async def test_mark_as_paid_raising_deletes_the_file_and_reraises(approved_refund):
    unit_of_work = build_unit_of_work()
    unit_of_work.refunds.mark_as_paid = AsyncMock(
        side_effect=RuntimeError("lock_not_available")
    )
    repository = build_repository(approved_refund)
    storage = MagicMock()
    storage.save = MagicMock(return_value="stored.pdf")
    storage.delete = MagicMock()
    controller = RefundPayerController(unit_of_work, repository, storage)

    with pytest.raises(RuntimeError):
        await controller.pay(
            refund_id=1, payer_id=9, role="admin", filename="proof.pdf", content=b"x"
        )

    storage.delete.assert_called_once_with("stored.pdf")


# Same guarantee, but the failure happens at commit() instead of mark_as_paid
# — a different line, same orphaning risk.
@pytest.mark.asyncio
async def test_commit_raising_deletes_the_file_and_reraises(approved_refund):
    unit_of_work = build_unit_of_work()
    unit_of_work.commit = AsyncMock(side_effect=RuntimeError("commit failed"))
    repository = build_repository(approved_refund)
    storage = MagicMock()
    storage.save = MagicMock(return_value="stored.pdf")
    storage.delete = MagicMock()
    controller = RefundPayerController(unit_of_work, repository, storage)

    with pytest.raises(RuntimeError):
        await controller.pay(
            refund_id=1, payer_id=9, role="admin", filename="proof.pdf", content=b"x"
        )

    storage.delete.assert_called_once_with("stored.pdf")


# Deferred minor: if the compensating delete itself raises (e.g. the file is
# already gone), that must not replace the original error the caller needs to
# see.
@pytest.mark.asyncio
async def test_a_failing_compensation_delete_does_not_mask_the_original_error(approved_refund):
    unit_of_work = build_unit_of_work(affected=0)
    repository = build_repository(approved_refund)
    storage = MagicMock()
    storage.save = MagicMock(return_value="stored.pdf")
    storage.delete = MagicMock(side_effect=OSError("disk gone"))
    controller = RefundPayerController(unit_of_work, repository, storage)

    with pytest.raises(HttpUnprocessableEntityError):
        await controller.pay(
            refund_id=1, payer_id=9, role="admin", filename="proof.pdf", content=b"x"
        )


# Deferred minor: the lost-race 422 and the pre-write "not approved" 422 need
# distinct messages so logs can tell "never approved" from "lost the race to
# another admin" when auditing an orphaned file.
@pytest.mark.asyncio
async def test_the_lost_race_message_differs_from_the_not_approved_message(approved_refund):
    unit_of_work = build_unit_of_work(affected=0)
    repository = build_repository(approved_refund)
    storage = MagicMock()
    storage.save = MagicMock(return_value="stored.pdf")
    storage.delete = MagicMock()
    controller = RefundPayerController(unit_of_work, repository, storage)

    with pytest.raises(HttpUnprocessableEntityError) as exc_info:
        await controller.pay(
            refund_id=1, payer_id=9, role="admin", filename="proof.pdf", content=b"x"
        )

    assert exc_info.value.message != "Only an approved refund can be paid"
