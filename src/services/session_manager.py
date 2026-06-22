from typing import Optional
from src.repositories import SessionRepository
from src.models import RegistrationSession, CravingAnalysisSession, FinalSurveySession


class SessionManager:
    """Сервис для управления пользовательскими сессиями с хранением в БД"""

    def __init__(self, session_repo: SessionRepository):
        self._session_repo = session_repo

    # === Registration Sessions ===

    async def create_registration_session(self, telegram_id: int) -> RegistrationSession:
        """Создает новую сессию регистрации"""
        return await self._session_repo.create_registration_session(telegram_id)

    async def get_registration_session_by_telegram_id(self, telegram_id: int) -> Optional[RegistrationSession]:
        """Получает активную сессию регистрации из БД для пользователя telegram"""
        return await self._session_repo.get_registration_session_by_telegram_id(telegram_id)

    async def has_registration_session(self, telegram_id: int) -> bool:
        """Проверяет наличие активной сессии"""
        return await self._session_repo.registration_session_exists(telegram_id)

    async def update_registration_session(self, session_obj: RegistrationSession) -> RegistrationSession:
        """Обновляет данные сессии в БД"""
        return await self._session_repo.update_registration_session(session_obj)

    async def delete_registration_session(self, telegram_id: int) -> None:
        """Удаляет сессию после завершения регистрации"""
        await self._session_repo.delete_registration_session(telegram_id)

    async def set_last_bot_message_id(self, telegram_id: int, message_id: int) -> None:
        """Сохраняет ID последнего сообщения бота для последующего удаления"""
        await self._session_repo.set_last_bot_message_id(telegram_id, message_id)

    async def get_last_bot_message_id(self, telegram_id: int) -> Optional[int]:
        """Получает ID последнего сообщения бота"""
        session = await self._session_repo.get_registration_session_by_telegram_id(telegram_id)
        if session:
            return session.last_bot_message_id
        return None


    # === Craving Analysis Sessions ===

    async def create_craving_session(self, telegram_id: int) -> CravingAnalysisSession:
        """Создает новую сессию анализа тяги"""
        return await self._session_repo.create_craving_session(telegram_id)

    async def get_craving_session(self, telegram_id: int) -> Optional[CravingAnalysisSession]:
        """Получает активную сессию анализа тяги из БД"""
        return await self._session_repo.get_craving_session(telegram_id)

    async def has_craving_session(self, telegram_id: int) -> bool:
        """Проверяет наличие активной сессии анализа"""
        return await self._session_repo.craving_session_exists(telegram_id)

    async def update_craving_session(self, session_obj: CravingAnalysisSession) -> CravingAnalysisSession:
        """Обновляет данные сессии анализа в БД"""
        return await self._session_repo.update_craving_session(session_obj)

    async def delete_craving_session(self, telegram_id: int) -> None:
        """Удаляет сессию анализа"""
        await self._session_repo.delete_craving_session(telegram_id)

    # === Final Survey Sessions ===

    async def create_or_update_final_survey_session(self, telegram_id: int, survey_id: int, **kwargs) -> FinalSurveySession:
        return await self._session_repo.create_or_update_final_survey_session(telegram_id, survey_id, **kwargs)

    async def get_final_survey_session_by_id(self, survey_id: int) -> Optional[FinalSurveySession]:
        return await self._session_repo.get_final_survey_session(survey_id)

    async def get_final_survey_session_by_telegram_id(self, telegram_id: int) -> Optional[FinalSurveySession]:
        return await self._session_repo.get_final_survey_session_by_telegram_id(telegram_id)

    async def has_final_survey_session(self, telegram_id: int) -> bool:
        return await self._session_repo.final_survey_session_exists(telegram_id)

    async def update_final_survey_session(self, survey_id: int, **kwargs) -> Optional[FinalSurveySession]:
        return await self._session_repo.update_final_survey_session(survey_id, **kwargs)

    async def delete_final_survey_session(self, survey_id: int) -> None:
        await self._session_repo.delete_final_survey_session(survey_id)

    # === FollowUp Sessions ===

    async def create_follow_up_session(
            self,
            telegram_id: int,
            follow_up_id: int,
            ppa_7d: bool,
    ):
        """Создает или обновляет сессию follow-up опроса"""
        await self.delete_follow_up_sessions_by_telegram_id(telegram_id)
        return await self._session_repo.create_follow_up_session(telegram_id, follow_up_id, ppa_7d)

    async def get_follow_up_session(self, follow_up_id: int):
        """Получает сессию follow-up опроса по ID опроса"""
        return await self._session_repo.get_follow_up_session(follow_up_id)

    async def get_follow_up_session_by_telegram_id(self, telegram_id: int):
        return await self._session_repo.get_follow_up_session_by_telegram(telegram_id)

    async def delete_follow_up_session(self, follow_up_id: int) -> None:
        """Удаляет сессию follow-up опроса"""
        await self._session_repo.delete_follow_up_session(follow_up_id)

    async def delete_follow_up_sessions_by_telegram_id(self, telegram_id: int) -> None:
        await self._session_repo.delete_follow_up_sessions_by_telegram_id(telegram_id)

    # === Weekly CheckIn Sessions ===

    async def create_or_update_weekly_checkin_session(
            self,
            telegram_id: int,
            checkin_id: int,
            status: str = None,
            craving: int = None,
            mood: str = None,
    ):
        """Создает или обновляет сессию weekly check-in (без дефолтных значений)"""
        return await self._session_repo.create_or_update_weekly_checkin_session(
            telegram_id, checkin_id, status, craving, mood
        )

    async def get_weekly_checkin_session(self, checkin_id: int):
        """Получает сессию weekly check-in по ID чек-ина"""
        return await self._session_repo.get_weekly_checkin_session(checkin_id)

    async def update_weekly_checkin_session(self, checkin_id: int, **kwargs):
        """Обновляет сессию weekly check-in"""
        return await self._session_repo.update_weekly_checkin_session(checkin_id, **kwargs)

    async def delete_weekly_checkin_session(self, checkin_id: int) -> None:
        """Удаляет сессию weekly check-in"""
        await self._session_repo.delete_weekly_checkin_session(checkin_id)
