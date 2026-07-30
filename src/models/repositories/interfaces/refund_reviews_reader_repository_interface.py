from abc import ABC, abstractmethod


class RefundReviewsReaderRepositoryInterface(ABC):

    @abstractmethod
    async def select_by_refund_id(self, refund_id: int) -> list[dict]:
        pass
