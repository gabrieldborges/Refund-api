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
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


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

    # Anything the logging module accepts. INFO by default because the access
    # log lives at that level: DEBUG would add library noise, WARNING would
    # hide every successful request.
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

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

    # Where uploaded files live. "local" keeps them on the instance's disk,
    # which is fine for development and fatal on a PaaS with an ephemeral
    # filesystem — every receipt would evaporate on redeploy, silently.
    storage_backend: Literal["local", "s3"] = "local"

    s3_bucket: str = ""
    # Empty means real AWS. Point it at MinIO (docker-compose.yml) or any other
    # S3-compatible provider — R2, B2, Spaces — and boto3 cannot tell the
    # difference.
    s3_endpoint_url: str = ""
    s3_region: str = "us-east-1"
    s3_access_key_id: str = ""
    s3_secret_access_key: SecretStr = SecretStr("")

    # How long a signed file URL stays valid. Short on purpose: a signed URL
    # freezes the authorization decision at the moment it is generated, unlike
    # the authenticated route it replaces, which re-checked on every request.
    # Five minutes is long enough to render a page and short enough that a
    # copied link stops working before it can be passed around.
    file_url_ttl_seconds: Annotated[int, Field(gt=0)] = 300

    # --- Abuse controls (Item 27) --------------------------------------
    #
    # In-memory, per process, on purpose. The item says to reach for Redis
    # "somente se o limite precisar ser compartilhado entre réplicas", and
    # there is one process and no production. A shared store would be
    # infrastructure bought for a problem nobody has.
    login_rate_limit: Annotated[int, Field(gt=0)] = 10
    register_rate_limit: Annotated[int, Field(gt=0)] = 5
    rate_limit_window_seconds: Annotated[int, Field(gt=0)] = 60

    # Rejected BEFORE the body is buffered. max_file_size_bytes is checked by
    # the validators, but by then the whole upload is already in memory — this
    # is the ceiling that keeps it from getting there. Larger than the 4MB file
    # limit because a multipart body carries the file plus its fields.
    max_request_body_bytes: Annotated[int, Field(gt=0)] = 8 * 1024 * 1024

    # The origin the API is reachable at, used to build local signed URLs. Only
    # matters for storage_backend="local" — with S3 the URL comes from the
    # provider.
    public_base_url: str = "http://localhost:3333"

    # NoDecode turns off pydantic-settings' default handling for complex types,
    # which is to run json.loads on the raw string. Without it, CORS_ORIGINS
    # would have to be written as JSON (["http://a", "http://b"]) in a .env
    # file — valid, but a trap for a human editing it. With it, the validator
    # below owns the parsing and the file stays comma-separated.
    cors_origins: Annotated[List[str], NoDecode] = ["http://localhost:5173"]

    @field_validator("database_url")
    @classmethod
    def check_the_url_can_be_parsed(cls, value: str) -> str:
        """Parse the URL here so a malformed one cannot reach a running app.

        This exists because the engine is built lazily (see
        database_connection_handler.build_engine). Creating the engine used to
        happen at import and was, incidentally, the only thing that ever
        parsed this string — deferring it to the first connection would have
        moved a malformed URL from "the process refuses to start" to "the app
        boots and 500s on the first request", which is the exact failure mode
        this whole item exists to remove.

        make_url only parses. It builds no pool and touches no network, so the
        check stays cheap and stays at the configuration boundary, where every
        other value is already validated.
        """
        try:
            make_url(value)
        except ArgumentError as error:
            raise ValueError(f"is not a valid SQLAlchemy URL: {error}") from error
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_comma_separated_origins(cls, value):
        """Accept "http://a,http://b" from the environment, a list from code."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def require_s3_configuration_when_selected(self) -> "Settings":
        """Fail at startup rather than on the first upload.

        Choosing the s3 backend without a bucket or credentials is exactly the
        kind of half-configured environment this whole settings layer exists to
        reject: the application would boot healthy and lose the first file
        somebody uploaded.
        """
        if self.storage_backend != "s3":
            return self

        missing = [
            name
            for name, value in (
                ("S3_BUCKET", self.s3_bucket),
                ("S3_ACCESS_KEY_ID", self.s3_access_key_id),
                ("S3_SECRET_ACCESS_KEY", self.s3_secret_access_key.get_secret_value()),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                f"storage_backend is 's3' but {', '.join(missing)} "
                "is not set. Set them, or use STORAGE_BACKEND=local."
            )
        return self

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
