from datetime import datetime
from typing import List

from sqlalchemy import delete, exists, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.sqlmodel.alembic_model import Follower


class FollowerService:
    """Service for Follower model, without DTO conversion."""

    async def exists(
        self, session: AsyncSession, follower_id: int, following_id: int
    ) -> bool:
        query = (
            exists()
            .where(
                Follower.follower_id == follower_id,
                Follower.following_id == following_id,
            )
            .select()
        )
        result = await session.execute(query)
        return result.scalar_one()

    async def list(
        self, session: AsyncSession, follower_id: int, following_ids: List[int]
    ) -> List[int]:
        query = select(Follower.following_id).where(
            Follower.following_id.in_(following_ids),
            Follower.follower_id == follower_id,
        )
        result = await session.execute(query)
        return list(result.scalars())

    async def create(
        self, session: AsyncSession, follower_id: int, following_id: int
    ) -> None:
        query = insert(Follower).values(
            follower_id=follower_id,
            following_id=following_id,
            created_at=datetime.now(),
        )
        await session.execute(query)
        await session.commit()  # 确保数据写入

    async def delete(
        self, session: AsyncSession, follower_id: int, following_id: int
    ) -> None:
        query = delete(Follower).where(
            Follower.follower_id == follower_id, Follower.following_id == following_id
        )
        await session.execute(query)
        await session.commit()  # 确保数据写入