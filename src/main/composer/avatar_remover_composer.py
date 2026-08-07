from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.users_repository import UsersRepository
from src.drivers.storage_factory import build_storage
from src.controllers.avatar_remover_controller import AvatarRemoverController
from src.views.avatar_remover_view import AvatarRemoverView


def avatar_remover_composer():
    repository = UsersRepository(database_connection_handler)
    storage = build_storage("avatars")
    controller = AvatarRemoverController(repository, storage)
    view = AvatarRemoverView(controller)
    return view
