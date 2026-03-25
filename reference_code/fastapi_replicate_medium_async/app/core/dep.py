import contextlib
from typing import Optional
from collections.abc import AsyncIterator
from functools import lru_cache

from fastapi import Depends, HTTPException
from starlette import status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.schemas.user import UserDTO
from app.core.config import get_app_settings,BaseAppSettings
from app.schemas.auth import TokenPayload
from app.core.exception import IncorrectJWTTokenException
from app.services.article import ArticleService
from app.services.comment import CommentService
from app.services.auth_token import AuthTokenService
from app.services.user import UserService
from app.services.profile import ProfileService
from app.services.tag import TagService
from app.core.security import HTTPTokenHeader
from app.services.auth import UserAuthService
from app.services.favorite import FavoriteService
from app.services.follower import FollowerService



# class Container:
#     def __init__(self, settings: BaseAppSettings) -> None:
#         self._settings = settings
#         self._engine = create_async_engine(**settings.sqlalchemy_engine_props)
#         self._sessionmaker = async_sessionmaker(bind=self._engine, expire_on_commit=False)

#         # 单例缓存
#         self._auth_token_service = None
#         self._user_service = None
#         self._user_auth_service = None
#         self._follower_service = None
#         self._profile_service = None
#         self._comment_service = None
#         self._article_service = None
#         self._tag_service = None
#         self._favorite_service = None

#     @contextlib.asynccontextmanager
#     async def context_session(self) -> AsyncIterator[AsyncSession]:
#         session = self._sessionmaker()  # 修复：使用 _sessionmaker 而不是 _session
#         try:
#             yield session
#             await session.commit()
#         except Exception:
#             await session.rollback()
#             raise
#         finally:
#             await session.close()

#     async def session(self) -> AsyncIterator[AsyncSession]:
#         async with self._sessionmaker() as session:  # 修复：使用 _sessionmaker 而不是 _session
#             try:
#                 yield session
#                 await session.commit()
#             except Exception:
#                 await session.rollback()
#                 raise
#             finally:
#                 await session.close()

#     def auth_token_service(self) -> AuthTokenService:
#         if self._auth_token_service is None:
#             self._auth_token_service = AuthTokenService(
#                 secret_key=self._settings.jwt_secret_key,
#                 token_expiration_minutes=self._settings.jwt_token_expiration_minutes,
#                 algorithm=self._settings.jwt_algorithm,
#             )
#         return self._auth_token_service

#     def user_service(self) -> UserService:
#         if self._user_service is None:
#             self._user_service = UserService()
#         return self._user_service

#     def user_auth_service(self) -> UserAuthService:
#         if self._user_auth_service is None:
#             self._user_auth_service = UserAuthService(
#                 user_service=self.user_service(),
#                 auth_token_service=self.auth_token_service(),
#             )
#         return self._user_auth_service

#     def follower_service(self) -> FollowerService:
#         if self._follower_service is None:
#             self._follower_service = FollowerService()
#         return self._follower_service

#     def profile_service(self) -> ProfileService:
#         if self._profile_service is None:
#             self._profile_service = ProfileService(
#                 user_service=self.user_service(),
#                 follower_service=self.follower_service(),
#             )
#         return self._profile_service

#     def comment_service(self) -> CommentService:
#         if self._comment_service is None:
#             self._comment_service = CommentService(
#                 user_service=self.user_service(),
#                 follower_service=self.follower_service(),
#             )
#         return self._comment_service

#     def article_service(self) -> ArticleService:
#         if self._article_service is None:
#             self._article_service = ArticleService()
#         return self._article_service

#     def tag_service(self) -> TagService:
#         if self._tag_service is None:
#             self._tag_service = TagService()
#         return self._tag_service

#     def favorite_service(self) -> FavoriteService:
#         if self._favorite_service is None:
#             self._favorite_service = FavoriteService()
#         return self._favorite_service
    


# container = Container(settings=get_app_settings())


