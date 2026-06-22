import logging
from datetime import datetime, date
from typing import List, Optional, Tuple

from telegram import Bot
from telegram.error import TelegramError

from src.models import Participant
from src.repositories import InterventionContentRepository
from src.repositories import ParticipantRepository

logger = logging.getLogger(__name__)


class InterventionContentSender:
    """
    Service for sending educational and motivational content to group B participants.
        Educational messages are sent every 7 days from registration date.
    Motivational messages are sent every 14 days with a configurable shift.
    """

    MOTIVATIONAL_START_DAY = 10  # Days after educational messages to send motivational content

    def __init__(
            self,
            bot: Bot,
            content_repo: InterventionContentRepository,
            participant_repo: ParticipantRepository,
    ):
        """
        Initialize the content sender service.

        Args:
            bot: Telegram bot instance
            content_repo: Repository for content operations
            participant_repo: Repository for participant operations
        """
        self._bot = bot
        self._content_repo = content_repo
        self._participant_repo = participant_repo

    async def _get_participants_due_for_educational(self, target_date: date) -> List[Participant]:
        """
        Get participants who should receive educational content on the target date.

        Educational messages are sent every 7 days from registration date.

        Args:
            target_date: Date to check for delivery

        Returns:
            List of tuples (participant, week_number) for participants due today
        """
        participants = await self._participant_repo.get_all_by_group('B')
        if not participants:
            return []

        due_participants = []

        for participant in participants:
            registration_date = participant.registration_date.date()
            days_since = (target_date - registration_date).days

            # Send on day 0 (registration day) and every 7 days thereafter
            if days_since >= 0 and days_since % 7 == 0:
                week_number = (days_since // 7) + 1

                if week_number <= 24:
                    due_participants.append((participant, week_number))

        return due_participants

    async def _get_participants_due_for_motivational(self, target_date: date) -> List[Tuple[Participant, int]]:
        """
        Get participants who should receive motivational content on the target date.

        Motivational messages are sent every 14 days with a shift from educational dates.
        Example with shift=3: educational on days 0,7,14,21... motivational on days 3,17,31...

        Args:
            target_date: Date to check for delivery

        Returns:
            List of tuples (participant, week_number) for participants due today
        """
        participants = await self._participant_repo.get_all_by_group('B')
        if not participants:
            return []

        due_participants = []

        for participant in participants:
            registration_date = participant.registration_date.date()
            days_since = (target_date - registration_date).days

            if days_since >= self.MOTIVATIONAL_START_DAY:
                days_offset = days_since - self.MOTIVATIONAL_START_DAY
                if days_offset % 14 == 0:
                    week_number = (days_since // 7) + 1

                    if week_number <= 24:
                        due_participants.append((participant, week_number))

        return due_participants

    async def send_educational_message(self, target_date: Optional[date] = None) -> None:
        """
        Send weekly educational messages to participants due on the target date.

        Args:
            target_date: Date for delivery (defaults to today)
        """

        if target_date is None:
            target_date = datetime.now().date()

        due_participants = await self._get_participants_due_for_educational(target_date)

        if not due_participants:
            logger.info(f"Нет участников группы Б для образовательной рассылки на {target_date}")
            return

        participant_weeks = {p.participant_code: week for p, week in due_participants}

        content_with_ids = await self._content_repo.get_educational_content_with_ids(participant_weeks)

        for participant, week_number in due_participants:
            participant_code = participant.participant_code

            if participant_code not in content_with_ids:
                logger.warning(f"Нет образовательного контента для участника {participant_code}, неделя {week_number}")
                continue

            content_id, content_text = content_with_ids[participant_code]

            already_sent = await self._content_repo.get_already_sent_content_ids(
                participant_code, [content_id]
            )

            if content_id in already_sent:
                logger.info(
                    f"Образовательный контент {content_id} (неделя {week_number}) уже был отправлен "
                    f"участнику {participant_code}, пропускаем"
                )
                continue

            try:
                await self._bot.send_message(
                    chat_id=participant.telegram_id,
                    text=f"📚 **Образовательная информация** (неделя {week_number})\n\n{content_text}",
                    parse_mode='Markdown'
                )

                await self._content_repo.log_content_sent(participant_code, content_id)

                logger.info(
                    f"Образовательное сообщение отправлено участнику {participant_code} "
                    f"(неделя {week_number}, content_id: {content_id})"
                )

            except TelegramError as e:
                logger.error(
                    f"Ошибка отправки образовательного сообщения участнику {participant.participant_code}: {e}"
                )

    async def send_motivational_message(self, target_date: Optional[date] = None) -> None:
        """
        Send motivational messages (every 2 weeks with shift) to participants due on the target date.

        Args:
            target_date: Date for delivery (defaults to today)
        """
        if target_date is None:
            target_date = datetime.now().date()

        due_participants = await self._get_participants_due_for_motivational(target_date)

        if not due_participants:
            logger.info(f"Нет участников группы Б для мотивационной рассылки на {target_date}")
            return

        participant_weeks = {p.participant_code: week for p, week in due_participants}

        content_with_ids = await self._content_repo.get_motivational_content_with_ids(participant_weeks)

        for participant, week_number in due_participants:
            participant_code = participant.participant_code

            if participant_code not in content_with_ids:
                logger.warning(f"Нет мотивационного контента для участника {participant_code}, неделя {week_number}")
                continue

            content_id, content_text = content_with_ids[participant_code]

            already_sent = await self._content_repo.get_already_sent_content_ids(
                participant_code, [content_id]
            )

            if content_id in already_sent:
                logger.info(
                    f"Мотивационный контент {content_id} (неделя {week_number}) уже был отправлен "
                    f"участнику {participant_code}, пропускаем"
                )
                continue

            try:
                await self._bot.send_message(
                    chat_id=participant.telegram_id,
                    text=f"💪 **Мотивационная история** (неделя {week_number})\n\n{content_text}",
                    parse_mode='Markdown'
                )

                await self._content_repo.log_content_sent(participant_code, content_id)

                logger.info(
                    f"Мотивационное сообщение отправлено участнику {participant_code} "
                    f"(неделя {week_number}, content_id: {content_id})"
                )

            except TelegramError as e:
                logger.error(
                    f"Ошибка отправки мотивационного сообщения участнику {participant.telegram_id_encrypted}: {e}"
                )

    async def send_all_messages_for_today(self) -> None:
        """Send all types of messages (educational and motivational) for today."""

        current_time = datetime.now()
        current_date = current_time.date()

        logger.info(f"Запуск ежедневной рассылки")

        await self.send_educational_message(current_date)

        await self.send_motivational_message(current_date)

        logger.info(f"Ежедневная рассылка на {current_date} завершена")
