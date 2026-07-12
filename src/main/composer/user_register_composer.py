from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.users_repository import UsersRepository
from src.controllers.user_register_controller import UserRegisterController
from src.views.user_register_view import UserRegisterView


def user_register_composer():
    model = UsersRepository(database_connection_handler)
    controller = UserRegisterController(model)
    view = UserRegisterView(controller)
    return view
