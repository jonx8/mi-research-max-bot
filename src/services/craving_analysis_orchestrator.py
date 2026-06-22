from dataclasses import dataclass
from typing import List

from src.exceptions import InvalidStepError, CravingSessionNotFoundError, ValidationError
from .participant_service import ParticipantService
from .craving_analysis_service import CravingAnalysisService
from .session_manager import SessionManager


@dataclass
class CravingQuestionData:
    """DTO для вопроса анализа тяги"""
    number: int
    total: int
    text: str


@dataclass
class CravingAnalysisResult:
    """DTO для результатов анализа"""
    user_id: int
    answers: List[str]


class CravingAnalysisOrchestrator:
    def __init__(
            self,
            session_manager: SessionManager,
            craving_analysis_service: CravingAnalysisService,
            participant_service: ParticipantService
    ):
        self._session_manager = session_manager
        self._participant_service = participant_service
        self._craving_analysis_service = craving_analysis_service

    @staticmethod
    def get_craving_analysis_questions() -> List[str]:
        """Вопросы для анализа триггеров тяги"""
        return [
            "Что спровоцировало тягу? (ситуация, эмоции, место)",
            "Какие мысли были у вас в момент тяги?",
            "Что вы почувствовали физически?",
            "Какой способ помог справиться с тягой?"
        ]

    async def _get_session_or_raise(self, user_id: int):
        session = await self._session_manager.get_craving_session(user_id)
        if not session:
            raise CravingSessionNotFoundError(user_id)
        return session

    async def _save_session(self, session_obj) -> None:
        """Сохраняет изменения сессии в БД"""
        await self._session_manager.update_craving_session(session_obj)

    async def start_analysis(self, telegram_id: int) -> None:
        """Начинает анализ тяги"""
        if await self.is_analysis_active(telegram_id):
            raise ValidationError("Анализ тяги уже активен")

        await self._session_manager.create_craving_session(telegram_id)

    async def get_current_question(self, user_id: int) -> CravingQuestionData:
        """Возвращает текущий вопрос"""
        session = await self._get_session_or_raise(user_id)
        questions = self.get_craving_analysis_questions()

        if session.step >= len(questions):
            raise InvalidStepError("Анализ уже завершён")

        return CravingQuestionData(
            number=session.step + 1,
            total=len(questions),
            text=questions[session.step]
        )

    async def save_answer(self, user_id: int, answer: str) -> None:
        """Сохраняет ответ и переходит к следующему вопросу"""
        session = await self._get_session_or_raise(user_id)
        questions = self.get_craving_analysis_questions()

        if session.step >= len(questions):
            raise InvalidStepError("Анализ уже завершён")

        if not answer.strip():
            raise ValidationError("Пожалуйста, введите ответ")

        if session.answers is None:
            session.answers = []

        session.answers.append(answer.strip())
        session.step += 1
        await self._save_session(session)

    async def is_completed(self, user_id: int) -> bool:
        """Проверяет, завершён ли анализ"""
        session = await self._get_session_or_raise(user_id)
        questions = self.get_craving_analysis_questions()
        return session.step >= len(questions)

    async def get_result(self, user_id: int) -> CravingAnalysisResult:
        """Возвращает результаты анализа"""
        session = await self._get_session_or_raise(user_id)
        questions = self.get_craving_analysis_questions()

        if session.step < len(questions):
            raise InvalidStepError("Анализ ещё не завершён")

        return CravingAnalysisResult(
            user_id=user_id,
            answers=session.answers.copy() if session.answers else []
        )

    async def finish_analysis(self, user_id: int) -> CravingAnalysisResult:
        """Завершает анализ и очищает сессию"""
        result = await self.get_result(user_id)
        participant = await self._participant_service.get_by_telegram_id(user_id)
        await self._craving_analysis_service.create(
            participant_code=participant.participant_code,
            answers=result.answers
        )

        await self._session_manager.delete_craving_session(user_id)
        return result

    async def is_analysis_active(self, telegram_id: int) -> bool:
        """Проверяет, активен ли анализ"""
        return await self._session_manager.has_craving_session(telegram_id)
