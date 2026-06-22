from datetime import datetime
from typing import Optional, List, NamedTuple

from sqlalchemy import select, and_

from src.database import Database
from src.models import FollowUp, Participant


class PendingFollowUp(NamedTuple):
    follow_up: FollowUp
    telegram_id: int


class FollowUpRepository:
    def __init__(self, db: Database):
        self._db = db

    async def save(self, follow_up: FollowUp) -> FollowUp:
        async with self._db.get_db_session() as session:
            session.add(follow_up)
            await session.flush()
            return follow_up

    async def save_batch(self, follow_ups: List[FollowUp]) -> List[FollowUp]:
        async with self._db.get_db_session() as session:
            session.add_all(follow_ups)
            await session.flush()
            return follow_ups

    async def update(self, follow_up: FollowUp) -> FollowUp:
        async with self._db.get_db_session() as session:
            await session.merge(follow_up)
            return follow_up

    async def get(self, follow_up_id) -> Optional[FollowUp]:
        async with self._db.get_db_session() as session:
            return await session.get(FollowUp, follow_up_id)

    async def get_all_pending_with_participant(self) -> List[PendingFollowUp]:
        async with self._db.get_db_session() as session:
            stmt = (
                select(FollowUp, Participant.telegram_id_encrypted)
                .join(Participant, FollowUp.participant_code == Participant.participant_code)
                .where(
                    and_(
                        FollowUp.completed_at.is_(None),
                        FollowUp.sent_at.is_(None),
                        FollowUp.scheduled_date <= datetime.now()
                    )
                )
            )
            result = await session.execute(stmt)
            rows = result.all()

            from src.utils.encryption import get_encryption_service
            encryption_service = get_encryption_service()
            pending_items = []
            for row in rows:
                follow_up = row[0]
                telegram_id_encrypted = row[1]
                telegram_id = encryption_service.decrypt_to_int(telegram_id_encrypted)
                pending_items.append(PendingFollowUp(follow_up=follow_up, telegram_id=telegram_id))
            return pending_items
