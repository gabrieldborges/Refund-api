"""Typed, validated application configuration.

Configuration is external input, exactly like a request body. This module gives
it the same treatment the validators already give HTTP payloads: declared
types, declared requiredness, and a failure that happens ONCE, at startup, with
a message naming the offending variable.

What this replaces: three plain dicts of os.getenv calls. Their failure modes
were all late and all misleading — a missing JWT_SECRET let the app boot
healthy and produced "TypeError: Expected a string value" on the first user
login; a missing DATABASE_URL became the literal string "None" and produced a
SQLAlchemy error about a malformed URL rather than about a missing variable.
"""
from typing import List, Literal
from typing_extensions import Annotated
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Every externally supplied value the API needs, validated on construction.

    Field names map to environment variables case-insensitively, so `database_url`
    reads DATABASE_URL. A field without a default is REQUIRED: leaving it unset
    aborts startup instead of poisoning a dict with None.
    """

    # Environment variables win over the .env file, which is what lets the test
    # suite (see the root conftest.py) pin fake values without editing anyone's
    # .env. extra="ignore" keeps unrelated variables in the real environment
    # from failing the whole application.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["local", "test", "production"] = "local"

    # Constraints go inside Annotated rather than in a `= Field(...)` default.
    # Both forms behave identically at runtime, but the assignment form makes
    # static analysis infer the attribute as FieldInfo instead of the declared
    # type — pylint reported "Instance of 'FieldInfo' has no get_secret_value
    # member" for every call site until this changed.
    database_url: Annotated[str, Field(min_length=1)]

    # SecretStr, not str: its repr() prints "**********", so a traceback or a
    # log line that happens to include the settings object cannot leak the
    # signing key. Reading it back is deliberately explicit —
    # .get_secret_value() marks the one place that genuinely needs the value.
    jwt_secret: Annotated[SecretStr, Field(min_length=1)]
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: Annotated[int, Field(gt=0)] = 8

    upload_dir: str = "uploads/receipts"
    avatar_dir: str = "uploads/avatars"
    payment_dir: str = "uploads/payment_receipts"
    max_file_size_bytes: int = 4 * 1024 * 1024

    # NoDecode turns off pydantic-settings' default handling for complex types,
    # which is to run json.loads on the raw string. Without it, CORS_ORIGINS
    # would have to be written as JSON (["http://a", "http://b"]) in a .env
    # file — valid, but a trap for a human editing it. With it, the validator
    # below owns the parsing and the file stays comma-separated.
    cors_origins: Annotated[List[str], NoDecode] = ["http://localhost:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_comma_separated_origins(cls, value):
        """Accept "http://a,http://b" from the environment, a list from code."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def reject_insecure_cors_in_production(self) -> "Settings":
        """Make an insecure production default impossible by construction.

        A wildcard origin lets any site on the internet call the API with the
        browser's credentials; a localhost origin in production is always a
        leftover from development. Both are mistakes that would otherwise be
        found by an incident, not by a startup error.
        """
        if self.environment != "production":
            return self

        for origin in self.cors_origins:
            if origin == "*" or "localhost" in origin or "127.0.0.1" in origin:
                raise ValueError(
                    f"cors_origins contains {origin!r}, which is not allowed when "
                    "environment is 'production'. Set CORS_ORIGINS to the real "
                    "frontend origin(s), comma-separated."
                )
        return self


# Built once, at import time, on purpose: this is the "fail fast" half of the
# item. An invalid or incomplete environment must stop the process here rather
# than surface later as a 500 on a user's first login.
settings = Settings()
