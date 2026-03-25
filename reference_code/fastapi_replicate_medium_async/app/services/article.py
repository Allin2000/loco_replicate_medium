from datetime import datetime
from typing import  List, Optional


from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, joinedload # Import joinedload
from sqlalchemy import (
    delete,
    exists,
    func,
    select,
    update,
    desc,
    and_,
)


from app.core.exception import ArticleNotFoundException
from app.sqlmodel.alembic_model import Article, ArticleTag, Favorite, Follower, Tag, User
from app.core.slug import (
    get_slug_unique_part,
    make_slug_from_title,
    make_slug_from_title_and_code,
)
from app.schemas.article import (
    ArticleRecordDTO,
    CreateArticleDTO,
    UpdateArticleDTO,
    ArticleAuthorDTO,
    ArticleDTO,
    ArticlesFeedDTO,
    DEFAULT_ARTICLES_LIMIT,
    DEFAULT_ARTICLES_OFFSET,
)

# Aliases for clarity in joins
FavoriteAlias = aliased(Favorite)
TagAlias = aliased(Tag)


class ArticleService:

    async def add(
        self, session: AsyncSession, author_id: int, create_item: CreateArticleDTO
    ) -> ArticleDTO:
        # Generate slug and ensure uniqueness
        base_slug = make_slug_from_title(create_item.title)
        existing_slug_count_query = select(func.count(Article.id)).where(Article.slug.like(f"{base_slug}%"))
        existing_slug_count = (await session.execute(existing_slug_count_query)).scalar_one()

        if existing_slug_count > 0:
            # Append a unique part if a similar slug already exists
            slug = make_slug_from_title_and_code(create_item.title, get_slug_unique_part())
        else:
            slug = base_slug

        now = datetime.utcnow()
        db_article = Article(
            author_id=author_id,
            slug=slug,
            title=create_item.title,
            description=create_item.description,
            body=create_item.body,
            created_at=now,
            updated_at=now,
        )
        session.add(db_article)
        await session.flush()  # Flush to get db_article.id

        # Handle tags
        article_tags_list: List[str] = []
        if create_item.tags:
            for tag_name in create_item.tags:
                # Check if tag already exists, create if not
                existing_tag_query = select(Tag).where(Tag.tag == tag_name)
                db_tag = (await session.execute(existing_tag_query)).unique().scalar_one_or_none()
                if not db_tag:
                    db_tag = Tag(tag=tag_name, created_at=now)
                    session.add(db_tag)
                    await session.flush() # Flush to get db_tag.id

                # Link article to tag
                db_article_tag = ArticleTag(article_id=db_article.id, tag_id=db_tag.id, created_at=now)
                session.add(db_article_tag)
                article_tags_list.append(tag_name)

        # Fetch author information
        user_query = select(User).where(User.id == author_id)
        user = (await session.execute(user_query)).scalar_one()

        author_dto = ArticleAuthorDTO(
            username=user.username,
            bio=user.bio or "",
            image=user.image_url, # Use image_url from User model
            following=False, # New article, author is not necessarily followed by current user
            id=user.id,
        )

        return ArticleDTO(
            id=db_article.id,
            author_id=db_article.author_id,
            slug=db_article.slug,
            title=db_article.title,
            description=db_article.description,
            body=db_article.body,
            tags=article_tags_list,
            author=author_dto,
            createdAt=db_article.created_at,
            updatedAt=db_article.updated_at,
            favorited=False,
            favoritesCount=0,
        )

    async def get_by_slug_or_none(
        self, session: AsyncSession, slug: str
    ) -> Optional[ArticleRecordDTO]:
        query = select(Article).where(Article.slug == slug)
        article = await session.scalar(query)
        if article:
            return ArticleRecordDTO(
                id=article.id,
                author_id=article.author_id,
                slug=article.slug,
                title=article.title,
                description=article.description,
                body=article.body,
                created_at=article.created_at,
                updated_at=article.updated_at,
            )
        return None

    async def get_by_slug(self, session: AsyncSession, slug: str, current_user_id: Optional[int] = None) -> ArticleDTO:
        # Load Article, its author, and tags
        stmt = select(Article).options(
            # Assuming you have a relationship named 'author_rel' in Article model pointing to User
            # If not, you should add one or use joinedload(User)
            joinedload(Article.author), # Use 'author' if that's the relationship name to User
            joinedload(Article.article_tags).joinedload(ArticleTag.tag_obj) # Load ArticleTags and then the associated Tag object
        ).where(Article.slug == slug)

        result = await session.execute(stmt)
        db_article = result.unique().scalar_one_or_none()

        if not db_article:
            raise ArticleNotFoundException()

        # Get tags list from the loaded ArticleTag objects
        tags_list = [article_tag.tag_obj.tag for article_tag in db_article.article_tags if article_tag.tag_obj]

        # Check if the author is followed by the current user
        is_following_author = False
        if current_user_id and db_article.author_id:
            follow_query = select(exists().where(
                and_(Follower.follower_id == current_user_id, Follower.following_id == db_article.author_id)
            ))
            is_following_author = (await session.execute(follow_query)).scalar_one()

        author_dto = ArticleAuthorDTO(
            username=db_article.author.username, # Access username through the loaded author relationship
            bio=db_article.author.bio or "",
            image=db_article.author.image_url, # Access image_url through the loaded author relationship
            following=is_following_author,
            id=db_article.author.id,
        )

        # Query favorite count
        favorites_count_query = select(func.count(Favorite.article_id)).where(Favorite.article_id == db_article.id)
        favorites_count = (await session.execute(favorites_count_query)).scalar_one()

        # Check if the article is favorited by the current user
        is_favorited = False
        if current_user_id:
            favorited_query = select(exists().where(
                and_(Favorite.user_id == current_user_id, Favorite.article_id == db_article.id)
            ))
            is_favorited = (await session.execute(favorited_query)).scalar_one()

        return ArticleDTO(
            id=db_article.id,
            author_id=db_article.author_id,
            slug=db_article.slug,
            title=db_article.title,
            description=db_article.description,
            body=db_article.body,
            tags=tags_list,
            author=author_dto,
            createdAt=db_article.created_at,
            updatedAt=db_article.updated_at,
            favorited=is_favorited,
            favoritesCount=favorites_count,
        )

    async def delete_by_slug(self, session: AsyncSession, slug: str) -> None:
        # Get article ID
        article_id_result = await session.execute(select(Article.id).where(Article.slug == slug))
        article_id = article_id_result.unique().scalar_one_or_none()

        if not article_id:
            raise ArticleNotFoundException()

        # Delete related records first due to foreign key constraints (CASCADE might handle this, but explicit is safer)
        await session.execute(delete(ArticleTag).where(ArticleTag.article_id == article_id))
        await session.execute(delete(Favorite).where(Favorite.article_id == article_id))
        
        # Delete the article
        result = await session.execute(delete(Article).where(Article.id == article_id))
        if result.rowcount == 0:
            # This should ideally not happen if article_id was found, but good for robustness
            raise ArticleNotFoundException()

    async def update_by_slug(
        self, session: AsyncSession, slug: str, update_item: UpdateArticleDTO, current_user_id: Optional[int] = None
    ) -> ArticleDTO:
        # Fetch the article
        query = select(Article).where(Article.slug == slug)
        article = await session.scalar(query)
        if not article:
            raise ArticleNotFoundException()

        update_data = update_item.model_dump(exclude_unset=True, by_alias=False)

        tags_to_update = update_data.pop("tags", None) # Extract tags separately

        # Handle title change and slug update
        if "title" in update_data and update_data["title"] != article.title:
            new_base_slug = make_slug_from_title(update_data["title"])
            existing_slug_count_query = select(func.count(Article.id)).where(
                and_(Article.slug.like(f"{new_base_slug}%"), Article.id != article.id)
            )
            existing_slug_count = (await session.execute(existing_slug_count_query)).scalar_one()
            if existing_slug_count > 0:
                new_slug = make_slug_from_title_and_code(update_data["title"], get_slug_unique_part())
            else:
                new_slug = new_base_slug
            update_data["slug"] = new_slug

        update_data["updated_at"] = datetime.utcnow()

        # Update article fields in database
        if update_data:
            await session.execute(
                update(Article)
                .where(Article.id == article.id)
                .values(**update_data)
            )
            await session.flush() # Ensure updates are applied before refreshing

        # Update tags
        if tags_to_update is not None: # Check if tags were even provided in the update payload
            # Delete existing tags for this article
            await session.execute(delete(ArticleTag).where(ArticleTag.article_id == article.id))
            
            if tags_to_update: # Add new tags if provided
                now = datetime.utcnow()
                for tag_name in tags_to_update:
                    # Find or create tag
                    existing_tag_query = select(Tag).where(Tag.tag == tag_name)
                    db_tag = (await session.execute(existing_tag_query)).unique().scalar_one_or_none()
                    if not db_tag:
                        db_tag = Tag(tag=tag_name, created_at=now)
                        session.add(db_tag)
                        await session.flush() # Flush to get new tag ID

                    # Link article to tag
                    db_article_tag = ArticleTag(article_id=article.id, tag_id=db_tag.id, created_at=now)
                    session.add(db_article_tag)
            await session.flush()

        # Refresh article to get latest state for DTO conversion
        await session.refresh(article)
        
        # Use get_by_slug to return a complete ArticleDTO, including author, tags, favorites
        updated_article_dto = await self.get_by_slug(session, article.slug, current_user_id=current_user_id)
        return updated_article_dto

    async def list_by_followings(
        self, session: AsyncSession, user_id: int, limit: int = DEFAULT_ARTICLES_LIMIT, offset: int = DEFAULT_ARTICLES_OFFSET
    ) -> ArticlesFeedDTO:
        # Count query for total articles
        total_articles_query = select(func.count(Article.id)).join(
            Follower, Follower.following_id == Article.author_id
        ).where(Follower.follower_id == user_id)
        articles_count = (await session.execute(total_articles_query)).scalar_one()

        # Main query to fetch articles with aggregated data
        # Use joinedload for efficient loading of related User and Tag data
        articles_query = (
            select(Article)
            .join(Follower, (Follower.following_id == Article.author_id) & (Follower.follower_id == user_id))
            .options(
                joinedload(Article.author), # Load the author (User)
                joinedload(Article.article_tags).joinedload(ArticleTag.tag_obj) # Load tags
            )
            .order_by(desc(Article.created_at))
            .limit(limit)
            .offset(offset)
        )

        articles_result = await session.execute(articles_query)
        db_articles = articles_result.scalars().unique().all() # Use scalars().unique().all() to get Article objects

        articles_dtos: List[ArticleDTO] = []
        for db_article in db_articles:
            # Author DTO
            author_dto = ArticleAuthorDTO(
                username=db_article.author.username,
                bio=db_article.author.bio or "",
                image=db_article.author.image_url,
                following=True, # Since this list is of followings
                id=db_article.author.id,
            )

            # Get tags list from loaded ArticleTag objects
            tags: List[str] = [article_tag.tag_obj.tag for article_tag in db_article.article_tags if article_tag.tag_obj]

            # Query favorites count for each article
            favorites_count_query = select(func.count(Favorite.article_id)).where(Favorite.article_id == db_article.id)
            favorites_count = (await session.execute(favorites_count_query)).scalar_one()

            # Check if current user favorited this article
            is_favorited = False
            if user_id: # Assuming user_id here is the current logged-in user
                favorited_query = select(exists().where(
                    and_(Favorite.user_id == user_id, Favorite.article_id == db_article.id)
                ))
                is_favorited = (await session.execute(favorited_query)).scalar_one()

            articles_dtos.append(
                ArticleDTO(
                    id=db_article.id,
                    author_id=db_article.author_id,
                    slug=db_article.slug,
                    title=db_article.title,
                    description=db_article.description,
                    body=db_article.body,
                    tags=tags,
                    author=author_dto,
                    createdAt=db_article.created_at,
                    updatedAt=db_article.updated_at,
                    favorited=is_favorited,
                    favoritesCount=favorites_count,
                )
            )

        return ArticlesFeedDTO(articles=articles_dtos, articlesCount=articles_count)

    async def list_by_filters(
        self,
        session: AsyncSession,
        limit: int = DEFAULT_ARTICLES_LIMIT,
        offset: int = DEFAULT_ARTICLES_OFFSET,
        tag: Optional[str] = None,
        author: Optional[str] = None,
        favorited: Optional[str] = None,
        current_user_id: Optional[int] = None,
    ) -> ArticlesFeedDTO:

        # Base query for counting articles
        count_query = (
            select(func.count(Article.id))
            .join(User, User.id == Article.author_id)
        )
        # Base query for fetching articles
        articles_query = (
            select(Article)
            .join(User, User.id == Article.author_id)
            .options(
                joinedload(Article.author),
                joinedload(Article.article_tags).joinedload(ArticleTag.tag_obj)
            )
        )

        # Apply filters to both queries
        if tag:
            count_query = count_query.join(ArticleTag, Article.id == ArticleTag.article_id).join(Tag, ArticleTag.tag_id == Tag.id).where(Tag.tag == tag)
            articles_query = articles_query.join(ArticleTag, Article.id == ArticleTag.article_id).join(Tag, ArticleTag.tag_id == Tag.id).where(Tag.tag == tag)

        if author:
            count_query = count_query.where(User.username == author)
            articles_query = articles_query.where(User.username == author)

        if favorited:
            favorited_user_id_query = select(User.id).where(User.username == favorited)
            _favorited_user_id = (await session.execute(favorited_user_id_query)).unique().scalar_one_or_none()
            if not _favorited_user_id:
                return ArticlesFeedDTO(articles=[], articlesCount=0) # If favorited user doesn't exist, no articles
            
            # Apply join for favorited filter
            count_query = count_query.join(Favorite, (Favorite.article_id == Article.id) & (Favorite.user_id == _favorited_user_id))
            articles_query = articles_query.join(Favorite, (Favorite.article_id == Article.id) & (Favorite.user_id == _favorited_user_id))


        # Execute count query first
        articles_count = (await session.execute(count_query)).scalar_one()

        # Apply ordering and pagination for articles query
        articles_query = articles_query.order_by(desc(Article.created_at)).limit(limit).offset(offset)

        articles_result = await session.execute(articles_query)
        db_articles = articles_result.scalars().unique().all()

        articles_dtos: List[ArticleDTO] = []
        for db_article in db_articles:
            # Check if author is followed by current user
            is_following_author = False
            if current_user_id and db_article.author_id:
                follow_check = await session.execute(
                    select(exists().where(
                        and_(Follower.follower_id == current_user_id, Follower.following_id == db_article.author_id)
                    ))
                )
                is_following_author = follow_check.scalar_one()

            author_dto = ArticleAuthorDTO(
                username=db_article.author.username,
                bio=db_article.author.bio or "",
                image=db_article.author.image_url,
                following=is_following_author,
                id=db_article.author.id,
            )

            # tags: List[str] = [article_tag.tag_obj.tag for article_tag in db_article.article_tags if article_tag.tag_obj]

                        # 修改为：获取标签名称列表后进行字母排序
            tags: List[str] = sorted([
                article_tag.tag_obj.tag
                for article_tag in db_article.article_tags
                if article_tag.tag_obj # 确保 tag_obj 存在
            ]) # <-- 增加 sorted() 函数进行排序

            # Query favorites count for each article
            favorites_count_query = select(func.count(Favorite.article_id)).where(Favorite.article_id == db_article.id)
            favorites_count = (await session.execute(favorites_count_query)).scalar_one()

            # Check if article is favorited by current user
            is_favorited = False
            if current_user_id:
                favorited_query = select(exists().where(
                    and_(Favorite.user_id == current_user_id, Favorite.article_id == db_article.id)
                ))
                is_favorited = (await session.execute(favorited_query)).scalar_one()


            articles_dtos.append(
                ArticleDTO(
                    id=db_article.id,
                    author_id=db_article.author_id,
                    slug=db_article.slug,
                    title=db_article.title,
                    description=db_article.description,
                    body=db_article.body,
                    tags=tags,
                    author=author_dto,
                    createdAt=db_article.created_at,
                    updatedAt=db_article.updated_at,
                    favorited=is_favorited,
                    favoritesCount=favorites_count,
                )
            )

        return ArticlesFeedDTO(articles=articles_dtos, articlesCount=articles_count)


    async def count_by_followings(self, session: AsyncSession, user_id: int) -> int:
        query = select(func.count(Article.id)).join(
            Follower, and_(Follower.following_id == Article.author_id, Follower.follower_id == user_id)
        )
        result = await session.execute(query)
        return result.scalar_one()

    async def count_by_filters(
        self,
        session: AsyncSession,
        tag: Optional[str] = None,
        author: Optional[str] = None,
        favorited: Optional[str] = None,
    ) -> int:
        query = select(func.count(Article.id))

        if tag:
            query = query.join(ArticleTag, Article.id == ArticleTag.article_id).join(Tag, ArticleTag.tag_id == Tag.id).where(Tag.tag == tag)

        if author:
            query = query.join(User, User.id == Article.author_id).where(User.username == author)

        if favorited:
            query = query.join(Favorite, Favorite.article_id == Article.id).where(
                Favorite.user_id == select(User.id).where(User.username == favorited).scalar_subquery()
            )

        result = await session.execute(query)
        return result.scalar_one()