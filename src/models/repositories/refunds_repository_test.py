# pylint: disable=w0621,w0212,duplicate-code
# w0621: silences the "redefined-outer-name" warning — expected when using fixtures,
#        since the test parameter shares its name with the fixture function.
# w0212: allows access to the "protected" attribute (_mapping) of the mock, which only exists here.
# duplicate-code: this file's mock_db bootstrap (MagicMock db/session, AsyncMock execute/commit)
#        necessarily looks like users_repository_test.py's — both fake the same connection
#        protocol for a different repository. Extracting a shared fixture would couple two
#        independent test files to one mock shape for no real reuse benefit.
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
import pytest
from .refunds_repository import RefundsRepository


# Fixture: builds a fake database (mock) with the default behavior expected by most
# tests. Each test gets a fresh instance (isolation), so one test can't contaminate
# another. MagicMock creates an object that accepts any attribute/method; here we only
# configure what the repository actually uses: session.execute/commit.
@pytest.fixture
def mock_db():
    db = MagicMock()
    execute_result = MagicMock()
    # Simulates the return of an INSERT: SQLAlchemy exposes the generated PK here.
    execute_result.inserted_primary_key = [1]
    # select_refunds always makes two round trips (totals, then rows) against the
    # same execute() mock. Tests that don't care about the actual numbers (e.g. the
    # JOIN/sort/order assertions, which only inspect the emitted SQL) still need
    # both calls to resolve without raising, hence these empty-but-valid defaults.
    execute_result.one = MagicMock(return_value=(0, 0))
    execute_result.fetchall = MagicMock(return_value=[])
    # AsyncMock because in the real code these methods are called with "await".
    db.session.execute = AsyncMock(return_value=execute_result)
    db.session.commit = AsyncMock()
    return db


# Verifies inserting a refund returns the generated id and commits the transaction.
# AAA pattern (Arrange-Act-Assert): set up -> execute -> verify.
@pytest.mark.asyncio
async def test_insert_refund_returns_the_new_id(mock_connection, mock_db):
    # Arrange: create the repository wired to the fake connection.
    repository = RefundsRepository(mock_connection)

    # Act: run the operation under test.
    refund_info = {
        "user_id": 1, "name": "Ana", "category": "food",
        "amount_in_cents": 1000, "filename": "receipt.jpg"
    }
    refund_id = await repository.insert_refund(refund_info)

    # Assert: the returned id came from the simulated PK, and INSERT + commit happened
    # exactly once (guarantees we actually saved to the database).
    assert refund_id == 1
    mock_db.session.execute.assert_awaited_once()
    mock_db.session.commit.assert_awaited_once()


# Verifies the listing returns the items (already converted to dict), the total count,
# and the total amount in cents.
@pytest.mark.asyncio
async def test_select_refunds_returns_items_total_and_sum(mock_connection, mock_db):
    # Arrange: simulate a database row. In SQLAlchemy Core, each row has _mapping,
    # which behaves like a column->value dict; the repository converts that into a dict.
    # A real joined row always carries user_name/avatar_filename from the JOIN, on
    # top of the refund's own columns and its (unlabelled) user_id. "name" and
    # "user_name" are deliberately DIFFERENT values here: if __to_refund ever read
    # the wrong one (the exact collision the label exists to prevent), this test
    # must fail instead of passing by coincidence.
    row = MagicMock()
    row._mapping = {
        "id": 1, "user_id": 1, "name": "Almoço", "category": "food",
        "amount_in_cents": 1000, "filename": "receipt.jpg", "payment_filename": None,
        "status": "pending", "created_at": "2026-07-29", "user_name": "Ana",
        "avatar_filename": "ana.png",
    }
    fetch_result = MagicMock()
    fetch_result.fetchall = MagicMock(return_value=[row])
    # count() and sum() now share a single query, so its result exposes .one() ->
    # a (total, total_amount) tuple, instead of the old scalar() COUNT result.
    totals_result = MagicMock()
    totals_result.one = MagicMock(return_value=(1, 1000))
    # select_refunds calls session.execute twice (totals query, then rows query), so
    # a single shared return_value can't serve both calls; side_effect supplies one
    # result per call, in order.
    mock_db.session.execute = AsyncMock(side_effect=[totals_result, fetch_result])

    repository = RefundsRepository(mock_connection)
    refunds, total, total_amount = await repository.select_refunds(page=1, per_page=10, user_id=1)

    assert total == 1
    assert total_amount == 1000
    assert refunds == [{
        "id": 1, "name": "Almoço", "category": "food", "amount_in_cents": 1000,
        "filename": "receipt.jpg", "payment_filename": None, "status": "pending",
        "created_at": "2026-07-29",
        "user": {"id": 1, "name": "Ana", "avatar_filename": "ana.png"},
    }]


