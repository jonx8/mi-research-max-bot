import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from src.exceptions import ValidationError
from src.services import CravingAnalysisOrchestrator
from src.services import ParticipantService
from src.services import SOSUsageService
from src.services import TechniqueService

logger = logging.getLogger(__name__)


class SOSModuleHandlers:
    """
    Handlers for SOS (emergency help) module for craving management.

    Provides techniques to help users cope with smoking cravings,
    tracks technique usage, and offers craving analysis functionality.
    """

    def __init__(
            self,
            techniques_service: TechniqueService,
            participant_service: ParticipantService,
            craving_analysis_orchestrator: CravingAnalysisOrchestrator,
            sos_usage_service: SOSUsageService,
    ):
        """
        Initialize SOS module handlers.

        Args:
            techniques_service: Service for managing coping techniques
            participant_service: Service for participant data management
            craving_analysis_orchestrator: Orchestrator for craving analysis flow
            sos_usage_service: Service for tracking SOS feature usage
        """
        self._participant_service = participant_service
        self._techniques_service = techniques_service
        self._sos_usage_service = sos_usage_service
        self._analysis_orchestrator = craving_analysis_orchestrator

    async def show_sos_menu(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Display SOS menu with available techniques.

        Args:
            update: Telegram update object
            _: Telegram context object (unused)
        """
        techniques = await self._techniques_service.get_sos_techniques(4)

        logger.info(
            f"Пользователь открыл SOS меню, показано {len(techniques)} техник"
        )
        keyboard = []
        for technique in techniques:
            keyboard.append([
                InlineKeyboardButton(technique.name, callback_data=f"sos_technique_{technique.id}")
            ])
        keyboard.append([
            InlineKeyboardButton("📝 Проанализировать тягу", callback_data="analyze_craving")
        ])

        message_text = (
            "🆘 **ЭКСТРЕННАЯ ПОМОЩЬ ПРИ ТЯГЕ К КУРЕНИЮ**\n\n"
            "Тяга обычно длится 5-15 минут. Выберите технику для преодоления:\n\n"
            "💡 *Совет: Попробуйте технику, которую еще не использовали!*"
        )

        if update.message:
            await update.message.reply_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            query = update.callback_query
            await query.edit_message_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

    async def handle_technique(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Display selected coping technique.

        Args:
            update: Telegram update object with callback query
            _: Telegram context object (unused)
        """
        query = update.callback_query
        telegram_id = query.from_user.id
        await query.answer()

        technique_id = "_".join(query.data.split('_')[2:])
        technique = await self._techniques_service.get_technique_by_id(technique_id)
        participant = await self._participant_service.get_by_telegram_id(telegram_id)

        # Track technique usage
        await self._sos_usage_service.create(participant.participant_code, technique_id)

        logger.info(
            f"Пользователь (participant_code={participant.participant_code}) "
            f"использовал технику (technique_id={technique_id}): {technique.name}"
        )

        message = (
            f"🆘 **{technique.name}**\n\n"
            f"{technique.description}\n\n"
            f"💪 {self._techniques_service.get_craving_message()}\n\n"
            f"*Попробуйте эту технику прямо сейчас!*"
        )
        keyboard = [
            [InlineKeyboardButton("🔄 Другая техника", callback_data="sos_new_techniques")],
            [InlineKeyboardButton("✅ Помогло!", callback_data="sos_helped")],
            [InlineKeyboardButton("📝 Затрудняюсь", callback_data="analyze_craving")]
        ]
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def handle_new_techniques(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Show alternative techniques.

        Args:
            update: Telegram update object with callback query
            _: Telegram context object (unused)
        """
        query = update.callback_query
        await query.answer()

        techniques = await self._techniques_service.get_sos_techniques(4)

        logger.info(
            f"Пользователь запросил другие техники, показано {len(techniques)} новых техник"
        )

        keyboard = []
        for technique in techniques:
            keyboard.append([
                InlineKeyboardButton(technique.name, callback_data=f"sos_technique_{technique.id}")
            ])
        keyboard.append([
            InlineKeyboardButton("📝 Проанализировать тягу", callback_data="analyze_craving")
        ])

        await query.edit_message_text(
            "🆘 **Выберите другую технику:**\n\n"
            "Иногда помогает попробовать что-то новое!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    @staticmethod
    async def handle_helped(update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Handle user confirmation that technique helped.

        Args:
            update: Telegram update object with callback query
            _: Telegram context object (unused)
        """
        query = update.callback_query
        await query.answer()

        logger.info(f"Пользователь подтвердил, что техника помогла справиться с тягой")

        await query.edit_message_text(
            "🎉 **Отлично! Вы справились с тягой!**\n\n"
            "Каждая такая победа делает вас сильнее и приближает к цели.\n\n"
            "💪 *Помните: вы способны контролировать свои привычки!*",
            parse_mode='Markdown'
        )

    async def start_analysis(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Start craving analysis flow.

        Args:
            update: Telegram update object with callback query
            _: Telegram context object (unused)
        """
        query = update.callback_query
        await query.answer()
        telegram_id = query.from_user.id

        await self._analysis_orchestrator.start_analysis(telegram_id)

        await query.edit_message_text(
            "📝 **Давайте проанализируем вашу тягу**\n\n"
            "Это поможет лучше понимать свои триггеры и эффективнее с ними бороться.\n\n"
            "Я задам вам несколько вопросов. Отвечайте текстом.\n\n"
            "Готовы?",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ НАЧАТЬ", callback_data="begin_craving_analysis")
            ]]),
            parse_mode='Markdown'
        )

    async def begin_analysis(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Begin asking analysis questions.

        Args:
            update: Telegram update object with callback query
            _: Telegram context object (unused)
        """
        query = update.callback_query
        await query.answer()
        telegram_id = query.from_user.id

        await self._send_current_question(query, telegram_id, is_callback=True)

    async def handle_analysis_answer(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Process text answer during craving analysis.

        Args:
            update: Telegram update object with message text
            _: Telegram context object (unused)
        """
        telegram_id = update.effective_user.id
        answer = update.message.text.strip()

        logger.info(f"Пользователь отвечает на вопрос анализа тяги: '{answer[:50]}...'")

        try:
            await self._analysis_orchestrator.save_answer(telegram_id, answer)
        except ValidationError as e:
            logger.warning(f"Ошибка валидации ответа для пользователя {telegram_id}: {e}")
            await update.message.reply_text(str(e))
            return

        if await self._analysis_orchestrator.is_completed(telegram_id):
            await self._complete_analysis(update)
        else:
            await self._send_current_question(update, telegram_id, is_callback=False)

    async def _send_current_question(self, update_or_query, telegram_id: int, is_callback: bool = True):
        """
        Send current craving analysis question.

        Args:
            update_or_query: Telegram update or callback query object
            telegram_id: User's Telegram ID
            is_callback: Whether the source is a callback query
        """
        question = await self._analysis_orchestrator.get_current_question(telegram_id)

        message_text = (
            f"📝 **Вопрос {question.number} из {question.total}**\n\n{question.text}\n\n"
            "Напишите ваш ответ текстом:"
        )

        if is_callback:
            await update_or_query.edit_message_text(message_text, parse_mode='Markdown')
        else:
            await update_or_query.message.reply_text(message_text, parse_mode='Markdown')

    async def _complete_analysis(self, update: Update):
        """
        Complete craving analysis.

        Args:
            update: Telegram update object
        """
        telegram_id = update.effective_user.id
        await self._analysis_orchestrator.finish_analysis(telegram_id)

        await update.message.reply_text(
            "📊 **Анализ завершён!**\n\n"
            "Теперь вы лучше понимаете свои триггеры. Используйте эти знания:\n\n"
            "• **Избегайте** ситуаций, провоцирующих тягу\n"
            "• **Подготовьте** техники для сложных моментов\n"
            "• **Гордитесь** тем, что анализируете свои привычки\n\n"
            "💪 *Осознанность — ключ к успешному отказу от курения!*",
            parse_mode='Markdown'
        )
