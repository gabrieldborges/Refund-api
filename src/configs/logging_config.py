"""Logging setup: one place decides format, level and destination.

Before this, the project had exactly one log call (file_cleanup.py, Item 21)
and NO configuration, so it fell through to Python's `lastResort` handler: no
timestamp, no level, no logger name, and anything below WARNING discarded in
silence. Measured, not assumed.

Structured logging means fields instead of a sentence — the difference between
grepping for text and filtering on `status=500 AND request_id=...`.

No dependency added. A JSON formatter is about twenty lines, and this project
has already declined a dependency twice for less (httpx, python-json-logger
would be a third).
"""
import json
import logging
import sys
from datetime import datetime, timezone
from src.configs.settings import settings
from src.main.middlewares.request_id import current_request_id


# Attributes every LogRecord carries. Anything NOT here came from a
# `logger.info(..., extra={...})` call and belongs in the output — that is what
# makes `extra` work without this formatter knowing the field names in advance.
_STANDARD_RECORD_FIELDS = {
    "args", "asctime", "created", "exc_info", "exc_text", "filename",
    "funcName", "levelname", "levelno", "lineno", "module", "msecs",
    "message", "msg", "name", "pathname", "process", "processName",
    "relativeCreated", "stack_info", "thread", "threadName", "taskName",
    "request_id",
    # uvicorn attaches this to its own records: the same message with ANSI
    # colour escapes in it. Treating it as a user-supplied extra put raw escape
    # sequences in the output — seen in the real log, not predicted.
    "color_message",
}


class RequestIdFilter(logging.Filter):
    """Puts the current request's id on every record.

    A filter rather than something each call site remembers to pass: a log line
    that only sometimes carries the correlation id is barely better than none,
    because you cannot tell "different request" from "someone forgot".
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = current_request_id()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }

        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_FIELDS and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # ensure_ascii=False so "Almoço" stays readable instead of becoming
        # escape sequences; default=str so an unexpected object degrades to its
        # repr rather than making the logger itself raise.
        return json.dumps(payload, ensure_ascii=False, default=str)


class HumanFormatter(logging.Formatter):
    """One readable line, for developing against a terminal.

    The trade is stated in ADR-006: what you read locally is not byte-for-byte
    what a log tool sees in production. A test asserts the JSON shape so the
    format that actually ships is the one under test.
    """

    def format(self, record: logging.LogRecord) -> str:
        stamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        request_id = getattr(record, "request_id", "-")
        short_id = request_id[:8] if request_id != "-" else "-"
        line = f"{stamp} {record.levelname:<7} [{short_id}] {record.name}: {record.getMessage()}"

        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_RECORD_FIELDS and not key.startswith("_")
        }
        if extras:
            line += " " + " ".join(f"{k}={v}" for k, v in extras.items())
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def configure_logging() -> None:
    """Install the handler. Safe to call more than once."""
    formatter = HumanFormatter() if settings.environment == "local" else JsonFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    # Replacing rather than appending: calling this twice (reload, a test)
    # would otherwise duplicate every line once per call.
    root.handlers = [handler]
    root.setLevel(settings.log_level)

    # Uvicorn prints its own access line — plain text, no request_id, and the
    # RAW query string, which would put a valid signed file URL (Item 22) in
    # the log. Silenced HERE rather than through run.py's uvicorn options so it
    # also applies when someone starts the server with `uvicorn ...` directly,
    # which is what CI and most editors do.
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers = []
    access_logger.propagate = False

    # Uvicorn's startup/shutdown lines are useful; route them through our
    # handler instead of its own so everything is one format.
    for name in ("uvicorn", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True