# The sum must cover every refund matching the filter, not just the page that
# was returned, and an empty result set must read as 0 rather than None.
@pytest.mark.asyncio
async def test_select_refunds_returns_zero_sum_when_there_are_no_rows(mock_connection, mock_db):
    # SUM over an empty set comes back as NULL from the database, i.e. None here.
    totals_result = MagicMock()
    totals_result.one = MagicMock(return_value=(0, None))
    fetch_result = MagicMock()
    fetch_result.fetchall = MagicMock(return_value=[])
    mock_db.session.execute = AsyncMock(side_effect=[totals_result, fetch_result])

    repository = RefundsRepository(mock_connection)
    _, total, total_amount = await repository.select_refunds(page=1, per_page=10)

    assert total == 0
    assert total_amount == 0


# Happy path: looking up an existing id returns the refund as a dict, with the
# requester nested under "user" instead of a bare user_id. "name" and "user_name"
# are deliberately different values so a swap between the two in __to_refund
# (the exact bug the "user_name" label exists to prevent) would fail this test
# instead of passing unnoticed.
@pytest.mark.asyncio
async def test_select_refund_by_id_found(mock_connection, mock_db):
    row = MagicMock()
    row._mapping = {
        "id": 1, "user_id": 1, "name": "Almoço", "category": "food",
        "amount_in_cents": 1000, "filename": "receipt.jpg", "payment_filename": None,
        "status": "pending", "created_at": "2026-07-29", "user_name": "Ana",
        "avatar_filename": "ana.png",
    }
    result = MagicMock()
    # fetchone returns a row -> refund found.
    result.fetchone = MagicMock(return_value=row)
    mock_db.session.execute = AsyncMock(return_value=result)

    repository = RefundsRepository(mock_connection)
    refund = await repository.select_refund_by_id(1)

    assert refund == {
        "id": 1, "name": "Almoço", "category": "food", "amount_in_cents": 1000,
        "filename": "receipt.jpg", "payment_filename": None, "status": "pending",
        "created_at": "2026-07-29",
        "user": {"id": 1, "name": "Ana", "avatar_filename": "ana.png"},
    }


# "Not found" path: when the database returns no row, the method returns None.
@pytest.mark.asyncio
async def test_select_refund_by_id_not_found(mock_connection, mock_db):
    result = MagicMock()
    # fetchone returns None -> nothing found.
    result.fetchone = MagicMock(return_value=None)
    mock_db.session.execute = AsyncMock(return_value=result)

    repository = RefundsRepository(mock_connection)
    refund = await repository.select_refund_by_id(999)

    assert refund is None


# Verifies deleting runs the DELETE and commits the transaction, and that
# rowcount is returned so the caller can tell "deleted" from "not eligible".
@pytest.mark.asyncio
async def test_delete_refund(mock_connection, mock_db):
    execute_result = MagicMock()
    execute_result.rowcount = 1
    mock_db.session.execute = AsyncMock(return_value=execute_result)

    repository = RefundsRepository(mock_connection)
    deleted_count = await repository.delete_refund(1)

    mock_db.session.execute.assert_awaited_once()
    mock_db.session.commit.assert_awaited_once()
    assert deleted_count == 1


