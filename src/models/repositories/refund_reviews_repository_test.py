# pylint: disable=w0621,w0212
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
import pytest
from .refund_reviews_repository import RefundReviewsRepository, RefundReviewsReaderRepository


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


# Fixture for the reader's own-session protocol (see mock_connection in
# conftest.py, which wraps this into the "async with connect() as session" shape).
@pytest.fixture
def mock_db():
    db = MagicMock()
    db.session.execute = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_insert_review_records_the_transition_without_committing(mock_session):
    repository = RefundReviewsRepository(mock_session)

    await repository.insert_review(
        refund_id=1,
        reviewer_id=9,
        from_status="pending",
        to_status="rejected",
        reason="Comprovante ilegível",
    )

    mock_session.execute.assert_awaited_once()
    mock_session.commit.assert_not_awaited()


# An approval carries no reason, and that must reach the database as NULL.
@pytest.mark.asyncio
async def test_insert_review_accepts_a_null_reason(mock_session):
    repository = RefundReviewsRepository(mock_session)

    await repository.insert_review(
        refund_id=1, reviewer_id=9, from_status="pending", to_status="approved", reason=None
    )

    mock_session.execute.assert_awaited_once()


# The reader opens its own session (via mock_connection from conftest.py),
# unlike RefundReviewsRepository above, which is handed one by the UnitOfWork.
@pytest.mark.asyncio
async def test_select_by_refund_id_returns_every_field_the_timeline_needs(
    mock_db, mock_connection
):
    row = MagicMock()
    row._mapping = {  # pylint: disable=protected-access
        "from_status": "pending",
        "to_status": "approved",
        "reason": None,
        "created_at": datetime(2026, 7, 30, 10, 0, 0),
        "reviewer_id": 1,
        "reviewer_name": "Gabriel",
    }
    result = MagicMock()
    result.fetchall = MagicMock(return_value=[row])
    mock_db.session.execute = AsyncMock(return_value=result)
    repository = RefundReviewsReaderRepository(mock_connection)

    reviews = await repository.select_by_refund_id(1)

    # These six keys are exactly what RefundReviewListerController.__serialize
    # reads. Asserting only "a query ran" would let a SELECT that drops or
    # renames a column pass here and fail at runtime — reviewer_name in
    # particular comes from the join, not from refund_reviews.
    assert set(reviews[0]) == {
        "from_status",
        "to_status",
        "reason",
        "created_at",
        "reviewer_id",
        "reviewer_name",
    }
    assert reviews[0]["reviewer_name"] == "Gabriel"
