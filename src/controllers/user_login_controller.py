from src.models.repositories.interfaces.users_repository_interface import UsersRepositoryInterface
from src.drivers.password_handler import PasswordHandler
from src.drivers.jwt_handler import JwtHandler
from src.controllers.interfaces.user_login_controller_interface import UserLoginControllerInterface
from src.errors.types.http_bad_request_error import HttpBadRequestError


class UserLoginController(UserLoginControllerInterface):
    def __init__(self, users_repository: UsersRepositoryInterface) -> None:
        self.__users_repository = users_repository
        self.__password_handler = PasswordHandler()
        self.__jwt_handler = JwtHandler()

    async def login(self, credentials: dict) -> dict:
        user = await self.__users_repository.select_user_by_email(credentials["email"])

        # Mensagem igual para "usuário não existe" e "senha errada",
        # pra não deixar um atacante descobrir quais emails estão cadastrados.
        if not user or not self.__password_handler.check_password(credentials["password"], user["password"]):
            raise HttpBadRequestError("Invalid credentials")

        token = self.__jwt_handler.create_jwt_token({"user_id": user["id"], "role": user["role"]})

        return self.__format_response(user, token)

    def __format_response(self, user: dict, token: str) -> dict:
        return {
            "access": True,
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "token": token,
        }
