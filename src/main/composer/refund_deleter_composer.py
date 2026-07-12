from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.refunds_repository import RefundsRepository
from src.drivers.receipt_storage import ReceiptStorage
from src.controllers.refund_deleter_controller import RefundDeleterController
from src.views.refund_deleter_view import RefundDeleterView


def refund_deleter_composer():
    repository = RefundsRepository(database_connection_handler)
    storage = ReceiptStorage()
    controller = RefundDeleterController(repository, storage)
    view = RefundDeleterView(controller)
    return view
