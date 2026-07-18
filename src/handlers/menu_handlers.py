from maxapi.enums import ParseMode
from maxapi.types import CallbackButton, MessageCreated, MessageCallback
from maxapi.types.attachments import AttachmentButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from src.config import Config
from src.payloads import SosPayload, IdPayload, HelpPayload
from src.services import ParticipantService


class MenuHandlers:
    def __init__(self, participant_service: ParticipantService, config: Config):
        self._participant_service = participant_service
        self._config = config

    async def _get_main_keyboard(self, max_id: int) -> AttachmentButton:
        builder = InlineKeyboardBuilder()

        if not await self._participant_service.exists(max_id):
            return builder.as_markup()

        group = await self._participant_service.get_group(max_id)
        if group == 'B':
            builder.row(CallbackButton(text="🆘 SOS - Экстренная помощь", payload=SosPayload().pack()))
        builder.row(CallbackButton(text="ℹ️ Мой код участника", payload=IdPayload().pack()))
        builder.row(CallbackButton(text="ℹ️ Помощь", payload=HelpPayload().pack()))
        return builder.as_markup()

    async def handle_main_menu(self, event: MessageCreated | MessageCallback):
        max_id = event.from_user.user_id
        keyboard = await self._get_main_keyboard(max_id)
        if await self._participant_service.exists(max_id):
            await event.message.answer(
                "**Меню**",
                parse_mode=ParseMode.MARKDOWN,
                attachments=[keyboard]
            )
            return
        await event.message.answer(
            "👋 Добро пожаловать!\n\n"
            "Для участия в исследовании нажмите /start"
        )

    async def handle_help_menu(self, event: MessageCallback | MessageCreated):
        max_id = event.from_user.user_id
        user_group = await self._participant_service.get_group(max_id)
        keyboard = await self._get_main_keyboard(max_id)
        contact_info = f"\nВ случае проблем с ботом, вопросами или желанием выйти из исследования обращайтесь к {self._config.PRINCIPAL_INVESTIGATOR_NAME}"
        if self._config.PRINCIPAL_INVESTIGATOR_CONTACT:
            contact_info += f": {self._config.PRINCIPAL_INVESTIGATOR_CONTACT}"

        sos_line = "• /sos - техники при тяге к курению\n" if user_group == 'B' else ""

        await event.message.answer(
            "ℹ️ **Помощь**\n\n"
            "Этот бот создан для исследования TELEGRAM-MI по поддержке отказа от курения "
            "после перенесенного инфаркта миокарда.\n\n"
            "Доступные команды:\n"
            f"{sos_line}"
            "• /id - получить ваш код участника\n"
            f"{contact_info}",
            format=ParseMode.MARKDOWN,
            attachments=[keyboard]
        )

    async def handle_id_menu(self, event: MessageCallback | MessageCreated):
        max_id = event.from_user.user_id
        if not await self._participant_service.exists(max_id):
            await event.message.answer(
                "❌ Вы не зарегистрированы в исследовании.\n\n"
                "Нажмите /start для регистрации.",
                format=ParseMode.MARKDOWN,
                attachments=[InlineKeyboardBuilder().as_markup()]
            )
            return
        participant = await self._participant_service.get_by_max_id(max_id)
        keyboard = await self._get_main_keyboard(max_id)

        await event.message.answer(
            f"🆔 **Ваш код участника:** `{participant.participant_code}`\n\n"
            f"Вы можете использовать этот код для идентификации в исследовании.",
            format=ParseMode.MARKDOWN,
            attachments=[keyboard]
        )
