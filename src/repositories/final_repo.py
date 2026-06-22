from datetime import datetime
from typing import NamedTuple, List

from sqlalchemy import select, and_

from src.database import Database
from src.models import FinalSurvey, Participant


class PendingFinalSurvey(NamedTuple):
    survey: FinalSurvey
    telegram_id: int


class FinalSurveyRepository:
    def __init__(self, db: Database):
        self._db = db

    async def save(self, survey: FinalSurvey) -> FinalSurvey:
        async with self._db.get_db_session() as session:
            session.add(survey)
            await session.flush()
            return survey

    async def update(self, survey: FinalSurvey) -> FinalSurvey:
        async with self._db.get_db_session() as session:
            await session.merge(survey)
            return survey

    async def get_all_pending_with_participant(self) -> List[PendingFinalSurvey]:
        async with self._db.get_db_session() as session:
            stmt = (
                select(FinalSurvey, Participant.telegram_id_encrypted)
                .join(Participant, FinalSurvey.participant_code == Participant.participant_code)
                .where(
                    and_(
                        FinalSurvey.completed_at.is_(None),
                        FinalSurvey.sent_at.is_(None),
                        FinalSurvey.scheduled_date <= datetime.now()
                    )
                )
            )
            result = await session.execute(stmt)
            rows = result.all()

            from src.utils.encryption import get_encryption_service
            encryption_service = get_encryption_service()

            pending_items = []
            for row in rows:
                survey = row[0]
                telegram_id_encrypted = row[1]
                telegram_id = encryption_service.decrypt_to_int(telegram_id_encrypted)
                pending_items.append(PendingFinalSurvey(survey=survey, telegram_id=telegram_id))
            return pending_items

    async def get(self, survey_id):
        async with self._db.get_db_session() as session:
            return await session.get(FinalSurvey, survey_id)