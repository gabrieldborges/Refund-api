"""The orphan sweep, against a real database and real files.

Mocking storage here would defeat the purpose: the whole job is a comparison
between what is ON DISK and what is IN THE DATABASE, so faking either side
would only prove the comparison compiles.
"""
import os
from datetime import timedelta
import pytest
from src.jobs.orphan_sweep import sweep
from src.models.repositories.refunds_repository import RefundsRepository
from src.models.repositories.users_repository import UsersRepository


def a_refund(user_id):
    return {
        "user_id": user_id, "name": "Almoço", "category": "food",
        "amount_in_cents": 1500, "filename": "referenciado.png",
    }


def write_file(directory, name, age_hours=0):
    """Writes a file and, when asked, backdates it past the minimum age."""
    path = os.path.join(directory, name)
    with open(path, "wb") as handle:
        handle.write(b"bytes")
    if age_hours:
        old = os.path.getmtime(path) - age_hours * 3600
        os.utime(path, (old, old))
    return path


@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_file_with_no_row_is_reported(connection_handler, local_storage_dirs, app_uses_the_test_database):  # pylint: disable=unused-argument
    write_file(local_storage_dirs["receipts"], "ninguem-aponta.png", age_hours=2)

    results = {result.storage: result for result in await sweep()}

    assert results["receipts"].orphans == ["ninguem-aponta.png"]


# THE SAFETY PROPERTY, and the reason the job has a minimum age at all. A file
# written seconds ago whose transaction has not committed yet is
# indistinguishable from an orphan — deleting it would destroy a receipt in
# flight, which is worse than the leak the sweep exists to clean.
@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_recent_file_is_never_touched(connection_handler, local_storage_dirs, app_uses_the_test_database):  # pylint: disable=unused-argument
    write_file(local_storage_dirs["receipts"], "acabou-de-chegar.png")

    results = {result.storage: result for result in await sweep(apply=True)}

    assert results["receipts"].orphans == []
    assert results["receipts"].too_recent == 1
    assert os.path.exists(os.path.join(local_storage_dirs["receipts"], "acabou-de-chegar.png"))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_referenced_file_is_never_reported(  # pylint: disable=unused-argument
    connection_handler, local_storage_dirs, app_uses_the_test_database
):
    users = UsersRepository(connection_handler)
    refunds = RefundsRepository(connection_handler)
    user_id = await users.insert_user(
        {"name": "Ana", "email": "sweep@example.com", "password": "hashed"}
    )
    await refunds.insert_refund(a_refund(user_id))
    # Old enough to qualify, but the database points at it.
    write_file(local_storage_dirs["receipts"], "referenciado.png", age_hours=2)

    results = {result.storage: result for result in await sweep(apply=True)}

    assert results["receipts"].orphans == []
    assert os.path.exists(os.path.join(local_storage_dirs["receipts"], "referenciado.png"))


# Dry run by default, because this deletes user data. A job that removes things
# the first time somebody runs it to see what it does will eventually remove
# something it should not have.
@pytest.mark.integration
@pytest.mark.asyncio
async def test_nothing_is_removed_without_apply(connection_handler, local_storage_dirs, app_uses_the_test_database):  # pylint: disable=unused-argument
    path = write_file(local_storage_dirs["receipts"], "orfao.png", age_hours=2)

    results = {result.storage: result for result in await sweep()}

    assert results["receipts"].orphans == ["orfao.png"]
    assert results["receipts"].removed == []
    assert os.path.exists(path)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_apply_removes_the_orphan(connection_handler, local_storage_dirs, app_uses_the_test_database):  # pylint: disable=unused-argument
    path = write_file(local_storage_dirs["receipts"], "orfao.png", age_hours=2)

    results = {result.storage: result for result in await sweep(apply=True)}

    assert results["receipts"].removed == ["orfao.png"]
    assert not os.path.exists(path)


# Idempotence, which the item lists as a requirement for any job: the second
# run has nothing left to do, and does not fail trying.
@pytest.mark.integration
@pytest.mark.asyncio
async def test_running_twice_is_harmless(connection_handler, local_storage_dirs, app_uses_the_test_database):  # pylint: disable=unused-argument
    write_file(local_storage_dirs["receipts"], "orfao.png", age_hours=2)

    await sweep(apply=True)
    second = {result.storage: result for result in await sweep(apply=True)}

    assert second["receipts"].orphans == []
    assert second["receipts"].removed == []


# All three storages are swept, not just receipts — the avatar and payment
# directories produce orphans by the same two mechanisms.
@pytest.mark.integration
@pytest.mark.asyncio
async def test_every_storage_is_swept(connection_handler, local_storage_dirs, app_uses_the_test_database):  # pylint: disable=unused-argument
    for name, directory in local_storage_dirs.items():
        write_file(directory, f"orfao-{name}.png", age_hours=2)

    results = {result.storage: result for result in await sweep(apply=True)}

    assert set(results) == {"receipts", "avatars", "payments"}
    for name in results:
        assert results[name].removed == [f"orfao-{name}.png"]


# The age threshold is a parameter, so an operator can widen it after an
# incident without editing code.
@pytest.mark.integration
@pytest.mark.asyncio
async def test_the_minimum_age_is_configurable(connection_handler, local_storage_dirs, app_uses_the_test_database):  # pylint: disable=unused-argument
    write_file(local_storage_dirs["receipts"], "duas-horas.png", age_hours=2)

    with_wide_window = {r.storage: r for r in await sweep(minimum_age=timedelta(hours=24))}
    with_narrow_window = {r.storage: r for r in await sweep(minimum_age=timedelta(minutes=30))}

    assert with_wide_window["receipts"].orphans == []
    assert with_narrow_window["receipts"].orphans == ["duas-horas.png"]
