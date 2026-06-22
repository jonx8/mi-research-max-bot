import random
from typing import Optional

from sqlalchemy import select

from src.database import Database
from src.models import MorningTip


class MorningTipRepository:
    def __init__(self, db: Database):
        self._db = db

    async def get_random_tip(self, month: int, tip_type: str) -> Optional[str]:
        async with self._db.get_db_session() as session:
            result = await session.execute(
                select(MorningTip.content)
                .where(MorningTip.month == month)
                .where(MorningTip.type == tip_type)
            )
            tips = [row[0] for row in result.all()]
            if not tips:
                return None
            return random.choice(tips)
