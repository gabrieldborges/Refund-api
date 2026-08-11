"""Fixtures shared by the controller tests in this directory.

A users row appeared verbatim in user_lister_controller_test and
user_finder_controller_test, and pylint's R0801 caught it. Hoisting it here is
the remedy AGENTS.md prescribes for fixtures repeated across tests of the same
directory — and it also means the row's shape has one definition, so a column
added to the table does not have to be remembered in two places.
"""
import pytest


@pytest.fixture
def user_row():
    """A users row exactly as the repository returns it — hash included.

    The `password` key is here on purpose: these tests assert that the
    serializer keeps it out of the response, so a fixture without it would make
    them pass for the wrong reason.
    """

    def build(**overrides):
        row = {
            "id": 7,
            "name": "Ana",
            "email": "ana@example.com",
            "password": "hashed",
            "role": "standard",
            "avatar_filename": None,
            "created_at": None,
        }
        row.update(overrides)
        return row

    return build
