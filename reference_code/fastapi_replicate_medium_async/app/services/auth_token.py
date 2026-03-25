from datetime import datetime, timedelta
from typing import Dict

import jwt
from structlog import get_logger
from pydantic import  ValidationError

from app.schemas.auth import TokenPayload
from app.core.exception import IncorrectJWTTokenException

logger = get_logger()



class AuthTokenService:
    """Service to handle JWT tokens using Pydantic models."""

    def __init__(
        self, secret_key: str, token_expiration_minutes: int, algorithm: str
    ) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._token_expiration_minutes = token_expiration_minutes

    def generate_jwt_token(self, user_id: int, username: str) -> str:
        expire = datetime.now() + timedelta(minutes=self._token_expiration_minutes)
        payload = {"user_id": user_id, "username": username, "exp": expire.timestamp()}
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def parse_jwt_token(self, token: str) -> TokenPayload:
        try:
            payload: Dict = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
            # Convert timestamp back to datetime
            payload["exp"] = datetime.fromtimestamp(payload["exp"])
            return TokenPayload(**payload)
        except jwt.InvalidTokenError as err:
            logger.error("Invalid JWT token", token=token, error=err)
            raise IncorrectJWTTokenException()
        except ValidationError as err:
            logger.error("Invalid JWT payload format", token=token, error=err)
            raise IncorrectJWTTokenException()