from typing import Optional

from sqlalchemy import select, delete

from src.database import Database
from src.models import (
    RegistrationSession,
    CravingAnalysisSession,
    FinalSurveySession,
    FollowUpSession,
    WeeklyCheckInSession,
)
from src.utils.encryption import get_encryption_service


class SessionRepository:
    """Единый репозиторий для работы со всеми типами сессий в БД"""

    def __init__(self, db: Database):
        self._db = db

    @staticmethod
    def _encrypt_max_id(max_id: int) -> str:
        """Шифрует max_id"""
        return get_encryption_service().encrypt(max_id)

    # === Registration Sessions ===

    async def create_registration_session(self, max_id: int) -> RegistrationSession:
        """Создает новую сессию регистрации"""
        async with self._db.get_db_session() as session:
            encrypted_id = self._encrypt_max_id(max_id)
            session_obj = RegistrationSession(max_id_encrypted=encrypted_id)
            session.add(session_obj)
            await session.flush()
            await session.refresh(session_obj)
            return session_obj

    async def get_registration_session_by_max_id(self, max_id: int) -> Optional[RegistrationSession]:
        """Получает сессию регистрации по max_id"""
        encrypted_id = self._encrypt_max_id(max_id)
        async with self._db.get_db_session() as session:
            stmt = select(RegistrationSession).where(
                RegistrationSession.max_id_encrypted == encrypted_id
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def set_last_bot_message_id(self, max_id: int, message_id: int) -> None:
        """Сохраняет ID последнего сообщения бота для последующего удаления"""
        async with self._db.get_db_session() as session:
            encrypted_id = self._encrypt_max_id(max_id)
            stmt = select(RegistrationSession).where(
                RegistrationSession.max_id_encrypted == encrypted_id
            )
            result = await session.execute(stmt)
            session_obj = result.scalar_one_or_none()
            if session_obj:
                session_obj.last_bot_message_id = message_id
                await session.flush()

    async def update_registration_session(self, session_obj: RegistrationSession) -> RegistrationSession:
        """Обновляет существующую сессию регистрации"""
        async with self._db.get_db_session() as session:
            return await session.merge(session_obj)

    async def registration_session_exists(self, max_id: int) -> bool:
        """Проверяет наличие сессии регистрации"""
        encrypted_id = self._encrypt_max_id(max_id)
        async with self._db.get_db_session() as session:
            stmt = select(RegistrationSession.max_id_encrypted).where(
                RegistrationSession.max_id_encrypted == encrypted_id
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None

    async def delete_registration_session(self, max_id: int) -> None:
        """Удаляет сессию регистрации"""
        encrypted_id = self._encrypt_max_id(max_id)
        async with self._db.get_db_session() as session:
            stmt = delete(RegistrationSession).where(
                RegistrationSession.max_id_encrypted == encrypted_id
            )
            await session.execute(stmt)

    # === Craving Analysis Sessions ===

    async def create_craving_session(self, max_id: int) -> CravingAnalysisSession:
        """Создает новую сессию анализа тяги"""
        async with self._db.get_db_session() as session:
            encrypted_id = self._encrypt_max_id(max_id)
            session_obj = CravingAnalysisSession(max_id_encrypted=encrypted_id)
            session.add(session_obj)
            await session.flush()
            return session_obj

    async def get_craving_session(self, max_id: int) -> Optional[CravingAnalysisSession]:
        """Получает сессию анализа тяги по max_id"""
        encrypted_id = self._encrypt_max_id(max_id)
        async with self._db.get_db_session() as session:
            stmt = select(CravingAnalysisSession).where(
                CravingAnalysisSession.max_id_encrypted == encrypted_id
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def update_craving_session(self, session_obj: CravingAnalysisSession) -> CravingAnalysisSession:
        """Обновляет существующую сессию анализа тяги"""
        async with self._db.get_db_session() as session:
            merged = await session.merge(session_obj)
            await session.flush()
            await session.refresh(merged)
            return merged

    async def craving_session_exists(self, max_id: int) -> bool:
        """Проверяет наличие сессии анализа тяги"""
        encrypted_id = self._encrypt_max_id(max_id)
        async with self._db.get_db_session() as session:
            stmt = select(CravingAnalysisSession.max_id_encrypted).where(
                CravingAnalysisSession.max_id_encrypted == encrypted_id
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None

    async def delete_craving_session(self, max_id: int) -> None:
        """Удаляет сессию анализа тяги"""
        encrypted_id = self._encrypt_max_id(max_id)
        async with self._db.get_db_session() as session:
            stmt = delete(CravingAnalysisSession).where(
                CravingAnalysisSession.max_id_encrypted == encrypted_id
            )
            await session.execute(stmt)

    # === Final Survey Sessions ===

    async def create_or_update_final_survey_session(
            self,
            max_id: int,
            survey_id: int,
            ppa_30d: bool = None,
            ppa_7d: bool = None,
            cigs_per_day: int = None,
            quit_attempt_made: bool = None,
            days_to_first_lapse: int = None,
    ) -> FinalSurveySession:
        """Создает или обновляет промежуточное состояние финального опроса в БД"""
        encrypted_id = self._encrypt_max_id(max_id)
        async with self._db.get_db_session() as session:
            session_obj = await session.get(FinalSurveySession, survey_id)

            if not session_obj:
                session_obj = FinalSurveySession(
                    max_id_encrypted=encrypted_id,
                    survey_id=survey_id,
                    ppa_30d=ppa_30d,
                    ppa_7d=ppa_7d,
                    cigs_per_day=cigs_per_day,
                    quit_attempt_made=quit_attempt_made,
                    days_to_first_lapse=days_to_first_lapse,
                )
                session.add(session_obj)
            else:
                session_obj.survey_id = survey_id
                if ppa_30d is not None:
                    session_obj.ppa_30d = ppa_30d
                if ppa_7d is not None:
                    session_obj.ppa_7d = ppa_7d
                if cigs_per_day is not None:
                    session_obj.cigs_per_day = cigs_per_day
                if quit_attempt_made is not None:
                    session_obj.quit_attempt_made = quit_attempt_made
                if days_to_first_lapse is not None:
                    session_obj.days_to_first_lapse = days_to_first_lapse

            return session_obj

    async def update_final_survey_session(self, survey_id: int, **kwargs) -> Optional[FinalSurveySession]:
        """Обновляет промежуточное состояние финального опроса в БД"""
        async with self._db.get_db_session() as session:
            session_obj = await session.get(FinalSurveySession, survey_id)
            if session_obj:
                for key, value in kwargs.items():
                    if hasattr(session_obj, key):
                        setattr(session_obj, key, value)
                await session.flush()
                await session.refresh(session_obj)
            return session_obj

    async def get_final_survey_session(self, survey_id: int) -> Optional[FinalSurveySession]:
        """Получает промежуточное состояние финального опроса из БД"""
        async with self._db.get_db_session() as session:
            return await session.get(FinalSurveySession, survey_id)

    async def get_final_survey_session_by_max_id(self, max_id: int):
        encrypted_id = self._encrypt_max_id(max_id)
        async with self._db.get_db_session() as session:
            stmt = select(FinalSurveySession).where(
                FinalSurveySession.max_id_encrypted == encrypted_id
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def final_survey_session_exists(self, max_id):
        encrypted_id = self._encrypt_max_id(max_id)
        async with self._db.get_db_session() as session:
            stmt = select(FinalSurveySession).where(
                FinalSurveySession.max_id_encrypted == encrypted_id
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None

    async def delete_final_survey_session(self, max_id: int) -> None:
        """Удаляет сессию финального опроса после завершения"""
        encrypted_id = self._encrypt_max_id(max_id)
        async with self._db.get_db_session() as session:
            stmt = select(FinalSurveySession).where(
                FinalSurveySession.max_id_encrypted == encrypted_id
            )
            result = await session.execute(stmt)
            session_obj = result.scalar_one_or_none()
            if session_obj:
                await session.delete(session_obj)

    # === FollowUp Sessions ===

    async def create_follow_up_session(
            self,
            max_id: int,
            follow_up_id: int,
            ppa_7d: bool,
    ) -> FollowUpSession:
        """Создает или обновляет сессию follow-up опроса"""
        encrypted_id = self._encrypt_max_id(max_id)
        async with self._db.get_db_session() as session:
            session_obj = FollowUpSession(
                max_id_encrypted=encrypted_id,
                follow_up_id=follow_up_id,
                ppa_7d=ppa_7d,
            )
            session.add(session_obj)

            await session.flush()
            await session.refresh(session_obj)
            return session_obj

    async def get_follow_up_session(self, follow_up_id: int) -> Optional[FollowUpSession]:
        """Получает сессию follow-up опроса по ID опроса"""
        async with self._db.get_db_session() as session:
            stmt = select(FollowUpSession).where(FollowUpSession.follow_up_id == follow_up_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_follow_up_session_by_max_id(self, max_id: int) -> Optional[FollowUpSession]:
        encrypted_id = self._encrypt_max_id(max_id)
        async with self._db.get_db_session() as session:
            stmt = select(FollowUpSession).where(FollowUpSession.max_id_encrypted == encrypted_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def delete_follow_up_session(self, follow_up_id: int) -> None:
        """Удаляет сессию follow-up опроса"""
        async with self._db.get_db_session() as session:
            stmt = delete(FollowUpSession).where(FollowUpSession.follow_up_id == follow_up_id)
            await session.execute(stmt)

    async def delete_follow_up_sessions_by_max_id(self, max_id: int):
        encrypted_id = self._encrypt_max_id(max_id)
        async with self._db.get_db_session() as session:
            stmt = delete(FollowUpSession).where(FollowUpSession.max_id_encrypted == encrypted_id)
            await session.execute(stmt)

    # === Weekly CheckIn Sessions ===

    async def create_or_update_weekly_checkin_session(
            self,
            max_id: int,
            checkin_id: int,
            status: str = None,
            craving: int = None,
            mood: str = None,
    ) -> WeeklyCheckInSession:
        """Создает или обновляет сессию weekly check-in"""
        encrypted_id = self._encrypt_max_id(max_id)
        async with self._db.get_db_session() as session:
            stmt = select(WeeklyCheckInSession).where(WeeklyCheckInSession.checkin_id == checkin_id)
            result = await session.execute(stmt)
            session_obj = result.scalar_one_or_none()

            if not session_obj:
                session_obj = WeeklyCheckInSession(
                    max_id_encrypted=encrypted_id,
                    checkin_id=checkin_id,
                    status=status,
                    craving=craving,
                    mood=mood,
                )
                session.add(session_obj)
            else:
                if status is not None:
                    session_obj.status = status
                if craving is not None:
                    session_obj.craving = craving
                if mood is not None:
                    session_obj.mood = mood

            await session.flush()
            await session.refresh(session_obj)
            return session_obj

    async def get_weekly_checkin_session(self, checkin_id: int) -> Optional[WeeklyCheckInSession]:
        """Получает сессию weekly check-in по ID чек-ина"""
        async with self._db.get_db_session() as session:
            stmt = select(WeeklyCheckInSession).where(WeeklyCheckInSession.checkin_id == checkin_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def update_weekly_checkin_session(
            self, checkin_id: int, **kwargs
    ) -> Optional[WeeklyCheckInSession]:
        """Обновляет сессию weekly check-in"""
        async with self._db.get_db_session() as session:
            stmt = select(WeeklyCheckInSession).where(WeeklyCheckInSession.checkin_id == checkin_id)
            result = await session.execute(stmt)
            session_obj = result.scalar_one_or_none()

            if session_obj:
                for key, value in kwargs.items():
                    if hasattr(session_obj, key):
                        setattr(session_obj, key, value)
                await session.flush()
                await session.refresh(session_obj)
            return session_obj

    async def delete_weekly_checkin_session(self, checkin_id: int) -> None:
        """Удаляет сессию weekly check-in"""
        async with self._db.get_db_session() as session:
            stmt = delete(WeeklyCheckInSession).where(WeeklyCheckInSession.checkin_id == checkin_id)
            await session.execute(stmt)
