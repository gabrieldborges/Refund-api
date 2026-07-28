"""Promotes an existing user to admin.

Registration always creates standard users (BR-003), so there is no way to get
the first admin through the API. Run it from the project root as a module —
plain `python init/promote_admin.py` fails because Python puts the script's
own directory on sys.path, not the working directory, so the `src` package
cannot be found:

    python -m init.promote_admin someone@example.com
"""
import asyncio
import sys
from sqlalchemy import update, select
from src.models.settings.database_connection_handler import database_connection_handler
from src.models.entities.users import Users


async def promote(email: str) -> None:
    async with database_connection_handler.connect() as session:
        found = (await session.execute(select(Users).where(Users.c.email == email))).fetchone()
        if not found:
            print(f"No user with email {email}")
            return

        await session.execute(update(Users).where(Users.c.email == email).values(role="admin"))
        await session.commit()
        print(f"{email} is now an admin")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python -m init.promote_admin <email>")
        sys.exit(1)
    asyncio.run(promote(sys.argv[1]))
