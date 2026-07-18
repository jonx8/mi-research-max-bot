import logging

from maxapi.enums import ParseMode
from maxapi.types.attachments import AttachmentButton
from maxapi.types.attachments.buttons.callback_button import CallbackButton
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from src.payloads import NewTechniquesPayload, HelpedPayload, AnalyzeCravingPayload, BeginAnalysisPayload, \
    TechniquePayload
from src.exceptions import ValidationError
from src.services import CravingAnalysisOrchestrator, ParticipantService, SOSUsageService, TechniqueService

logger = logging.getLogger(__name__)


class SOSModuleHandlers:
    def __init__(
            self,
            techniques_service: TechniqueService,
            participant_service: ParticipantService,
            craving_analysis_orchestrator: CravingAnalysisOrchestrator,
            sos_usage_service: SOSUsageService,
    ):
        self._participant_service = participant_service
        self._techniques_service = techniques_service
        self._sos_usage_service = sos_usage_service
        self._analysis_orchestrator = craving_analysis_orchestrator

    async def show_sos_menu(self, event: MessageCreated | MessageCallback) -> None:
        keyboard = await self._get_techniques_keyboard()
        await event.message.answer(
            "🆘 **ЭКСТРЕННАЯ ПОМОЩЬ ПРИ ТЯГЕ К КУРЕНИЮ**\n\n"
            "Тяга обычно длится 5-15 минут. Выберите технику для преодоления:\n\n"
            "💡 *Совет: Попробуйте технику, которую еще не использовали!*",
            format=ParseMode.MARKDOWN,
            attachments=[keyboard]
        )

    async def handle_technique_callback(self, max_id: int, technique_id: str, event: MessageCallback) -> None:
        technique = await self._techniques_service.get_technique_by_id(technique_id)
        participant = await self._participant_service.get_by_max_id(max_id)
        await self._sos_usage_service.create(participant.participant_code, technique_id)

        logger.info(
            f"Пользователь (participant_code={participant.participant_code}) "
            f"использовал технику (technique_id={technique_id}): {technique.name}"
        )

        builder = InlineKeyboardBuilder()
        builder.row(CallbackButton(text="🔄 Другая техника", payload=NewTechniquesPayload().pack()))
        builder.row(CallbackButton(text="✅ Помогло!", payload=HelpedPayload().pack()))
        builder.row(CallbackButton(text="📝 Затрудняюсь", payload=AnalyzeCravingPayload().pack()))

        await event.edit(
            text=f"🆘 **{technique.name}**\n\n"
                 f"{technique.description}\n\n"
                 f"💪 {self._techniques_service.get_craving_message()}\n\n"
                 f"*Попробуйте эту технику прямо сейчас!*",
            format=ParseMode.MARKDOWN,
            attachments=[builder.as_markup()]
        )

    async def handle_new_techniques_callback(self, event: MessageCallback) -> None:
        keyboard = await self._get_techniques_keyboard()

        await event.edit(
            text="🆘 **Выберите другую технику:**\n\nИногда помогает попробовать что-то новое!",
            format=ParseMode.MARKDOWN,
            attachments=[keyboard]
        )

    async def _get_techniques_keyboard(self) -> AttachmentButton:
        techniques = await self._techniques_service.get_sos_techniques(4)
        logger.info(f"Пользователь запросил другие техники, показано {len(techniques)} новых техник")

        builder = InlineKeyboardBuilder()
        for technique in techniques:
            builder.row(CallbackButton(text=technique.name, payload=TechniquePayload(technique_id=technique.id).pack()))
        builder.row(CallbackButton(text="📝 Проанализировать тягу", payload=AnalyzeCravingPayload().pack()))
        return builder.as_markup()

    async def handle_helped_callback(self, event: MessageCallback) -> None:
        logger.info(f"Пользователь подтвердил, что техника помогла справиться с тягой")
        await event.edit(
            text="🎉 **Отлично! Вы справились с тягой!**\n\n"
                 "Каждая такая победа делает вас сильнее и приближает к цели.\n\n"
                 "💪 *Помните: вы способны контролировать свои привычки!*",
            format=ParseMode.MARKDOWN,
            attachments=[]
        )

    async def start_analysis_callback(self, event: MessageCallback) -> None:
        telegram_id = event.callback.user.user_id
        await self._analysis_orchestrator.start_analysis(telegram_id)

        builder = InlineKeyboardBuilder()
        builder.row(CallbackButton(text="✅ НАЧАТЬ", payload=BeginAnalysisPayload().pack()))

        await event.edit(
            text="📝 **Давайте проанализируем вашу тягу**\n\n"
                 "Это поможет лучше понимать свои триггеры и эффективнее с ними бороться.\n\n"
                 "Я задам вам несколько вопросов. Отвечайте текстом.\n\n"
                 "Готовы?",
            format=ParseMode.MARKDOWN,
            attachments=[builder.as_markup()]
        )

    async def begin_analysis_callback(self, event: MessageCallback) -> None:
        telegram_id = event.callback.user.user_id
        await self._send_current_question(telegram_id, event)

    async def handle_analysis_answer_from_message(self, event: MessageCreated) -> None:
        max_id = event.from_user.user_id
        answer = event.message.body.text.strip() if event.message.body else ""

        logger.info(f"Пользователь отвечает на вопрос анализа тяги: '{answer[:50]}...'")

        try:
            await self._analysis_orchestrator.save_answer(max_id, answer)
        except ValidationError as e:
            logger.warning(f"Ошибка валидации ответа для пользователя {max_id}: {e}")
            await event.message.answer(str(e))
            return

        if await self._analysis_orchestrator.is_completed(max_id):
            await self._complete_analysis(event)
        else:
            await self._send_current_question(max_id, event)

    async def _send_current_question(self, telegram_id: int, event_or_msg) -> None:
        question = await self._analysis_orchestrator.get_current_question(telegram_id)
        message_text = (
            f"📝 **Вопрос {question.number} из {question.total}**\n\n{question.text}\n\n"
            "Напишите ваш ответ текстом:"
        )

        if isinstance(event_or_msg, MessageCreated):
            await event_or_msg.message.answer(message_text, format=ParseMode.MARKDOWN, attachments=[])
        else:
            await event_or_msg.edit(text=message_text, format=ParseMode.MARKDOWN, attachments=[])

    async def _complete_analysis(self, event: MessageCreated) -> None:
        max_id = event.from_user.user_id
        await self._analysis_orchestrator.finish_analysis(max_id)

        await event.message.answer(
            "📊 **Анализ завершён!**\n\n"
            "Теперь вы лучше понимаете свои триггеры. Используйте эти знания:\n\n"
            "• **Избегайте** ситуаций, провоцирующих тягу\n"
            "• **Подготовьте** техники для сложных моментов\n"
            "• **Гордитесь** тем, что анализируете свои привычки\n\n"
            "💪 *Осознанность — ключ к успешному отказу от курения!*",
            format=ParseMode.MARKDOWN,
        )