# The DELETE must be conditional on status, not just id: this is what closes the
# race with a concurrent review that moves the refund out of "pending" between
# the controller's read and this delete. Mirrors how
# refund_status_repository_test.py asserts on "FOR UPDATE" by inspecting the
# emitted statement's string form.
@pytest.mark.asyncio
async def test_delete_refund_filters_on_pending_status(mock_connection, mock_db):
    execute_result = MagicMock()
    execute_result.rowcount = 0
    mock_db.session.execute = AsyncMock(return_value=execute_result)

    repository = RefundsRepository(mock_connection)
    deleted_count = await repository.delete_refund(1)

    statement = str(mock_db.session.execute.call_args[0][0])
    assert "status" in statement
    assert deleted_count == 0


# The requester's name and picture come from a JOIN, not from a query per row:
# an admin listing 10 refunds must cost one round trip, not eleven. This also
# checks the returned shape actually nests the requester under "user" — asserting
# only "JOIN users" in the emitted SQL would still pass even if the nesting in
# __to_refund were deleted entirely.
@pytest.mark.asyncio
async def test_select_refunds_joins_users_and_nests_the_requester(mock_connection, mock_db):
    row = MagicMock()
    # "name" and "user_name" are deliberately different values, same reasoning
    # as the other fixtures: a swap between them must fail this test.
    row._mapping = {
        "id": 1, "user_id": 5, "name": "Almoço", "category": "food",
        "amount_in_cents": 1000, "filename": "receipt.jpg", "payment_filename": None,
        "status": "pending", "created_at": "2026-07-29", "user_name": "Ana",
        "avatar_filename": "ana.png",
    }
    totals_result = MagicMock()
    totals_result.one = MagicMock(return_value=(1, 1000))
    fetch_result = MagicMock()
    fetch_result.fetchall = MagicMock(return_value=[row])
    mock_db.session.execute = AsyncMock(side_effect=[totals_result, fetch_result])

    repository = RefundsRepository(mock_connection)
    refunds, _, _ = await repository.select_refunds(page=1, per_page=10)

    statements = [str(call[0][0]) for call in mock_db.session.execute.call_args_list]
    rows_statement = statements[-1]
    assert "JOIN users" in rows_statement
    assert refunds == [{
        "id": 1, "name": "Almoço", "category": "food", "amount_in_cents": 1000,
        "filename": "receipt.jpg", "payment_filename": None, "status": "pending",
        "created_at": "2026-07-29",
        "user": {"id": 5, "name": "Ana", "avatar_filename": "ana.png"},
    }]


# The count/sum query needs nothing from users, so joining there would be work
# with no result.
@pytest.mark.asyncio
async def test_the_totals_query_does_not_join_users(mock_connection, mock_db):
    repository = RefundsRepository(mock_connection)

    await repository.select_refunds(page=1, per_page=10)

    totals_statement = str(mock_db.session.execute.call_args_list[0][0][0])
    assert "JOIN users" not in totals_statement


@pytest.mark.asyncio
async def test_status_filter_reaches_both_queries(mock_connection, mock_db):
    repository = RefundsRepository(mock_connection)

    await repository.select_refunds(page=1, per_page=10, status="pending")

    statements = [str(call[0][0]) for call in mock_db.session.execute.call_args_list]
    assert all("refunds.status =" in statement for statement in statements)


@pytest.mark.asyncio
async def test_sort_and_order_reach_the_order_by(mock_connection, mock_db):
    repository = RefundsRepository(mock_connection)

    await repository.select_refunds(page=1, per_page=10, sort="amount_in_cents", order="asc")

    rows_statement = str(mock_db.session.execute.call_args_list[-1][0][0])
    assert "ORDER BY refunds.amount_in_cents ASC" in rows_statement


# Only "asc" flips the direction; any other order value (including "desc" itself)
# must fall back to descending, covered here for the explicit "desc" case.
@pytest.mark.asyncio
async def test_sort_and_order_reach_the_order_by_desc(mock_connection, mock_db):
    repository = RefundsRepository(mock_connection)

    await repository.select_refunds(page=1, per_page=10, sort="amount_in_cents", order="desc")

    rows_statement = str(mock_db.session.execute.call_args_list[-1][0][0])
    assert "ORDER BY refunds.amount_in_cents DESC" in rows_statement