class Container:
    """Dependency injector project container."""

    def __init__(self, settings: BaseAppSettings) -> None:
        self._settings = settings
        self._engine = create_async_engine(**settings.sqlalchemy_engine_props)
        self._session = async_sessionmaker(bind=self._engine, expire_on_commit=False)



    @contextlib.asynccontextmanager
    async def context_session(self) -> AsyncIterator[AsyncSession]:
        session = self._session()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


    @lru_cache(maxsize=1)
    def auth_token_service(self) -> AuthTokenService:
        return AuthTokenService(
            secret_key=self._settings.jwt_secret_key,
            token_expiration_minutes=self._settings.jwt_token_expiration_minutes,
            algorithm=self._settings.jwt_algorithm,
        )
    

    @lru_cache(maxsize=1)
    def user_auth_service(self) -> UserAuthService:
        return UserAuthService(
            user_service=self.user_service(),
            auth_token_service=self.auth_token_service(),
        )
    
    @lru_cache(maxsize=1)
    def user_service(self) -> UserService:
        return UserService()
    
    @lru_cache(maxsize=1)
    def profile_service(self) -> ProfileService:
        return ProfileService(
            user_service=self.user_service(),
            follower_service=self.follower_service()
            )
    
    @lru_cache(maxsize=1)
    def tag_service(self) -> TagService:
        return TagService()


    @lru_cache(maxsize=1)
    def article_service(self) -> ArticleService:
        return ArticleService()
    

    @lru_cache(maxsize=1)
    def comment_service(self) -> CommentService:
        return CommentService(
            user_service=self.user_service(),
            follower_service=self.follower_service()
        )
    
    @lru_cache(maxsize=1)
    def follower_service(self) -> FollowerService:
        return FollowerService()
    
    @lru_cache(maxsize=1)
    def favorite_service(self) -> FavoriteService:
        return FavoriteService()
          
container = Container(settings=get_app_settings())

token_security = HTTPTokenHeader(
    name="Authorization",
    scheme_name="JWT Token",
    description="Token Format: `Token xxxxxx.yyyyyyy.zzzzzz`",
    raise_error=True,
)
token_security_optional = HTTPTokenHeader(
    name="Authorization",
    scheme_name="JWT Token",
    description="Token Format: `Token xxxxxx.yyyyyyy.zzzzzz`",
    raise_error=False,
)



async def get_current_user(
    session: AsyncSession = Depends(container.session),
    token: str = Depends(token_security),
    auth_token_service: AuthTokenService = Depends(container.auth_token_service),
    user_service: UserService = Depends(container.user_service),
) -> UserDTO:
    """
    获取当前用户，必须提供有效的 token，否则返回 401 错误。
    """
    try:
        token_payload: TokenPayload = auth_token_service.parse_jwt_token(token)
    except IncorrectJWTTokenException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = await user_service.get_user_by_id(session=session, user_id=token_payload.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserDTO(
        id=user.id,
        email=user.email,
        username=user.username,
        bio=user.bio,
        image=user.image_url,
        password_hash=user.password_hash,
        created_at=user.created_at
    )

async def get_current_user_or_none(
    session: AsyncSession = Depends(container.session),
    token: str = Depends(token_security_optional),
    auth_token_service: AuthTokenService = Depends(container.auth_token_service),
    user_service: UserService = Depends(container.user_service),
) -> Optional[UserDTO]:
    """
    尝试获取当前用户，如果无效或未提供 token，返回 None。
    """
    if not token:
        return None

    try:
        token_payload: TokenPayload = auth_token_service.parse_jwt_token(token)
    except IncorrectJWTTokenException:
        return None

    user = await user_service.get_user_by_id(session=session, user_id=token_payload.user_id)
    if not user:
        return None

    return UserDTO(
        id=user.id,
        email=user.email,
        username=user.username,
        bio=user.bio,
        image_url=user.image_url,
        password_hash=user.password_hash,
        created_at=user.created_at
    )
