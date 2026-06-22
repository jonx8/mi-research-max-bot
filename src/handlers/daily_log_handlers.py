import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.services import DailyLogService

logger = logging.getLogger(__name__)


class DailyLogHandlers:
    """
    Handlers for daily evening survey responses.

    These handlers process user responses to the daily evening questionnaire
    about smoking cravings and difficulties.
    """

    def __init__(self, daily_log_service: DailyLogService):
        """
        Initialize daily log handlers.

        Args:
            daily_log_service: Service for managing daily log entries
        """
        self._daily_service = daily_log_service

    async def handle_evening_response(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Process callback response from evening survey.

        Expected callback data format: "daily_{log_id}_{yes/difficult/craving}"

        Args:
            update: Telegram update object containing callback query
            _: Context object (unused)
        """
        query = update.callback_query
        await query.answer()
        data = query.data  # "daily_{log_id}_{yes/difficult/craving}"

        parts = data.split('_')
        log_id = int(parts[1])
        response = parts[2]

        logger.info(
            f"Пользователь отвечает на вечерний опрос (log_id={log_id}): ответ='{response}'"
        )

        # Map values to human-readable format
        response_map = {'yes': 'да', 'difficult': 'трудности', 'craving': 'тяга'}

        await self._daily_service.save_evening_response(log_id, response_map[response])

        await query.edit_message_text(
            "✅ Спасибо за ответ! Желаем спокойного вечера и хорошего отдыха."
        )

        logger.info(
            f"Вечерний опрос (log_id={log_id}) успешно сохранён с ответом '{response_map[response]}'"
        )
