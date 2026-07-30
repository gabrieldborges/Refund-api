from src.models.settings.database_connection_handler import database_connection_handler
from src.models.settings.unit_of_work import UnitOfWork
from src.models.repositories.refunds_repository import RefundsRepository
from src.drivers.file_storage import FileStorage
from src.configs.global_config import upload_info
from src.controllers.refund_payer_controller import RefundPayerController
from src.views.refund_payer_view import RefundPayerView


def refund_payer_composer():
    # A fresh UnitOfWork per request: it holds a session for one transaction, so
    # sharing one across requests would share a session.
    unit_of_work = UnitOfWork(database_connection_handler)
    repository = RefundsRepository(database_connection_handler)
    storage = FileStorage(upload_info["PAYMENT_DIR"])
    controller = RefundPayerController(unit_of_work, repository, storage)
    view = RefundPayerView(controller)
    return view
