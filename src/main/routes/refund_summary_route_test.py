from unittest.mock import patch
from src.main.routes.conftest import STANDARD_TOKEN


# The defect this guards against passes every unit test of the layers below and
# fails on first use: with GET /{refund_id} declared first, "summary" is read as an
# id, fails int coercion and answers 422. Asserting the SPECIFIC composer ran is
# what proves the path matched the right route, rather than just asserting a 200.
def test_the_summary_path_is_not_read_as_a_refund_id(client, view, as_standard):  # pylint: disable=unused-argument
    view = view({"type": "RefundSummary"})

    with patch("src.main.routes.refund_routes.refund_summary_composer", return_value=view) as s:
        response = client.get("/refunds/summary")

    assert response.status_code == 200
    assert s.called


# The "/{refund_id}" guard lives in refund_daily_counts_route_test, in one place: it
# is a property of the whole route table — that no literal sibling shadows the id
# path — not of this endpoint. Duplicating it here is what pylint's R0801 caught.

def test_the_route_passes_the_year_and_the_token_through(client, view, as_standard):  # pylint: disable=unused-argument
    view = view({"type": "RefundSummary"})

    with patch("src.main.routes.refund_routes.refund_summary_composer", return_value=view):
        client.get("/refunds/summary?year=2025")

    request = view.handle.call_args[0][0]
    assert request.query == {"year": 2025, "user_id": None}
    assert request.token_info == STANDARD_TOKEN


# No literal default in the signature: the current year cannot be baked into a
# parameter evaluated at import time. Absent means "today's year", and the
# controller decides that with its injectable clock.
def test_the_route_leaves_an_absent_year_absent(client, view, as_standard):  # pylint: disable=unused-argument
    view = view({"type": "RefundSummary"})

    with patch("src.main.routes.refund_routes.refund_summary_composer", return_value=view):
        client.get("/refunds/summary")

    assert view.handle.call_args[0][0].query["year"] is None


# Two barriers on the bounds: FastAPI's Query(ge=, le=) on the route, and the
# validator behind it. This asserts the outer one.
def test_the_route_refuses_a_year_outside_the_bounds(client, view, as_standard):  # pylint: disable=unused-argument
    assert client.get("/refunds/summary?year=1999").status_code == 422
    assert client.get("/refunds/summary?year=2101").status_code == 422
