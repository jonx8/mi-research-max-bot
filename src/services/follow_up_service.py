from datetime import datetime, timedelta
from typing import Optional, List

from src.models import FollowUp
from src.repositories import FollowUpRepository


class FollowUpService:
    def __init__(self, repo: FollowUpRepository):
        self._repo = repo

    async def create_scheduled(
            self,
            participant_code: str,
            registration_date: datetime,
            intervals_minutes: List[int]
    ) -> None:
        """
        Создаёт запланированные опросы.

        Args:
            participant_code: код участника
            registration_date: дата регистрации
            intervals_minutes: список интервалов в минутах
        """
        follow_ups = [
            FollowUp(
                participant_code=participant_code,
                scheduled_date=registration_date + timedelta(minutes=minutes)
            )
            for minutes in intervals_minutes
        ]
        await self._repo.save_batch(follow_ups)

    async def get_by_id(self, follow_up_id: int) -> Optional[FollowUp]:
        return await self._repo.get(follow_up_id)

    async def complete(
            self,
            follow_up: FollowUp,
            ppa_7d: bool,
            cigs_per_day: Optional[int] = None
    ) -> FollowUp:
        follow_up.completed_at = datetime.now()
        follow_up.ppa_7d = ppa_7d
        follow_up.cigs_per_day = cigs_per_day
        return await self._repo.update(follow_up)

    async def update(self, follow_up: FollowUp) -> FollowUp:
        return await self._repo.update(follow_up)
