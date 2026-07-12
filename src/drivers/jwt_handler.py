from datetime import datetime, timedelta, timezone
import jwt
from src.configs.global_config import jwt_info


class JwtHandler:
    def create_jwt_token(self, payload: dict) -> str:
        token = jwt.encode(
            payload={
                "exp": datetime.now(timezone.utc) + timedelta(hours=jwt_info["EXPIRATION_TIME"]),
                **payload
            },
            key=jwt_info["KEY"],
            algorithm=jwt_info["ALGORITHM"],
        )
        return token

    def decode_jwt_token(self, token: str) -> dict:
        token_information = jwt.decode(
            token,
            key=jwt_info["KEY"],
            algorithms=[jwt_info["ALGORITHM"]]
        )
        return token_information
