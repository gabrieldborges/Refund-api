# pylint: disable=w0621
import logging
from types import SimpleNamespace
import pytest
from .access_log import AccessLogMiddleware, mask_query


class FakeUrl:
    def __init__(self, path="/refunds", query=""):
        self.path = path
        self.query = query


class FakeRequest:
    def __init__(self, method="GET", path="/refunds", query=""):
        self.method = method
        self.url = FakeUrl(path, query)
        self.state = SimpleNamespace()


# THE LEAK THIS EXISTS TO PREVENT. Item 22 serves files through signed URLs; a
# log that records the raw query keeps a working capability, and the log
# outlives the token's five minutes by years.
def test_a_signed_url_token_is_masked():
    masked = mask_query("token=eyJhbGciOiJIUzI1NiJ9.PAYLOAD.SIGNATURE")

    assert "PAYLOAD" not in masked
    assert masked == "token=***"


# The mask must read as *** rather than %2A%2A%2A — noticed in the real output.
def test_the_mask_is_not_percent_encoded():
    assert mask_query("token=abc") == "token=***"


# The NAME survives: "a token was present" is useful when reading a log, the
# value is what must not be.
def test_other_parameters_are_kept_intact():
    assert mask_query("page=2&token=abc&name=Ana") == "page=2&token=***&name=Ana"


def test_an_empty_query_stays_empty():
    assert mask_query("") == ""


# `?token=` with no value must still show up, or the line quietly loses the
# fact that the parameter was sent at all.
def test_a_blank_token_is_still_reported():
    assert mask_query("token=") == "token=***"


def test_masking_is_case_insensitive_on_the_name():
    assert mask_query("TOKEN=abc") == "TOKEN=***"


@pytest.fixture
def captured(caplog):
    caplog.set_level(logging.INFO, logger="api.access")
    return caplog


@pytest.mark.asyncio
async def test_a_request_produces_one_line_with_the_essentials(captured):
    async def call_next(_request):
        return SimpleNamespace(status_code=200)

    await AccessLogMiddleware(app=None).dispatch(FakeRequest(), call_next)

    record = captured.records[-1]
    assert record.message == "request"
    assert record.method == "GET"
    assert record.path == "/refunds"
    assert record.status == 200
    assert isinstance(record.duration_ms, float)


# The requests that matter most must not be the ones missing from the log.
@pytest.mark.asyncio
async def test_a_failing_request_is_still_logged_as_500(captured):
    async def call_next(_request):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await AccessLogMiddleware(app=None).dispatch(FakeRequest(), call_next)

    assert captured.records[-1].status == 500


@pytest.mark.asyncio
async def test_the_logged_query_is_masked(captured):
    async def call_next(_request):
        return SimpleNamespace(status_code=200)

    request = FakeRequest(path="/files/receipts/a.png", query="token=SECRET")
    await AccessLogMiddleware(app=None).dispatch(request, call_next)

    assert "SECRET" not in captured.text
    assert captured.records[-1].query == "token=***"
