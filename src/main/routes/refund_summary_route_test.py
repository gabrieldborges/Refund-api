from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from src.main.server.server import app
from src.main.middlewares.auth_jwt import get_current_user
from src.views.http_types.http_response import HttpResponse

client = TestClient(app)
STANDARD = {"user_id": 1, "role": "standard"}


def _view(body):
    view = AsyncMock()
    view.handle.return_value = HttpResponse(body=body, status_code=200)
    return view


@pytest.fixture(autouse=True)
def authenticated():
    app.dependency_overrides[get_current_user] = lambda: STANDARD
    yield
    app.dependency_overrides.clear()


# The defect this guards against passes every unit test of the layers below and
# fails on first use: with GET /{refund_id} declared first, "summary" is read as an
# id, fails int coercion and answers 422. Asserting the SPECIFIC composer ran is
# what proves the path matched the right route, rather than just asserting a 200.
def test_the_summary_path_is_not_read_as_a_refund_id():
    view = _view({"type": "RefundSummary"})

    with patch("src.main.routes.refund_routes.refund_summary_composer", return_value=view) as s:
        response = client.get("/refunds/summary")

    assert response.status_code == 200
    assert s.called


def test_a_numeric_id_still_reaches_the_finder():
    view = _view({"type": "Refund", "count": 1, "attributes": {}})

    with patch("src.main.routes.refund_routes.refund_finder_composer", return_value=view) as f:
        client.get("/refunds/7")

    assert f.called


def test_the_route_passes_months_and_the_token_through():
    view = _view({"type": "RefundSummary"})

    with patch("src.main.routes.refund_routes.refund_summary_composer", return_value=view):
        client.get("/refunds/summary?months=3")

    request = view.handle.call_args[0][0]
    assert request.query == {"months": 3, "user_id": None}
    assert request.token_info == STANDARD


def test_the_route_defaults_to_six_months():
    view = _view({"type": "RefundSummary"})

    with patch("src.main.routes.refund_routes.refund_summary_composer", return_value=view):
        client.get("/refunds/summary")

    assert view.handle.call_args[0][0].query["months"] == 6


# Two barriers on the ceiling: FastAPI's Query(le=12) on the route, and the
# validator behind it. This asserts the outer one.
def test_the_route_refuses_a_window_past_the_ceiling():
    assert client.get("/refunds/summary?months=13").status_code == 422
    assert client.get("/refunds/summary?months=0").status_code == 422
