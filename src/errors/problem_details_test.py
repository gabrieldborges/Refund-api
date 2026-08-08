import json
from .problem_details import DEFAULT_TYPE, MEDIA_TYPE, problem_response


def body_of(response) -> dict:
    return json.loads(response.body)


# The RFC's content type is what tells a client this is a problem document and
# not an ordinary JSON body that happens to have a "detail" key.
def test_the_response_uses_the_problem_json_media_type():
    response = problem_response(404, "Refund not found", "/refunds/1", "req-1")

    assert response.media_type == MEDIA_TYPE


def test_the_envelope_carries_every_required_field():
    response = problem_response(404, "Refund not found", "/refunds/1", "req-1")

    assert body_of(response) == {
        "type": DEFAULT_TYPE,
        "title": "Not Found",
        "status": 404,
        "detail": "Refund not found",
        "instance": "/refunds/1",
        "request_id": "req-1",
    }


# The whole compatibility story rests on this: `detail` is a string in the RFC
# too, so a client reading `.detail` keeps working through the migration —
# including for validation errors, which used to arrive as a list.
def test_detail_is_always_a_string():
    response = problem_response(422, "Amount must be greater than zero", "/refunds", "r")

    assert isinstance(body_of(response)["detail"], str)


# The title comes from the status registry rather than being written by hand at
# 38 call sites.
def test_the_title_comes_from_the_status_code():
    assert body_of(problem_response(422, "x", "/", "r"))["title"] == "Unprocessable Entity"
    assert body_of(problem_response(401, "x", "/", "r"))["title"] == "Unauthorized"
    assert body_of(problem_response(500, "x", "/", "r"))["title"] == "Internal Server Error"


# An unregistered status must not turn an error response into a second error.
def test_an_unknown_status_still_produces_a_document():
    response = problem_response(599, "Weird", "/", "r")

    assert body_of(response)["title"] == "Error"
    assert body_of(response)["status"] == 599


# The extension only appears when there is something to put in it, so an
# ordinary error is not padded with an empty array.
def test_the_errors_extension_is_omitted_when_there_are_none():
    assert "errors" not in body_of(problem_response(404, "x", "/", "r"))


def test_the_errors_extension_is_included_when_present():
    response = problem_response(
        422, "Field required", "/auth/login", "r",
        errors=[{"field": "password", "message": "Field required"}],
    )

    assert body_of(response)["errors"] == [{"field": "password", "message": "Field required"}]


# The header is set on the response itself, not left to the middleware. This is
# a REGRESSION NET: on a 500 the exception travels up past RequestIdMiddleware
# before the handler runs, so the middleware never adds it — the body had the
# id and the header did not, on exactly the response someone would want to copy
# from. Measured against the running API, not reasoned about.
def test_the_request_id_is_echoed_in_the_header():
    response = problem_response(500, "Internal server error", "/boom", "req-42")

    assert response.headers["X-Request-Id"] == "req-42"
    assert body_of(response)["request_id"] == "req-42"
