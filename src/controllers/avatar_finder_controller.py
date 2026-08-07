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

        # Item 22: a signed URL instead of the bytes. The authorization checks
        # above still run — the URL is only minted for a caller already
        # entitled to the file, and it expires in FILE_URL_TTL_SECONDS.
        #
        # WHAT CHANGED IN BEHAVIOUR: this no longer reads the file, so "the row
        # survived but the file did not" is no longer a 404 from HERE; it
        # surfaces when the browser follows the URL. The anti-enumeration
        # property that mattered is intact — "does not exist" and "is not
        # yours" are still indistinguishable, because both are refused before a
        # URL exists. Checking existence would cost a HEAD request per URL
        # against S3, which is most of what this item was trying to avoid.
        return {
            "url": self.__avatar_storage.get_url(filename),
            "media_type": self.__media_type(filename),
        }

    def __media_type(self, filename: str) -> str:
        # Derived from the stored extension, never from a client header — the
        # same reason the upload validators refuse to trust Content-Type. Kept
        # in the response even though the bytes now come from elsewhere: the
        # client has to decide between <img> and <object> BEFORE fetching, and
        # a URL carries no type.
        guessed, _ = mimetypes.guess_type(filename)
        return guessed or "application/octet-stream"
