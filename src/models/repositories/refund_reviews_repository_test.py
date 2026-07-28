# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from .refund_reviews_repository import RefundReviewsRepository


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


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
