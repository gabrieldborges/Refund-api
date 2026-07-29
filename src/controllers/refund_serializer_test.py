from datetime import datetime
from .refund_serializer import serialize_refund


def repository_row(**overrides) -> dict:
    row = {
        "id": 58,
        "name": "Estacionamento",
        "category": "transport",
        "amount_in_cents": 4500,
        "filename": "606771d4-abc.jpg",
        "status": "approved",
        "created_at": datetime(2026, 7, 28, 17, 0, 25),
        "user": {"id": 13, "name": "Validacao Visual", "avatar_filename": "foto.png"},
    }
    row.update(overrides)
    return row


# The stored filename is internal: the client fetches the file from
# GET /refunds/{id}/receipt and has no use for the storage name.
def test_the_storage_filename_is_not_exposed():
    assert "filename" not in serialize_refund(repository_row())


def test_avatar_filename_becomes_a_boolean():
    serialized = serialize_refund(repository_row())

    assert serialized["user"]["has_avatar"] is True
    assert "avatar_filename" not in serialized["user"]


# None means "no picture, show the gradient" — it must become False, not vanish.
def test_a_user_without_a_picture_has_avatar_false():
    row = repository_row(user={"id": 13, "name": "Ana", "avatar_filename": None})

    assert serialize_refund(row)["user"]["has_avatar"] is False


def test_created_at_becomes_an_iso_string():
    assert serialize_refund(repository_row())["created_at"] == "2026-07-28T17:00:25"


def test_a_null_created_at_survives_as_none():
    assert serialize_refund(repository_row(created_at=None))["created_at"] is None


# Everything else passes through untouched.
def test_the_remaining_fields_are_preserved():
    serialized = serialize_refund(repository_row())

    assert serialized["id"] == 58
    assert serialized["name"] == "Estacionamento"
    assert serialized["category"] == "transport"
    assert serialized["amount_in_cents"] == 4500
    assert serialized["status"] == "approved"
    assert serialized["user"]["id"] == 13
    assert serialized["user"]["name"] == "Validacao Visual"


# The serializer must not mutate what the repository handed it: the deleter
# reads `filename` off that same dict to remove the file from disk.
def test_the_input_row_is_not_mutated():
    row = repository_row()

    serialize_refund(row)

    assert row["filename"] == "606771d4-abc.jpg"
    assert row["user"]["avatar_filename"] == "foto.png"
