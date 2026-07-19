import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from maxapi import Bot, Dispatcher, F
from maxapi.enums import ParseMode
from maxapi.filters.command import Command, CommandStart
from maxapi.types import BotStarted
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from scripts import seed_intervention_content, seed_techniques, seed_tips
from src.config.config import Config
from src.config.logging_config import setup_logging
from src.database import Database
from src.handlers.daily_log_handlers import DailyLogHandlers
from src.handlers.final_survey_handlers import FinalSurveyHandlers
from src.handlers.follow_up_survey_handlers import FollowUpSurveyHandlers
from src.handlers.menu_handlers import MenuHandlers
from src.handlers.registration_handlers import RegistrationHandlers
from src.handlers.sos_module_handlers import SOSModuleHandlers
from src.handlers.weekly_check_in_handlers import WeeklyCheckInHandlers
from src.payloads.daily_log import DailyLogPayload
from src.payloads.final_survey import FinalPPA30Payload, FinalPPA7Payload, FinalQuitAttemptsPayload
from src.payloads.follow_up import FollowUpPPA7Payload
from src.payloads.menu import HelpPayload, IdPayload, MenuPayload, SosPayload
from src.payloads.registration import AnswerPayload, BackPayload, ClinicCenterPayload, ConsentPayload, GenderPayload, MedicalHelpPayload, QuitAttemptsPayload, SmokerHouseholdPayload, StartQuestionnairePayload, VapePayload
from src.payloads.sos_module import AnalyzeCravingPayload, BeginAnalysisPayload, HelpedPayload, NewTechniquesPayload, TechniquePayload
from src.payloads.weekly_checkin import WeeklyCheckInCravingPayload, WeeklyCheckInMoodPayload, WeeklyCheckInStatusPayload
from src.repositories.baseline_repo import BaselineQuestionnaireRepository
from src.repositories.craving_analysis_repo import CravingAnalysisRepository
from src.repositories.daily_log_repo import DailyLogRepository
from src.repositories.final_repo import FinalSurveyRepository
from src.repositories.follow_up_repo import FollowUpRepository
from src.repositories.intervention_content_repo import InterventionContentRepository
from src.repositories.morning_tips_repo import MorningTipRepository
from src.repositories.participant_repo import ParticipantRepository
from src.repositories.session_repo import SessionRepository
from src.repositories.sos_usage_repo import SOSUsageRepository
from src.repositories.technique_repo import TechniqueRepository
from src.repositories.weekly_check_in_repo import WeeklyCheckInRepository
from src.schedulers.intervention_scheduler import InterventionContentScheduler
from src.schedulers.scheduler import SchedulerService
from src.services.baseline_questionnaire_service import BaselineQuestionnaireService
from src.services.craving_analysis_orchestrator import CravingAnalysisOrchestrator
from src.services.craving_analysis_service import CravingAnalysisService
from src.services.daily_log_sender import DailyLogSender
from src.services.daily_log_service import DailyLogService
from src.services.final_service import FinalSurveyService
from src.services.follow_up_service import FollowUpService
from src.services.google_sheets_exporter import GoogleSheetsExporter
from src.services.intervention_content_sender import InterventionContentSender
from src.services.participant_service import ParticipantService
from src.services.registration_orchestrator import RegistrationOrchestrator, RegistrationStep, RegistrationStep
from src.services.session_manager import SessionManager
from src.services.sos_usage_service import SOSUsageService
from src.services.technique_service import TechniqueService
from src.services.weekly_check_in_service import WeeklyCheckInService
from src.utils.batch_sender import BatchSender
from src.utils.encryption import init_encryption


config = Config()
setup_logging(config)
init_encryption(config.ENCRYPTION_KEY)

logger = logging.getLogger(__name__)

database = Database(config.DATABASE_URL)

batch_sender = BatchSender()

participant_repo = ParticipantRepository(database)
baseline_repo = BaselineQuestionnaireRepository(database)
follow_up_repo = FollowUpRepository(database)
weekly_checkin_repo = WeeklyCheckInRepository(database)
daily_log_repo = DailyLogRepository(database)
final_survey_repo = FinalSurveyRepository(database)
morning_tip_repo = MorningTipRepository(database)
intervention_content_repo = InterventionContentRepository(database)
technique_repo = TechniqueRepository(database)
sos_usage_repo = SOSUsageRepository(database)
craving_analysis_repo = CravingAnalysisRepository(database)
session_repo = SessionRepository(database)

