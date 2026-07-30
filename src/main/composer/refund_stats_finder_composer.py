from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.refunds_repository import RefundsRepository
from src.controllers.refund_stats_finder_controller import RefundStatsFinderController
from src.views.refund_stats_finder_view import RefundStatsFinderView


def refund_stats_finder_composer():
    repository = RefundsRepository(database_connection_handler)
    controller = RefundStatsFinderController(repository)
    view = RefundStatsFinderView(controller)
    return view
