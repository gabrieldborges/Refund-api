from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.refunds_repository import RefundsRepository
from src.drivers.receipt_storage import ReceiptStorage
from src.controllers.refund_creator_controller import RefundCreatorController
from src.views.refund_creator_view import RefundCreatorView


def refund_creator_composer():
    repository = RefundsRepository(database_connection_handler)
    storage = ReceiptStorage()
    controller = RefundCreatorController(repository, storage)
    view = RefundCreatorView(controller)
    return view
