from typing import Optional

from fastapi import APIRouter, Path, Depends, HTTPException
from starlette import status
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger # 确保导入 logger

from app.schemas.comment import CreateCommentRequest
from app.schemas.comment import CommentResponse, CommentsListResponse
from app.schemas.user import UserDTO
from app.services.comment import CommentService
from app.core.exception import ( # 导入可能抛出的新异常
    ArticleNotFoundException,
    CommentNotFoundException,
                            )
from app.core.dep import (
    get_current_user_or_none,
    get_current_user,
    container
            )


logger = get_logger()

router = APIRouter()


@router.get("/{slug}/comments", response_model=CommentsListResponse)
async def get_comments(
    slug: str,
    session: AsyncSession = Depends(container.session),
    current_user: Optional[UserDTO] = Depends(get_current_user_or_none),
    comment_service: CommentService = Depends(container.comment_service)
) -> CommentsListResponse:
    """
    获取一篇文章的所有评论。
    """
    try:
        comments_list_dto = await comment_service.get_comments_for_article(
            session=session, slug=slug, current_user=current_user
        )
        return CommentsListResponse.from_dto(dto=comments_list_dto)
    except ArticleNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found."
        )
    except Exception as e:
        logger.error(f"Error getting comments for article with slug: {slug}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        )


@router.post("/{slug}/comments", response_model=CommentResponse)
async def create_comment(
    slug: str,
    payload: CreateCommentRequest,
    session: AsyncSession = Depends(container.session),
    current_user: UserDTO = Depends(get_current_user), # 必须认证用户才能创建评论
    comment_service: CommentService = Depends(container.comment_service)
) -> CommentResponse:
    """
    为指定文章创建一条评论。
    """
    try:
        comment_dto = await comment_service.create_comment_for_article(
            session=session,
            slug=slug,
            comment_to_create=payload.to_dto(), # 假设 CreateCommentRequest 有 to_dto 方法
            current_user=current_user,
        )
        return CommentResponse.from_dto(dto=comment_dto)
    except ArticleNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found."
        )
    except Exception as e:
        logger.error(f"Error getting comments for article with slug: {slug}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        )


@router.delete("/{slug}/comments/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    slug: str,
    session: AsyncSession = Depends(container.session),
    current_user: UserDTO = Depends(get_current_user), # 必须认证用户才能删除评论
    comment_service: CommentService = Depends(container.comment_service),
    comment_id: int = Path(..., alias="id"),
) -> None:
    """
    删除指定文章中的评论。
    """
    try:
        await comment_service.delete_comment_from_article(
            session=session, slug=slug, comment_id=comment_id, current_user=current_user
        )
    except ArticleNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found."
        )
    except CommentNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found."
        )
    except Exception as e:
        logger.error(f"Error getting comments for article with slug: {slug}comment_id{comment_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        )