participant_service = ParticipantService(participant_repo)
baseline_service = BaselineQuestionnaireService(baseline_repo)
follow_up_service = FollowUpService(follow_up_repo)
weekly_checkin_service = WeeklyCheckInService(weekly_checkin_repo)
final_survey_service = FinalSurveyService(final_survey_repo)
technique_service = TechniqueService(technique_repo)
daily_log_service = DailyLogService(daily_log_repo)
sos_usage_service = SOSUsageService(sos_usage_repo)
craving_analysis_service = CravingAnalysisService(craving_analysis_repo)

session_manager = SessionManager(session_repo)
registration_orchestrator = RegistrationOrchestrator(
    session_manager,
    participant_service,
    baseline_service,
    follow_up_service,
    weekly_checkin_service,
    final_survey_service,
    config
)
craving_analysis_orchestrator = CravingAnalysisOrchestrator(
    session_manager,
    craving_analysis_service,
    participant_service
)

registration_handlers = RegistrationHandlers(registration_orchestrator, participant_service)
menu_handlers = MenuHandlers(participant_service, config)
sos_module_handlers = SOSModuleHandlers(
    technique_service,
    participant_service,
    craving_analysis_orchestrator,
    sos_usage_service
)

follow_up_handlers = FollowUpSurveyHandlers(follow_up_service, session_manager)
weekly_checkin_handlers = WeeklyCheckInHandlers(weekly_checkin_service, session_manager)
final_survey_handlers = FinalSurveyHandlers(final_survey_service, session_manager)
daily_log_handlers = DailyLogHandlers(daily_log_service)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()


@dp.bot_started()
async def on_bot_started(event: BotStarted):
    await registration_handlers.handle_start(event)


@dp.message_created(CommandStart())
async def on_start(event: MessageCreated) -> None:
    await registration_handlers.handle_start(event)

@dp.message_callback(MenuPayload().filter())
async def on_menu_button(event: MessageCallback) -> None:
    await event.answer()
    await menu_handlers.handle_main_menu(event)

@dp.message_callback(IdPayload().filter())
async def on_id_button(event: MessageCallback) -> None:
    await event.answer()
    await menu_handlers.handle_id_menu(event)


@dp.message_created(Command("id"))
async def on_id_command(event: MessageCreated) -> None:
    await menu_handlers.handle_id_menu(event)


@dp.message_callback(HelpPayload.filter())
async def on_help_button(event: MessageCallback) -> None:
    await event.answer()
    await menu_handlers.handle_help_menu(event)


@dp.message_created(Command("help"))
async def on_help_command(event: MessageCreated):
    await menu_handlers.handle_help_menu(event)


@dp.message_callback(SosPayload().filter())
async def on_sos_button(event: MessageCallback):
    await event.answer()
    await sos_module_handlers.show_sos_menu(event)


@dp.message_created(Command("sos"))
async def on_sos_command(event: MessageCreated) -> None:
    user_id = event.message.sender.user_id
    if not await participant_service.exists(user_id):
        await event.message.answer(
            "❌ Вы не зарегистрированы в исследовании.\n\n"
            "Введите /start для регистрации."
        )
        return

    user_group = await participant_service.get_group(user_id)
    if user_group == 'A':
        await event.message.answer(
            "ℹ️ **Вам назначен базовый тип поддержки**\n\n"
            "Вы будете получать периодические опросы о вашем статусе курения.\n\n"
            "Спасибо за участие в исследовании!",
            format=ParseMode.MARKDOWN,
            attachments=[InlineKeyboardBuilder().as_markup()]
        )
        return
    await sos_module_handlers.show_sos_menu(event)


@dp.message_callback(ConsentPayload.filter())
async def on_consent(event: MessageCallback, payload: ConsentPayload) -> None:
    await event.answer()
    await registration_handlers.handle_consent(event, payload)


@dp.message_created(F.message.body.text)
async def on_text(event: MessageCreated) -> None:
    max_id = event.from_user.user_id

    if await craving_analysis_orchestrator.is_analysis_active(max_id):
        await sos_module_handlers.handle_analysis_answer_from_message(event)
        return

    registration_session = await session_manager.get_registration_session_by_max_id(max_id)
    if registration_session and registration_session.step:
        await registration_handlers.handle_text_for_step(event, RegistrationStep(registration_session.step))
        return

    follow_up_session = await session_manager.get_follow_up_session_by_max_id(max_id)
    if follow_up_session:
        await follow_up_handlers.handle_follow_up_cigs_input(event)
        return

    final_session = await session_manager.get_final_survey_session_by_max_id(max_id)
    if final_session:
        if final_session.cigs_per_day is None and final_session.ppa_7d:
            await final_survey_handlers.handle_final_cigs_input(event)
        elif final_session.days_to_first_lapse is None and final_session.quit_attempt_made:
            await final_survey_handlers.handle_final_days_input(event)
        return

    await menu_handlers.handle_main_menu(event)


