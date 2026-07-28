from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest

# "pending" is intentionally absent: it is a valid refund status but never a
# valid target of a review — nothing goes back to pending (BR-017).
#
# RefundReviewerController.review() relies on this set being exactly these two
# values: its entire transition rule is the single check
# `current_status == status`, which is only complete because every allowed
# target here differs from every possible current status pair except "no
# change". Widening this set (e.g. adding "pending") reopens transitions the
# controller does not guard against — revisit its transition check first.
ALLOWED_REVIEW_STATUSES = {"approved", "rejected"}


def refund_reviewer_validator(http_request: HttpRequest) -> None:
    body = http_request.body

    if body.get("status") not in ALLOWED_REVIEW_STATUSES:
        raise HttpUnprocessableEntityError(
            f"Status must be one of: {', '.join(sorted(ALLOWED_REVIEW_STATUSES))}"
        )

    if body["status"] == "rejected" and not str(body.get("reason") or "").strip():
        raise HttpUnprocessableEntityError("Reason is required when rejecting a refund")
