"""Database-and-file consistency, with a real database and real files.

The unit tests for Item 21 prove the controllers CALL delete on the storage
mock. These prove the file actually leaves the disk, and that the database
failure driving the compensation is a real one — a foreign key PostgreSQL
refuses, not an exception a mock was told to raise.

This is the pairing the project could not write before Item 19: "no file was
left behind" used to be checkable only by listing the directory by hand, which
is how seven orphans were once found.
"""
import os
import pytest
from sqlalchemy.exc import IntegrityError
from src.controllers.refund_creator_controller import RefundCreatorController
from src.controllers.refund_deleter_controller import RefundDeleterController
from src.drivers.file_storage import FileStorage
from src.models.repositories.refunds_repository import RefundsRepository
from src.models.repositories.users_repository import UsersRepository


def a_refund_payload(name: str = "Almoço") -> dict:
    return {
        "name": name,
        "category": "food",
        "amount": 15.00,
        "filename": "receipt.png",
        "content": b"pretend this is a png",
    }


# Positive control first. Without it, an "empty directory" assertion below
# would also pass if the file had never been written at all.
@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_successful_creation_leaves_exactly_one_file(connection_handler, tmp_path):
    storage = FileStorage(str(tmp_path))
    users = UsersRepository(connection_handler)
    user_id = await users.insert_user(
        {"name": "Ana", "email": "consistency@example.com", "password": "hashed"}
    )
    controller = RefundCreatorController(RefundsRepository(connection_handler), storage)

    await controller.create(a_refund_payload(), user_id=user_id)

    assert len(os.listdir(tmp_path)) == 1


# The real thing: PostgreSQL refuses the insert because the user does not
# exist, and the receipt that was already written must not survive it.
@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_failed_insert_leaves_no_orphan_on_disk(connection_handler, tmp_path):
    storage = FileStorage(str(tmp_path))
    controller = RefundCreatorController(RefundsRepository(connection_handler), storage)

    with pytest.raises(IntegrityError):
        await controller.create(a_refund_payload(), user_id=999999)

    assert os.listdir(tmp_path) == []


# Deleting a refund must take its receipt with it. The mocked test can only
# assert that delete() was called with the right name.
@pytest.mark.integration
@pytest.mark.asyncio
async def test_deleting_a_refund_removes_its_receipt_from_disk(connection_handler, tmp_path):
    storage = FileStorage(str(tmp_path))
    users = UsersRepository(connection_handler)
    refunds = RefundsRepository(connection_handler)
    user_id = await users.insert_user(
        {"name": "Ana", "email": "delete-file@example.com", "password": "hashed"}
    )
    created = await RefundCreatorController(refunds, storage).create(
        a_refund_payload(), user_id=user_id
    )
    assert len(os.listdir(tmp_path)) == 1

    await RefundDeleterController(refunds, storage).delete(
        refund_id=created["attributes"]["id"], user_id=user_id, role="standard"
    )

    assert os.listdir(tmp_path) == []


# The post-commit rule, end to end: the row is gone and the response is a
# success, even though the file could not be removed. A read-only directory is
# the closest reproduction of the real cause (a permission or I/O error) that
# does not require mocking anything.
@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_refund_is_deleted_even_when_its_file_cannot_be_removed(
    connection_handler, tmp_path
):
    storage = FileStorage(str(tmp_path))
    users = UsersRepository(connection_handler)
    refunds = RefundsRepository(connection_handler)
    user_id = await users.insert_user(
        {"name": "Ana", "email": "readonly@example.com", "password": "hashed"}
    )
    created = await RefundCreatorController(refunds, storage).create(
        a_refund_payload(), user_id=user_id
    )
    refund_id = created["attributes"]["id"]

    os.chmod(tmp_path, 0o500)  # r-x: the file can be listed, not unlinked
    try:
        response = await RefundDeleterController(refunds, storage).delete(
            refund_id=refund_id, user_id=user_id, role="standard"
        )
    finally:
        os.chmod(tmp_path, 0o700)

    assert response["attributes"]["deleted"] is True
    # The row really is gone — the success was not a lie in the other direction.
    assert await refunds.select_refund_by_id(refund_id) is None
    # And the orphan is real, which is exactly why it gets logged.
    assert len(os.listdir(tmp_path)) == 1
