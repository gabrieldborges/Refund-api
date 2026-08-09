# pylint: disable=w0621,no-member
# w0621: expected with pytest fixtures.
# no-member: request_id is stamped onto the LogRecord by RequestIdFilter at
#            runtime, which is precisely the behaviour these tests assert.
import json
import logging
import sys
import pytest
from src.configs.settings import settings
from src.main.middlewares.request_id import current_request_id
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


# The filter is what guarantees EVERY line carries the id — a line that only
# sometimes has it cannot be told apart from one where somebody forgot.
def test_the_filter_stamps_the_current_request_id():
    record = a_record()

    assert RequestIdFilter().filter(record) is True
    assert record.request_id == current_request_id()


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
