from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.refunds_repository import RefundsRepository
from src.controllers.refund_lister_controller import RefundListerController
from src.views.refund_lister_view import RefundListerView


def refund_lister_composer():
    repository = RefundsRepository(database_connection_handler)
    controller = RefundListerController(repository)
    view = RefundListerView(controller)
    return view
