# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.errors.types.http_not_found_error import HttpNotFoundError
from .payment_receipt_finder_controller import PaymentReceiptFinderController


@pytest.fixture
def paid_refund():
    return {
        "id": 1,
        "status": "paid",
        "payment_filename": "proof.pdf",
        "user": {"id": 7, "name": "Ana", "avatar_filename": None},
    }


def build_controller(refund, content=b"bytes"):
    repository = MagicMock()
    repository.select_refund_by_id = AsyncMock(return_value=refund)
    storage = MagicMock()
    storage.read = MagicMock(return_value=content)
    return PaymentReceiptFinderController(repository, storage), storage


@pytest.mark.asyncio
async def test_owner_reads_the_payment_receipt(paid_refund):
    controller, _ = build_controller(paid_refund)

    response = await controller.find(refund_id=1, user_id=7, role="standard")

    assert response["content"] == b"bytes"
    assert response["media_type"] == "application/pdf"


@pytest.mark.asyncio
async def test_admin_reads_someone_elses_payment_receipt(paid_refund):
    controller, _ = build_controller(paid_refund)

    response = await controller.find(refund_id=1, user_id=99, role="admin")

    assert response["content"] == b"bytes"


# All four failure modes answer with the SAME 404 message: unknown id, someone
# else's refund, a refund that was never paid, and a row whose file vanished.
# Any difference between them would be an oracle.
@pytest.mark.asyncio
async def test_unknown_refund_is_not_found():
    controller, _ = build_controller(None)

    with pytest.raises(HttpNotFoundError, match="Refund not found"):
        await controller.find(refund_id=1, user_id=7, role="standard")


@pytest.mark.asyncio
async def test_someone_elses_refund_is_not_found(paid_refund):
    controller, _ = build_controller(paid_refund)

    with pytest.raises(HttpNotFoundError, match="Refund not found"):
        await controller.find(refund_id=1, user_id=99, role="standard")


@pytest.mark.asyncio
async def test_an_unpaid_refund_is_not_found(paid_refund):
    controller, _ = build_controller({**paid_refund, "status": "approved", "payment_filename": None})

    with pytest.raises(HttpNotFoundError, match="Refund not found"):
        await controller.find(refund_id=1, user_id=7, role="standard")


@pytest.mark.asyncio
async def test_a_missing_file_is_not_found(paid_refund):
    controller, storage = build_controller(paid_refund)
    storage.read = MagicMock(side_effect=FileNotFoundError)

    with pytest.raises(HttpNotFoundError, match="Refund not found"):
        await controller.find(refund_id=1, user_id=7, role="standard")
