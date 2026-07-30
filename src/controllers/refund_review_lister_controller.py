# pylint: disable=duplicate-code
# Shares the "404 for both missing and not-yours" guard with the finder
# controllers; the rule is deliberately identical.
from src.models.repositories.interfaces.refunds_repository_interface import RefundsRepositoryInterface
from src.models.repositories.interfaces.refund_reviews_reader_repository_interface import (
    RefundReviewsReaderRepositoryInterface,
)
from src.controllers.interfaces.refund_review_lister_controller_interface import (
    RefundReviewListerControllerInterface,
)
from src.errors.types.http_not_found_error import HttpNotFoundError


class RefundReviewListerController(RefundReviewListerControllerInterface):
    def __init__(
        self,
        refunds_repository: RefundsRepositoryInterface,
        reviews_repository: RefundReviewsReaderRepositoryInterface,
    ) -> None:
        self.__refunds_repository = refunds_repository
        self.__reviews_repository = reviews_repository

    async def list(self, refund_id: int, user_id: int, role: str) -> dict:
        # Authorization is about the REFUND, not the reviews: whoever may see
        # the refund may see how it was decided.
        refund = await self.__refunds_repository.select_refund_by_id(refund_id)

        if not refund or (role != "admin" and refund["user"]["id"] != user_id):
            raise HttpNotFoundError("Refund not found")

        reviews = await self.__reviews_repository.select_by_refund_id(refund_id)

        return {
            "type": "RefundReview",
            "count": len(reviews),
            "attributes": [self.__serialize(review) for review in reviews],
        }

    def __serialize(self, review: dict) -> dict:
        created_at = review.get("created_at")
        return {
            "from_status": review["from_status"],
            "to_status": review["to_status"],
            "reason": review["reason"],
            "reviewer": {"id": review["reviewer_id"], "name": review["reviewer_name"]},
            "created_at": created_at.isoformat() if created_at else None,
        }
