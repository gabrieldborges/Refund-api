# pylint: disable=w0621,no-member
# w0621: expected with pytest fixtures.
# no-member: request_id is stamped onto the LogRecord by RequestIdFilter at
#            runtime, which is precisely the behaviour these tests assert.
import json
import logging
import sys
import pytest
from fastapi.testclient import TestClient
from src.configs.settings import settings
from src.main.middlewares.request_id import _current_request_id
from src.main.server.server import app
from .logging_config import HumanFormatter, JsonFormatter, RequestIdFilter, configure_logging


def a_record(message="hello", level=logging.INFO, **extra) -> logging.LogRecord:
    record = logging.LogRecord("src.thing", level, "f.py", 1, message, None, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_the_json_line_parses_and_carries_the_core_fields():
    line = JsonFormatter().format(a_record("orphaned receipt", request_id="req-1"))

    payload = json.loads(line)
    assert payload["level"] == "info"
    assert payload["logger"] == "src.thing"
    assert payload["msg"] == "orphaned receipt"
    assert payload["request_id"] == "req-1"
    assert payload["ts"].endswith("Z")


# The point of structured logging: fields, not a sentence. `extra` has to reach
# the output without the formatter knowing the names in advance.
def test_extra_fields_become_top_level_keys():
    line = JsonFormatter().format(a_record("request", status=404, duration_ms=12.5))

    payload = json.loads(line)
    assert payload["status"] == 404
    assert payload["duration_ms"] == 12.5


# uvicorn attaches the same message with ANSI escapes under this name. Treating
# it as a user extra put raw escape sequences in the output.
def test_uvicorns_colour_field_is_not_emitted():
    line = JsonFormatter().format(a_record("Started", color_message="\x1b[32mStarted\x1b[0m"))

    assert "color_message" not in json.loads(line)
    assert "\x1b" not in line


def test_an_exception_is_included_as_text():
    try:
        raise ValueError("boom")
    except ValueError:
        record = a_record("failed")
        record.exc_info = sys.exc_info()

    payload = json.loads(JsonFormatter().format(record))

    assert "ValueError: boom" in payload["exception"]


# A value json cannot serialise must degrade, never make the logger itself
# raise — a logging call that throws turns an incident into two.
def test_an_unserialisable_extra_does_not_break_the_line():
    line = JsonFormatter().format(a_record("odd", thing=object()))

    assert "thing" in json.loads(line)


def test_non_ascii_stays_readable():
    payload = json.loads(JsonFormatter().format(a_record("Almoço")))

    assert payload["msg"] == "Almoço"


# The filter's job is to CONSULT the contextvar, not to invent its own value
# or hardcode one. A record compared against current_request_id() a SECOND
# time (the previous version of this test) proves nothing: both reads see
# whatever the contextvar already holds, so the assertion passes even if the
# filter statement were `record.request_id = "-"` outright — confirmed by
# actually replacing it with that and watching the old version of this test
# pass anyway. Setting a KNOWN, non-default value directly on the
# contextvar — with no middleware and no request involved — isolates the
# filter's own claim: given this value is current, does the filter read it?
# Whether that value SURVIVES an ASGI boundary is a different claim, proved
# separately by test_a_real_requests_access_log_line_matches_its_response_header
# below.
def test_the_filter_stamps_the_current_request_id():
    token = _current_request_id.set("req-known")
    try:
        record = a_record()

        assert RequestIdFilter().filter(record) is True
        assert record.request_id == "req-known"
    finally:
        # Reset rather than leaving the contextvar set — a value it leaked
        # into another test would be indistinguishable from that test's own.
        _current_request_id.reset(token)


def test_outside_a_request_the_id_is_a_dash():
    record = a_record()
    RequestIdFilter().filter(record)

    assert record.request_id == "-"


def test_the_human_format_is_one_line_with_the_short_id():
    line = HumanFormatter().format(a_record("hello", request_id="abcdef12-3456-7890"))

    assert "abcdef12" in line
    assert "hello" in line
    assert "\n" not in line


@pytest.fixture
def restore_logging():
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    yield
    root.handlers, root.level = handlers, level


def test_configuring_twice_does_not_duplicate_handlers(restore_logging):  # pylint: disable=unused-argument
    configure_logging()
    configure_logging()

    assert len(logging.getLogger().handlers) == 1


# Uvicorn's own access line is plain text, has no request_id, and carries the
# RAW query string — which would put a valid signed file URL in the log.
def test_uvicorns_access_logger_is_silenced(restore_logging):  # pylint: disable=unused-argument
    configure_logging()

    access = logging.getLogger("uvicorn.access")
    assert access.handlers == []
    assert access.propagate is False


def test_the_format_follows_the_environment(restore_logging, monkeypatch):  # pylint: disable=unused-argument
    monkeypatch.setattr(settings, "environment", "production")
    configure_logging()
    assert isinstance(logging.getLogger().handlers[0].formatter, JsonFormatter)

    monkeypatch.setattr(settings, "environment", "local")
    configure_logging()
    assert isinstance(logging.getLogger().handlers[0].formatter, HumanFormatter)


# The filter has to be INSTALLED, not merely correct. Removing the addFilter
# call failed nothing until this test existed: the tests above prove the filter
# stamps a record when invoked, which is a different claim from "every line
# that goes through the handler gets stamped".
def test_the_handler_has_the_request_id_filter_installed(restore_logging):  # pylint: disable=unused-argument
    configure_logging()

    handler = logging.getLogger().handlers[0]
    assert any(isinstance(f, RequestIdFilter) for f in handler.filters)


# THE ASSEMBLY, not the part. test_the_filter_stamps_the_current_request_id
# above proves the filter reads whatever the contextvar currently holds — with
# the value set directly, no middleware and no request involved. It says
# nothing about whether the value is still there once it actually needs to be:
# RequestIdMiddleware.dispatch sets it from inside a BaseHTTPMiddleware, and
# the only real reader is a DIFFERENT middleware's log call (AccessLogMiddleware),
# on the other side of that boundary. Only a real request through the fully
# assembled app exercises that path.
#
# capsys, not caplog: caplog attaches its own handler directly to the root
# logger, bypassing every handler-level filter — including the RequestIdFilter
# this test exists to prove is actually installed and reading the right value.
# Capturing real stdout goes through the exact handler configure_logging()
# wires in production, filter included.
def test_a_real_requests_access_log_line_matches_its_response_header(
    restore_logging, capsys
):  # pylint: disable=unused-argument
    # Rebind the handler to the stdout capsys is capturing right now — the one
    # server.py built at import time is still bound to the ORIGINAL sys.stdout,
    # which this fixture cannot see.
    configure_logging()

    with TestClient(app) as client:
        response = client.get("/health")

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    access_lines = [line for line in lines if line.get("msg") == "request"]

    # A pass with nothing captured would be a false pass: it would mean this
    # request never actually went through the installed filter.
    assert access_lines, "expected the access-log line for this request; none was captured"
    assert access_lines[-1]["request_id"] == response.headers["x-request-id"]
