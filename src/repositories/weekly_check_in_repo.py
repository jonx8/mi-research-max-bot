from datetime import datetime
from typing import Optional, List, NamedTuple

from sqlalchemy import select, and_

from src.database import Database
from src.models import WeeklyCheckIn, Participant


class PendingWeeklyCheckIn(NamedTuple):
    checkin: WeeklyCheckIn
    telegram_id: int


class WeeklyCheckInRepository:
    def __init__(self, db: Database):
        self._db = db

    async def get(self, check_in_id: int) -> Optional[WeeklyCheckIn]:
        async with self._db.get_db_session() as session:
            return await session.get(WeeklyCheckIn, check_in_id)

    async def save(self, checkin: WeeklyCheckIn) -> WeeklyCheckIn:
        async with self._db.get_db_session() as session:
            session.add(checkin)
            await session.flush()
            return checkin

    async def save_batch(self, checkins: List[WeeklyCheckIn]) -> List[WeeklyCheckIn]:
        async with self._db.get_db_session() as session:
            session.add_all(checkins)
            await session.flush()
            return checkins

    async def update(self, checkin: WeeklyCheckIn) -> WeeklyCheckIn:
        async with self._db.get_db_session() as session:
            await session.merge(checkin)
            return checkin

    async def get_pending(self, participant_code: str) -> Optional[WeeklyCheckIn]:
        async with self._db.get_db_session() as session:
            result = await session.execute(
                select(WeeklyCheckIn)
                .where(WeeklyCheckIn.participant_code == participant_code)
                .where(WeeklyCheckIn.completed_at.is_(None))
                .order_by(WeeklyCheckIn.scheduled_date)
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def get_latest_completed_week(self, participant_code: str) -> int:
        async with self._db.get_db_session() as session:
            result = await session.execute(
                select(WeeklyCheckIn.week_number)
                .where(WeeklyCheckIn.participant_code == participant_code)
                .where(WeeklyCheckIn.completed_at.isnot(None))
                .order_by(WeeklyCheckIn.week_number.desc())
                .limit(1)
            )
            week = result.scalar_one_or_none()
            return week or 0

    async def get_all_pending_with_participant(self) -> List[PendingWeeklyCheckIn]:
        async with self._db.get_db_session() as session:
            stmt = (
                select(WeeklyCheckIn, Participant.telegram_id_encrypted)
                .join(Participant, WeeklyCheckIn.participant_code == Participant.participant_code)
                .where(
                    and_(
                        WeeklyCheckIn.completed_at.is_(None),
                        WeeklyCheckIn.sent_at.is_(None),
                        WeeklyCheckIn.scheduled_date <= datetime.now()
                    )
                )
            )
            result = await session.execute(stmt)
            rows = result.all()

            from src.utils.encryption import get_encryption_service
            encryption_service = get_encryption_service()

            pending_items = []
            for row in rows:
                checkin = row[0]
                telegram_id_encrypted = row[1]
                telegram_id = encryption_service.decrypt_to_int(telegram_id_encrypted)
                pending_items.append(PendingWeeklyCheckIn(checkin=checkin, telegram_id=telegram_id))
            return pending_items