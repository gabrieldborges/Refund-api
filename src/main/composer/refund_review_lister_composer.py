from src.models.settings.database_connection_handler import database_connection_handler
from src.models.repositories.refunds_repository import RefundsRepository
from src.models.repositories.refund_reviews_repository import RefundReviewsReaderRepository
from src.controllers.refund_review_lister_controller import RefundReviewListerController
from src.views.refund_review_lister_view import RefundReviewListerView


def refund_review_lister_composer():
    refunds_repository = RefundsRepository(database_connection_handler)
    # The READER sibling, not RefundReviewsRepository: that one takes an
    # AsyncSession from the UnitOfWork, this one takes the handler and opens
    # its own.
    reviews_repository = RefundReviewsReaderRepository(database_connection_handler)
    controller = RefundReviewListerController(refunds_repository, reviews_repository)
    view = RefundReviewListerView(controller)
    return view