# Omitting them must preserve today's behaviour exactly.
@pytest.mark.asyncio
async def test_default_ordering_is_newest_first(mock_connection, mock_db):
    repository = RefundsRepository(mock_connection)

    await repository.select_refunds(page=1, per_page=10)

    rows_statement = str(mock_db.session.execute.call_args_list[-1][0][0])
    assert "ORDER BY refunds.created_at DESC" in rows_statement


# Ties are the norm, not the exception, for sort=status/name/amount_in_cents
# (e.g. every "pending" refund ties). Without a secondary key, PostgreSQL is
# free to order tied rows differently between the LIMIT/OFFSET calls for page
# 1 and page 2, so a row can be duplicated across pages while another is
# skipped entirely. Asserting only the primary ORDER BY (as the tests above
# do) would stay green even if the tiebreaker were deleted — this test pins
# the id DESC tiebreaker's presence, right after the primary key.
@pytest.mark.asyncio
async def test_order_by_appends_id_tiebreaker_for_explicit_sort(mock_connection, mock_db):
    repository = RefundsRepository(mock_connection)

    await repository.select_refunds(page=1, per_page=10, sort="status", order="asc")

    rows_statement = str(mock_db.session.execute.call_args_list[-1][0][0])
    assert "ORDER BY refunds.status ASC, refunds.id DESC" in rows_statement


# The default ordering (no sort/order given) must be just as stable as an
# explicit one: created_at ties are rarer but not impossible (e.g. two refunds
# inserted in the same transaction/millisecond), so the tiebreaker must apply
# here too.
@pytest.mark.asyncio
async def test_order_by_appends_id_tiebreaker_for_default_sort(mock_connection, mock_db):
    repository = RefundsRepository(mock_connection)

    await repository.select_refunds(page=1, per_page=10)

    rows_statement = str(mock_db.session.execute.call_args_list[-1][0][0])
    assert "ORDER BY refunds.created_at DESC, refunds.id DESC" in rows_statement


# An unknown sort name must never reach the query. The validator refuses it
# first, but the repository must not trust that: the dictionary lookup falls
# back to the default instead of interpolating anything.
@pytest.mark.asyncio
async def test_unknown_sort_falls_back_to_the_default_column(mock_connection, mock_db):
    repository = RefundsRepository(mock_connection)

    await repository.select_refunds(page=1, per_page=10, sort="password")

    rows_statement = str(mock_db.session.execute.call_args_list[-1][0][0])
    assert "ORDER BY refunds.created_at DESC" in rows_statement
    assert "password" not in rows_statement


# count_by_status runs a single grouped query and turns each (status, count,
# sum) row into the {status: {"count", "amount_in_cents"}} shape the
# controller relies on to fill in the statuses that had no rows.
@pytest.mark.asyncio
async def test_count_by_status_builds_a_dict_from_the_grouped_rows(mock_connection, mock_db):
    fetch_result = MagicMock()
    fetch_result.fetchall = MagicMock(return_value=[
        ("pending", 2, 3000),
        ("approved", 1, 1000),
    ])
    mock_db.session.execute = AsyncMock(return_value=fetch_result)

    repository = RefundsRepository(mock_connection)
    totals = await repository.count_by_status(1)

    mock_db.session.execute.assert_awaited_once()
    assert totals == {
        "pending": {"count": 2, "amount_in_cents": 3000},
        "approved": {"count": 1, "amount_in_cents": 1000},
    }


# A status group can never have a NULL sum in practice (a group only exists
# if it has rows), but the `or 0` guard is what keeps that true; this test
# pins the guard itself in case a group ever carries a NULL amount.
@pytest.mark.asyncio
async def test_count_by_status_guards_a_null_sum(mock_connection, mock_db):
    fetch_result = MagicMock()
    fetch_result.fetchall = MagicMock(return_value=[("pending", 1, None)])
    mock_db.session.execute = AsyncMock(return_value=fetch_result)

    repository = RefundsRepository(mock_connection)
    totals = await repository.count_by_status(1)

    assert totals == {"pending": {"count": 1, "amount_in_cents": 0}}


