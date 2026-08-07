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

    def create_short_lived_token(self, payload: dict, ttl_seconds: int) -> str:
        """A token that expires in seconds rather than hours.

        Signed with the same key and read back by the same decode below — the
        point of putting it here instead of reaching for `jwt` directly in a
        driver is that this project has exactly ONE place that signs.

        Used for local file URLs (Item 22): the permission to read one file has
        to live in the link, because an <img> tag cannot send a header, and it
        has to expire far sooner than a login session.
        """
        return jwt.encode(
            payload={
                "exp": datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
                **payload,
            },
            key=settings.jwt_secret.get_secret_value(),
            algorithm=settings.jwt_algorithm,
        )

    def decode_jwt_token(self, token: str) -> dict:
        token_information = jwt.decode(
            token,
            key=settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm]
        )
        return token_information
