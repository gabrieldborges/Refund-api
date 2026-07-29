import mimetypes
from src.models.repositories.interfaces.users_repository_interface import UsersRepositoryInterface
from src.drivers.interfaces.file_storage_interface import FileStorageInterface
from src.controllers.interfaces.avatar_finder_controller_interface import (
    AvatarFinderControllerInterface,
)
from src.errors.types.http_not_found_error import HttpNotFoundError


class AvatarFinderController(AvatarFinderControllerInterface):
    def __init__(
        self,
        users_repository: UsersRepositoryInterface,
        avatar_storage: FileStorageInterface,
    ) -> None:
        self.__users_repository = users_repository
        self.__avatar_storage = avatar_storage

    async def find(self, user_id: int) -> dict:
        user = await self.__users_repository.select_user_by_id(user_id)

        # Unknown user and user without a picture answer the same 404: neither is
        # an error worth distinguishing, and both mean "there is no avatar here".
        if not user or not user["avatar_filename"]:
            raise HttpNotFoundError("Avatar not found")

        filename = user["avatar_filename"]

        try:
            content = self.__avatar_storage.read(filename)
        except FileNotFoundError as exception:
            raise HttpNotFoundError("Avatar not found") from exception

        return {"content": content, "media_type": self.__media_type(filename)}

    def __media_type(self, filename: str) -> str:
        # Derived from the stored extension, never from a client header.
        guessed, _ = mimetypes.guess_type(filename)
        return guessed or "application/octet-stream"