# The query must filter by the given user and group by status, otherwise the
# stats would leak other users' refunds or collapse every status into one row.
@pytest.mark.asyncio
async def test_count_by_status_filters_by_user_and_groups_by_status(mock_connection, mock_db):
    fetch_result = MagicMock()
    fetch_result.fetchall = MagicMock(return_value=[])
    mock_db.session.execute = AsyncMock(return_value=fetch_result)

    repository = RefundsRepository(mock_connection)
    await repository.count_by_status(1)

    statement = str(mock_db.session.execute.call_args[0][0])
    assert "refunds.user_id =" in statement
    assert "GROUP BY refunds.status" in statement


# summarize_refunds runs THREE GROUP BY queries in one session; this wires the
# session to answer them in call order so each test can reach any of the three.
def _wire_summary(mock_db, status_rows, category_rows, month_rows):
    results = []
    for rows in (status_rows, category_rows, month_rows):
        result = MagicMock()
        result.fetchall = MagicMock(return_value=rows)
        results.append(result)
    mock_db.session.execute = AsyncMock(side_effect=results)


def _summary_statements(mock_db):
    return [str(call[0][0]) for call in mock_db.session.execute.call_args_list]


@pytest.mark.asyncio
async def test_summarize_refunds_groups_by_status(mock_connection, mock_db):
    _wire_summary(mock_db, [("pending", 2, 3000), ("paid", 1, 1000)], [], [])

    by_status, _, _ = await RefundsRepository(mock_connection).summarize_refunds(
        user_id=None, since=datetime(2026, 1, 1), until=datetime(2027, 1, 1)
    )

    assert by_status == {
        "pending": {"count": 2, "amount_in_cents": 3000},
        "paid": {"count": 1, "amount_in_cents": 1000},
    }


@pytest.mark.asyncio
async def test_summarize_refunds_groups_by_category(mock_connection, mock_db):
    _wire_summary(mock_db, [], [("food", 3, 4500)], [])

    _, by_category, _ = await RefundsRepository(mock_connection).summarize_refunds(
        user_id=None, since=datetime(2026, 1, 1), until=datetime(2027, 1, 1)
    )

    assert by_category == {"food": {"count": 3, "amount_in_cents": 4500}}


# The month rows carry status too: that cross-tab is what feeds the stacked chart,
# and asking for it separately would be a fourth scan of the same rows.
@pytest.mark.asyncio
async def test_summarize_refunds_crosses_month_with_status(mock_connection, mock_db):
    _wire_summary(mock_db, [], [], [(datetime(2026, 7, 1), "paid", 2, 5000)])

    _, _, by_month = await RefundsRepository(mock_connection).summarize_refunds(
        user_id=None, since=datetime(2026, 1, 1), until=datetime(2027, 1, 1)
    )

    assert by_month == [
        {"month": "2026-07", "status": "paid", "count": 2, "amount_in_cents": 5000}
    ]


# A NULL sum cannot happen in a group that has rows, but an all-NULL column would
# produce one — the same guard count_by_status carries.
@pytest.mark.asyncio
async def test_summarize_refunds_guards_a_null_sum(mock_connection, mock_db):
    _wire_summary(mock_db, [("pending", 1, None)], [], [])

    by_status, _, _ = await RefundsRepository(mock_connection).summarize_refunds(
        user_id=None, since=datetime(2026, 1, 1), until=datetime(2027, 1, 1)
    )

    assert by_status["pending"]["amount_in_cents"] == 0


# The window has to be in ALL THREE queries: a status total that ignored it would
# disagree with the months that are supposed to add up to it.
@pytest.mark.asyncio
async def test_summarize_refunds_applies_the_window_to_every_query(mock_connection, mock_db):
    _wire_summary(mock_db, [], [], [])

    await RefundsRepository(mock_connection).summarize_refunds(
        user_id=None, since=datetime(2026, 1, 1), until=datetime(2027, 1, 1)
    )

    statements = _summary_statements(mock_db)
    assert len(statements) == 3
    for statement in statements:
        assert "refunds.created_at >=" in statement


