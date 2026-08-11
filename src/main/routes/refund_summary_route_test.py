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


def test_the_route_passes_the_year_and_the_token_through():
    view = _view({"type": "RefundSummary"})

    with patch("src.main.routes.refund_routes.refund_summary_composer", return_value=view):
        client.get("/refunds/summary?year=2025")

    request = view.handle.call_args[0][0]
    assert request.query == {"year": 2025, "user_id": None}
    assert request.token_info == STANDARD


# No literal default in the signature: the current year cannot be baked into a
# parameter evaluated at import time. Absent means "today's year", and the
# controller decides that with its injectable clock.
def test_the_route_leaves_an_absent_year_absent():
    view = _view({"type": "RefundSummary"})

    with patch("src.main.routes.refund_routes.refund_summary_composer", return_value=view):
        client.get("/refunds/summary")

    assert view.handle.call_args[0][0].query["year"] is None


# Two barriers on the bounds: FastAPI's Query(ge=, le=) on the route, and the
# validator behind it. This asserts the outer one.
def test_the_route_refuses_a_year_outside_the_bounds():
    assert client.get("/refunds/summary?year=1999").status_code == 422
    assert client.get("/refunds/summary?year=2101").status_code == 422
