from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest

# "pending" is intentionally absent: it is a valid refund status but never a
# valid target of a review — nothing goes back to pending (BR-017).
#
# RefundReviewerController.review() relies on this set being exactly these two
# values, paired with an explicit "current_status == 'paid'" guard for the
# terminal state: together they cover every (current, target) pair. The two
# guards are independent, not order-dependent — because this set never
# contains "paid", the "already paid" and "already this status" conditions
# can never both hold, so which one runs first only picks the message.
# Coverage, not order, is what the reasoning below is about. Both halves of
# that reasoning are set-shaped, not fixed by inspection — widening either
# one can reopen a transition the controller does not guard against:
# - Widening this set (e.g. adding "pending") lets a new value collide with a
#   current status the controller does not separately reject.
# - Widening the set of reachable *source* statuses (i.e. adding a way to
#   reach a status other than pending/approved/rejected/paid) needs its own
#   guard in the controller, the same way "paid" needed one.
# Revisit the controller's transition checks before widening either set.
ALLOWED_REVIEW_STATUSES = {"approved", "rejected"}


def refund_reviewer_validator(http_request: HttpRequest) -> None:
    body = http_request.body

    if body.get("status") not in ALLOWED_REVIEW_STATUSES:
        raise HttpUnprocessableEntityError(
            f"Status must be one of: {', '.join(sorted(ALLOWED_REVIEW_STATUSES))}"
        )

    if body["status"] == "rejected" and not str(body.get("reason") or "").strip():
        raise HttpUnprocessableEntityError("Reason is required when rejecting a refund")
