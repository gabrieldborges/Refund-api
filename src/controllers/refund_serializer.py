from typing import Optional


# One place turning a repository row into the API's refund shape. It exists
# because three use cases — list, detail and create — now produce the SAME shape
# from the SAME source; three copies is how one of them silently keeps a field
# the others dropped.
#
# The review use case deliberately does NOT use this: it reads a different
# repository whose flat row is documented as divergent in UC-007.
def serialize_refund(refund: dict) -> dict:
    user = refund["user"]

    # A new dict rather than a mutation: the caller's row is also what the
    # deleter reads `filename` from to remove the file from disk.
    return {
        "id": refund["id"],
        "name": refund["name"],
        "category": refund["category"],
        "amount_in_cents": refund["amount_in_cents"],
        "status": refund["status"],
        "created_at": _iso(refund.get("created_at")),
        "user": {
            "id": user["id"],
            "name": user["name"],
            # The client only needs to know whether to show a picture or the
            # gradient; it fetches the image from GET /users/{id}/avatar.
            "has_avatar": bool(user["avatar_filename"]),
        },
    }


def _iso(created_at) -> Optional[str]:
    return created_at.isoformat() if created_at else None
