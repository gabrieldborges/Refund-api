from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.users_repository import UsersRepository
from src.drivers.storage_factory import build_storage
from src.controllers.avatar_finder_controller import AvatarFinderController
from src.views.avatar_finder_view import AvatarFinderView


def avatar_finder_composer():
    repository = UsersRepository(database_connection_handler)
    storage = build_storage("avatars")
    controller = AvatarFinderController(repository, storage)
    view = AvatarFinderView(controller)
    return view
