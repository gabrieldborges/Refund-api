from src.configs.global_config import upload_info
from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.users_repository import UsersRepository
from src.drivers.file_storage import FileStorage
from src.controllers.avatar_remover_controller import AvatarRemoverController
from src.views.avatar_remover_view import AvatarRemoverView


def avatar_remover_composer():
    repository = UsersRepository(database_connection_handler)
    storage = FileStorage(upload_info["AVATAR_DIR"])
    controller = AvatarRemoverController(repository, storage)
    view = AvatarRemoverView(controller)
    return view
