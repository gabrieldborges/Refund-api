from src.models.settings.database_connection_handler import database_connection_handler
from src.models.settings.unit_of_work import UnitOfWork
from src.controllers.refund_reviewer_controller import RefundReviewerController
from src.views.refund_reviewer_view import RefundReviewerView


def refund_reviewer_composer():
    # A fresh UnitOfWork per request: it holds a session for the duration of one
    # transaction, so sharing one across requests would share a session — the very
    # bug fixed in DatabaseConnectionHandler.
    unit_of_work = UnitOfWork(database_connection_handler)
    controller = RefundReviewerController(unit_of_work)
    view = RefundReviewerView(controller)
    return view
