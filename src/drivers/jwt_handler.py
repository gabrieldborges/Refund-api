from datetime import datetime, timedelta, timezone
import jwt
from src.configs.settings import settings


class JwtHandler:
    def create_jwt_token(self, payload: dict) -> str:
        token = jwt.encode(
            payload={
                "exp": datetime.now(timezone.utc)
                + timedelta(hours=settings.jwt_expiration_hours),
                **payload
            },
            # get_secret_value() is the deliberate cost of SecretStr: the two
            # places that genuinely need the signing key say so explicitly,
            # and nothing else can print it by accident.
            key=settings.jwt_secret.get_secret_value(),
            algorithm=settings.jwt_algorithm,
        )
        return token

    def decode_jwt_token(self, token: str) -> dict:
        token_information = jwt.decode(
            token,
            key=settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm]
        )
        return token_information
