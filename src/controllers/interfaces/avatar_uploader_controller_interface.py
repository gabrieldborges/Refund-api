from abc import ABC, abstractmethod


class AvatarUploaderControllerInterface(ABC):

    @abstractmethod
    async def upload(self, user_id: int, original_filename: str, content: bytes) -> dict:
        pass
