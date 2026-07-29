from src.configs.global_config import upload_info
from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.users_repository import UsersRepository
from src.drivers.file_storage import FileStorage
from src.controllers.avatar_finder_controller import AvatarFinderController
from src.views.avatar_finder_view import AvatarFinderView


def avatar_finder_composer():
    repository = UsersRepository(database_connection_handler)
    storage = FileStorage(upload_info["AVATAR_DIR"])
    controller = AvatarFinderController(repository, storage)
    view = AvatarFinderView(controller)
    return view