@dp.message_callback(GenderPayload.filter())
async def on_gender(event: MessageCallback, payload: GenderPayload) -> None:
    await event.answer()
    await registration_handlers.handle_gender_callback(event, payload)


@dp.message_callback(ClinicCenterPayload.filter())
async def on_clinic_center(event: MessageCallback, payload: ClinicCenterPayload) -> None:
    await event.answer()
    await registration_handlers.handle_clinic_center_callback(event, payload)


@dp.message_callback(QuitAttemptsPayload.filter())
async def on_quit_attempts(event: MessageCallback, payload: QuitAttemptsPayload) -> None:
    await event.answer()
    await registration_handlers.handle_quit_attempts_callback(event, payload)


@dp.message_callback(VapePayload.filter())
async def on_vape(event: MessageCallback, payload: VapePayload) -> None:
    await event.answer()
    await registration_handlers.handle_vape_usage_callback(event, payload)


@dp.message_callback(SmokerHouseholdPayload.filter())
async def on_smoker_household(event: MessageCallback, payload: SmokerHouseholdPayload) -> None:
    await event.answer()
    await registration_handlers.handle_smoker_household_callback(event, payload)


@dp.message_callback(MedicalHelpPayload.filter())
async def on_medical_help(event: MessageCallback, payload: MedicalHelpPayload) -> None:
    await event.answer()
    await registration_handlers.handle_medical_help_callback(event, payload)


@dp.message_callback(StartQuestionnairePayload.filter())
async def on_start_questionnaire(event: MessageCallback, payload: StartQuestionnairePayload) -> None:
    await event.answer()
    await registration_handlers.start_questionnaire_handler(event, payload)


@dp.message_callback(AnswerPayload.filter())
async def on_answer(event: MessageCallback, payload: AnswerPayload) -> None:
    await event.answer()
    await registration_handlers.handle_answer_callback(event, payload)


@dp.message_callback(BackPayload.filter())
async def on_back(event: MessageCallback, payload: BackPayload) -> None:
    await event.answer()
    await registration_handlers.handle_back_callback(event, payload)


@dp.message_callback(TechniquePayload.filter())
async def on_technique(event: MessageCallback, payload: TechniquePayload) -> None:
    await event.answer()
    await sos_module_handlers.handle_technique_callback(event.callback.user.user_id, payload.technique_id, event)


@dp.message_callback(NewTechniquesPayload.filter())
async def on_new_techniques(event: MessageCallback) -> None:
    await event.answer()
    await sos_module_handlers.handle_new_techniques_callback(event)


@dp.message_callback(HelpedPayload.filter())
async def on_helped(event: MessageCallback) -> None:
    await event.answer()
    await sos_module_handlers.handle_helped_callback(event)


@dp.message_callback(AnalyzeCravingPayload.filter())
async def on_analyze_craving(event: MessageCallback) -> None:
    await event.answer()
    await sos_module_handlers.start_analysis_callback(event)


@dp.message_callback(BeginAnalysisPayload.filter())
async def on_begin_analysis(event: MessageCallback) -> None:
    await event.answer()
    await sos_module_handlers.begin_analysis_callback(event)


@dp.message_callback(DailyLogPayload.filter())
async def on_daily_log(event: MessageCallback, payload: DailyLogPayload) -> None:
    await event.answer()
    await daily_log_handlers.handle_evening_response(event, payload)


@dp.message_callback(FollowUpPPA7Payload.filter())
async def on_follow_up(event: MessageCallback, payload: FollowUpPPA7Payload) -> None:
    await event.answer()
    await follow_up_handlers.handle_follow_up_answer(event, payload)


@dp.message_callback(WeeklyCheckInStatusPayload.filter())
async def on_weekly_status(event: MessageCallback, payload: WeeklyCheckInStatusPayload) -> None:
    await event.answer()
    await weekly_checkin_handlers.handle_weekly_status(event, payload)


@dp.message_callback(WeeklyCheckInCravingPayload.filter())
async def on_weekly_craving(event: MessageCallback, payload: WeeklyCheckInCravingPayload) -> None:
    await event.answer()
    await weekly_checkin_handlers.handle_weekly_craving_input(event, payload)


