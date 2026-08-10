from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey, Index, text
from sqlalchemy.sql import func
from src.models.settings.metadata import metadata

Refunds = Table(
    "refunds",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("name", String, nullable=False),
    Column("category", String, nullable=False),
    Column("amount_in_cents", Integer, nullable=False),
    Column("filename", String, nullable=False),
    # server_default matters beyond new rows: it is what lets the ALTER TABLE in
    # the migration backfill the rows that already exist without violating the
    # NOT NULL constraint.
    Column("status", String, nullable=False, server_default="pending"),
    # Nullable on purpose: only a paid refund has one. BR-022 makes the file
    # mandatory to REACH "paid", which is what gives the invariant
    # status == "paid" <=> this column is filled. Nothing in the database
    # enforces that pairing — it lives in RefundPayerController.
    Column("payment_filename", String, nullable=True),
    Column("created_at", DateTime, server_default=func.now()),  # pylint: disable=not-callable
    # Declared here as well as in the migration so autogenerate does not see a
    # difference between the entities and the database — the check that the
    # Item 19 suite runs.
    #
    # (user_id, created_at DESC) rather than user_id alone: every listing
    # filters by owner AND orders by date, so one index serves the lookup and
    # the sort. Measured before adding (Item 31): no effect at today's 80 rows,
    # 4x at 50,000.
    Index("ix_refunds_user_created", "user_id", text("created_at DESC")),
)
