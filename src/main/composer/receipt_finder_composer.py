from src.configs.global_config import upload_info
from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.refunds_repository import RefundsRepository
from src.drivers.file_storage import FileStorage
from src.controllers.receipt_finder_controller import ReceiptFinderController
from src.views.receipt_finder_view import ReceiptFinderView


def receipt_finder_composer():
    repository = RefundsRepository(database_connection_handler)
    storage = FileStorage(upload_info["UPLOAD_DIR"])
    controller = ReceiptFinderController(repository, storage)
    view = ReceiptFinderView(controller)
    return view
