import logging
from datetime import datetime

from src.services import InterventionContentSender

logger = logging.getLogger(__name__)


class InterventionContentScheduler:
    """
    Scheduler for regular educational and motivational content delivery.

    Runs daily checks and sends messages when the configured hour threshold is reached.
    """

    EDUCATIONAL_HOUR = 14
    MOTIVATIONAL_HOUR = 14

    def __init__(self, content_sender: InterventionContentSender):
        """
        Initialize the content scheduler.

        Args:
            content_sender: Service instance for sending content messages
        """

        self._content_sender = content_sender

    async def process_daily(self) -> None:
        """Perform daily content check and delivery."""
        now = datetime.now()

        if now.hour >= self.EDUCATIONAL_HOUR:
            await self._content_sender.send_educational_message()

        if now.hour >= self.MOTIVATIONAL_HOUR:
            await self._content_sender.send_motivational_message()

    async def run_all(self) -> None:
        """Execute all content scheduler tasks."""
        try:
            await self.process_daily()
        except Exception as e:
            logger.error(f"Ошибка в планировщике контента: {e}", exc_info=True)
