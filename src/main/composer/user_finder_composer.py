from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.users_repository import UsersRepository
from src.controllers.user_finder_controller import UserFinderController
from src.views.user_finder_view import UserFinderView


def user_finder_composer():
    repository = UsersRepository(database_connection_handler)
    controller = UserFinderController(repository)
    view = UserFinderView(controller)
    return view
