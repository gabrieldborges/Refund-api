"""Row-lock contention against a real PostgreSQL.

Closes the second pendency Item 19 was blocking: "o ajuste de
pool/lock_timeout não tem teste comportamental na suíte.
database_connection_handler_pool_test.py verifica os PARÂMETROS passados a
create_async_engine, não que o Postgres real os aceitou nem que a contenção
efetivamente some."

Until now the only evidence for either half was manual: a `SHOW lock_timeout`
typed against the real connection, and three concurrent PATCHes raced by hand
during a verification task. Neither was repeatable in CI.

These tests are NOT a race. One transaction takes the lock deliberately and
holds it; the other has exactly one possible outcome. There is nothing to win
or lose, which is what keeps a concurrency test out of the flake category the
project already paid for once with ResizeObserver.
"""
import asyncio
import time
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from src.models.repositories.refund_status_repository import RefundStatusRepository
from src.models.repositories.refunds_repository import RefundsRepository
from src.models.repositories.users_repository import UsersRepository


# The engine sets lock_timeout to 3000ms. A blocked statement should therefore
# give up after roughly 3s: long enough that these bounds do not depend on
# machine speed, tight enough to tell "waited then gave up" from both "failed
# instantly for some other reason" and "hung".
LOCK_TIMEOUT_SECONDS = 3
MINIMUM_WAIT = 1.5
MAXIMUM_WAIT = 15


# The half that a SHOW typed by hand used to prove. It matters more than it
# looks: the form asyncpg's own documentation recommends
# (server_settings={"lock_timeout": ...}) is silently DISCARDED by the Neon
# proxy, and the project only found out because someone asked the server. This
# asserts the surviving form still arrives.
@pytest.mark.integration
@pytest.mark.asyncio
async def test_the_lock_timeout_setting_reaches_the_server(engine):
    async with engine.connect() as connection:
        value = (await connection.execute(text("SHOW lock_timeout"))).scalar()

    assert value == "3s"


# The behavioural half: a second transaction wanting the same row must give up
# instead of waiting forever while holding a pooled connection. That is the
# failure this configuration exists to prevent — two blocked reviewers used to
# exhaust a pool of two and turn an unrelated login into a 500.
@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_blocked_row_lock_gives_up_instead_of_waiting_forever(
    engine, connection_handler
):
    users = UsersRepository(connection_handler)
    refunds = RefundsRepository(connection_handler)
    user_id = await users.insert_user(
        {"name": "Ana", "email": "lock@example.com", "password": "hashed"}
    )
    refund_id = await refunds.insert_refund(
        {
            "user_id": user_id,
            "name": "Almoço",
            "category": "food",
            "amount_in_cents": 1500,
            "filename": "receipt.png",
        }
    )

    factory = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    holder = factory()
    try:
        # Transaction A takes the row lock and keeps it. This is the "another
        # admin is reviewing the same refund right now" situation.
        await RefundStatusRepository(holder).select_for_update(refund_id)

        blocked = factory()
        started_at = time.monotonic()
        try:
            # asyncio.wait_for is the guard that keeps a REGRESSION from
            # hanging the suite instead of failing it. Without lock_timeout the
            # statement below waits forever; wrapped, it raises TimeoutError
            # after MAXIMUM_WAIT, which is not a DBAPIError, so pytest.raises
            # reports a failure. A test that hangs on regression is worse than
            # no test — nobody reads a suite that never finishes.
            with pytest.raises(DBAPIError) as error:
                await asyncio.wait_for(
                    RefundStatusRepository(blocked).select_for_update(refund_id),
                    timeout=MAXIMUM_WAIT,
                )
        finally:
            elapsed = time.monotonic() - started_at
            await blocked.rollback()
            await blocked.close()
    finally:
        await holder.rollback()
        await holder.close()

    # It waited for the lock rather than failing for some unrelated reason...
    assert elapsed > MINIMUM_WAIT
    # ...and it gave up rather than blocking indefinitely.
    assert elapsed < MAXIMUM_WAIT
    assert "lock" in str(error.value).lower()


# The lock must actually be released, or the timeout above would just be
# trading one outage for another. Once the holder rolls back, the same read
# succeeds immediately.
@pytest.mark.integration
@pytest.mark.asyncio
async def test_the_row_is_available_again_once_the_holder_releases_it(
    engine, connection_handler
):
    users = UsersRepository(connection_handler)
    refunds = RefundsRepository(connection_handler)
    user_id = await users.insert_user(
        {"name": "Ana", "email": "release@example.com", "password": "hashed"}
    )
    refund_id = await refunds.insert_refund(
        {
            "user_id": user_id,
            "name": "Almoço",
            "category": "food",
            "amount_in_cents": 1500,
            "filename": "receipt.png",
        }
    )

    factory = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    holder = factory()
    await RefundStatusRepository(holder).select_for_update(refund_id)
    await holder.rollback()
    await holder.close()

    waiter = factory()
    try:
        started_at = time.monotonic()
        row = await RefundStatusRepository(waiter).select_for_update(refund_id)
        elapsed = time.monotonic() - started_at
    finally:
        await waiter.rollback()
        await waiter.close()

    assert row["id"] == refund_id
    # No waiting at all: the lock was gone, not merely timed out again.
    assert elapsed < LOCK_TIMEOUT_SECONDS


# Two reviewers acting on DIFFERENT refunds must not block each other. Without
# this, a lock_timeout that "works" could just as well be a table-level lock
# serialising every review in the system.
@pytest.mark.integration
@pytest.mark.asyncio
async def test_locks_on_different_rows_do_not_block_each_other(engine, connection_handler):
    users = UsersRepository(connection_handler)
    refunds = RefundsRepository(connection_handler)
    user_id = await users.insert_user(
        {"name": "Ana", "email": "two-rows@example.com", "password": "hashed"}
    )
    first = await refunds.insert_refund(
        {
            "user_id": user_id, "name": "Almoço", "category": "food",
            "amount_in_cents": 1500, "filename": "a.png",
        }
    )
    second = await refunds.insert_refund(
        {
            "user_id": user_id, "name": "Jantar", "category": "food",
            "amount_in_cents": 2500, "filename": "b.png",
        }
    )

    factory = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    holder, other = factory(), factory()
    try:
        await RefundStatusRepository(holder).select_for_update(first)

        started_at = time.monotonic()
        row = await asyncio.wait_for(
            RefundStatusRepository(other).select_for_update(second),
            timeout=MAXIMUM_WAIT,
        )
        elapsed = time.monotonic() - started_at
    finally:
        await holder.rollback()
        await holder.close()
        await other.rollback()
        await other.close()

    assert row["id"] == second
    assert elapsed < LOCK_TIMEOUT_SECONDS
