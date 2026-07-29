from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.refunds_repository import RefundsRepository
from src.configs.global_config import upload_info
from src.drivers.file_storage import FileStorage
from src.controllers.refund_deleter_controller import RefundDeleterController
from src.views.refund_deleter_view import RefundDeleterView


def refund_deleter_composer():
    repository = RefundsRepository(database_connection_handler)
    storage = FileStorage(upload_info["UPLOAD_DIR"])
    controller = RefundDeleterController(repository, storage)
    view = RefundDeleterView(controller)
    return view
