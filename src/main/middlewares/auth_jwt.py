from fastapi import Header, HTTPException
from src.drivers.jwt_handler import JwtHandler


async def get_current_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.split(" ")[1]

    try:
        token_info = JwtHandler().decode_jwt_token(token)
    except Exception as exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exception

    return token_info
