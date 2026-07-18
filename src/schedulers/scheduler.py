import asyncio
import logging
from datetime import datetime
from typing import Optional

from maxapi import Bot
from maxapi.enums import Intent, ParseMode
from maxapi.types import CallbackButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from src.payloads import FollowUpPPA7Payload, FinalPPA30Payload
from src.config import Config
from src.models import FollowUp, WeeklyCheckIn, FinalSurvey
from src.payloads.weekly_checkin import WeeklyCheckInStatusPayload
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
            google_sheets_exporter: Optional[GoogleSheetsExporter]
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
                await self._session_manager.delete_follow_up_sessions_by_max_id(item.max_id)
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
                await self._session_manager.delete_follow_up_sessions_by_max_id(item.max_id)
                await self._mark_sent_final(item.survey)
            else:
                logger.warning(f"Final survey {item.survey.id} не отправлен, пропускаем отметку")

    async def _send_follow_up(self, item: PendingFollowUp) -> bool:
        follow_up = item.follow_up
        max_id = item.max_id

        builder = InlineKeyboardBuilder()
        builder.row(CallbackButton(text="✅ Да", intent=Intent.POSITIVE,
                                   payload=FollowUpPPA7Payload(follow_up_id=follow_up.id, answer="yes").pack()))
        builder.row(CallbackButton(text="❌ Нет", intent=Intent.NEGATIVE,
                                   payload=FollowUpPPA7Payload(follow_up_id=follow_up.id, answer="no").pack()))

        text = (
            "📋 «Здравствуйте! Напоминаем о вашем участии в исследовании.\n"
            "Пожалуйста, ответьте на несколько коротких вопросов о вашем текущем статусе курения».\n\n"
            "Курили ли Вы хотя бы одну сигарету за последние 7 дней?"
        )
        try:
            result = await self._bot.send_message(
                user_id=max_id,
                text=text,
                attachments=[builder.as_markup()],

            )
            if result:
                logger.info(f"Follow‑up отправлен участнику (опрос {follow_up.id})")
                return True
            logger.error(f"Ошибка отправки follow-up участнику (опрос {follow_up.id})")
        except Exception as e:
            logger.error(f"Ошибка отправки follow‑up участнику (опрос {follow_up.id}): {e}")
            return False

    async def _send_weekly_checkin(self, item: PendingWeeklyCheckIn) -> bool:
        checkin = item.checkin
        max_id = item.max_id

        builder = InlineKeyboardBuilder()
        builder.row(
            CallbackButton(text="🚭 Не курил",
                           payload=WeeklyCheckInStatusPayload(checkin_id=checkin.id, answer="not").pack()))
        builder.row(CallbackButton(text="📅 Эпизодически",
                                   payload=WeeklyCheckInStatusPayload(checkin_id=checkin.id, answer="some").pack()))
        builder.row(CallbackButton(text="🔁 Регулярно",
                                   payload=WeeklyCheckInStatusPayload(checkin_id=checkin.id, answer="regular").pack()))
        text = (
            f"📅 **Чек-ин недели {checkin.week_number}**\n\n"
            "Ваш статус курения за прошедшую неделю:"
        )
        try:
            result = await self._bot.send_message(
                user_id=max_id,
                text=text,
                attachments=[builder.as_markup()],
                format=ParseMode.MARKDOWN,
            )
            if result:
                logger.info(f"Weekly check‑in (неделя {checkin.week_number}) отправлен участнику")
                return True
            logger.error(f"Ошибка отправки weekly check‑in (checkin_id: {checkin.id})")
            return False
        except Exception as e:
            logger.error(f"Ошибка отправки weekly check‑in (checkin_id: {checkin.id}): {e}")
            return False

    async def _send_final_survey(self, item: PendingFinalSurvey) -> bool:
        survey = item.survey
        max_id = item.max_id

        builder = InlineKeyboardBuilder()
        builder.row(CallbackButton(text="✅ Да", intent=Intent.POSITIVE,
                                   payload=FinalPPA30Payload(survey_id=survey.id, answer="yes").pack()))
        builder.row(CallbackButton(text="❌ Нет", intent=Intent.NEGATIVE,
                                   payload=FinalPPA30Payload(survey_id=survey.id, answer="no").pack()))

        text = (
            "🎯 **Финальный опрос (6 месяцев)**\n\n"
            "Курили ли Вы хотя бы одну сигарету за последние 30 дней?"
        )
        try:
            result = await self._bot.send_message(
                user_id=max_id,
                text=text,
                attachments=[builder.as_markup()],
                format=ParseMode.MARKDOWN,
            )
            if result:
                logger.info(f"Финальный опрос отправлен участнику (survey_id: {survey.id})")
                return True
            logger.error(f"Ошибка отправки финального опроса участнику (survey_id: {survey.id})")
        except Exception as e:
            logger.error(f"Ошибка отправки финального опроса участнику (survey_id: {survey.id}): {e}")
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
