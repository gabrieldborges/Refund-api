# Tests the connection handler's concurrency safety. The previous design stored
# the session on a shared instance (self.session), so two concurrent requests
# overwrote each other's session — causing asyncpg "operation in progress"
# errors and leaked connections. connect() must give each caller its own session.
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from .database_connection_handler import DatabaseConnectionHandler


# connect() must open a session, hand it to the caller, and close it on exit.
@pytest.mark.asyncio
async def test_connect_yields_a_session_and_closes_it():
    session = MagicMock()
    session.close = AsyncMock()

    with patch(
        "src.models.settings.database_connection_handler.async_session",
        return_value=session,
    ):
        handler = DatabaseConnectionHandler()
        async with handler.connect() as active_session:
            assert active_session is session

        session.close.assert_awaited_once()


# Two overlapping connect() blocks must use independent sessions, even from the
# same handler instance. This is the actual bug: with a shared self.session the
# second block would clobber the first.
@pytest.mark.asyncio
async def test_concurrent_connects_use_independent_sessions():
    sessions = [MagicMock(), MagicMock()]
    for session in sessions:
        session.close = AsyncMock()

    with patch(
        "src.models.settings.database_connection_handler.async_session",
        side_effect=sessions,
    ):
        handler = DatabaseConnectionHandler()
        seen = []

        async def use_connection():
            async with handler.connect() as active_session:
                seen.append(active_session)
                # Yield control so both blocks are open at the same time.
                await asyncio.sleep(0)

        await asyncio.gather(use_connection(), use_connection())

        # Each concurrent block saw its own session, and both were closed.
        assert seen[0] is not seen[1]
        for session in sessions:
            session.close.assert_awaited_once()
