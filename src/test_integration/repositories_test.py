"""Repositories against a real PostgreSQL.

The 34 mocked repository tests assert that the right SQL is BUILT. These assert
that PostgreSQL accepts it and does what we assumed — constraints, defaults,
generated ids, foreign keys, real aggregates. The two are complementary: the
mocked ones are fast and cover branching, these cover the half a mock cannot
reach.
"""
import pytest
from sqlalchemy.exc import IntegrityError
from src.errors.types.http_bad_request_error import HttpBadRequestError
from src.models.repositories.refunds_repository import RefundsRepository
from src.models.repositories.users_repository import UsersRepository


def a_user(email: str = "ana@example.com") -> dict:
    return {"name": "Ana", "email": email, "password": "hashed", "role": "standard"}


def a_refund(user_id: int, name: str = "Almoço") -> dict:
    return {
        "user_id": user_id,
        "name": name,
        "category": "food",
        "amount_in_cents": 1500,
        "filename": "receipt.png",
    }


# The generated id comes from a real sequence, not from a mock we told to answer
# 1. This also proves TRUNCATE ... RESTART IDENTITY actually restarts it, which
# every other test in this file quietly depends on.
@pytest.mark.integration
@pytest.mark.asyncio
async def test_inserting_a_user_returns_a_real_generated_id(connection_handler):
    repository = UsersRepository(connection_handler)

    user_id = await repository.insert_user(a_user())

    assert user_id == 1
    assert (await repository.select_user_by_email("ana@example.com"))["name"] == "Ana"


# The UNIQUE constraint on users.email exists only in the database — no mocked
# test can fail this way. Worth stating what this proves and what it does not:
# UsersRepository CATCHES the IntegrityError and re-raises HttpBadRequestError,
# so this asserts the whole translation, from a PostgreSQL constraint through to
# the error type the controller layer expects.
@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_duplicate_email_is_rejected_and_translated(connection_handler):
    repository = UsersRepository(connection_handler)
    await repository.insert_user(a_user())

    with pytest.raises(HttpBadRequestError):
        await repository.insert_user(a_user())


# server_default="standard" lives in the migration, not in Python. A mocked
# session would happily report whatever value the fixture handed back.
@pytest.mark.integration
@pytest.mark.asyncio
async def test_the_role_default_comes_from_the_schema(connection_handler):
    repository = UsersRepository(connection_handler)
    user_id = await repository.insert_user(
        {"name": "Ana", "email": "sem-role@example.com", "password": "hashed"}
    )

    assert (await repository.select_user_by_id(user_id))["role"] == "standard"


# Same for the status column added by the approval-workflow migration.
@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_new_refund_starts_pending_by_schema_default(connection_handler):
    users = UsersRepository(connection_handler)
    refunds = RefundsRepository(connection_handler)
    user_id = await users.insert_user(a_user())

    refund_id = await refunds.insert_refund(a_refund(user_id))

    assert (await refunds.select_refund_by_id(refund_id))["status"] == "pending"


# refunds.user_id references users.id. A refund for a user that does not exist
# must be refused by PostgreSQL rather than silently written. Unlike the users
# repository above, this one does NOT translate the error — it propagates as
# IntegrityError, and that difference between the two repositories is exactly
# the kind of thing only a real database can show.
@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_refund_for_a_missing_user_violates_the_foreign_key(connection_handler):
    repository = RefundsRepository(connection_handler)

    with pytest.raises(IntegrityError):
        await repository.insert_refund(a_refund(user_id=9999))


# The count and the SUM run for real here. The mocked suite asserts on the SQL
# text; this asserts on the numbers PostgreSQL computes from actual rows.
@pytest.mark.integration
@pytest.mark.asyncio
async def test_listing_computes_total_and_sum_over_real_rows(connection_handler):
    users = UsersRepository(connection_handler)
    refunds = RefundsRepository(connection_handler)
    user_id = await users.insert_user(a_user())
    await refunds.insert_refund(a_refund(user_id, "Almoço"))
    await refunds.insert_refund(a_refund(user_id, "Jantar"))

    rows, total, sum_amount = await refunds.select_refunds(
        page=1, per_page=10, user_id=user_id
    )

    assert total == 2
    assert sum_amount == 3000
    assert {row["name"] for row in rows} == {"Almoço", "Jantar"}


# The filter must narrow the aggregates too, not just the rows — a regression
# here would show a total that disagrees with the list on screen.
@pytest.mark.integration
@pytest.mark.asyncio
async def test_a_status_filter_narrows_the_aggregates_as_well(connection_handler):
    users = UsersRepository(connection_handler)
    refunds = RefundsRepository(connection_handler)
    user_id = await users.insert_user(a_user())
    await refunds.insert_refund(a_refund(user_id, "Almoço"))
    await refunds.insert_refund(a_refund(user_id, "Jantar"))

    rows, total, sum_amount = await refunds.select_refunds(
        page=1, per_page=10, user_id=user_id, status="approved"
    )

    assert rows == []
    assert total == 0
    assert sum_amount == 0


# The nested user object comes out of a JOIN. Against a mock, "user" is whatever
# the fixture returned; here it has to be assembled from two real tables.
@pytest.mark.integration
@pytest.mark.asyncio
async def test_selecting_a_refund_joins_the_real_user_row(connection_handler):
    users = UsersRepository(connection_handler)
    refunds = RefundsRepository(connection_handler)
    user_id = await users.insert_user(a_user())
    refund_id = await refunds.insert_refund(a_refund(user_id))

    stored = await refunds.select_refund_by_id(refund_id)

    assert stored["name"] == "Almoço"
    assert stored["user"]["id"] == user_id
    assert stored["user"]["name"] == "Ana"


# Deletion reports how many rows it removed, which is what the controller uses
# to tell "deleted" from "was not there" — the 404 for a refund that is gone.
@pytest.mark.integration
@pytest.mark.asyncio
async def test_deleting_reports_the_row_count_it_actually_removed(connection_handler):
    users = UsersRepository(connection_handler)
    refunds = RefundsRepository(connection_handler)
    user_id = await users.insert_user(a_user())
    refund_id = await refunds.insert_refund(a_refund(user_id))

    assert await refunds.delete_refund(refund_id) == 1
    assert await refunds.delete_refund(refund_id) == 0


# count_by_status is a GROUP BY, so it can only return statuses that HAVE rows.
# Worth pinning down, because UC-014 promises the API always answers with all
# four statuses — and that guarantee lives one layer up, in
# RefundStatsFinderController, not here. A reader who assumes the repository
# fills the gaps (as the first draft of this test did) would be wrong about
# where to look when a status goes missing from the response.
@pytest.mark.integration
@pytest.mark.asyncio
async def test_counting_by_status_only_returns_statuses_that_have_rows(connection_handler):
    users = UsersRepository(connection_handler)
    refunds = RefundsRepository(connection_handler)
    user_id = await users.insert_user(a_user())
    await refunds.insert_refund(a_refund(user_id))

    stats = await refunds.count_by_status(user_id)

    assert set(stats.keys()) == {"pending"}
    assert stats["pending"] == {"count": 1, "amount_in_cents": 1500}


# An aggregate over no rows at all must not blow up or return NULL.
@pytest.mark.integration
@pytest.mark.asyncio
async def test_counting_by_status_for_a_user_with_no_refunds_is_empty(connection_handler):
    users = UsersRepository(connection_handler)
    refunds = RefundsRepository(connection_handler)
    user_id = await users.insert_user(a_user())

    assert await refunds.count_by_status(user_id) == {}
