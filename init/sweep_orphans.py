"""Runs the orphan sweep from the command line.

    python -m init.sweep_orphans            # reports, removes nothing
    python -m init.sweep_orphans --apply    # removes what it reported

Same invocation shape as init/promote_admin.py, and for the same reason: run
as a module from the project root, or Python puts this file's own directory on
sys.path and the `src` package cannot be found.
"""
import asyncio
import sys
from src.configs.logging_config import configure_logging
from src.jobs.orphan_sweep import sweep


async def main() -> None:
    configure_logging()
    apply = "--apply" in sys.argv

    results = await sweep(apply=apply)

    total = sum(len(result.orphans) for result in results)
    print()
    for result in results:
        print(
            f"{result.storage:<10} órfãos: {len(result.orphans):<4} "
            f"removidos: {len(result.removed):<4} recentes demais: {result.too_recent}"
        )
    if total and not apply:
        print("\nNada foi removido. Repita com --apply para remover.")


if __name__ == "__main__":
    asyncio.run(main())
