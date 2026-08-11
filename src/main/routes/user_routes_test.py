from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from src.main.server.server import app
from src.main.middlewares.auth_jwt import get_current_user
from src.views.http_types.http_response import HttpResponse

client = TestClient(app)

# The auth dependency is overridden rather than a real token minted: these tests
# are about routing and wiring, not about JWT decoding, which auth_jwt covers.
ADMIN = {"user_id": 1, "role": "admin"}


def _view(body):
    view = AsyncMock()
    view.handle.return_value = HttpResponse(body=body, status_code=200)
    return view


@pytest.fixture(autouse=True)
def as_admin():
    """Every test here speaks as an admin, and the override is undone after.

    autouse so no test can forget it, and the teardown matters: dependency
    overrides live on the app object, which is shared across the whole session.
    """
    app.dependency_overrides[get_current_user] = lambda: ADMIN
    yield
    app.dependency_overrides.clear()


def test_the_listing_route_passes_the_query_and_the_token_through():
    view = _view({"type": "User", "attributes": []})

    with patch("src.main.routes.user_routes.user_lister_composer", return_value=view):
        response = client.get("/users?page=2&per_page=5&name=an")

    assert response.status_code == 200
    request = view.handle.call_args[0][0]
    assert request.query == {"page": 2, "per_page": 5, "name": "an"}
    assert request.token_info == ADMIN


def test_the_listing_route_defaults_page_and_per_page():
    view = _view({"type": "User", "attributes": []})

    with patch("src.main.routes.user_routes.user_lister_composer", return_value=view):
        client.get("/users")

    assert view.handle.call_args[0][0].query == {"page": 1, "per_page": 10, "name": None}


# The bounds come from FastAPI's Query(ge=, le=), which is exactly why this slice
# adds no validator: there is no whitelist to express, so a validator would only
# duplicate what the framework already refuses.
def test_the_listing_route_rejects_out_of_range_pagination():
    assert client.get("/users?page=0").status_code == 422
    assert client.get("/users?per_page=0").status_code == 422
    assert client.get("/users?per_page=101").status_code == 422


def test_the_detail_route_passes_the_path_param_through():
    view = _view({"type": "User", "count": 1, "attributes": {}})

    with patch("src.main.routes.user_routes.user_finder_composer", return_value=view):
        response = client.get("/users/7")

    assert response.status_code == 200
    assert view.handle.call_args[0][0].path_params == {"user_id": 7}


def test_the_detail_route_rejects_a_non_numeric_id():
    assert client.get("/users/abc").status_code == 422


# The route added here must not swallow the two that already lived under the same
# {user_id} prefix. Asserting the SPECIFIC composer is the one invoked is what
# proves FastAPI matched the more specific path, rather than just asserting a 200.
def test_the_detail_route_does_not_shadow_the_avatar_route():
    view = _view({"url": "http://x/f.png", "media_type": "image/png"})

    with patch("src.main.routes.user_routes.avatar_finder_composer", return_value=view) as avatar:
        client.get("/users/7/avatar")

    assert avatar.called


def test_the_detail_route_does_not_shadow_the_refund_stats_route():
    view = _view({"type": "RefundStats", "user_id": 7, "by_status": {}})

    with patch(
        "src.main.routes.user_routes.refund_stats_finder_composer", return_value=view
    ) as stats:
        client.get("/users/7/refund-stats")

    assert stats.called
