# pylint: disable=duplicate-code
# Shares its constructor and "raise 404 when the user is missing" setup with
# AvatarUploaderController; a shared helper would be more machinery than the
# problem needs for a 2-attribute constructor and a 2-line guard.
from src.models.repositories.interfaces.users_repository_interface import UsersRepositoryInterface
from src.drivers.interfaces.file_storage_interface import FileStorageInterface
from src.controllers.interfaces.avatar_remover_controller_interface import (
    AvatarRemoverControllerInterface,
)
from src.errors.types.http_not_found_error import HttpNotFoundError


class AvatarRemoverController(AvatarRemoverControllerInterface):
    def __init__(
        self,
        users_repository: UsersRepositoryInterface,
        avatar_storage: FileStorageInterface,
    ) -> None:
        self.__users_repository = users_repository
        self.__avatar_storage = avatar_storage

    async def remove(self, user_id: int) -> dict:
        user = await self.__users_repository.select_user_by_id(user_id)

        if not user:
            raise HttpNotFoundError("User not found")

        # Clearing the column first, deleting the file after: same ordering rule
        # as the upload — never leave the row pointing at a file that is gone.
        current_filename = user.get("avatar_filename")
        await self.__users_repository.update_avatar(user_id, None)

        if current_filename:
            self.__avatar_storage.delete(current_filename)

        return {
            "type": "User",
            "count": 1,
            "attributes": {"avatar_filename": None},
        }
