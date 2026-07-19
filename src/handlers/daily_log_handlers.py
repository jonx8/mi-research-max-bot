import logging

from maxapi.enums import ParseMode
from maxapi.types import MessageCallback

from src.payloads import DailyLogPayload
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

    async def handle_evening_response(self, event: MessageCallback, payload: DailyLogPayload) -> None:
        """Process callback response from evening survey."""

        logger.info(
            f"Пользователь отвечает на вечерний опрос (log_id={payload.log_id}): ответ='{payload.answer}'"
        )

        # Map values to human-readable format
        response_map = {'yes': 'да', 'difficult': 'трудности', 'craving': 'тяга'}

        try:
            await self._daily_service.save_evening_response(payload.log_id, response_map[payload.answer])
        except Exception as e:
            logger.error(f"Ошибка сохранения ответа (log_id={payload.log_id}): {e}")

        await event.message.edit(
            text="✅ Спасибо за ответ! Желаем спокойного вечера и хорошего отдыха.",
            format=ParseMode.MARKDOWN,
            attachments=[]
        )

        logger.info(
            f"Вечерний опрос (log_id={payload.log_id}) успешно сохранён с ответом '{response_map[payload.answer]}'"
        )
