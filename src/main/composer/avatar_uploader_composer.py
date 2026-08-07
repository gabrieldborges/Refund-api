from src.configs.settings import settings
from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.users_repository import UsersRepository
from src.drivers.file_storage import FileStorage
from src.controllers.avatar_uploader_controller import AvatarUploaderController
from src.views.avatar_uploader_view import AvatarUploaderView


def avatar_uploader_composer():
    repository = UsersRepository(database_connection_handler)
    storage = FileStorage(settings.avatar_dir)
    controller = AvatarUploaderController(repository, storage)
    view = AvatarUploaderView(controller)
    return view