# Same for the user filter — it is the whole point of the scope rule.
@pytest.mark.asyncio
async def test_summarize_refunds_filters_by_user_in_every_query(mock_connection, mock_db):
    _wire_summary(mock_db, [], [], [])

    await RefundsRepository(mock_connection).summarize_refunds(
        user_id=7, since=datetime(2026, 1, 1), until=datetime(2027, 1, 1)
    )

    for statement in _summary_statements(mock_db):
        assert "refunds.user_id =" in statement


@pytest.mark.asyncio
async def test_summarize_refunds_without_a_user_does_not_filter(mock_connection, mock_db):
    _wire_summary(mock_db, [], [], [])

    await RefundsRepository(mock_connection).summarize_refunds(
        user_id=None, since=datetime(2026, 1, 1), until=datetime(2027, 1, 1)
    )

    for statement in _summary_statements(mock_db):
        assert "refunds.user_id =" not in statement


# The stacked chart needs month AND status as grouping keys, in that order.
@pytest.mark.asyncio
async def test_summarize_refunds_groups_the_month_query_by_both_keys(mock_connection, mock_db):
    _wire_summary(mock_db, [], [], [])

    await RefundsRepository(mock_connection).summarize_refunds(
        user_id=None, since=datetime(2026, 1, 1), until=datetime(2027, 1, 1)
    )

    month_statement = _summary_statements(mock_db)[2]
    assert "GROUP BY date_trunc" in month_statement
    assert "refunds.status" in month_statement
    assert "ORDER BY date_trunc" in month_statement


def _wire_years(mock_db, rows):
    result = MagicMock()
    result.fetchall = MagicMock(return_value=rows)
    mock_db.session.execute = AsyncMock(return_value=result)


# EXTRACT returns a numeric type, not an int, so the cast is what keeps a Decimal
# out of the JSON response.
@pytest.mark.asyncio
async def test_available_years_returns_ints(mock_connection, mock_db):
    _wire_years(mock_db, [(2024.0,), (2026.0,)])

    years = await RefundsRepository(mock_connection).available_years(user_id=None)

    assert years == [2024, 2026]
    assert all(isinstance(year, int) for year in years)


@pytest.mark.asyncio
async def test_available_years_groups_and_orders_ascending(mock_connection, mock_db):
    _wire_years(mock_db, [])

    await RefundsRepository(mock_connection).available_years(user_id=None)

    statement = str(mock_db.session.execute.call_args[0][0])
    assert "GROUP BY" in statement
    assert "ORDER BY" in statement and "ASC" in statement


# Scoped like every other aggregate: a standard user must not learn which years
# OTHER people have refunds in.
@pytest.mark.asyncio
async def test_available_years_filters_by_user(mock_connection, mock_db):
    _wire_years(mock_db, [])

    await RefundsRepository(mock_connection).available_years(user_id=7)

    assert "refunds.user_id =" in str(mock_db.session.execute.call_args[0][0])


@pytest.mark.asyncio
async def test_available_years_without_a_user_does_not_filter(mock_connection, mock_db):
    _wire_years(mock_db, [])

    await RefundsRepository(mock_connection).available_years(user_id=None)

    assert "refunds.user_id =" not in str(mock_db.session.execute.call_args[0][0])


# The half-open upper bound: a closed one would need to name the last instant of
# the year, and "23:59:59" silently drops the final second.
@pytest.mark.asyncio
async def test_summarize_refunds_uses_a_half_open_window(mock_connection, mock_db):
    _wire_summary(mock_db, [], [], [])

    await RefundsRepository(mock_connection).summarize_refunds(
        user_id=None, since=datetime(2026, 1, 1), until=datetime(2027, 1, 1)
    )

    for statement in _summary_statements(mock_db):
        assert "refunds.created_at >=" in statement
        assert "refunds.created_at <" in statement
