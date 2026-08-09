"""Caps how often one client may hit the endpoints that reward hammering.

THE THREAT, from the model done before writing this. Login already answers the
same message for "no such user" and "wrong password", deliberately, so an
attacker cannot learn which emails exist. But nothing stopped ten thousand
attempts a minute against an email they already knew — and bcrypt makes each
attempt expensive for the SERVER, so the login is both a credential target and
a CPU exhaustion target.

Registration is limited for a different reason. It answers "Email already
registered", which is genuinely useful to a person and is exactly what login
refuses to reveal — the anti-enumeration care of one endpoint leaked through
the door next to it. The decision (ADR-009) was to keep the useful message and
make bulk enumeration impractical instead: ten emails is still possible, ten
thousand is not.

IN-MEMORY AND PER PROCESS, on purpose. The item says to reach for Redis "only
if the limit needs to be shared between replicas". There is one process and no
production. The costs of that choice, stated rather than discovered later:
counters reset on restart, and a second replica would double the effective
limit. Both are acceptable now and both stop being acceptable the day this
runs more than once.
"""
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Tuple


class RateLimiter:
    """Fixed number of hits per rolling window, keyed by whatever the caller picks."""

    def __init__(self) -> None:
        self.__hits: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)

    def allow(self, scope: str, identity: str, limit: int, window_seconds: int) -> bool:
        """Records an attempt and says whether it is within the limit.

        A rolling window rather than a fixed clock bucket: with buckets, an
        attacker gets `limit` attempts at 11:59:59 and `limit` more at
        12:00:00, doubling the real allowance at every boundary.
        """
        now = time.monotonic()
        attempts = self.__hits[(scope, identity)]

        # Drop what fell out of the window. Doing it on every call is what
        # keeps this from growing without bound for a key nobody hits again.
        cutoff = now - window_seconds
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()

        if len(attempts) >= limit:
            return False

        attempts.append(now)
        return True

    def reset(self) -> None:
        """Only for tests — a shared counter between them would make order matter."""
        self.__hits.clear()


# One instance for the process, which is the whole point: a limiter per request
# would count to one and never stop anybody.
rate_limiter = RateLimiter()


def client_identity(request) -> str:
    """Who to count against.

    The peer address, NOT an X-Forwarded-For header. Trusting that header
    without a proxy in front means any client can pick its own identity and
    reset its own counter by changing a string. When this project gains a real
    proxy, that is the moment to read the header — and to trust only the hop
    the proxy itself appended.
    """
    return request.client.host if request.client else "unknown"
