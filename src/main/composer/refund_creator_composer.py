from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.refunds_repository import RefundsRepository
from src.configs.settings import settings
from src.drivers.file_storage import FileStorage
from src.controllers.refund_creator_controller import RefundCreatorController
from src.views.refund_creator_view import RefundCreatorView


def refund_creator_composer():
    repository = RefundsRepository(database_connection_handler)
    storage = FileStorage(settings.upload_dir)
    controller = RefundCreatorController(repository, storage)
    view = RefundCreatorView(controller)
    return view
