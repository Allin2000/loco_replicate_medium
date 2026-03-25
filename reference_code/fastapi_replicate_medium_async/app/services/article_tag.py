from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.sqlmodel.alembic_model import ArticleTag, Tag
from app.schemas.tag import TagDTO  


class ArticleTagService:

    async def add_many(
        self, session: AsyncSession, article_id: int, tags: list[str]
    ) -> list[TagDTO]:  
        insert_tag_query = (
            insert(Tag)
            .on_conflict_do_nothing()
            .values([{"tag": tag, "created_at": datetime.now()} for tag in tags])
            .returning(Tag)
        )
        result = await session.execute(insert_tag_query)
        tag_objects = result.scalars().all()

        link_values = [
            {"article_id": article_id, "tag_id": tag.id, "created_at": datetime.now()}
            for tag in tag_objects
        ]
        insert_link_query = insert(ArticleTag).on_conflict_do_nothing().values(link_values)
        await session.execute(insert_link_query)
        await session.commit()

      
        return [TagDTO.from_model(tag) for tag in tag_objects]

    async def list(self, session: AsyncSession, article_id: int) -> list[TagDTO]:  
        query = (
            select(Tag)
            .join(ArticleTag, (ArticleTag.tag_id == Tag.id) & (ArticleTag.article_id == article_id))
            .order_by(Tag.created_at.desc())
        )
        result = await session.execute(query)
        tags = result.scalars().all()
        return [TagDTO.from_model(tag) for tag in tags]  