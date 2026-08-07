from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.refunds_repository import RefundsRepository
from src.drivers.storage_factory import build_storage
from src.controllers.refund_creator_controller import RefundCreatorController
from src.views.refund_creator_view import RefundCreatorView


def refund_creator_composer():
    repository = RefundsRepository(database_connection_handler)
    storage = build_storage("receipts")
    controller = RefundCreatorController(repository, storage)
    view = RefundCreatorView(controller)
    return view
