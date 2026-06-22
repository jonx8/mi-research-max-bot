from src.database import Database
from src.models import CravingAnalysis


class CravingAnalysisRepository:
    def __init__(self, db: Database):
        self._db = db

    async def save(self, analysis: CravingAnalysis) -> CravingAnalysis:
        async with self._db.get_db_session() as session:
            session.add(analysis)
            await session.flush()
            return analysis
