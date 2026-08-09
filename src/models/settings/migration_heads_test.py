"""Migration checks that need no database, and therefore run in the fast suite.

The Item 19 suite already verifies migrations properly — upgrade, downgrade
revision by revision, and no pending autogenerate diff — but all of that needs
PostgreSQL running. These two checks read only the versions directory, so they
run on every push in the cheap job, which is where a mistake this common
should be caught.
"""
from alembic.config import Config
from alembic.script import ScriptDirectory


def script_directory() -> ScriptDirectory:
    # No URL is set: ScriptDirectory reads alembic/versions from disk and never
    # opens a connection, which is the whole point of putting these here.
    return ScriptDirectory.from_config(Config("alembic.ini"))


# THE MOST COMMON ALEMBIC MISTAKE, and one nothing here would have caught. Two
# migrations authored in parallel both claim the same parent, so the history
# forks and `alembic upgrade head` fails with "Multiple head revisions are
# present". Nobody finds out until someone tries to apply them — which, with no
# production, would be the very first deploy.
def test_the_migration_history_has_a_single_head():
    heads = script_directory().get_heads()

    assert len(heads) == 1, (
        f"Alembic history has forked into {len(heads)} heads: {heads}. "
        "Merge them with `alembic merge` before this can be applied."
    )


# A revision that names a parent nobody wrote leaves an unreachable chain:
# upgrade walks the history and never arrives.
def test_every_revision_points_at_a_parent_that_exists():
    directory = script_directory()
    known = {revision.revision for revision in directory.walk_revisions()}

    for revision in directory.walk_revisions():
        if revision.down_revision is None:
            continue
        parents = (
            revision.down_revision
            if isinstance(revision.down_revision, tuple)
            else (revision.down_revision,)
        )
        for parent in parents:
            assert parent in known, (
                f"Revision {revision.revision} points at {parent}, which does not exist."
            )
