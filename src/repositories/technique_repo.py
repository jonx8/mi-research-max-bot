import random
from typing import Optional, List

from sqlalchemy import select

from src.database import Database
from src.models import Technique


class TechniqueRepository:
    def __init__(self, db: Database):
        self.db = db

    async def get_all(self) -> List[Technique]:
        async with self.db.get_db_session() as session:
            result = await session.execute(select(Technique))
            return result.scalars().all()

    async def get_random(self, count: int = 4) -> List[Technique]:
        async with self.db.get_db_session() as session:
            result = await session.execute(select(Technique.id))
            all_ids = result.scalars().all()

            if len(all_ids) <= count:
                result = await session.execute(select(Technique))
                return result.scalars().all()

            random_ids = random.sample(all_ids, count)

            result = await session.execute(
                select(Technique)
                .where(Technique.id.in_(random_ids))
            )
            return result.scalars().all()

    async def get_by_id(self, technique_id: str) -> Optional[Technique]:
        async with self.db.get_db_session() as session:
            result = await session.execute(
                select(Technique).where(Technique.id == technique_id)
            )
            return result.scalar_one_or_none()
