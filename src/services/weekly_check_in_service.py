from datetime import datetime, timedelta
from typing import Optional

from src.models import WeeklyCheckIn
from src.repositories import WeeklyCheckInRepository


class WeeklyCheckInService:
    def __init__(self, repo: WeeklyCheckInRepository):
        self._repo = repo

    async def create_scheduled(
            self,
            participant_code: str,
            registration_date: datetime,
            interval_minutes: int,
            total: int = 24
    ) -> None:
        """
        Создаёт еженедельные чек-ины.

        Args:
            participant_code: код участника
            registration_date: дата регистрации
            interval_minutes: интервал между чек-инами в минутах
            total: количество чек-инов
        """
        checkins = [
            WeeklyCheckIn(
                participant_code=participant_code,
                week_number=week,
                scheduled_date=registration_date + timedelta(minutes=week * interval_minutes)
            )
            for week in range(1, total + 1)
        ]
        await self._repo.save_batch(checkins)

    async def get_by_id(self, check_in_id: int) -> Optional[WeeklyCheckIn]:
        return await self._repo.get(check_in_id)

    async def complete(
            self,
            checkin: WeeklyCheckIn,
            smoking_status: str,
            craving_level: int,
            mood: str
    ) -> WeeklyCheckIn:
        checkin.completed_at = datetime.now()
        checkin.smoking_status = smoking_status
        checkin.craving_level = craving_level
        checkin.mood = mood
        return await self._repo.update(checkin)

    async def get_latest_completed_week(self, participant_code: str) -> int:
        return await self._repo.get_latest_completed_week(participant_code)
