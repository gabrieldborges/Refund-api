"""Finds files that no database row references, and optionally removes them.

WHY A SWEEP AND NOT A QUEUE (Item 28). The item's own text says not to add a
worker for simple CRUD, and this API has no email, no reports and no file
processing — nothing that needs decoupling from an HTTP response. What it does
have, recorded twice in current-state.md, is orphaned files that no in-process
compensation can reach:

  - a SIGKILL between storage.save() and the commit leaves a file nobody will
    ever reference (Item 21's remainder, explicitly deferred to "varredura
    posterior ou fila (Item 28)");
  - a delete that fails AFTER the commit logs a warning and moves on, because
    breaking a successful response over a leftover file is the worse trade —
    and nothing ever removes what it left.

A queue decouples work from a request. This work belongs to no request at all,
which is why it is a sweep.

THE THREE PROPERTIES THE ITEM DEMANDS OF A JOB:

  idempotent  running it twice removes nothing the second time, because the
              first run already made those files not exist.
  observable  every decision is logged through the handler from Item 24, with
              the filename, so a removal can be traced afterwards.
  safe        a minimum age, and dry-run by default. Together these are what
              keep it from destroying data.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, NamedTuple
from sqlalchemy import select
from src.drivers.storage_factory import build_storage
from src.models.entities.refunds import Refunds
from src.models.entities.users import Users
from src.models.settings.database_connection_handler import database_connection_handler


logger = logging.getLogger(__name__)

# How long a file must have existed before it can be called an orphan.
#
# THIS IS THE WHOLE SAFETY ARGUMENT. A file written two seconds ago, whose
# transaction has not committed yet, is indistinguishable from one nobody will
# ever reference — and deleting it would destroy a receipt in flight. An hour
# is far longer than any request here can take, so anything older than that
# either has its row or never will.
MINIMUM_AGE = timedelta(hours=1)


class SweepResult(NamedTuple):
    storage: str
    orphans: List[str]
    removed: List[str]
    too_recent: int


async def referenced_filenames() -> Dict[str, set]:
    """Every filename the database currently points at, grouped by storage.

    Read in ONE pass before touching storage. Querying per file would be N+1,
    and worse, would widen the window in which a row is written between two
    checks — making a valid file look orphaned because of when we happened to
    look.
    """
    async with database_connection_handler.connect() as session:
        refunds = (await session.execute(select(Refunds.c.filename, Refunds.c.payment_filename))).fetchall()
        avatars = (await session.execute(select(Users.c.avatar_filename))).fetchall()

    return {
        "receipts": {row[0] for row in refunds if row[0]},
        "payments": {row[1] for row in refunds if row[1]},
        "avatars": {row[0] for row in avatars if row[0]},
    }


async def sweep(apply: bool = False, minimum_age: timedelta = MINIMUM_AGE) -> List[SweepResult]:
    """Reports orphans. Removes them only when `apply` is True.

    Dry-run by default because this deletes user data. A job that removes files
    the first time somebody runs it to see what it does is a job that will
    eventually delete something it should not have.
    """
    referenced = await referenced_filenames()
    cutoff = datetime.now(timezone.utc) - minimum_age
    results = []

    for storage_name, in_use in referenced.items():
        storage = build_storage(storage_name)
        orphans, too_recent = [], 0

        for stored in storage.list_files():
            if stored.name in in_use:
                continue
            if stored.modified_at > cutoff:
                # Not an orphan yet — possibly a row still being written.
                too_recent += 1
                continue
            orphans.append(stored.name)

        removed = []
        for name in orphans:
            if apply:
                storage.delete(name)
                removed.append(name)
                logger.warning("Removed orphaned file %s from %s", name, storage_name)
            else:
                logger.info("Orphan found in %s: %s (dry run)", storage_name, name)

        logger.info(
            "Swept %s",
            storage_name,
            extra={
                "storage": storage_name,
                "orphans": len(orphans),
                "removed": len(removed),
                "too_recent": too_recent,
                "applied": apply,
            },
        )
        results.append(SweepResult(storage_name, orphans, removed, too_recent))

    return results
