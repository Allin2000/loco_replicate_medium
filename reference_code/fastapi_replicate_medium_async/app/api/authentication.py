from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth import UserAuthService  # 正确的 service
from app.core.dep import container
from app.schemas.user import (
    UserRegistrationRequest,
    UserLoginRequest,
    UserRegistrationResponse,
    UserLoginResponse,
)

router = APIRouter()


@router.post("", response_model=UserRegistrationResponse)
async def register_user(
    payload: UserRegistrationRequest,
    session: AsyncSession = Depends(container.session),
    user_auth_service: UserAuthService = Depends(container.user_auth_service),
) -> UserRegistrationResponse:
    """
    用户注册
    """
    user_dto = await user_auth_service.sign_up_user(
        session=session, user_to_create=payload.to_dto()
    )
    return UserRegistrationResponse.from_dto(user_dto)


@router.post("/login", response_model=UserLoginResponse)
async def login_user(
    payload: UserLoginRequest,
    session: AsyncSession = Depends(container.session),
    user_auth_service: UserAuthService = Depends(container.user_auth_service),
) -> UserLoginResponse:
    """
    用户登录
    """
    user_dto = await user_auth_service.sign_in_user(
        session=session, user_to_login=payload.to_dto()
    )
    return UserLoginResponse.from_dto(user_dto)