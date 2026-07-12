# We do NOT use mocks or fixtures here: JwtHandler is a small, pure unit
# (just crypto math, no database or network), so we test it "for real".
# Not every test needs a fixture — they only pay off when setup repeats across tests.
from datetime import datetime, timedelta, timezone
import jwt as pyjwt
import pytest
from src.configs.global_config import jwt_info
from .jwt_handler import JwtHandler


# A valid JWT is a string with 3 dot-separated parts (header.payload.signature).
def test_create_jwt_token_returns_a_token_string():
    handler = JwtHandler()
    token = handler.create_jwt_token({"user_id": 1, "role": "standard"})

    assert isinstance(token, str)
    assert len(token.split(".")) == 3


# Round-trip: whatever was encoded into the token must come back out when decoded.
def test_decode_jwt_token_returns_the_original_payload_fields():
    handler = JwtHandler()
    token = handler.create_jwt_token({"user_id": 1, "role": "admin"})

    decoded = handler.decode_jwt_token(token)

    assert decoded["user_id"] == 1
    assert decoded["role"] == "admin"


# An expired token must be rejected. Since the handler itself never lets you create an
# already-expired token, we forge one by hand with the pyjwt lib, setting exp 1 hour in
# the past, to prove decode_jwt_token raises in that case.
def test_decode_jwt_token_raises_for_an_expired_token():
    handler = JwtHandler()
    expired_token = pyjwt.encode(
        payload={
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "user_id": 1,
        },
        key=jwt_info["KEY"],
        algorithm=jwt_info["ALGORITHM"],
    )

    with pytest.raises(Exception):
        handler.decode_jwt_token(expired_token)
