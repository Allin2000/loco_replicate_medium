from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.sqlmodel.alembic_model import Tag
from app.schemas.tag import TagDTO  # 导入 Pydantic 模型


class TagService:
    """Service for Tag model, without DTO conversion."""

    async def list(self, session: AsyncSession) -> list[TagDTO]:
        query = select(Tag)
        tags = await session.scalars(query)
        return [TagDTO.from_model(tag) for tag in tags]
