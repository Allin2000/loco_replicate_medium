from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.exception import IncorrectLoginInputException, UserNotFoundException
from app.services.auth_token import AuthTokenService
from app.services.user import UserService
from app.services.password import verify_password
from app.schemas.user import (
    CreatedUserDTO,
    UserRegistrationDataDTO,
    LoggedInUserDTO,
    LoginUserDTO,
)

logger = get_logger()


class UserAuthService:
    """Service to handle users auth logic."""

    def __init__(
        self, user_service: UserService, auth_token_service: AuthTokenService
    ):
        self._user_service = user_service
        self._auth_token_service = auth_token_service

    async def sign_up_user(
        self, session: AsyncSession, user_to_create:UserRegistrationDataDTO
    ) -> CreatedUserDTO:
        user = await self._user_service.add(
            session=session, create_item=user_to_create
        )
        jwt_token = self._auth_token_service.generate_jwt_token(user.id, user.username)
  
        return CreatedUserDTO(
            id=user.id,
            email=user.email,
            username=user.username,
            bio=user.bio,
            image=user.image_url,
            token=jwt_token,
        )

    async def sign_in_user(
        self, session: AsyncSession, user_to_login: LoginUserDTO
    ) -> LoggedInUserDTO:
        try:
            user = await self._user_service.get_by_email(
                session=session, email=user_to_login.email
            )
        except UserNotFoundException:
            logger.error("User not found", email=user_to_login.email)
            raise IncorrectLoginInputException()

        if not verify_password(
            plain_password=user_to_login.password, hashed_password=user.password_hash
        ):
            logger.error("Incorrect password", user_id=user_to_login.email)
            raise IncorrectLoginInputException()

        jwt_token = self._auth_token_service.generate_jwt_token(user.id, user.username)
        return LoggedInUserDTO(
            email=user.email,
            username=user.username,
            bio=user.bio,
            image=user.image_url,
            token=jwt_token,
        )