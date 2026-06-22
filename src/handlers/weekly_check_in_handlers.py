import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

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

    async def handle_weekly_status(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Step 1: Process smoking status selection for the week.

        Expected callback data format: "weekly_{id}_status_{not/some/regular}"

        Args:
            update: Telegram update object
            _: Telegram context object (unused)
        """
        query = update.callback_query
        await query.answer()
        data = query.data
        telegram_id = update.effective_user.id

        parts = data.split('_')
        checkin_id = int(parts[1])
        status = parts[3]

        logger.info(
            f"Пользователь выбирает статус курения для чек-ина (checkin_id={checkin_id}): статус='{status}'"
        )

        checkin = await self._weekly_service.get_by_id(checkin_id)
        if not checkin or checkin.completed_at:
            logger.error(f"Чек-ин завершён или не найден (checkin_id={checkin_id})")
            await query.edit_message_text("Этот чек‑ин уже завершён или не найден.")
            return

        await self._session_manager.create_or_update_weekly_checkin_session(
            telegram_id=telegram_id,
            checkin_id=checkin_id,
            status=status
        )

        logger.info(
            f"Создана сессия для чек-ина (checkin_id={checkin_id}) со статусом '{status}'"
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(str(i), callback_data=f"weekly_{checkin_id}_craving_{i}") for i in range(1, 6)],
            [InlineKeyboardButton(str(i), callback_data=f"weekly_{checkin_id}_craving_{i}") for i in range(6, 11)],
        ])

        await query.edit_message_text(
            "📊 Оцените уровень тяги к курению за прошедшую неделю по шкале от 1 до 10:\n"
            "(1 — совсем не было, 10 — очень сильная тяга)",
            reply_markup=keyboard
        )

    async def handle_weekly_craving_input(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Step 2: Process craving level selection (1-10) via inline buttons.

        Expected callback data format: "weekly_{id}_craving_{1-10}"

        Args:
            update: Telegram update object
            _: Telegram context object (unused)
        """
        query = update.callback_query
        await query.answer()
        data = query.data

        parts = data.split('_')
        checkin_id = int(parts[1])
        craving = int(parts[3])

        logger.info(f"Пользователь выбирает уровень тяги для чек-ина (checkin_id={checkin_id}): уровень={craving}")

        session = await self._session_manager.get_weekly_checkin_session(checkin_id)
        if not session:
            logger.error(f"Сессия чек-ина не найдена (checkin_id={checkin_id})")
            await query.edit_message_text("Сессия не найдена. Начните заново.")
            return

        checkin = await self._weekly_service.get_by_id(checkin_id)
        if not checkin or checkin.completed_at:
            logger.warning(f"Чек-ин уже завершён (checkin_id={checkin_id})")
            await query.edit_message_text("Чек‑ин уже завершён.")
            await self._session_manager.delete_weekly_checkin_session(checkin_id)
            return

        await self._session_manager.update_weekly_checkin_session(
            checkin_id=checkin_id,
            craving=craving
        )

        logger.info(f"Сохранён уровень тяги {craving} для чек-ина (checkin_id={checkin_id})")

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("😊 Хорошее", callback_data=f"weekly_{checkin_id}_mood_good")],
            [InlineKeyboardButton("😐 Среднее", callback_data=f"weekly_{checkin_id}_mood_average")],
            [InlineKeyboardButton("😞 Плохое", callback_data=f"weekly_{checkin_id}_mood_bad")],
        ])

        await query.edit_message_text(
            "😌 Как бы вы оценили своё общее самочувствие за неделю?",
            reply_markup=keyboard
        )

    async def handle_weekly_mood(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Step 3: Process mood selection.

        Expected callback data format: "weekly_{id}_mood_{good/average/bad}"

        Args:
            update: Telegram update object
            _: Telegram context object (unused)
        """
        query = update.callback_query
        await query.answer()
        data = query.data

        parts = data.split('_')
        checkin_id = int(parts[1])
        mood = parts[3]

        logger.info(
            f"Пользователь выбирает настроение для чек-ина (checkin_id={checkin_id}): настроение='{mood}'"
        )

        session = await self._session_manager.get_weekly_checkin_session(checkin_id)
        if not session:
            logger.error(f"Сессия чек-ина не найдена (checkin_id={checkin_id})")
            await query.edit_message_text("Сессия не найдена. Начните заново.")
            return

        checkin = await self._weekly_service.get_by_id(checkin_id)
        if not checkin or checkin.completed_at:
            logger.warning(f"Чек-ин уже завершён (checkin_id={checkin_id})")
            await query.edit_message_text("Чек‑ин уже завершён.")
            await self._session_manager.delete_weekly_checkin_session(checkin_id)
            return

        await self._session_manager.update_weekly_checkin_session(
            checkin_id=checkin_id,
            mood=mood
        )

        # Map values to human-readable format
        status_map = {'not': 'не курил', 'some': 'эпизодически', 'regular': 'регулярно'}
        mood_map = {'good': 'хорошее', 'average': 'среднее', 'bad': 'плохое'}

        smoking_status = status_map.get(session.status)
        craving = session.craving
        mood_value = mood_map.get(mood)

        logger.info(
            f"Завершение чек-ина (checkin_id={checkin_id}) "
            f"статус='{smoking_status}', тяга={craving}, настроение='{mood_value}'"
        )

        await self._weekly_service.complete(checkin, smoking_status, craving, mood_value)
        await self._session_manager.delete_weekly_checkin_session(checkin_id)

        await query.edit_message_text("✅ Спасибо! Ваш еженедельный отчёт записан.")
