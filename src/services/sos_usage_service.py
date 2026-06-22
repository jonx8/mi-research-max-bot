from datetime import datetime
from typing import Optional

from src.models import SOSUsage
from src.repositories import SOSUsageRepository


class SOSUsageService:
    def __init__(self, repo: SOSUsageRepository):
        self._repo = repo

    async def create(self, participant_code: str, technique_id: Optional[str] = None) -> SOSUsage:
        usage = SOSUsage(
            participant_code=participant_code,
            triggered_at=datetime.now(),
            technique_id=technique_id,
        )
        return await self._repo.save(usage)
