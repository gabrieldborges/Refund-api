from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.refunds_repository import RefundsRepository
from src.controllers.refund_finder_controller import RefundFinderController
from src.views.refund_finder_view import RefundFinderView


def refund_finder_composer():
    repository = RefundsRepository(database_connection_handler)
    controller = RefundFinderController(repository)
    view = RefundFinderView(controller)
    return view
