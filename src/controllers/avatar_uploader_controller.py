from src.models.repositories.interfaces.users_repository_interface import UsersRepositoryInterface
from src.drivers.interfaces.file_storage_interface import FileStorageInterface
from src.controllers.interfaces.avatar_uploader_controller_interface import (
    AvatarUploaderControllerInterface,
)
from src.errors.types.http_not_found_error import HttpNotFoundError


class AvatarUploaderController(AvatarUploaderControllerInterface):
    def __init__(
        self,
        users_repository: UsersRepositoryInterface,
        avatar_storage: FileStorageInterface,
    ) -> None:
        self.__users_repository = users_repository
        self.__avatar_storage = avatar_storage

    async def upload(self, user_id: int, original_filename: str, content: bytes) -> dict:
        user = await self.__users_repository.select_user_by_id(user_id)

        if not user:
            raise HttpNotFoundError("User not found")

        new_filename = self.__avatar_storage.save(original_filename, content)
        await self.__users_repository.update_avatar(user_id, new_filename)

        # The old file is deleted LAST, on purpose. Deleting it before the row
        # points at the new one would leave the user with no picture at all if
        # the update failed — losing data instead of leaking a file.
        previous_filename = user.get("avatar_filename")
        if previous_filename:
            self.__avatar_storage.delete(previous_filename)

        return self.__format_response(new_filename)

    def __format_response(self, avatar_filename: str) -> dict:
        return {
            "type": "User",
            "count": 1,
            "attributes": {"avatar_filename": avatar_filename},
        }
