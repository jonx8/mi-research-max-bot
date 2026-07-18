import logging

from maxapi.enums import ParseMode
from maxapi.types import BotStarted
from maxapi.types.attachments.buttons.callback_button import CallbackButton
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from src.payloads import GenderPayload, BackPayload, ClinicCenterPayload, QuitAttemptsPayload, VapePayload, \
    SmokerHouseholdPayload, MedicalHelpPayload, StartQuestionnairePayload, AnswerPayload, ConsentPayload
from src.exceptions import ValidationError
from src.services import ParticipantService, RegistrationOrchestrator, RegistrationStep

logger = logging.getLogger(__name__)
CLINIC_CENTERS = {
    "ulyanovsk": "ГУЗ Ульяновская областная больница",
}

BACK_STEPS = {
    "age": (RegistrationStep.AGE, "Отлично! Давайте начнем регистрацию.\n\n📝 **Введите ваш возраст:**\n(число от 18 до 120 лет)", "consent"),
    "gender": (RegistrationStep.GENDER, "👤 **Выберите ваш пол:**", "age"),
    "clinic_center": (RegistrationStep.CLINIC_CENTER, "🏥 **В каком клиническом центре вы находитесь?**", "gender"),
    "smoking_years": (RegistrationStep.SMOKING_YEARS, "🚬 **Расскажите о вашем опыте курения**\n\n📝 **Сколько лет вы курите?**\n(введите целое число лет)", "clinic_center"),
    "cigs_per_day": (RegistrationStep.CIGS_PER_DAY, "📝 **Сколько сигарет в среднем вы выкуриваете в день?**\n(введите целое число от 0 до 100)", "smoking_years"),
    "quit_attempts": (RegistrationStep.QUIT_ATTEMPTS, "📝 **Были ли у вас попытки бросить курить ранее?**", "cigs_per_day"),
    "vape_usage": (RegistrationStep.VAPE_USAGE, "📝 **Используете ли вы электронные сигареты/вейп?**", "quit_attempts"),
    "smoker_household": (RegistrationStep.SMOKER_HOUSEHOLD, "📝 **Курит ли кто-то ещё у вас дома/в семье?**", "vape_usage"),
    "medical_help": (RegistrationStep.MEDICAL_HELP, "📝 **Получали ли вы ранее лекарственную помощь или консультацию врача для отказа от курения?**", "smoker_household"),
}

BACK_KEYBOARDS = {
    "age": lambda: _build_back_row("consent"),
    "gender": lambda: _build_gender_keyboard() + _build_back_row("age"),
    "clinic_center": lambda: _build_clinic_center_keyboard() + _build_back_row("gender"),
    "smoking_years": lambda: _build_back_row("clinic_center"),
    "cigs_per_day": lambda: _build_back_row("smoking_years"),
    "quit_attempts": lambda: _build_quit_attempts_keyboard() + _build_back_row("cigs_per_day"),
    "vape_usage": lambda: _build_vape_keyboard() + _build_back_row("quit_attempts"),
    "smoker_household": lambda: _build_smoker_household_keyboard() + _build_back_row("vape_usage"),
    "medical_help": lambda: _build_medical_help_keyboard() + _build_back_row("smoker_household"),
}


def _build_back_row(target: str) -> list:
    return [CallbackButton(text="◀️ Назад", payload=BackPayload(target=target).pack())]


def _build_gender_keyboard() -> list:
    return [
        CallbackButton(text="👨 Мужской", payload=GenderPayload(value="male").pack()),
        CallbackButton(text="👩 Женский", payload=GenderPayload(value="female").pack())
    ]


def _build_clinic_center_keyboard() -> list:
    return [CallbackButton(text=name, payload=ClinicCenterPayload(center=cb_data).pack()) for cb_data, name in CLINIC_CENTERS.items()]


def _build_quit_attempts_keyboard() -> list:
    return [
        CallbackButton(text="✅ Да", payload=QuitAttemptsPayload(value="yes").pack()),
        CallbackButton(text="❌ Нет", payload=QuitAttemptsPayload(value="no").pack())
    ]


