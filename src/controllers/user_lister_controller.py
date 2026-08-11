from typing import Optional
from src.models.repositories.interfaces.users_repository_interface import (
    UsersRepositoryInterface,
)
from src.controllers.interfaces.user_lister_controller_interface import (
    UserListerControllerInterface,
)
from src.controllers.user_serializer import format_user_list_response
from src.errors.types.http_forbidden_error import HttpForbiddenError


class UserListerController(UserListerControllerInterface):
    def __init__(self, users_repository: UsersRepositoryInterface) -> None:
        self.__users_repository = users_repository

    async def list(
        self, page: int, per_page: int, role: str, name: Optional[str] = None
    ) -> dict:
        # Refused BEFORE touching the database, the same idiom the reviewer and
        # payer controllers use. Refusing after querying would run work for a
        # request that was never allowed, and the response time would still tell
        # an outsider roughly how many users exist.
        #
        # 403 here and not 404 (BR-025): a listing reveals nothing about any
        # particular id, so it can be honest about the missing permission. The
        # single-user lookup answers 404 precisely because a 403 there would
        # confirm that the id exists.
        if role != "admin":
            raise HttpForbiddenError("Only administrators can list users")

        users, total = await self.__users_repository.select_users(
            page=page, per_page=per_page, name=name
        )

        return format_user_list_response(users, total, page, per_page)
