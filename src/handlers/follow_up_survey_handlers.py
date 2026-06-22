import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.services import FollowUpService
from src.services import SessionManager

logger = logging.getLogger(__name__)


class FollowUpSurveyHandlers:
    """
    Handlers for follow-up surveys (intermediate checkpoints).

    These handlers process follow-up surveys that check smoking status
    at regular intervals during the study period.
    """

    def __init__(self, follow_up_service: FollowUpService, session_manager: SessionManager):
        """
        Initialize follow-up survey handlers.

        Args:
            follow_up_service: Service for managing follow-up survey data
            session_manager: Manager for user session state
        """
        self._follow_up_service = follow_up_service
        self._session_manager = session_manager

    async def handle_follow_up_answer(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Process first question of follow-up survey (7-day smoking status).

        Expected callback data format: "followup_{id}_ppa_{yes/no}"

        Args:
            update: Telegram update object
            _: Telegram context object (unused)
        """
        query = update.callback_query
        await query.answer()
        data = query.data  # format: "followup_{id}_ppa_{yes/no}"

        parts = data.split('_')
        if len(parts) != 4:
            logger.error(f"Некорректный формат данных follow-up: '{data}'")
            await query.edit_message_text("Некорректный формат данных.")
            return

        follow_up_id = int(parts[1])
        answer = parts[3]

        logger.info(f"Пользователь отвечает на follow-up опрос (follow_up_id={follow_up_id}): ответ='{answer}'")

        follow_up = await self._follow_up_service.get_by_id(int(follow_up_id))
        if not follow_up:
            logger.error(f"Follow-up опрос не найден (follow_up_id={follow_up_id})")
            await query.edit_message_text("Опрос не найден.")
            return

        if follow_up.completed_at:
            logger.warning(
                f"Пользователь попытался ответить на завершённый follow-up опрос (follow_up_id={follow_up_id})"
            )
            await query.edit_message_text("Вы уже ответили на этот опрос.")
            return

        if answer == 'yes':
            await self._session_manager.create_follow_up_session(
                telegram_id=update.effective_user.id,
                follow_up_id=follow_up_id,
                ppa_7d=True
            )

            logger.info(
                f"Пользователь указал, что курит, для опроса (follow_up_id={follow_up_id})"
            )

            await query.edit_message_text(
                "📝 Сколько сигарет в день в среднем выкуриваете сейчас?\n"
                "(введите целое число от 0 до 100)"
            )
            return

        await self._follow_up_service.complete(follow_up, ppa_7d=False, cigs_per_day=None)

        logger.info(f"Follow-up опрос (follow_up_id={follow_up_id}) завершён. ppa7d: False")

        await query.edit_message_text("✅ Спасибо! Ваш ответ записан.")

    async def handle_follow_up_cigs_input(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Process cigarette count input after affirmative smoking answer.

        Args:
            update: Telegram update object with message text
            _: Telegram context object (unused)
        """
        user_id = update.effective_user.id
        user_input = update.message.text.strip()

        logger.info(
            f"Пользователь вводит количество сигарет для follow-up опроса: '{user_input}'"
        )

        session = await self._session_manager.get_follow_up_session_by_telegram_id(user_id)

        if not session:
            logger.error(f"Сессия follow-up опроса не найдена для пользователя {user_id}")
            await update.message.reply_text("Опрос уже завершён или не существует.")
            return

        try:
            cigs = int(user_input)
        except ValueError:
            logger.warning(
                f"Пользователь ввёл некорректное количество сигарет для опроса (follow_up_id={session.follow_up_id}): '{user_input}'"
            )
            await update.message.reply_text("⚠️ Пожалуйста, введите целое число.")
            return

        if not (0 <= cigs <= 100):
            logger.warning(
                f"Пользователь ввёл недопустимое количество сигарет для опроса (follow_up_id={session.follow_up_id}): {cigs}"
            )
            await update.message.reply_text("⚠️ Введите число от 0 до 100.")
            return

        follow_up = await self._follow_up_service.get_by_id(session.follow_up_id)
        await self._follow_up_service.complete(follow_up, ppa_7d=True, cigs_per_day=cigs)
        await self._session_manager.delete_follow_up_session(session.follow_up_id)

        logger.info(
            f"Follow-up опрос (follow_up_id={session.follow_up_id}) завершён для пользователя: курит {cigs} сигарет/день"
        )

        await update.message.reply_text("✅ Спасибо! Ваш ответ записан.")
