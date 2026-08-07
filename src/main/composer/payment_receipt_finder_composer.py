from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.refunds_repository import RefundsRepository
from src.drivers.storage_factory import build_storage
from src.controllers.payment_receipt_finder_controller import PaymentReceiptFinderController
from src.views.payment_receipt_finder_view import PaymentReceiptFinderView


def payment_receipt_finder_composer():
    repository = RefundsRepository(database_connection_handler)
    storage = build_storage("payments")
    controller = PaymentReceiptFinderController(repository, storage)
    view = PaymentReceiptFinderView(controller)
    return view
