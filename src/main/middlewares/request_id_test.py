from types import SimpleNamespace
import pytest
from .request_id import RequestIdMiddleware, request_id_of


class FakeRequest:
    # SimpleNamespace for `state` on purpose: the middleware assigns
    # request_id dynamically, and a hand-written class would either need the
    # attribute pre-declared (which breaks the "no id at all" test below) or a
    # blanket no-member disable.
    def __init__(self, headers=None):
        self.state = SimpleNamespace()
        self.headers = headers or {}


class FakeResponse:
    def __init__(self):
        self.headers = {}


# Every request gets an id, and the SAME id goes on the response header.
@pytest.mark.asyncio
async def test_the_request_gets_an_id_echoed_in_the_header():
    request = FakeRequest()
    response = FakeResponse()

    async def call_next(_request):
        # The id must exist by the time the route runs, not only afterwards —
        # the exception handlers read it off request.state.
        assert request_id_of(_request) != "unknown"
        return response

    result = await RequestIdMiddleware(app=None).dispatch(request, call_next)

    assert result.headers["X-Request-Id"] == request.state.request_id


# Two requests must not share an id, or correlation is worthless.
@pytest.mark.asyncio
async def test_two_requests_get_different_ids():
    async def call_next(_request):
        return FakeResponse()

    first, second = FakeRequest(), FakeRequest()
    await RequestIdMiddleware(app=None).dispatch(first, call_next)
    await RequestIdMiddleware(app=None).dispatch(second, call_next)

    assert first.state.request_id != second.state.request_id


# An incoming header is IGNORED. Trusting it would let a client choose what
# appears in our logs, which is how log forging works.
@pytest.mark.asyncio
async def test_a_client_supplied_id_is_not_trusted():
    request = FakeRequest(headers={"X-Request-Id": "attacker-chosen"})

    async def call_next(_request):
        return FakeResponse()

    await RequestIdMiddleware(app=None).dispatch(request, call_next)

    assert request.state.request_id != "attacker-chosen"


# The fallback keeps an exception handler from crashing on a request that never
# passed through the middleware.
def test_a_request_without_an_id_reads_as_unknown():
    assert request_id_of(FakeRequest()) == "unknown"
