import math
from typing import Optional


# One place turning a users row into the API's public user shape, for the same
# reason refund_serializer.py exists: two use cases (list and detail) produce
# the SAME shape from the SAME source, and two copies is how one of them keeps
# a field the other dropped.
#
# Here that risk is not cosmetic. The row carries `password` — a bcrypt hash —
# so this function is the boundary that keeps it out of every response. It
# builds a NEW dict and names each field explicitly instead of deleting keys
# from the row: a column added to the users table later stays invisible until
# somebody adds it here on purpose.
def serialize_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        # The client only needs to know whether to show a picture or the
        # initials gradient; it fetches the image from GET /users/{id}/avatar.
        "has_avatar": bool(user["avatar_filename"]),
        "created_at": _iso(user.get("created_at")),
    }


# The envelope around a PAGE of serialized users. Separate from serialize_user
# so the pagination arithmetic has one home, and so the detail response — which
# carries no page metadata — cannot accidentally grow it.
def format_user_list_response(users: list, total: int, page: int, per_page: int) -> dict:
    return {
        "type": "User",
        "count": len(users),
        "total": total,
        "page": page,
        "per_page": per_page,
        # 0 rather than 1 for an empty set, matching how the refund listing
        # already answers: "no pages" is not the same claim as "one empty page".
        "total_pages": math.ceil(total / per_page) if total else 0,
        "attributes": [serialize_user(user) for user in users],
    }


def _iso(created_at) -> Optional[str]:
    return created_at.isoformat() if created_at else None
