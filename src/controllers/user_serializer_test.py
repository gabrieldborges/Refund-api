from datetime import datetime
from .user_serializer import serialize_user, format_user_list_response


# The whole reason this module exists: the hash must never reach a response.
def test_the_password_is_absent_from_the_serialized_user(user_row):
    assert "password" not in serialize_user(user_row())


# Asserting the exact key set, not just the absence of "password": a column
# added to the table later would otherwise flow straight into the API.
def test_only_the_public_fields_are_exposed(user_row):
    assert set(serialize_user(user_row())) == {
        "id",
        "name",
        "email",
        "role",
        "has_avatar",
        "created_at",
    }


# The client only needs to know whether to show a picture or the initials
# gradient, so the filename itself is not client data.
def test_has_avatar_is_a_boolean_derived_from_the_filename(user_row):
    assert serialize_user(user_row(avatar_filename="a.png"))["has_avatar"] is True
    assert serialize_user(user_row(avatar_filename=None))["has_avatar"] is False


# created_at is nullable in the row mapping, and a formatter that assumed a
# datetime would raise instead of answering.
def test_created_at_is_iso_or_none(user_row):
    serialized = serialize_user(user_row(created_at=datetime(2026, 1, 2, 3, 4, 5)))
    assert serialized["created_at"] == "2026-01-02T03:04:05"
    assert serialize_user(user_row(created_at=None))["created_at"] is None


def test_the_list_envelope_carries_the_pagination_metadata(user_row):
    response = format_user_list_response(
        [user_row(), user_row(id=8)], total=25, page=2, per_page=10
    )

    assert response["type"] == "User"
    assert response["count"] == 2
    assert response["total"] == 25
    assert response["page"] == 2
    assert response["per_page"] == 10
    assert response["total_pages"] == 3
    assert len(response["attributes"]) == 2


# total_pages must be 0 rather than 1 for an empty set, matching how the refund
# listing already answers: "no pages" is not the same claim as "one empty page".
def test_total_pages_is_zero_when_there_is_nothing():
    assert format_user_list_response([], total=0, page=1, per_page=10)["total_pages"] == 0


# The envelope serializes every row, so a hash cannot slip through the list path
# either — the listing is the response that exposes the most users at once.
def test_the_list_envelope_serializes_every_row(user_row):
    response = format_user_list_response([user_row(), user_row(id=8)], total=2, page=1, per_page=10)

    for user in response["attributes"]:
        assert "password" not in user
