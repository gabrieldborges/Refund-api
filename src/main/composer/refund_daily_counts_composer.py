from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.refunds_repository import RefundsRepository
from src.controllers.refund_daily_counts_controller import RefundDailyCountsController
from src.views.refund_daily_counts_view import RefundDailyCountsView


def refund_daily_counts_composer():
    repository = RefundsRepository(database_connection_handler)
    controller = RefundDailyCountsController(repository)
    view = RefundDailyCountsView(controller)
    return view
