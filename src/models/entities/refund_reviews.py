from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from src.models.settings.metadata import metadata

# One row per decision taken on a refund. A refund only gets rows here once it
# has been decided. A review can never be orphaned, but that is not BR-015 by
# itself: it takes the conditional DELETE in refunds_repository.delete_refund
# (which only removes a row still "pending" at the moment the DELETE runs, closing
# the race with a concurrent review) together with the refund_id foreign key
# below — the pair is what makes a decided refund's row un-deletable in practice,
# which is why there is no ON DELETE CASCADE.
#
# NOTE: despite the table name, this is now a status-transition log, not only
# a review log. RefundPayerController (POST /refunds/{id}/payment, UC-012)
# also inserts a row here for the approved -> paid transition, with
# reviewer_id set to whoever paid and reason=None, even though paying is a
# fact rather than a reviewer's decision. Renaming the table would cost a
# migration and a rewrite across the layers that reference it; kept as-is
# and documented in docs/domain-model.md instead.
RefundReviews = Table(
    "refund_reviews",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("refund_id", Integer, ForeignKey("refunds.id"), nullable=False),
    Column("reviewer_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("from_status", String, nullable=False),
    Column("to_status", String, nullable=False),
    # Required only when rejecting (BR-018). The database cannot express a
    # conditional NOT NULL without a CHECK constraint, so the rule lives in
    # refund_reviewer_validator.
    Column("reason", String, nullable=True),
    Column("created_at", DateTime, server_default=func.now()),  # pylint: disable=not-callable
    # An unindexed foreign key makes two things slow: reading a refund's
    # history, which every detail screen does, and deleting the parent, which
    # scans this table looking for children.
    Index("ix_refund_reviews_refund", "refund_id"),
)
