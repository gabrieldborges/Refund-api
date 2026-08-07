"""Test-environment configuration, applied before any test module is imported.

pytest imports the rootdir conftest.py first, which is the only hook that runs
early enough: src/configs/settings.py builds its Settings instance at import
time, so the variables have to exist before the first test module pulls that
module in.

These values USED TO LIVE IN .github/workflows/ci.yml, where a comment
correctly called them a symptom. They belong here instead — they are test
configuration, not deployment configuration, and putting them in the repository
means the suite also runs for someone who cloned the project and has no .env.

The values are deliberately fake and nothing connects to them: every test mocks
its repositories. Because environment variables take precedence over .env in
pydantic-settings, they also apply on a machine that HAS a real .env — which is
a safety property, not a side effect: the suite cannot reach the real database
by accident.

setdefault, not assignment: an explicitly exported variable still wins, so a
future integration test can point at a throwaway PostgreSQL (Item 19) without
editing this file.
"""
import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
# At least 32 bytes: PyJWT emits InsecureKeyLengthWarning below that, which
# would put ten warnings in every suite run for no reason.
os.environ.setdefault("JWT_SECRET", "test-only-not-a-real-secret-0123456789")