@dp.message_callback(WeeklyCheckInMoodPayload.filter())
async def on_weekly_mood(event: MessageCallback, payload: WeeklyCheckInMoodPayload) -> None:
    await event.answer()
    await weekly_checkin_handlers.handle_weekly_mood(event, payload)


@dp.message_callback(FinalPPA30Payload.filter())
async def on_final_survey_start(event: MessageCallback, payload: FinalPPA30Payload) -> None:
    await event.answer()
    await final_survey_handlers.handle_final_survey_start(event, payload)


@dp.message_callback(FinalPPA7Payload.filter())
async def on_final_ppa7(event: MessageCallback, payload: FinalPPA7Payload) -> None:
    await event.answer()
    await final_survey_handlers.handle_final_ppa7(event, payload)


@dp.message_callback(FinalQuitAttemptsPayload.filter())
async def on_final_quit_attempt(event: MessageCallback, payload: FinalQuitAttemptsPayload) -> None:
    await event.answer()
    await final_survey_handlers.handle_final_quit_attempt(event, payload)


async def main() -> None:
    await seed_techniques.seed_techniques()
    await seed_tips.seed_morning_tips()
    await seed_intervention_content.seed_intervention_content()
    logger.info("База данных инициализирована")
    logger.info("Бот запущен и готов к работе")
    daily_log_sender = DailyLogSender(
        bot, daily_log_repo, participant_repo, morning_tip_repo, baseline_repo, batch_sender
    )

    intervention_content_sender = InterventionContentSender(
        bot=bot,
        content_repo=intervention_content_repo,
        participant_repo=participant_repo,
    )

    google_sheets_exporter = None
    if config.GOOGLE_SHEETS_SPREADSHEET_ID:
        try:
            google_sheets_exporter = GoogleSheetsExporter(
                credentials_path=config.GOOGLE_SHEETS_CREDENTIALS_PATH,
                spreadsheet_id=config.GOOGLE_SHEETS_SPREADSHEET_ID,
                database=database
            )
            logger.info("Google Sheets экспортер инициализирован")
        except Exception as e:
            logger.warning(f"Не удалось инициализировать Google Sheets экспортер: {e}")

    scheduler_service = SchedulerService(
        bot=bot,
        config=config,
        session_manager=session_manager,
        follow_up_repo=follow_up_repo,
        weekly_check_in_repo=weekly_checkin_repo,
        final_repo=final_survey_repo,
        daily_log_sender=daily_log_sender,
        google_sheets_exporter=google_sheets_exporter
    )

    intervention_content_scheduler = InterventionContentScheduler(
        content_sender=intervention_content_sender
    )

    apscheduler = AsyncIOScheduler()
    apscheduler.add_job(
        scheduler_service.process_all_pending,
        'interval',
        seconds=config.SURVEY_CHECK_INTERVAL
    )
    apscheduler.add_job(
        scheduler_service.process_daily_logs,
        'interval',
        seconds=config.DAILY_LOG_CHECK_INTERVAL
    )
    apscheduler.add_job(
        intervention_content_scheduler.run_all,
        'interval',
        seconds=config.INTERVENTION_CONTENT_INTERVAL
    )
    if google_sheets_exporter:
        apscheduler.add_job(
            scheduler_service.export_to_google_sheets,
            'interval',
            seconds=config.GOOGLE_SHEETS_EXPORT_INTERVAL
        )
        logger.info(
            f"Планировщик экспорта в Google Sheets запущен (интервал: {config.GOOGLE_SHEETS_EXPORT_INTERVAL} сек)"
        )

    apscheduler.start()
    logger.info(f"Планировщик контента запущен (интервал: {config.INTERVENTION_CONTENT_INTERVAL} сек)")
    logger.info("Бот запущен и готов к работе")
    logger.info("Для остановки нажмите Ctrl+C")

    try:
        await bot.subscribe_webhook(url=config.WEBHOOK_URL, secret=config.WEBHOOK_SECRET)

        await dp.handle_webhook(
            bot=bot,
            host=config.WEBHOOK_HOST,
            port=config.WEBHOOK_PORT,
            secret=config.WEBHOOK_SECRET,
            path='/webhook',
        )

    except KeyboardInterrupt:
        logger.info("Получен сигнал завершения")
    finally:
        apscheduler.shutdown()
        await bot.close_session()


if __name__ == "__main__":
    asyncio.run(main())
