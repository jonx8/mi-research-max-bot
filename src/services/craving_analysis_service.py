from datetime import datetime
from typing import List

from src.models import CravingAnalysis
from src.repositories.craving_analysis_repo import CravingAnalysisRepository


class CravingAnalysisService:
    def __init__(self, repo: CravingAnalysisRepository):
        self._repo = repo

    async def create(
            self,
            participant_code: str,
            answers: List[str],
    ) -> CravingAnalysis:
        analysis = CravingAnalysis(
            participant_code=participant_code,
            completed_at=datetime.now(),
            trigger_situation=answers[0],
            thoughts=answers[1],
            physical_sensation=answers[2],
            coping_strategy=answers[3],
        )
        return await self._repo.save(analysis)
