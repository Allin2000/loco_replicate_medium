from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import UserUpdateRequest , CurrentUserResponse, UserDTO, UpdatedUserResponse
from app.services.user import UserService
from app.core import dep

router = APIRouter()


@router.get("", response_model=CurrentUserResponse)
async def get_current_user(
    token: str=Depends(dep.token_security),
    current_user: UserDTO = Depends(dep.get_current_user),
) -> CurrentUserResponse:
    """
    获取当前用户详细信息，并返回带 token 的响应。
    """
    return CurrentUserResponse.from_dto(current_user, token=token)




@router.put("", response_model=UpdatedUserResponse)
async def update_current_user(
    payload: UserUpdateRequest,
    token: str=Depends(dep.token_security),
    current_user: UserDTO = Depends(dep.get_current_user),
    user_service: UserService = Depends(dep.container.user_service),
    session: AsyncSession = Depends(dep.container.session),
) -> UpdatedUserResponse:
    """
    更新当前用户信息，并返回更新后的用户和 token。
    """
    # 更新用户   返回的是UpdateUserDTO 
    updated_user_dto = await user_service.update(
        session=session,
        user_id=current_user.id,
        update_item=payload.user
    )


    return UpdatedUserResponse.from_dto(updated_user_dto, token=token)