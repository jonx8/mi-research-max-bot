from typing import Optional

from sqlalchemy import select

from src.database import Database
from src.models import BaselineQuestionnaire


class BaselineQuestionnaireRepository:
    def __init__(self, db: Database):
        self._db = db

    async def save(self, questionnaire: BaselineQuestionnaire) -> BaselineQuestionnaire:
        async with self._db.get_db_session() as session:
            session.add(questionnaire)
            await session.flush()
            return questionnaire

    async def get_by_participant_code(self, participant_code: str) -> Optional[BaselineQuestionnaire]:
        async with self._db.get_db_session() as session:
            result = await session.execute(
                select(BaselineQuestionnaire).where(BaselineQuestionnaire.participant_code == participant_code)
            )
            return result.scalar_one_or_none()
