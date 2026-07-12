from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey
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
    Column("created_at", DateTime, server_default=func.now()),
)
