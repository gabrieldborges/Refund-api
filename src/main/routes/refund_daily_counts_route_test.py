from unittest.mock import patch
from src.main.routes.conftest import STANDARD_TOKEN


# The defect this guards against passes every unit test of the layers below and fails
# on first use: with GET /{refund_id} declared first, "daily-counts" is read as an id,
# fails int coercion and answers 422. Asserting the SPECIFIC composer ran is what
# proves the path matched the right route — a 200 could come from the wrong one.
def test_the_daily_counts_path_is_not_read_as_a_refund_id(client, view, as_standard):  # pylint: disable=unused-argument
    view = view({"type": "RefundDailyCounts"})

    with patch(
        "src.main.routes.refund_routes.refund_daily_counts_composer", return_value=view
    ) as composer:
        response = client.get("/refunds/daily-counts?month=2026-08")

    assert response.status_code == 200
    assert composer.called


def test_a_numeric_id_still_reaches_the_finder(client, view, as_standard):  # pylint: disable=unused-argument
    view = view({"type": "Refund", "count": 1, "attributes": {}})

    with patch("src.main.routes.refund_routes.refund_finder_composer", return_value=view) as f:
        client.get("/refunds/7")

    assert f.called


# And the summary route added in the previous cycle must still work: three sibling
# literal paths now sit above /{refund_id}.
def test_the_summary_route_still_reaches_its_own_composer(client, view, as_standard):  # pylint: disable=unused-argument
    view = view({"type": "RefundSummary"})

    with patch("src.main.routes.refund_routes.refund_summary_composer", return_value=view) as s:
        client.get("/refunds/summary")

    assert s.called


def test_the_route_passes_the_month_and_the_token_through(client, view, as_standard):  # pylint: disable=unused-argument
    view = view({"type": "RefundDailyCounts"})

    with patch("src.main.routes.refund_routes.refund_daily_counts_composer", return_value=view):
        client.get("/refunds/daily-counts?month=2026-08")

    request = view.handle.call_args[0][0]
    assert request.query == {"month": "2026-08", "user_id": None}
    assert request.token_info == STANDARD_TOKEN


# month is required: without it there is no window to count, and defaulting to
# "this month" in the route would hide a client bug.
def test_the_month_is_required(client, view, as_standard):  # pylint: disable=unused-argument
    assert client.get("/refunds/daily-counts").status_code == 422


def test_the_listing_route_accepts_the_date_filters(client, view, as_standard):  # pylint: disable=unused-argument
    view = view({"type": "Refund", "attributes": []})

    with patch("src.main.routes.refund_routes.refund_lister_composer", return_value=view):
        response = client.get("/refunds?created_from=2026-08-03&created_to=2026-08-03")

    assert response.status_code == 200
    query = view.handle.call_args[0][0].query
    assert str(query["created_from"]) == "2026-08-03"
    assert str(query["created_to"]) == "2026-08-03"


# Typed as `date` on the route, so FastAPI refuses a malformed one before any layer
# below sees it — which is why this slice needs no whitelist for the dates.
def test_the_listing_route_refuses_a_malformed_date(client, view, as_standard):  # pylint: disable=unused-argument
    assert client.get("/refunds?created_from=03-08-2026").status_code == 422
    assert client.get("/refunds?created_to=nao-e-data").status_code == 422
