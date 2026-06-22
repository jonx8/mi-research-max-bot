import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

from scripts.seed_intervention_content import seed_intervention_content
from scripts.seed_techniques import seed_techniques
from scripts.seed_tips import seed_morning_tips
from src.config import Config, setup_logging
from src.database import Database
from src.handlers import RegistrationHandlers, SOSModuleHandlers, FollowUpSurveyHandlers, WeeklyCheckInHandlers, \
    FinalSurveyHandlers, DailyLogHandlers, global_error_handler
from src.repositories import ParticipantRepository, BaselineQuestionnaireRepository, FollowUpRepository, \
    WeeklyCheckInRepository, DailyLogRepository, FinalSurveyRepository, MorningTipRepository, \
    InterventionContentRepository, TechniqueRepository, SOSUsageRepository, CravingAnalysisRepository, SessionRepository
from src.schedulers import SchedulerService, InterventionContentScheduler
from src.services import ParticipantService, BaselineQuestionnaireService, FollowUpService, WeeklyCheckInService, \
    FinalSurveyService, TechniqueService, DailyLogService, SOSUsageService, CravingAnalysisService, SessionManager, \
    RegistrationOrchestrator, CravingAnalysisOrchestrator, RegistrationStep, DailyLogSender, InterventionContentSender, \
    GoogleSheetsExporter
from src.utils import init_encryption, BatchSender

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


async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await participant_service.exists(user_id):
        await update.message.reply_text(
            "❌ Вы не зарегистрированы в исследовании.\n\n"
            "Нажмите /start для регистрации.",
            parse_mode='Markdown'
        )
        return

    participant = await participant_service.get_by_telegram_id(user_id)
    keyboard = await participant_service.get_main_keyboard(user_id)
    await update.message.reply_text(
        f"🆔 **Ваш код участника:** `{participant.participant_code}`\n\n"
        f"Вы можете использовать этот код для идентификации в исследовании.",
        parse_mode='Markdown',
        reply_markup=keyboard
    )


