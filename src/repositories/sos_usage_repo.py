from src.database import Database
from src.models import SOSUsage


class SOSUsageRepository:
    def __init__(self, db: Database):
        self._db = db

    async def save(self, usage: SOSUsage) -> SOSUsage:
        async with self._db.get_db_session() as session:
            session.add(usage)
            await session.flush()
            return usage

    async def update(self, usage: SOSUsage) -> SOSUsage:
        async with self._db.get_db_session() as session:
            await session.merge(usage)
            return usage
