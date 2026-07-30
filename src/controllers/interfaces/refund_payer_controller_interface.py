from abc import ABC, abstractmethod


class RefundPayerControllerInterface(ABC):

    @abstractmethod
    async def pay(
        self,
        refund_id: int,
        payer_id: int,
        role: str,
        filename: str,
        content: bytes,
    ) -> dict:
        pass