async def sos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await participant_service.exists(user_id):
        await update.message.reply_text(
            "❌ Вы не зарегистрированы в исследовании.\n\n"
            "Нажмите /start для регистрации.",
            parse_mode='Markdown'
        )
        return

    user_group = await participant_service.get_group(user_id)
    if user_group == 'A':
        keyboard = await participant_service.get_main_keyboard(user_id)
        await update.message.reply_text(
            "ℹ️ **Вам назначен базовый тип поддержки**\n\n"
            "Вы будете получать периодические опросы о вашем статусе курения.\n\n"
            "Спасибо за участие в исследовании!",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        return
    await sos_module_handlers.show_sos_menu(update, context)


async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if not await participant_service.exists(user_id):
        await update.message.reply_text(
            "❌ Вы не зарегистрированы в исследовании.\n\n"
            "Нажмите /start для регистрации."
        )
        return

    user_group = await participant_service.get_group(user_id)

    if text == "🆘 SOS - Экстренная помощь":
        if user_group == 'B':
            await sos_module_handlers.show_sos_menu(update, context)
        else:
            keyboard = await participant_service.get_main_keyboard(user_id)
            await update.message.reply_text(
                "ℹ️ **Вам назначен базовый тип поддержки**\n\n"
                "Вы будете получать периодические опросы о вашем статусе курения.\n\n"
                "Спасибо за участие в исследовании!",
                reply_markup=keyboard
            )
    elif text == "ℹ️ Мой код участника":
        participant = await participant_service.get_by_telegram_id(user_id)
        keyboard = await participant_service.get_main_keyboard(user_id)
        await update.message.reply_text(
            f"🆔 **Ваш код участника:** `{participant.participant_code}`\n\n"
            f"Вы можете использовать этот код для идентификации в исследовании.",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    elif text == "ℹ️ Помощь":
        user_group = await participant_service.get_group(user_id)
        keyboard = await participant_service.get_main_keyboard(user_id)
        contact_info = ""
        if config.PRINCIPAL_INVESTIGATOR_CONTACT:
            contact_info = f"\nВ случае проблем с ботом, вопросами или желанием выйти из исследования обращайтесь к {config.PRINCIPAL_INVESTIGATOR_NAME}: {config.PRINCIPAL_INVESTIGATOR_CONTACT}"
        else:
            contact_info = f"\nВ случае проблем с ботом, вопросами или желанием выйти из исследования обращайтесь к {config.PRINCIPAL_INVESTIGATOR_NAME}"

        sos_line = "• /sos - техники при тяге к курению\n" if user_group == 'B' else ""

        await update.message.reply_text(
            "ℹ️ **Помощь**\n\n"
            "Этот бот создан для исследования TELEGRAM-MI по поддержке отказа от курения "
            "после перенесенного инфаркта миокарда.\n\n"
            "Доступные команды:\n"
            f"{sos_line}"
            "• /id - получить ваш код участника\n"
            f"{contact_info}",
            parse_mode='Markdown',
            reply_markup=keyboard
        )


async def handle_all_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Единая точка входа для всех текстовых сообщений."""
    telegram_id = update.effective_user.id

    if await craving_analysis_orchestrator.is_analysis_active(telegram_id):
        await sos_module_handlers.handle_analysis_answer(update, context)
        return

    registration_session = await session_manager.get_registration_session_by_telegram_id(telegram_id)
    if registration_session and registration_session.step:
        await registration_handlers.handle_text_for_step(update, context, RegistrationStep(registration_session.step))
        return

    final_session = await session_manager.get_final_survey_session_by_telegram_id(telegram_id)
    if final_session:
        if final_session.cigs_per_day is None and final_session.ppa_7d:
            await final_survey_handlers.handle_final_cigs_input(update, context)
        elif final_session.days_to_first_lapse is None and final_session.quit_attempt_made:
            await final_survey_handlers.handle_final_days_input(update, context)
        return

    follow_up_session = await session_manager.get_follow_up_session_by_telegram_id(telegram_id)
    if follow_up_session:
        await follow_up_handlers.handle_follow_up_cigs_input(update, context)
        return

    if await participant_service.exists(telegram_id):
        keyboard = await participant_service.get_main_keyboard(telegram_id)
        await update.message.reply_text(
            "🤖 Используйте кнопки ниже для навигации:",
            reply_markup=keyboard
        )
        return

    await update.message.reply_text(
        "👋 Добро пожаловать!\n\n"
        "Для участия в исследовании нажмите /start",
        parse_mode='Markdown'
    )


async def post_init(application: Application):
    """Инициализация после запуска бота"""
    await seed_techniques()
    await seed_morning_tips()
    await seed_intervention_content()
    logger.info("База данных инициализирована")


def main():
    logger.info("Запуск бота...")
    logger.info(f"Токен бота: {'установлен' if config.BOT_TOKEN else 'отсутствует'}")

    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN не найден в файле .env")
        return

    app = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Глобальный обработчик ошибок
    app.add_error_handler(global_error_handler)

    # Регистрация
    app.add_handler(CommandHandler("start", registration_handlers.start))
    app.add_handler(CallbackQueryHandler(registration_handlers.handle_consent, pattern="^(consent_yes|consent_no)$"))
    app.add_handler(CallbackQueryHandler(registration_handlers.handle_gender, pattern="^(gender_male|gender_female)$"))
    app.add_handler(CallbackQueryHandler(registration_handlers.handle_clinic_center, pattern="^clinic_center_"))
    app.add_handler(CallbackQueryHandler(registration_handlers.handle_quit_attempts, pattern="^quit_attempts_"))
    app.add_handler(CallbackQueryHandler(registration_handlers.handle_vape_usage, pattern="^vape_"))
    app.add_handler(CallbackQueryHandler(registration_handlers.handle_smoker_household, pattern="^smoker_household_"))
    app.add_handler(CallbackQueryHandler(registration_handlers.handle_medical_help, pattern="^medical_help_"))
    app.add_handler(CallbackQueryHandler(registration_handlers.start_fagerstrom, pattern="^start_fagerstrom$"))
    app.add_handler(CallbackQueryHandler(registration_handlers.start_prochaska, pattern="^start_prochaska$"))
    app.add_handler(CallbackQueryHandler(registration_handlers.handle_back,
                                         pattern="^back_(fagerstrom|prochaska|registration_(consent|age|gender|clinic_center|smoking_years|cigs_per_day|quit_attempts|vape_usage|smoker_household|medical_help))$"))
    app.add_handler(CallbackQueryHandler(registration_handlers.handle_answer, pattern="^answer_"))

    # SOS-модуль
    app.add_handler(CommandHandler("sos", sos_command))
    app.add_handler(CallbackQueryHandler(sos_module_handlers.handle_technique, pattern="^sos_technique_"))
    app.add_handler(CallbackQueryHandler(sos_module_handlers.handle_new_techniques, pattern="^sos_new_techniques$"))
    app.add_handler(CallbackQueryHandler(sos_module_handlers.handle_helped, pattern="^sos_helped$"))
    app.add_handler(CallbackQueryHandler(sos_module_handlers.start_analysis, pattern="^analyze_craving$"))
    app.add_handler(CallbackQueryHandler(sos_module_handlers.begin_analysis, pattern="^begin_craving_analysis$"))

    # Главное меню
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex('^(🆘 SOS - Экстренная помощь|ℹ️ Мой код участника|ℹ️ Помощь)$'),
        handle_main_menu))

    # Команда /id
    app.add_handler(CommandHandler("id", id_command))

    # Ежедневный опрос
    app.add_handler(CallbackQueryHandler(daily_log_handlers.handle_evening_response, pattern="^daily_"))

    # Промежуточные опросы
    app.add_handler(CallbackQueryHandler(follow_up_handlers.handle_follow_up_answer, pattern="^followup_"))

    # Еженедельные чек-ины
    app.add_handler(CallbackQueryHandler(weekly_checkin_handlers.handle_weekly_status, pattern="^weekly_.*_status_"))
    app.add_handler(
        CallbackQueryHandler(weekly_checkin_handlers.handle_weekly_craving_input, pattern="^weekly_.*_craving_"))
    app.add_handler(CallbackQueryHandler(weekly_checkin_handlers.handle_weekly_mood, pattern="^weekly_.*_mood_"))

    # Финальный опрос
    app.add_handler(CallbackQueryHandler(final_survey_handlers.handle_final_survey_start, pattern="^final_.*_ppa30_"))
    app.add_handler(CallbackQueryHandler(final_survey_handlers.handle_final_ppa7, pattern="^final_.*_ppa7_"))
    app.add_handler(CallbackQueryHandler(final_survey_handlers.handle_final_quit_attempt, pattern="^final_.*_quit_"))

    # Текстовые сообщения
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_text_messages))

    daily_log_sender = DailyLogSender(app.bot, daily_log_repo, participant_repo, morning_tip_repo, baseline_repo,
                                      batch_sender)

    intervention_content_sender = InterventionContentSender(
        bot=app.bot,
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

    scheduler = SchedulerService(
        bot=app.bot,
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

    scheduled_survey_check = lambda context: scheduler.process_all_pending()
    scheduled_daily_log_check = lambda context: scheduler.process_daily_logs()
    scheduled_intervention_content = lambda context: intervention_content_scheduler.run_all()
    scheduled_google_sheets_export = lambda context: scheduler.export_to_google_sheets()

    job_queue = app.job_queue
    job_queue.run_repeating(scheduled_survey_check, interval=config.SURVEY_CHECK_INTERVAL, first=5)
    job_queue.run_repeating(scheduled_daily_log_check, interval=config.DAILY_LOG_CHECK_INTERVAL, first=5)
    job_queue.run_repeating(scheduled_intervention_content, interval=config.INTERVENTION_CONTENT_INTERVAL, first=10)
    if google_sheets_exporter:
        job_queue.run_repeating(
            scheduled_google_sheets_export,
            interval=config.GOOGLE_SHEETS_EXPORT_INTERVAL,
            first=10
        )
        logger.info(
            f"Планировщик экспорта в Google Sheets запущен (интервал: {config.GOOGLE_SHEETS_EXPORT_INTERVAL} сек)")

    logger.info(f"Планировщик контента запущен (интервал: {config.INTERVENTION_CONTENT_INTERVAL} сек)")
    logger.info("Бот запущен и готов к работе")
    logger.info("Для остановки нажмите Ctrl+C")

    app.run_polling()


if __name__ == '__main__':
    main()