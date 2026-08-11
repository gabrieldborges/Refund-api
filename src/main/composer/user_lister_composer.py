from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.users_repository import UsersRepository
from src.controllers.user_lister_controller import UserListerController
from src.views.user_lister_view import UserListerView


def user_lister_composer():
    repository = UsersRepository(database_connection_handler)
    controller = UserListerController(repository)
    view = UserListerView(controller)
    return view
