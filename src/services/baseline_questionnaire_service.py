from datetime import datetime

from src.models import BaselineQuestionnaire
from src.repositories import BaselineQuestionnaireRepository


class BaselineQuestionnaireService:
    def __init__(self, repo: BaselineQuestionnaireRepository):
        self._repo = repo

    async def save(self, questionnaire: BaselineQuestionnaire) -> BaselineQuestionnaire:
        questionnaire.completed_at = datetime.now()
        return await self._repo.save(questionnaire)
