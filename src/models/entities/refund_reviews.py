from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from src.models.settings.metadata import metadata

# One row per decision taken on a refund. A refund only gets rows here once it
# has been decided, and a decided refund cannot be deleted (BR-015), so a review
# can never be orphaned — which is why there is no ON DELETE CASCADE.
RefundReviews = Table(
    "refund_reviews",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("refund_id", Integer, ForeignKey("refunds.id"), nullable=False),
    Column("reviewer_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("from_status", String, nullable=False),
    Column("to_status", String, nullable=False),
    # Required only when rejecting (BR-017). The database cannot express a
    # conditional NOT NULL without a CHECK constraint, so the rule lives in
    # refund_reviewer_validator.
    Column("reason", String, nullable=True),
    Column("created_at", DateTime, server_default=func.now()),  # pylint: disable=not-callable
)
