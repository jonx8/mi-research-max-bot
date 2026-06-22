import logging
from datetime import datetime

from src.repositories import DailyLogRepository

logger = logging.getLogger(__name__)


class DailyLogService:
    def __init__(self, daily_log_repo: DailyLogRepository):
        self._daily_log_repo = daily_log_repo

    async def save_evening_response(self, log_id: int, response: str) -> None:
        """Сохраняет ответ на вечерний опрос."""
        log = await self._daily_log_repo.get_by_id(log_id)
        if not log:
            logger.error(f"DailyLog {log_id} не найден при сохранении ответа")
            return
        log.evening_response = response
        log.evening_response_at = datetime.now()
        await self._daily_log_repo.update(log)
        logger.info(f"Вечерний ответ сохранён для {log.participant_code}: {response}")
