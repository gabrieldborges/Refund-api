from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.refunds_repository import RefundsRepository
from src.configs.global_config import upload_info
from src.drivers.file_storage import FileStorage
from src.controllers.refund_creator_controller import RefundCreatorController
from src.views.refund_creator_view import RefundCreatorView


def refund_creator_composer():
    repository = RefundsRepository(database_connection_handler)
    storage = FileStorage(upload_info["UPLOAD_DIR"])
    controller = RefundCreatorController(repository, storage)
    view = RefundCreatorView(controller)
    return view
