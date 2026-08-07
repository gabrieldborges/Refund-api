"""Tests for the configuration boundary.

Every test builds its own Settings with _env_file=None so the developer's real
.env cannot influence the result — the point of these tests is what happens
with a given environment, not what happens on one machine.
"""
import pytest
from pydantic import ValidationError
from .settings import Settings


# The whole reason the item exists: a missing signing key must stop the process
# at startup. Before this, the app booted fine and raised "Expected a string
# value" from PyJWT on the first user login.
def test_missing_jwt_secret_aborts_startup(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, database_url="postgresql+asyncpg://a:b@c/d")

    assert "jwt_secret" in str(error.value)


# A missing database URL used to become the literal string "None" and surface as
# a SQLAlchemy complaint about a malformed URL, which named the wrong problem.
def test_missing_database_url_aborts_startup(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, jwt_secret="s")

    assert "database_url" in str(error.value)


# An empty string is not a usable secret, and os.getenv could never tell the
# difference between "unset" and "set to nothing".
def test_empty_jwt_secret_is_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="postgresql+asyncpg://a:b@c/d", jwt_secret="")


# int() on a bad value used to raise a bare ValueError during import, naming no
# variable. Pydantic names the field.
def test_non_numeric_expiration_is_rejected():
    with pytest.raises(ValidationError) as error:
        Settings(
            _env_file=None,
            database_url="postgresql+asyncpg://a:b@c/d",
            jwt_secret="s",
            jwt_expiration_hours="eight hours",
        )

    assert "jwt_expiration_hours" in str(error.value)


# The secret must not be printable by accident. This is what SecretStr buys.
def test_the_secret_does_not_appear_in_the_settings_repr():
    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://a:b@c/d",
        jwt_secret="super-secret-value",
    )

    assert "super-secret-value" not in repr(settings)
    assert settings.jwt_secret.get_secret_value() == "super-secret-value"


# CORS_ORIGINS is written comma-separated by a human, not as JSON.
def test_cors_origins_are_parsed_from_a_comma_separated_string(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example.com, https://b.example.com")

    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://a:b@c/d",
        jwt_secret="s",
    )

    assert settings.cors_origins == ["https://a.example.com", "https://b.example.com"]


# The insecure-default guard: production cannot start with a wildcard origin,
# which would let any site call the API with the browser's credentials.
def test_production_rejects_a_wildcard_cors_origin():
    with pytest.raises(ValidationError) as error:
        Settings(
            _env_file=None,
            database_url="postgresql+asyncpg://a:b@c/d",
            jwt_secret="s",
            environment="production",
            cors_origins=["*"],
        )

    assert "production" in str(error.value)


# The same guard catches the likelier mistake: shipping the development origin.
def test_production_rejects_a_localhost_cors_origin():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url="postgresql+asyncpg://a:b@c/d",
            jwt_secret="s",
            environment="production",
            cors_origins=["http://localhost:5173"],
        )


# The guard must not fire outside production, or local development breaks.
def test_local_environment_keeps_the_localhost_origin():
    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://a:b@c/d",
        jwt_secret="s",
        environment="local",
        cors_origins=["http://localhost:5173"],
    )

    assert settings.cors_origins == ["http://localhost:5173"]


# environment is the only field whose default matters for safety: an unset
# ENVIRONMENT must mean "local", never "production", so the guard above can
# never be skipped by omission. Note the suite itself runs with ENVIRONMENT=test
# (root conftest.py), which is why this test has to clear it.
def test_environment_defaults_to_local_when_unset(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://a:b@c/d",
        jwt_secret="s",
    )

    assert settings.environment == "local"


# A real production origin is accepted — the guard rejects insecure values, not
# the production environment itself.
def test_production_accepts_a_real_origin():
    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://a:b@c/d",
        jwt_secret="s",
        environment="production",
        cors_origins=["https://refund.example.com"],
    )

    assert settings.cors_origins == ["https://refund.example.com"]


# An unknown environment name is a typo, not a new environment.
def test_unknown_environment_is_rejected():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url="postgresql+asyncpg://a:b@c/d",
            jwt_secret="s",
            environment="staging",
        )
