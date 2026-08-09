# pylint: disable=w0621
# w0621: expected with pytest fixtures.
import pytest
from .rate_limit import RateLimiter


@pytest.fixture
def limiter():
    return RateLimiter()


def test_attempts_within_the_limit_are_allowed(limiter):
    assert all(limiter.allow("login", "1.2.3.4", limit=3, window_seconds=60) for _ in range(3))


def test_the_attempt_past_the_limit_is_refused(limiter):
    for _ in range(3):
        limiter.allow("login", "1.2.3.4", limit=3, window_seconds=60)

    assert limiter.allow("login", "1.2.3.4", limit=3, window_seconds=60) is False


# One client hitting its limit must not lock out everybody else — the failure
# mode of a limiter keyed too coarsely.
def test_clients_are_counted_separately(limiter):
    for _ in range(3):
        limiter.allow("login", "1.2.3.4", limit=3, window_seconds=60)

    assert limiter.allow("login", "5.6.7.8", limit=3, window_seconds=60) is True


# Burning the login allowance must not also block registration.
def test_scopes_are_counted_separately(limiter):
    for _ in range(3):
        limiter.allow("login", "1.2.3.4", limit=3, window_seconds=60)

    assert limiter.allow("register", "1.2.3.4", limit=3, window_seconds=60) is True


# THE REASON FOR A ROLLING WINDOW. With fixed clock buckets an attacker gets
# `limit` attempts just before the boundary and `limit` more just after,
# doubling the real allowance every window. Time is moved rather than waited
# on: a test that sleeps for the window would make the suite slower for
# nothing.
def test_the_window_rolls_rather_than_resetting_on_a_boundary(limiter, monkeypatch):
    clock = {"now": 1000.0}
    monkeypatch.setattr("src.main.middlewares.rate_limit.time.monotonic", lambda: clock["now"])

    for _ in range(3):
        limiter.allow("login", "1.2.3.4", limit=3, window_seconds=60)
    assert limiter.allow("login", "1.2.3.4", limit=3, window_seconds=60) is False

    # Half a window later the old attempts have NOT expired.
    clock["now"] += 30
    assert limiter.allow("login", "1.2.3.4", limit=3, window_seconds=60) is False

    # Past the full window they have.
    clock["now"] += 31
    assert limiter.allow("login", "1.2.3.4", limit=3, window_seconds=60) is True


# Old entries have to be dropped, or a key that is hit once and abandoned grows
# forever — a limiter that leaks memory is its own denial of service.
def test_expired_attempts_are_discarded(limiter, monkeypatch):
    clock = {"now": 1000.0}
    monkeypatch.setattr("src.main.middlewares.rate_limit.time.monotonic", lambda: clock["now"])

    for _ in range(100):
        limiter.allow("login", "1.2.3.4", limit=1000, window_seconds=60)

    clock["now"] += 61
    limiter.allow("login", "1.2.3.4", limit=1000, window_seconds=60)

    stored = getattr(limiter, "_RateLimiter__hits")[("login", "1.2.3.4")]
    assert len(stored) == 1
