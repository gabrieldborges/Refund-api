from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.users_repository import UsersRepository
from src.drivers.storage_factory import build_storage
from src.controllers.avatar_uploader_controller import AvatarUploaderController
from src.views.avatar_uploader_view import AvatarUploaderView


def avatar_uploader_composer():
    repository = UsersRepository(database_connection_handler)
    storage = build_storage("avatars")
    controller = AvatarUploaderController(repository, storage)
    view = AvatarUploaderView(controller)
    return view
