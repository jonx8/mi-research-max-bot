import logging
from datetime import datetime, date

from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import TelegramError

from src.models import DailyLog
from src.repositories import BaselineQuestionnaireRepository
from src.repositories import DailyLogRepository
from src.repositories import MorningTipRepository
from src.repositories import ParticipantRepository
from src.utils import BatchSender

logger = logging.getLogger(__name__)


class DailyLogSender:
    def __init__(
            self,
            bot: Bot,
            daily_log_repo: DailyLogRepository,
            participant_repo: ParticipantRepository,
            morning_tip_repo: MorningTipRepository,
            baseline_repo: BaselineQuestionnaireRepository,
            batch_sender: BatchSender[DailyLog]
    ):
        self._bot = bot
        self._daily_log_repo = daily_log_repo
        self._morning_tip_repo = morning_tip_repo
        self._participant_repo = participant_repo
        self._baseline_repo = baseline_repo
        self._batch_sender = batch_sender

    async def _send_tip_message(self, log: DailyLog, telegram_id: int, tip_type: str) -> None:
        participant = await self._participant_repo.get_by_id(log.participant_code)

        if not participant:
            logger.error(f"Не найдены данные для участника {log.participant_code}")
            return

        registration_date = participant.registration_date

        days_since_registration = (datetime.now().date() - registration_date.date()).days
        month_index = min(max(days_since_registration // 30 + 1, 1), 6)

        baseline = await self._baseline_repo.get_by_participant_code(log.participant_code)

        if tip_type == 'high_dependence' and (baseline is None or baseline.fagerstrom_score < 7):
            return

        tip = await self._morning_tip_repo.get_random_tip(month_index, tip_type)

        try:
            await self._bot.send_message(
                chat_id=telegram_id,
                text=f"💡 **Совет:**\n\n {tip}\n\n",
                parse_mode='Markdown'
            )
            if tip_type == 'regular':
                log.morning_sent_at = datetime.now()
            else:
                log.high_dep_sent_at = datetime.now()
            await self._daily_log_repo.update(log)
            logger.info(f"Утреннее сообщение отправлено {telegram_id}")
        except TelegramError as e:
            logger.error(f"Ошибка отправки утреннего сообщения {telegram_id}: {e}")

    async def _send_evening_message(self, log: DailyLog, telegram_id: int) -> None:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да, справился", callback_data=f"daily_{log.id}_yes")],
            [InlineKeyboardButton("❌ Были трудности", callback_data=f"daily_{log.id}_difficult")],
            [InlineKeyboardButton("🆘 Сильная тяга", callback_data=f"daily_{log.id}_craving")],
        ])
        text = "🌙 **Как прошёл день?**\n\nУдалось ли избежать курения?"
        try:
            await self._bot.send_message(
                chat_id=telegram_id,
                text=text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            log.evening_sent_at = datetime.now()
            await self._daily_log_repo.update(log)
            logger.info(f"Вечерний опрос отправлен {telegram_id}")
        except TelegramError as e:
            logger.error(f"Ошибка отправки вечернего опроса {telegram_id}: {e}")

    async def send_morning_messages(self, log_date: date) -> None:
        """Отправляет утренние сообщения всем участникам группы B."""
        participants = await self._participant_repo.get_all_by_group('B')

        if not participants:
            logger.info("Нет участников группы B для утренней рассылки")
            return

        codes = [participant.participant_code for participant in participants]
        logs = list(filter(lambda log: not log.morning_sent_at,
                           await self._daily_log_repo.get_or_create_batch(codes, log_date)))

        telegram_ids = {participant.participant_code: participant.telegram_id for participant in participants}

        async def send_one(log: DailyLog):
            if log.morning_sent_at:
                return
            telegram_id = telegram_ids.get(log.participant_code)
            if not telegram_id:
                logger.error(f"Не найден telegram_id для участника {log.participant_code}")
                return

            await self._send_tip_message(log, telegram_id, 'regular')

        await self._batch_sender.send(items=logs, send_func=send_one)

    async def send_high_dep_messages(self, log_date: date) -> None:
        """Отправляет сообщения для высокой зависимости всем участникам группы B с высоким баллом."""
        participants = await self._participant_repo.get_all_by_group('B')

        if not participants:
            logger.info("Нет участников группы B для рассылки высокой зависимости")
            return
        codes = [participant.participant_code for participant in participants]
        logs = list(filter(lambda log: not log.high_dep_sent_at,
                           await self._daily_log_repo.get_or_create_batch(codes, log_date)))

        telegram_ids = {participant.participant_code: participant.telegram_id for participant in participants}

        async def send_one(log: DailyLog):
            if log.high_dep_sent_at:
                return
            telegram_id = telegram_ids.get(log.participant_code)
            if not telegram_id:
                logger.error(f"Не найден telegram_id для участника {log.participant_code}")
                return

            await self._send_tip_message(log, telegram_id, 'high_dependence')

        await self._batch_sender.send(items=logs, send_func=send_one)

    async def send_evening_messages(self, log_date: date) -> None:
        """Отправляет вечерние опросы всем участникам группы B."""
        participants = await self._participant_repo.get_all_by_group('B')
        if not participants:
            logger.info("Нет участников группы B для вечерней рассылки")
            return

        codes = [participant.participant_code for participant in participants]
        logs = list(filter(lambda log: not log.evening_sent_at,
                           await self._daily_log_repo.get_or_create_batch(codes, log_date)))

        telegram_ids = {participant.participant_code: participant.telegram_id for participant in participants}

        async def send_one(log: DailyLog):
            if log.evening_sent_at:
                return
            telegram_id = telegram_ids.get(log.participant_code)
            if not telegram_id:
                logger.error(f"Не найден telegram_id для участника {log.participant_code}")
                return
            await self._send_evening_message(log, telegram_id)

        await self._batch_sender.send(items=logs, send_func=send_one)
