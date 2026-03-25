from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.schemas.profile import ProfileResponse,ProfileData
from app.schemas.user import UserDTO
from app.services.profile import ProfileService
from app.core.dep import get_current_user, get_current_user_or_none, container
from app.core.exception import (
    OwnProfileFollowingException,
    ProfileAlreadyFollowedException,
    ProfileNotFollowedFollowedException,
    ProfileNotFoundException,
)

router = APIRouter() # 添加前缀和标签，使路由更清晰

@router.get("/{username}", response_model=ProfileResponse)
async def get_user_profile(
    username: str,
    session: AsyncSession = Depends(container.session),
    current_user: Optional[UserDTO] = Depends(get_current_user_or_none),
    profile_service: ProfileService = Depends(container.profile_service)
) -> ProfileResponse:
    """
    根据用户名获取用户资料。
    """
    try:
        # 直接调用 ProfileService 中已有的方法
        profile = await profile_service.get_profile_by_username(
            session=session, username=username, current_user=current_user
        )
    except ProfileNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found."
        )
    except Exception as e:
        # 捕获其他可能的异常，进行通用处理
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        )

    # ProfileDTO 已经包含了 following 字段，直接用它来构建 ProfileResponse
    return ProfileResponse(
        profile=ProfileData(
            username=profile.username,
            bio=profile.bio,
            image=profile.image,
            following=profile.following, # 直接使用 ProfileDTO 中的 following 字段
        )
    )


@router.post("/{username}/follow", response_model=ProfileResponse)
async def follow_username(
    username: str,
    session: AsyncSession = Depends(container.session),
    current_user: UserDTO = Depends(get_current_user), # 当前用户必须存在才能关注
    profile_service: ProfileService = Depends(container.profile_service)
) -> ProfileResponse:
    """
    关注指定用户名的资料。
    """
    try:
        # 直接调用 ProfileService 中封装的 follow_user 方法
        await profile_service.follow_user(
            session=session, username=username, current_user=current_user
        )
        # 关注成功后，重新获取最新的资料以确保 following 状态为 True
        profile = await profile_service.get_profile_by_username(
            session=session, username=username, current_user=current_user
        )
    except OwnProfileFollowingException:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot follow yourself."
        )
    except ProfileAlreadyFollowedException:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already following this profile."
        )
    except ProfileNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile to follow not found."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        )

    return ProfileResponse(
        profile=ProfileData(
            username=profile.username,
            bio=profile.bio,
            image=profile.image,
            following=profile.following, # 此时应为 True
        )
    )


@router.delete("/{username}/follow", response_model=ProfileResponse)
async def unfollow_username(
    username: str,
    session: AsyncSession = Depends(container.session),
    current_user: UserDTO = Depends(get_current_user), # 当前用户必须存在才能取消关注
    profile_service: ProfileService = Depends(container.profile_service),
    # follower_service: FollowerService = Depends(get_FollowerService) # 不再需要直接注入 FollowerService
) -> ProfileResponse:
    """
    取消关注指定用户名的资料。
    """
    try:
        # 直接调用 ProfileService 中封装的 unfollow_user 方法
        await profile_service.unfollow_user(
            session=session, username=username, current_user=current_user
        )
        # 取消关注成功后，重新获取最新的资料以确保 following 状态为 False
        profile = await profile_service.get_profile_by_username(
            session=session, username=username, current_user=current_user
        )
    except OwnProfileFollowingException:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot unfollow yourself."
        )
    except ProfileNotFollowedFollowedException: # 这里你写错了，应该是 ProfileNotFollowedException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not following this profile."
        )
    except ProfileNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile to unfollow not found."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        )

    return ProfileResponse(
        profile=ProfileData(
            username=profile.username,
            bio=profile.bio,
            image=profile.image,
            following=profile.following, # 此时应为 False
        )
    )