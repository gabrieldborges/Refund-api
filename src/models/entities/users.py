from sqlalchemy import Table, Column, Integer, String, DateTime
from sqlalchemy.sql import func
from src.models.settings.metadata import metadata

Users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False),
    Column("email", String, nullable=False, unique=True),
    Column("password", String, nullable=False),
    Column("role", String, nullable=False, server_default="standard"),
    # Nullable is the normal state, not a failure: the product's default avatar
    # is a gradient over the user's initials, and a picture is opt-in.
    Column("avatar_filename", String, nullable=True),
    Column("created_at", DateTime, server_default=func.now()),  # pylint: disable=not-callable
)