def _build_vape_keyboard() -> list:
    return [
        CallbackButton(text="✅ Да", payload=VapePayload(value="yes").pack()),
        CallbackButton(text="❌ Нет", payload=VapePayload(value="no").pack())
    ]


def _build_smoker_household_keyboard() -> list:
    return [
        CallbackButton(text="✅ Да", payload=SmokerHouseholdPayload(value="yes").pack()),
        CallbackButton(text="❌ Нет", payload=SmokerHouseholdPayload(value="no").pack())
    ]


def _build_medical_help_keyboard() -> list:
    return [
        CallbackButton(text="✅ Да", payload=MedicalHelpPayload(value="yes").pack()),
        CallbackButton(text="❌ Нет", payload=MedicalHelpPayload(value="no").pack()),
        CallbackButton(text="🤔 Не помню", payload=MedicalHelpPayload(value="not_sure").pack())
    ]


def _make_keyboard(rows: list) -> list:
    builder = InlineKeyboardBuilder()
    for row in rows:
        if isinstance(row, list):
            builder.row(*row)
        else:
            builder.row(row)
    return [builder.as_markup()]


class RegistrationHandlers:
    def __init__(self, orchestrator: RegistrationOrchestrator, participant_service: ParticipantService):
        self._orchestrator = orchestrator
        self._participant_service = participant_service
        self._text_step_handlers = {
            RegistrationStep.AGE: self.handle_age,
            RegistrationStep.SMOKING_YEARS: self.handle_smoking_years,
            RegistrationStep.CIGS_PER_DAY: self.handle_cigs_per_day,
        }

    async def handle_start(self, event: MessageCreated | BotStarted):
        max_id = event.from_user.user_id
        if await self._participant_service.exists(max_id):
            participant = await self._participant_service.get_by_max_id(max_id)
            logger.info(f"Пользователь уже зарегистрирован (participant_code={participant.participant_code})")
            await event.send(f"✅ Вы уже зарегистрированы!\nКод: `{participant.participant_code}`\n", format=ParseMode.MARKDOWN)
            return

        logger.info(f"Пользователь не зарегистрирован, показано согласие на участие")
        await event.send(
            "🎯 **ДОБРО ПОЖАЛОВАТЬ В ИССЛЕДОВАНИЕ max-MI!**\n\n"
            "Это исследование помощи в отказе от курения после перенесенного инфаркта миокарда.\n\n"
            "**УСЛОВИЯ УЧАСТИЯ:**\n"
            "• Исследование длится 6 месяцев\n"
            "• Ваши данные полностью анонимны\n"
            "• Вы можете выйти из исследования в любой момент\n\n"
            "Вы согласны участвовать в исследовании?",
            format=ParseMode.MARKDOWN,
            attachments=_make_keyboard([
                CallbackButton(text="✅ ДА, СОГЛАСЕН", payload=ConsentPayload(choice="yes").pack()),
                CallbackButton(text="❌ НЕТ, ОТКАЗЫВАЮСЬ", payload=ConsentPayload(choice="no").pack())
            ])
        )

    async def handle_consent(self, event: MessageCallback, payload: ConsentPayload) -> None:
        user_id = event.callback.user.user_id
        if payload.choice == "yes":
            logger.info(f"Пользователь дал согласие на участие в исследовании")
            await self._orchestrator.start_registration(user_id)
            await event.edit(
                text="Отлично! Давайте начнем регистрацию.\n\n📝 **Введите ваш возраст:**\n(число от 18 до 120 лет)",
                format=ParseMode.MARKDOWN,
                attachments=_make_keyboard([_build_back_row("consent")])
            )
        else:
            logger.info(f"Пользователь отказался от участия в исследовании")
            await event.edit(text="Спасибо за ваше время! ❤️\nЕсли передумаете - просто напишите /start", attachments=[])

    async def handle_text_for_step(self, event: MessageCreated, step: RegistrationStep) -> None:
        handler = self._text_step_handlers.get(step)
        if handler:
            await handler(event)
            return
        await event.message.answer("📝 Пожалуйста, используйте кнопки для ответа.")

    @staticmethod
    async def _validate_int_input(event: MessageCreated, min_val: int, max_val: int, error_msg: str) -> int | None:
        user_input = event.message.body.text if event.message.body else ""
        logger.info(f"Пользователь вводит: '{user_input}'")
        try:
            value = int(user_input)
            if not (min_val <= value <= max_val):
                raise ValueError("out of range")
            return value
        except ValueError:
            logger.warning(f"Некорректный ввод от пользователя: '{user_input}'")
            await event.message.answer(error_msg, format=ParseMode.MARKDOWN)
            return None

    async def handle_age(self, event: MessageCreated) -> None:
        max_id = event.from_user.user_id
        age = await self._validate_int_input(event, 18, 120, "⚠️ **Ошибка:** пожалуйста, введите число (например: 35)\n\n📝 **Введите ваш возраст:**\n(число от 18 до 120 лет)")
        if age is None:
            return
        try:
            await self._orchestrator.set_age(max_id, age)
        except ValidationError as e:
            logger.warning(f"Ошибка валидации возраста: {e}")
            await event.message.answer(f"{e}\n\n📝 **Введите ваш возраст:**\n(число от 18 до 120 лет)", format=ParseMode.MARKDOWN)
            return
        await event.message.answer("👤 **Выберите ваш пол:**", format=ParseMode.MARKDOWN, attachments=_make_keyboard([_build_gender_keyboard(), _build_back_row("age")]))

    async def handle_gender_callback(self, event: MessageCallback, payload: GenderPayload) -> None:
        max_id = event.from_user.user_id
        try:
            await self._orchestrator.set_gender(max_id, payload.value)
        except ValidationError as e:
            logger.warning(f"Ошибка валидации пола: {e}")
            await event.edit(text=str(e))
            return
        await event.edit(text="🏥 **В каком клиническом центре вы находитесь?**", format=ParseMode.MARKDOWN, attachments=_make_keyboard([_build_clinic_center_keyboard(), _build_back_row("gender")]))

    async def handle_clinic_center_callback(self, event: MessageCallback, payload: ClinicCenterPayload) -> None:
        center_name = CLINIC_CENTERS.get(payload.center)
        if not center_name:
            await event.edit(text="Некорректное значение клинического центра")
            return
        max_id = event.from_user.user_id
        try:
            await self._orchestrator.set_clinic_center(max_id, center_name)
        except ValidationError as e:
            logger.warning(f"Ошибка валидации клинического центра: {e}")
            await event.edit(text="Некорректное значение клинического центра")
            return
        await event.edit(text="🚬 **Расскажите о вашем опыте курения**\n\n📝 **Сколько лет вы курите?**\n(введите целое число лет)", format=ParseMode.MARKDOWN, attachments=_make_keyboard([_build_back_row("clinic_center")]))

    async def handle_smoking_years(self, event: MessageCreated) -> None:
        max_id = event.from_user.user_id
        years = await self._validate_int_input(event, 0, 120, "⚠️ **Ошибка:** пожалуйста, введите число\n\n📝 **Сколько лет вы курите?**\n(введите целое число лет)")
        if years is None:
            return
        try:
            await self._orchestrator.set_smoking_years(max_id, years)
        except ValidationError as e:
            logger.warning(f"Ошибка валидации стажа курения: {e}")
            await event.message.answer(f"{e}\n\n📝 **Сколько лет вы курите?**\n(введите целое число лет)", format=ParseMode.MARKDOWN)
            return
        await event.message.answer("📝 **Сколько сигарет в среднем вы выкуриваете в день?**\n(введите целое число от 0 до 100)", format=ParseMode.MARKDOWN, attachments=_make_keyboard([_build_back_row("smoking_years")]))

    async def handle_cigs_per_day(self, event: MessageCreated) -> None:
        max_id = event.message.sender.user_id
        cigs = await self._validate_int_input(event, 0, 100, "⚠️ **Ошибка:** пожалуйста, введите число\n\n📝 **Сколько сигарет в среднем вы выкуриваете в день?**\n(введите целое число от 0 до 100)")
        if cigs is None:
            return
        try:
            await self._orchestrator.set_cigs_per_day(max_id, cigs)
        except ValidationError as e:
            logger.warning(f"Ошибка валидации количества сигарет: {e}")
            await event.message.answer(f"{e}\n\n📝 **Сколько сигарет в среднем вы выкуриваете в день?**\n(введите целое число от 0 до 100)", format=ParseMode.MARKDOWN)
            return
        await event.message.answer("📝 **Были ли у вас попытки бросить курить ранее?**", format=ParseMode.MARKDOWN, attachments=_make_keyboard([_build_quit_attempts_keyboard(), _build_back_row("cigs_per_day")]))

    async def handle_quit_attempts_callback(self, event: MessageCallback, payload: QuitAttemptsPayload) -> None:
        await self._orchestrator.set_quit_attempts(event.from_user.user_id, has_attempts=payload.value == "yes")
        await event.edit(text="📝 **Используете ли вы электронные сигареты/вейп?**", format=ParseMode.MARKDOWN, attachments=_make_keyboard([_build_vape_keyboard(), _build_back_row("quit_attempts")]))

    async def handle_vape_usage_callback(self, event: MessageCallback, payload: VapePayload) -> None:
        await self._orchestrator.set_uses_vape(event.from_user.user_id, payload.value == "yes")
        await event.edit(text="📝 **Курит ли кто-то ещё у вас дома/в семье?**", format=ParseMode.MARKDOWN, attachments=_make_keyboard([_build_smoker_household_keyboard(), _build_back_row("vape_usage")]))

    async def handle_smoker_household_callback(self, event: MessageCallback, payload: SmokerHouseholdPayload) -> None:
        await self._orchestrator.set_smoker_in_household(event.from_user.user_id, has_smoker=payload.value == "yes")
        await event.edit(text="📝 **Получали ли вы ранее лекарственную помощь или консультацию врача для отказа от курения?**", format=ParseMode.MARKDOWN, attachments=_make_keyboard([_build_medical_help_keyboard(), _build_back_row("smoker_household")]))

    async def handle_medical_help_callback(self, event: MessageCallback, payload: MedicalHelpPayload) -> None:
        mapping = {"yes": "Да", "no": "Нет", "not_sure": "Не помню"}
        medical_help = mapping.get(payload.value)
        if not medical_help:
            logger.error("Некорректное значение medical_help")
            return
        await self._orchestrator.set_prior_medical_help(event.from_user.user_id, medical_help)
        await event.edit(
            text="📋 **Отлично! Теперь заполним опросник никотиновой зависимости (Фагерстрём)**\n\nЭто поможет нам лучше понять ваши привычки курения.\nОпросник состоит из 6 вопросов.\n\nГотовы начать?",
            format=ParseMode.MARKDOWN,
            attachments=_make_keyboard([CallbackButton(text="✅ НАЧАТЬ ОПРОС", payload=StartQuestionnairePayload(q_type="fagerstrom").pack()), _build_back_row("medical_help")])
        )

    async def start_questionnaire_handler(self, event: MessageCallback, payload: StartQuestionnairePayload) -> None:
        await self._orchestrator.start_questionnaire(event.from_user.user_id, payload.q_type)
        await self._send_current_question(event.from_user.user_id, event)

    async def handle_back_callback(self, event: MessageCallback, payload: BackPayload) -> None:
        logger.info(f"Пользователь нажал кнопку 'Назад' с данными: {payload.target}")
        max_id = event.from_user.user_id

        if payload.target == "consent":
            await self._orchestrator.delete_registration_session(max_id)
            await event.edit(
                text="🎯 **ДОБРО ПОЖАЛОВАТЬ В ИССЛЕДОВАНИЕ max-MI!**\n\n"
                     "Это исследование помощи в отказе от курения после перенесенного инфаркта миокарда.\n\n"
                     "**УСЛОВИЯ УЧАСТИЯ:**\n"
                     "• Исследование длится 6 месяцев\n"
                     "• Ваши данные полностью анонимны\n"
                     "• Вы можете выйти из исследования в любой момент\n\n"
                     "Вы согласны участвовать в исследовании?",
                attachments=_make_keyboard([
                    CallbackButton(text="✅ ДА, СОГЛАСЕН", payload=ConsentPayload(choice="yes").pack()),
                    CallbackButton(text="❌ НЕТ, ОТКАЗЫВАЮСЬ", payload=ConsentPayload(choice="no").pack())
                ])
            )
            return

        if payload.target in ("fagerstrom", "prochaska"):
            try:
                await self._orchestrator.go_to_previous_question(max_id)
            except ValidationError as e:
                logger.warning(f"Ошибка при возврате к вопросу: {e}")
                return
            await self._send_current_question(max_id, event)
            return

        if payload.target in BACK_STEPS:
            step, text, back_target = BACK_STEPS[payload.target]
            await self._orchestrator.go_back_to_step(max_id, step)
            keyboard_rows = BACK_KEYBOARDS[payload.target]()
            await event.edit(text=text, format=ParseMode.MARKDOWN, attachments=_make_keyboard(keyboard_rows))

    async def handle_answer_callback(self, event: MessageCallback, payload: AnswerPayload) -> None:
        max_id = event.from_user.user_id
        await self._orchestrator.save_answer(max_id, payload.q_type, payload.q_idx, payload.ans_idx)

        if await self._orchestrator.is_questionnaire_completed(max_id, payload.q_type):
            if payload.q_type == "fagerstrom":
                result = await self._orchestrator.complete_fagerstrom(max_id)
                await event.edit(
                    text=f"📊 **Результаты теста Фагерстрёма:**\n\n• **Общий балл:** {result.score}/10\n• **Уровень зависимости:** {result.level}\n\nТеперь заполним опросник мотивации...",
                    format=ParseMode.MARKDOWN,
                    attachments=_make_keyboard([CallbackButton(text="➡️ ПРОДОЛЖИТЬ", payload=StartQuestionnairePayload(q_type="prochaska").pack())])
                )
            elif payload.q_type == "prochaska":
                await self._orchestrator.complete_prochaska(max_id)
                participant = await self._orchestrator.finalize_registration(max_id)
                sos_str = f"• /sos — техники по борьбе с тягой к курению\n" if participant.group_name == "B" else ""
                await event.message.edit(
                    text=f"✅ **РЕГИСТРАЦИЯ ЗАВЕРШЕНА!**\n\n🆔 **Ваш код участника:** `{participant.participant_code}`\n\n💙 **Спасибо за участие в исследовании!**\n**Доступные команды меню:**\n{sos_str}• /id — показать ваш код участника исследования\n• /help — справка по боту",
                    format=ParseMode.MARKDOWN,
                    attachments=[

                    ]
                )
        else:
            await self._send_current_question(max_id, event)

    async def _send_current_question(self, max_id: int, event: MessageCallback) -> None:
        q = await self._orchestrator.get_current_question(max_id)
        builder = InlineKeyboardBuilder()
        for i, option in enumerate(q.options):
            builder.row(CallbackButton(text=option, payload=AnswerPayload(q_type=q.callback_prefix, q_idx=q.number - 1, ans_idx=i).pack()))
        if q.can_go_back:
            builder.row(CallbackButton(text="◀️ Назад", payload=BackPayload(target=q.callback_prefix).pack()))
        await event.edit(text=f"📝 **Вопрос {q.number} из {q.total}**\n\n{q.text}", format=ParseMode.MARKDOWN, attachments=[builder.as_markup()])