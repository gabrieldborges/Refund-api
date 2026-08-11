from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.refunds_repository import RefundsRepository
from src.controllers.refund_summary_controller import RefundSummaryController
from src.views.refund_summary_view import RefundSummaryView


def refund_summary_composer():
    repository = RefundsRepository(database_connection_handler)
    # The clock keeps its default here: only tests inject one.
    controller = RefundSummaryController(repository)
    view = RefundSummaryView(controller)
    return view
