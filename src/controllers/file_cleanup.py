"""Best-effort file deletion, shared by every flow that writes or removes files.

A SQL transaction covers the database. It does not cover the filesystem, so
"all or nothing" across the two is not automatic — it has to be written by
hand. This module holds the one piece that every such flow needs: a delete
that cannot make things worse.

Two different situations call it, and the reason it must swallow differs:

- BEFORE the database write is durable, as compensation. The file we just
  wrote has no row pointing at it, so it must go. If this delete itself fails,
  its exception must NOT replace the original failure already propagating —
  the caller is in an `except` block about to re-raise something more
  important.

- AFTER the write is durable, as cleanup. The row is already gone and the file
  is now the only leftover. Letting this failure escape would turn a
  SUCCESSFUL operation into a 500, and the user would retry a deletion that
  already happened and get a 404.

In both cases the outcome of a failure is the same: a file nobody references.
That is worth a log line, because the alternative is finding out by listing the
directory — which is literally how this project discovered seven orphans once.
"""
import logging
from src.drivers.interfaces.file_storage_interface import FileStorageInterface


logger = logging.getLogger(__name__)


def delete_quietly(storage: FileStorageInterface, filename: str, context: str) -> None:
    """Delete a file, never raising.

    `context` says which flow asked, since this module's logger cannot know.
    Item 24 (structured logs) will turn these into searchable fields; until
    then the filename is in the message, which is enough to find the orphan.
    """
    try:
        storage.delete(filename)
    except Exception:
        logger.warning(
            "Could not delete file %s (%s); it is now orphaned on disk",
            filename,
            context,
            exc_info=True,
        )
