import logging

from maxapi.types import MessageCallback, CallbackButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from src.payloads import WeeklyCheckInStatusPayload, WeeklyCheckInCravingPayload, WeeklyCheckInMoodPayload
from src.services import SessionManager
from src.services import WeeklyCheckInService

logger = logging.getLogger(__name__)


class WeeklyCheckInHandlers:
    """
    Handlers for weekly check-in surveys.

    Manages weekly assessment of:
    - Smoking status
    - Craving intensity (1-10 scale)
    - Overall mood/well-being
    """

    def __init__(self, weekly_check_in_service: WeeklyCheckInService, session_manager: SessionManager):
        """
        Initialize weekly check-in handlers.

        Args:
            weekly_check_in_service: Service for managing weekly check-in data
            session_manager: Manager for user session state
        """
        self._weekly_service = weekly_check_in_service
        self._session_manager = session_manager

    async def handle_weekly_status(self, event: MessageCallback, payload: WeeklyCheckInStatusPayload):
        """Step 1: Process smoking status selection for the week."""

        logger.info(
            f"Пользователь выбирает статус курения для чек-ина (checkin_id={payload.checkin_id}): статус='{payload.answer}'"
        )

        checkin = await self._weekly_service.get_by_id(payload.checkin_id)
        if not checkin or checkin.completed_at:
            logger.error(f"Чек-ин завершён или не найден (checkin_id={payload.checkin_id})")
            await event.message.edit("Этот чек‑ин уже завершён или не найден.", attachments=[])
            return

        await self._session_manager.create_or_update_weekly_checkin_session(
            max_id=event.from_user.user_id,
            checkin_id=payload.checkin_id,
            status=payload.answer
        )

        logger.info(
            f"Создана сессия для чек-ина (checkin_id={payload.checkin_id}) со статусом '{payload.answer}'"
        )

        builder = InlineKeyboardBuilder()
        builder.row(*[CallbackButton(
            text=str(i),
            payload=WeeklyCheckInCravingPayload(checkin_id=payload.checkin_id, craving=i).pack()
        ) for i in range(1, 6)])

        builder.row(*[CallbackButton(
            text=str(i),
            payload=WeeklyCheckInCravingPayload(checkin_id=payload.checkin_id, craving=i).pack()
        ) for i in range(6, 11)])

        await event.message.edit(
            text="📊 Оцените уровень тяги к курению за прошедшую неделю по шкале от 1 до 10:\n"
            "(1 — совсем не было, 10 — очень сильная тяга)",
            attachments=[builder.as_markup()]
        )

    async def handle_weekly_craving_input(self, event: MessageCallback, payload: WeeklyCheckInCravingPayload):
        """Step 2: Process craving level selection (1-10) via inline buttons."""

        logger.info(
            f"Пользователь выбирает уровень тяги для чек-ина (checkin_id={payload.checkin_id}): уровень={payload.craving}")

        session = await self._session_manager.get_weekly_checkin_session(payload.checkin_id)
        if not session:
            logger.error(f"Сессия чек-ина не найдена (checkin_id={payload.checkin_id})")
            await event.message.edit("Сессия не найдена. Начните заново.", attachments=[])
            return

        checkin = await self._weekly_service.get_by_id(payload.checkin_id)
        if not checkin or checkin.completed_at:
            logger.warning(f"Чек-ин уже завершён (checkin_id={payload.checkin_id})")
            await event.message.edit("Чек‑ин уже завершён.", attachments=[])
            await self._session_manager.delete_weekly_checkin_session(payload.checkin_id)
            return

        await self._session_manager.update_weekly_checkin_session(
            checkin_id=payload.checkin_id,
            craving=payload.craving
        )

        logger.info(f"Сохранён уровень тяги {payload.craving} для чек-ина (checkin_id={payload.checkin_id})")

        builder = InlineKeyboardBuilder()
        builder.row(CallbackButton(text="😊 Хорошее",
                                   payload=WeeklyCheckInMoodPayload(checkin_id=payload.checkin_id, mood="good").pack()))
        builder.row(CallbackButton(text="😐 Среднее",
                                   payload=WeeklyCheckInMoodPayload(checkin_id=payload.checkin_id,
                                                                    mood="average").pack()))
        builder.row(CallbackButton(text="😞 Плохое",
                                   payload=WeeklyCheckInMoodPayload(checkin_id=payload.checkin_id, mood="bad").pack()))

        await event.message.edit(
            "😌 Как бы вы оценили своё общее самочувствие за неделю?",
            attachments=[builder.as_markup()]
        )

    async def handle_weekly_mood(self, event: MessageCallback, payload: WeeklyCheckInMoodPayload):
        """Step 3: Process mood selection."""

        logger.info(
            f"Пользователь выбирает настроение для чек-ина (checkin_id={payload.checkin_id}): настроение='{payload.mood}'"
        )

        session = await self._session_manager.get_weekly_checkin_session(payload.checkin_id)
        if not session:
            logger.error(f"Сессия чек-ина не найдена (checkin_id={payload.checkin_id})")
            await event.message.edit("Сессия не найдена. Начните заново.", attachments=[])
            return

        checkin = await self._weekly_service.get_by_id(payload.checkin_id)
        if not checkin or checkin.completed_at:
            logger.warning(f"Чек-ин уже завершён (checkin_id={payload.checkin_id})")
            await event.message.edit("Чек‑ин уже завершён.", attachments=[])
            await self._session_manager.delete_weekly_checkin_session(payload.checkin_id)
            return

        await self._session_manager.update_weekly_checkin_session(
            checkin_id=payload.checkin_id,
            mood=payload.mood
        )

        # Map values to human-readable format
        status_map = {'not': 'не курил', 'some': 'эпизодически', 'regular': 'регулярно'}
        mood_map = {'good': 'хорошее', 'average': 'среднее', 'bad': 'плохое'}

        smoking_status = status_map.get(session.status)
        craving = session.craving
        mood_value = mood_map.get(payload.mood)

        logger.info(
            f"Завершение чек-ина (checkin_id={payload.checkin_id}) "
            f"статус='{smoking_status}', тяга={craving}, настроение='{mood_value}'"
        )

        await self._weekly_service.complete(checkin, smoking_status, craving, mood_value)
        await self._session_manager.delete_weekly_checkin_session(payload.checkin_id)

        await event.message.edit("✅ Спасибо! Ваш еженедельный отчёт записан.", attachments=[])
