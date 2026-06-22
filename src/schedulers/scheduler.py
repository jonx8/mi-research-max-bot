import asyncio
import logging
from datetime import datetime

from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import TelegramError

from src.config import Config
from src.models import FollowUp, WeeklyCheckIn, FinalSurvey
from src.repositories import FollowUpRepository, WeeklyCheckInRepository, FinalSurveyRepository, PendingFollowUp, \
    PendingWeeklyCheckIn, PendingFinalSurvey
from src.services import GoogleSheetsExporter, DailyLogSender
from src.services import SessionManager

logger = logging.getLogger(__name__)


class SchedulerService:
    """Сервис периодической рассылки запланированных опросов."""

    def __init__(
            self,
            bot: Bot,
            config: Config,
            session_manager: SessionManager,
            follow_up_repo: FollowUpRepository,
            weekly_check_in_repo: WeeklyCheckInRepository,
            final_repo: FinalSurveyRepository,
            daily_log_sender: DailyLogSender,
            google_sheets_exporter: GoogleSheetsExporter
    ):
        self._bot = bot
        self._config = config
        self._session_manager = session_manager
        self._follow_up_repo = follow_up_repo
        self._weekly_check_in_repo = weekly_check_in_repo
        self._final_repo = final_repo
        self._daily_log_sender = daily_log_sender
        self._google_sheets_exporter = google_sheets_exporter

    async def process_all_pending(self) -> None:
        await self._process_follow_ups()
        await self._process_weekly_checkins()
        await self._process_final_surveys()

    async def process_daily_logs(self) -> None:
        now = datetime.now()
        today = now.date()

        if now.time() > self._config.DAILY_MORNING_SENDING_TIME:
            await self._daily_log_sender.send_morning_messages(today)
        if now.time() > self._config.DAILY_HIGH_DEP_SENDING_TIME:
            await self._daily_log_sender.send_high_dep_messages(today)
        if now.time() > self._config.DAILY_EVENING_SENDING_TIME:
            await self._daily_log_sender.send_evening_messages(today)

    async def export_to_google_sheets(self) -> None:
        if self._google_sheets_exporter is None:
            logger.warning("Google Sheets экспортер не настроен, экспорт пропущен")
            return

        try:
            logger.info("Начало экспорта данных в Google Sheets")
            results = await asyncio.wait_for(
                asyncio.to_thread(self._google_sheets_exporter.export_all_optimized_sync),
                timeout=self._config.GOOGLE_SHEETS_EXPORT_TIMEOUT
            )
            logger.info(f"Экспорт завершен: {results}")
        except Exception as e:
            logger.error(f"Ошибка при экспорте в Google Sheets: {e}", exc_info=True)

    async def _process_follow_ups(self) -> None:
        """Обрабатывает pending follow‑up опросы."""
        pending_items = await self._follow_up_repo.get_all_pending_with_participant()
        for item in pending_items:
            success = await self._send_follow_up(item)
            if success:
                await self._session_manager.delete_follow_up_sessions_by_telegram_id(item.telegram_id)
                await self._mark_sent_follow_up(item.follow_up)
            else:
                logger.warning(f"Follow‑up {item.follow_up.id} не отправлен, пропускаем отметку")

    async def _process_weekly_checkins(self) -> None:
        """Обрабатывает pending weekly check‑in опросы."""
        pending_items = await self._weekly_check_in_repo.get_all_pending_with_participant()
        for item in pending_items:
            success = await self._send_weekly_checkin(item)
            if success:
                await self._mark_sent_weekly(item.checkin)
            else:
                logger.warning(f"Weekly check‑in {item.checkin.id} не отправлен, пропускаем отметку")

    async def _process_final_surveys(self) -> None:
        """Обрабатывает pending финальные опросы."""
        pending_items = await self._final_repo.get_all_pending_with_participant()
        for item in pending_items:
            success = await self._send_final_survey(item)
            if success:
                await self._session_manager.delete_follow_up_sessions_by_telegram_id(item.telegram_id)
                await self._mark_sent_final(item.survey)
            else:
                logger.warning(f"Final survey {item.survey.id} не отправлен, пропускаем отметку")

    async def _send_follow_up(self, item: PendingFollowUp) -> bool:
        follow_up = item.follow_up
        telegram_id = item.telegram_id

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да", callback_data=f"followup_{follow_up.id}_ppa_yes")],
            [InlineKeyboardButton("❌ Нет", callback_data=f"followup_{follow_up.id}_ppa_no")]
        ])
        text = (
            "📋 «Здравствуйте! Напоминаем о вашем участии в исследовании.\n"
            "Пожалуйста, ответьте на несколько коротких вопросов о вашем текущем статусе курения».\n\n"
            "Курили ли Вы хотя бы одну сигарету за последние 7 дней?"
        )
        try:
            await self._bot.send_message(
                chat_id=telegram_id,
                text=text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            logger.info(f"Follow‑up отправлен участнику {telegram_id} (опрос {follow_up.id})")
            return True
        except TelegramError as e:
            logger.error(f"Ошибка отправки follow‑up участнику {telegram_id}: {e}")
            return False

    async def _send_weekly_checkin(self, item: PendingWeeklyCheckIn) -> bool:
        checkin = item.checkin
        telegram_id = item.telegram_id

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚭 Не курил", callback_data=f"weekly_{checkin.id}_status_not")],
            [InlineKeyboardButton("📅 Эпизодически", callback_data=f"weekly_{checkin.id}_status_some")],
            [InlineKeyboardButton("🔁 Регулярно", callback_data=f"weekly_{checkin.id}_status_regular")],
        ])
        text = (
            f"📅 **Чек-ин недели {checkin.week_number}**\n\n"
            "Ваш статус курения за прошедшую неделю:"
        )
        try:
            await self._bot.send_message(
                chat_id=telegram_id,
                text=text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            logger.info(f"Weekly check‑in (неделя {checkin.week_number}) отправлен участнику {telegram_id}")
            return True
        except TelegramError as e:
            logger.error(f"Ошибка отправки weekly check‑in участнику {telegram_id}: {e}")
            return False

    async def _send_final_survey(self, item: PendingFinalSurvey) -> bool:
        survey = item.survey
        telegram_id = item.telegram_id

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да", callback_data=f"final_{survey.id}_ppa30_yes")],
            [InlineKeyboardButton("❌ Нет", callback_data=f"final_{survey.id}_ppa30_no")]
        ])
        text = (
            "🎯 **Финальный опрос (6 месяцев)**\n\n"
            "Курили ли Вы хотя бы одну сигарету за последние 30 дней?"
        )
        try:
            await self._bot.send_message(
                chat_id=telegram_id,
                text=text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            logger.info(f"Финальный опрос отправлен участнику {telegram_id}")
            return True
        except TelegramError as e:
            logger.error(f"Ошибка отправки финального опроса участнику {telegram_id}: {e}")
            return False

    async def _mark_sent_follow_up(self, follow_up: FollowUp) -> None:
        follow_up.sent_at = datetime.now()
        await self._follow_up_repo.update(follow_up)

    async def _mark_sent_weekly(self, checkin: WeeklyCheckIn) -> None:
        checkin.sent_at = datetime.now()
        await self._weekly_check_in_repo.update(checkin)

    async def _mark_sent_final(self, survey: FinalSurvey) -> None:
        survey.sent_at = datetime.now()
        await self._final_repo.update(survey)