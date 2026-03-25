from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Query, HTTPException
from starlette import status

from app.schemas.user import UserDTO
from app.services.article import ArticleService
from app.services.favorite import FavoriteService
from app.core.dep import container
from app.core.dep import get_current_user, get_current_user_or_none
from app.schemas.article import (
    ArticleResponse,
    ArticlesFeedDTO,
    CreateArticleRequest,
    UpdateArticleDTO,
)

router = APIRouter()


@router.get("/feed", response_model=ArticlesFeedDTO)
async def get_article_feed(
    session: AsyncSession = Depends(container.session),
    current_user: UserDTO = Depends(get_current_user),
    article_service: ArticleService = Depends(container.article_service),
    limit: int = Query(20, ge=1),
    offset: int = Query(0, ge=0),
) -> ArticlesFeedDTO:
    """
    Get article feed from following users.
    """
    # The list_by_followings method now returns ArticlesFeedDTO directly
    articles_feed = await article_service.list_by_followings(
        session=session, user_id=current_user.id, limit=limit, offset=offset
    )
    # The count is already part of the ArticlesFeedDTO returned by the service
    return articles_feed


@router.get("", response_model=ArticlesFeedDTO)
async def get_global_article_feed(
    session: AsyncSession = Depends(container.session),
    current_user: Optional[UserDTO] = Depends(get_current_user_or_none),
    article_service: ArticleService = Depends(container.article_service),
    tag: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    favorited: Optional[str] = Query(None),
    limit: int = Query(20, ge=1),
    offset: int = Query(0, ge=0),
) -> ArticlesFeedDTO:
    """
    Get global article feed.
    """
    user_id = current_user.id if current_user else None
    # The list_by_filters method now returns ArticlesFeedDTO directly
    articles_feed = await article_service.list_by_filters(
        session=session,
        current_user_id=user_id, # Pass current_user_id to correctly set favorited/following
        tag=tag,
        author=author,
        favorited=favorited,
        limit=limit,
        offset=offset,
    )
    # The count is already part of the ArticlesFeedDTO returned by the service
    return articles_feed



@router.post("", response_model=ArticleResponse)
async def create_article(
    payload: CreateArticleRequest,
    session: AsyncSession = Depends(container.session),
    current_user: UserDTO = Depends(get_current_user),
    article_service: ArticleService = Depends(container.article_service),
) -> ArticleResponse:
    """
    Create new article.
    """
    # The 'add' method in ArticleService now handles tag creation and returns the full ArticleDTO
    article_dto = await article_service.add(session=session, author_id=current_user.id, create_item=payload.to_dto())
    return ArticleResponse(article=article_dto)


@router.put("/{slug}", response_model=ArticleResponse)
async def update_article(
    slug: str,
    payload: UpdateArticleDTO,
    session: AsyncSession = Depends(container.session),
    current_user: UserDTO = Depends(get_current_user),
    article_service: ArticleService = Depends(container.article_service),
) -> ArticleResponse:
    """
    Update an article.
    """
    # First, get the article to check authorization
    existing_article = await article_service.get_by_slug(session=session, slug=slug, current_user_id=current_user.id)
    if existing_article.author.id != current_user.id: # Use existing_article.author.id since it's now populated
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this article")

    # The 'update_by_slug' method now handles tag updates and returns the full ArticleDTO
    article_dto = await article_service.update_by_slug(
        session=session, slug=slug, update_item=payload, current_user_id=current_user.id
    )
    return ArticleResponse(article=article_dto)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(
    slug: str,
    session: AsyncSession = Depends(container.session),
    current_user: UserDTO = Depends(get_current_user),
    article_service: ArticleService = Depends(container.article_service),
) -> None:
    """
    Delete an article by slug.
    """
    # Get the article to check authorization (pass current_user.id for accurate DTO)
    article = await article_service.get_by_slug(session=session, slug=slug, current_user_id=current_user.id)
    if article.author.id != current_user.id: # Use article.author.id
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this article")
    
    await article_service.delete_by_slug(session=session, slug=slug)




@router.get("/{slug}", response_model=ArticleResponse)
async def get_article(
    slug: str,
    session: AsyncSession = Depends(container.session),
    current_user: Optional[UserDTO] = Depends(get_current_user_or_none),
    article_service: ArticleService = Depends(container.article_service),
) -> ArticleResponse:
    """
    Get an article by slug.
    """
    user_id = current_user.id if current_user else None
    # The 'get_by_slug' method now returns the full ArticleDTO, including favorited and following status
    article_dto = await article_service.get_by_slug(session=session, slug=slug, current_user_id=user_id)
    return ArticleResponse(article=article_dto)


@router.post("/{slug}/favorite", response_model=ArticleResponse)
async def favorite_article(
    slug: str,
    session: AsyncSession = Depends(container.session),
    current_user: UserDTO = Depends(get_current_user),
    article_service: ArticleService = Depends(container.article_service),
    favorite_service: FavoriteService = Depends(container.favorite_service)
) -> ArticleResponse:
    """
    Favorite an article.
    """
    # Get the article (need current_user_id to properly get the 'favorited' status for the response)
    article_dto = await article_service.get_by_slug(session=session, slug=slug, current_user_id=current_user.id)

    if not await favorite_service.exists(session, current_user.id, article_dto.id):
        await favorite_service.create(session, article_dto.id, current_user.id)
    
    # Re-fetch the article to get updated favorite count and ensure 'favorited' is true
    # This ensures the response reflects the latest state from the database
    updated_article_dto = await article_service.get_by_slug(session=session, slug=slug, current_user_id=current_user.id)
    return ArticleResponse(article=updated_article_dto)


@router.delete("/{slug}/favorite", response_model=ArticleResponse)
async def unfavorite_article(
    slug: str,
    session: AsyncSession = Depends(container.session),
    current_user: UserDTO = Depends(get_current_user), # Should be `get_current_user` as unfavoriting requires authentication
    article_service: ArticleService = Depends(container.article_service),
    favorite_service: FavoriteService = Depends(container.favorite_service)
) -> ArticleResponse:
    """
    Unfavorite an article.
    """
    # Get the article
    article_dto = await article_service.get_by_slug(session=session, slug=slug, current_user_id=current_user.id)

    if await favorite_service.exists(session, current_user.id, article_dto.id):
        await favorite_service.delete(session, article_dto.id, current_user.id)
    
    # Re-fetch the article to get updated favorite count and ensure 'favorited' is false
    updated_article_dto = await article_service.get_by_slug(session=session, slug=slug, current_user_id=current_user.id)
    return ArticleResponse(article=updated_article_dto)