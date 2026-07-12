from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.users_repository import UsersRepository
from src.controllers.user_login_controller import UserLoginController
from src.views.user_login_view import UserLoginView


def user_login_composer():
    model = UsersRepository(database_connection_handler)
    controller = UserLoginController(model)
    view = UserLoginView(controller)
    return view
