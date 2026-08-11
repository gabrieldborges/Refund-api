from src.models.repositories.interfaces.users_repository_interface import (
    UsersRepositoryInterface,
)
from src.controllers.interfaces.user_finder_controller_interface import (
    UserFinderControllerInterface,
)
from src.controllers.user_serializer import serialize_user
from src.errors.types.http_not_found_error import HttpNotFoundError


class UserFinderController(UserFinderControllerInterface):
    def __init__(self, users_repository: UsersRepositoryInterface) -> None:
        self.__users_repository = users_repository

    async def find(self, user_id: int, role: str) -> dict:
        # 404 and not 403, the same choice refund_stats_finder_controller.py:19
        # makes: answering 403 would confirm that this id exists to somebody who
        # is not allowed to know. Checked before the query for the same reason as
        # the lister — no work for a request that was never allowed.
        if role != "admin":
            raise HttpNotFoundError("User not found")

        user = await self.__users_repository.select_user_by_id(user_id)

        # Deliberately the SAME message as the branch above, so "you may not see
        # this" and "this does not exist" are indistinguishable from outside. A
        # different message here would undo the reason for answering 404 at all.
        if not user:
            raise HttpNotFoundError("User not found")

        return {"type": "User", "count": 1, "attributes": serialize_user(user)}
