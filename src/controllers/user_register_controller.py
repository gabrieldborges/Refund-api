from src.models.repositories.interfaces.users_repository_interface import UsersRepositoryInterface
from src.drivers.password_handler import PasswordHandler
from src.controllers.interfaces.user_register_controller_interface import (
    UserRegisterControllerInterface,
)


class UserRegisterController(UserRegisterControllerInterface):
    def __init__(self, users_repository: UsersRepositoryInterface) -> None:
        self.__users_repository = users_repository
        self.__password_handler = PasswordHandler()

    async def register(self, user_data: dict) -> dict:
        hashed_password = self.__password_handler.encrypt_password(user_data["password"])

        user_info = {
            "name": user_data["name"],
            "email": user_data["email"],
            "password": hashed_password,
            "role": "standard",
        }

        user_id = await self.__users_repository.insert_user(user_info)

        return self.__format_response(user_id, user_info)

    def __format_response(self, user_id: int, user_info: dict) -> dict:
        return {
            "type": "User",
            "count": 1,
            "attributes": {
                "id": user_id,
                "name": user_info["name"],
                "email": user_info["email"],
                "role": user_info["role"],
            }
        }
