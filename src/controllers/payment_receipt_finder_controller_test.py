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


def build_controller(refund):
    repository = MagicMock()
    repository.select_refund_by_id = AsyncMock(return_value=refund)
    storage = MagicMock()
    storage.get_url = MagicMock(return_value="https://signed.example/file?token=t")
    return PaymentReceiptFinderController(repository, storage), storage


@pytest.mark.asyncio
async def test_owner_reads_the_payment_receipt(paid_refund):
    controller, _ = build_controller(paid_refund)

    response = await controller.find(refund_id=1, user_id=7, role="standard")

    assert response["url"] == "https://signed.example/file?token=t"


@pytest.mark.asyncio
async def test_admin_reads_someone_elses_payment_receipt(paid_refund):
    controller, _ = build_controller(paid_refund)

    response = await controller.find(refund_id=1, user_id=99, role="admin")

    assert response["url"] == "https://signed.example/file?token=t"


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


# BEHAVIOUR REMOVED BY ITEM 22 — see the note in
# receipt_finder_controller_test.py. This endpoint had FOUR identical 404 paths
# verified byte for byte when it was built: unknown id, not yours, never paid,
# and file gone from disk. The fourth one moved: the controller no longer reads
# the file, so a missing object is discovered when the URL is followed.
#
# THE THREE THAT MATTER ARE INTACT and still tested above — they are the ones
# that would leak whether a refund exists, or whether it was paid, to someone
# not entitled to know. The fourth only ever told an already-authorized caller
# that their own file is gone.
@pytest.mark.asyncio
async def test_a_url_is_minted_from_the_stored_payment_filename(paid_refund):
    controller, storage = build_controller(paid_refund)

    response = await controller.find(refund_id=1, user_id=7, role="standard")

    storage.get_url.assert_called_once_with(paid_refund["payment_filename"])
    assert response["url"] == "https://signed.example/file?token=t"


@pytest.mark.asyncio
async def test_the_response_carries_the_media_type(paid_refund):
    controller, _ = build_controller(paid_refund)

    response = await controller.find(refund_id=1, user_id=7, role="standard")

    assert response["media_type"] == "application/pdf"
