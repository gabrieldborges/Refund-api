from fastapi import Header
from src.drivers.jwt_handler import JwtHandler
from src.errors.types.http_unauthorized_error import HttpUnauthorizedError


async def get_current_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HttpUnauthorizedError("Missing or invalid authorization header")

    token = authorization.split(" ")[1]

    try:
        token_info = JwtHandler().decode_jwt_token(token)
    except Exception as exception:
        raise HttpUnauthorizedError("Invalid or expired token") from exception

    return token_info
