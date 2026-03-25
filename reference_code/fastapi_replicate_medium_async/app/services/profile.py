from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.exception import (
    OwnProfileFollowingException,
    ProfileAlreadyFollowedException,
    ProfileNotFollowedFollowedException,
    ProfileNotFoundException,
    UserNotFoundException,
)
from app.schemas.profile import ProfileDTO
from app.schemas.user import UserDTO
from app.services.user import UserService
from app.services.follower import FollowerService # <-- 新增导入 FollowerService


logger = get_logger()


class ProfileService:
    """Service to handle user profiles and following logic, using Pydantic."""

    def __init__(
        self,
        user_service: UserService,
        # database_service: DatabaseService, # <-- 移除这个参数
        follower_service: FollowerService # <-- 新增 follower_service 参数
    ):
        self._user_service = user_service
        # self._database_service = database_service # <-- 移除这个属性
        self._follower_service = follower_service # <-- 新增 follower_service 属性

    async def get_profile_by_username(
        self, session: AsyncSession, username: str, current_user: Optional[UserDTO] = None
    ) -> ProfileDTO:
        try:
            target_user = await self._user_service.get_by_username(
                session=session, username=username
            )
        except UserNotFoundException:
            logger.exception("Profile not found", username=username)
            raise ProfileNotFoundException()

        profile = ProfileDTO(
            user_id=target_user.id,
            username=target_user.username,
            bio=target_user.bio,
            image=target_user.image_url,
            following=False,  # Default value
        )
        if current_user:
            # 直接使用传入的 session
            profile.following = await self._follower_service.exists(
                session=session, follower_id=current_user.id, following_id=target_user.id
            )
        return profile

    async def get_profile_by_user_id(
        self, session: AsyncSession, user_id: int, current_user: Optional[UserDTO] = None
    ) -> ProfileDTO:
        # 修正：使用 UserService 的 get 方法
        target_user = await self._user_service.get(session=session, user_id=user_id)

        profile = ProfileDTO(
            user_id=target_user.id,
            username=target_user.username,
            bio=target_user.bio,
            image=target_user.image_url,
            following=False,  # Default
        )

        if current_user:
            # 直接使用传入的 session
            profile.following = await self._follower_service.exists(
                session=session, follower_id=current_user.id, following_id=target_user.id
            )
        return profile

    async def get_profiles_by_user_ids(
        self, session: AsyncSession, user_ids: List[int], current_user: Optional[UserDTO]
    ) -> List[ProfileDTO]:
        # 修正：使用 UserService 的 list_by_users 方法
        target_users = await self._user_service.list_by_users(session=session, user_ids=user_ids)
        profiles = []
        following_map = {}

        if current_user:
            # 直接使用传入的 session
            following_user_ids = await self._follower_service.list(
                session=session, follower_id=current_user.id, following_ids=user_ids
            )
            following_map = {
                following_id: True for following_id in following_user_ids
            }  # Create a map for efficient lookup

        for user_dto in target_users:
            profile = ProfileDTO(
                user_id=user_dto.id,
                username=user_dto.username,
                bio=user_dto.bio,
                image=user_dto.image_url,
                following=following_map.get(user_dto.id, False),  # Use the map
            )
            profiles.append(profile)
        return profiles

    async def follow_user(self, session: AsyncSession, username: str, current_user: UserDTO) -> None:
        if username == current_user.username:
            raise OwnProfileFollowingException()

        target_user = await self._user_service.get_by_username(session=session, username=username)

        # 直接使用传入的 session
        if await self._follower_service.exists(session=session, follower_id=current_user.id, following_id=target_user.id):
            raise ProfileAlreadyFollowedException()

        await self._follower_service.create(
            session=session, follower_id=current_user.id, following_id=target_user.id
        )
        # FollowerService.create 内部已经包含了 commit()，所以这里不需要再 commit


    async def unfollow_user(self, session: AsyncSession, username: str, current_user: UserDTO) -> None:
        if username == current_user.username:
            raise OwnProfileFollowingException()

        target_user = await self._user_service.get_by_username(session=session, username=username)
        # 直接使用传入的 session
        if not await self._follower_service.exists(session=session, follower_id=current_user.id, following_id=target_user.id):
            logger.exception("User not followed", username=username)
            raise ProfileNotFollowedFollowedException()
        await self._follower_service.delete(
            session=session, follower_id=current_user.id, following_id=target_user.id
        )
 

