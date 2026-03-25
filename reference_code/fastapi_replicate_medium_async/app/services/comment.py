from datetime import datetime
from typing import List, Optional

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count
from structlog import get_logger # 确保导入 logger

from app.core.exception import (
    CommentNotFoundException,
    ArticleNotFoundException, # 可能需要，如果你的路由会先根据 slug 查找文章
    UserNotFoundException, # 可能需要，如果作者不存在
)
from app.sqlmodel.alembic_model import Comment, Article # 导入 Article 模型
from app.schemas.comment import (
    CreateCommentDTO,
    CommentRecordDTO,
    CommentDTO,
    CommentsListDTO
)
from app.schemas.profile import ProfileDTO
from app.schemas.user import UserDTO
from app.services.user import UserService # 导入 UserService
from app.services.follower import FollowerService # 导入 FollowerService


logger = get_logger()

class CommentService:
    def __init__(self, user_service: UserService, follower_service: FollowerService):
        self._user_service = user_service
        self._follower_service = follower_service

    # --- 核心业务逻辑方法（面向路由） ---

    async def get_comments_for_article(
        self, session: AsyncSession, slug: str, current_user: Optional[UserDTO] = None
    ) -> CommentsListDTO:
        """
        根据文章 slug 获取评论列表，并包含作者资料和关注状态。
        """
        # 首先获取文章ID (假设你的文章服务可以根据 slug 获取文章)
        # 这里需要一个获取文章的方法，例如 article_service.get_article_by_slug
        # 为了简化，这里假设你能直接获取 article_id
        article = await session.scalar(select(Article).where(Article.slug == slug))
        if not article:
            raise ArticleNotFoundException() # 确保定义了这个异常

        query = select(Comment).where(Comment.article_id == article.id)
        comments_records = (await session.scalars(query)).all()

        comment_dtos = []
        for comment_record in comments_records:
            comment_dto = await self._build_comment_dto_with_profile(
                session=session,
                comment_record=comment_record,
                current_user=current_user
            )
            comment_dtos.append(comment_dto)

        return CommentsListDTO(comments=comment_dtos, commentsCount=len(comment_dtos))

    async def create_comment_for_article(
        self,
        session: AsyncSession,
        slug: str,
        comment_to_create: CreateCommentDTO,
        current_user: UserDTO,
    ) -> CommentDTO:
        """
        为指定文章创建一条评论。
        """
        article = await session.scalar(select(Article).where(Article.slug == slug))
        if not article:
            raise ArticleNotFoundException()

        query = (
            insert(Comment)
            .values(
                author_id=current_user.id,
                article_id=article.id,
                body=comment_to_create.body,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            .returning(Comment)
        )
        result = await session.execute(query)
        await session.commit()
        new_comment_record = result.scalar_one()

        # 构建包含作者资料和关注状态的 CommentDTO
        comment_dto = await self._build_comment_dto_with_profile(
            session=session,
            comment_record=new_comment_record,
            current_user=current_user
        )
        return comment_dto

    async def delete_comment_from_article(
        self, session: AsyncSession, slug: str, comment_id: int, current_user: UserDTO
    ) -> None:
        """
        从指定文章中删除一条评论。
        需要验证评论是否存在且当前用户是作者。
        """
        article = await session.scalar(select(Article).where(Article.slug == slug))
        if not article:
            raise ArticleNotFoundException()

        comment = await session.scalar(
            select(Comment).where(Comment.id == comment_id, Comment.article_id == article.id)
        )
        if not comment:
            raise CommentNotFoundException()

        if comment.author_id != current_user.id:
            # 如果不是作者，抛出未授权异常
            raise UserNotFoundException("You are not authorized to delete this comment.")

        query = delete(Comment).where(Comment.id == comment_id)
        await session.execute(query)
        await session.commit()

    # --- 辅助方法（内部使用或更底层的CRUD） ---

    async def _build_comment_dto_with_profile(
        self, session: AsyncSession, comment_record: Comment, current_user: Optional[UserDTO]
    ) -> CommentDTO:
        """
        根据 Comment SQLAlchemy 模型和当前用户，构建包含 ProfileDTO 的 CommentDTO。
        """
        author_user = await self._user_service.get_user_by_id(
            session=session, user_id=comment_record.author_id
        )
        if not author_user:
            # 这种情况通常不应该发生，因为评论总是有作者
            logger.error("Comment author not found", author_id=comment_record.author_id)
            raise UserNotFoundException(f"Author with ID {comment_record.author_id} for comment {comment_record.id} not found.")

        # 判断当前用户是否关注了作者
        is_following = False
        if current_user:
            is_following = await self._follower_service.exists(
                session=session,
                follower_id=current_user.id,
                following_id=author_user.id
            )

        profile_dto = ProfileDTO(
            user_id=author_user.id,
            username=author_user.username,
            bio=author_user.bio,
            image=author_user.image_url,
            following=is_following,
        )

        return CommentDTO(
            id=comment_record.id,
            body=comment_record.body,
            author=profile_dto,
            createdAt=comment_record.created_at,
            updatedAt=comment_record.updated_at,
        )

    # --- 原始的CommentRecordDTO操作，如果它们仍然在其他地方被直接需要，则保留 ---
    # 通常这些方法会被高层业务方法调用，而不是直接暴露给路由层

    async def get_comment_record_by_id_or_none(
        self, session: AsyncSession, comment_id: int
    ) -> Optional[CommentRecordDTO]:
        """
        根据 ID 获取评论记录，如果不存在则返回 None。
        """
        query = select(Comment).where(Comment.id == comment_id)
        comment = await session.scalar(query)
        if comment:
            return self._to_comment_record_dto(comment)
        return None

    async def get_comment_record_by_id(self, session: AsyncSession, comment_id: int) -> CommentRecordDTO:
        """
        根据 ID 获取评论记录，如果不存在则抛出 CommentNotFoundException。
        """
        comment_record = await self.get_comment_record_by_id_or_none(session, comment_id)
        if not comment_record:
            raise CommentNotFoundException()
        return comment_record

    async def get_comment_records_by_article_id(
        self, session: AsyncSession, article_id: int
    ) -> List[CommentRecordDTO]:
        """
        根据文章 ID 获取所有评论记录。
        """
        query = select(Comment).where(Comment.article_id == article_id)
        comments = await session.scalars(query)
        return [self._to_comment_record_dto(c) for c in comments]

    async def count_comments_by_article_id(self, session: AsyncSession, article_id: int) -> int:
        """
        统计指定文章的评论数量。
        """
        query = select(count(Comment.id)).where(Comment.article_id == article_id)
        result = await session.execute(query)
        return result.scalar_one()

    # --- 内部辅助转换方法 ---
    @staticmethod
    def _to_comment_record_dto(comment: Comment) -> CommentRecordDTO:
        """
        将 SQLAlchemy Comment 模型转换为 CommentRecordDTO。
        """
        return CommentRecordDTO(
            id=comment.id,
            body=comment.body,
            author_id=comment.author_id,
            article_id=comment.article_id,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
        )