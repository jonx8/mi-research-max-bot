import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from telegram.ext import ContextTypes

from src.exceptions import ValidationError
from src.services import ParticipantService
from src.services import RegistrationOrchestrator, QuestionData
from src.services import RegistrationStep

logger = logging.getLogger(__name__)

CLINIC_CENTERS = {
    "clinic_center_ulyanovsk": "ГУЗ Ульяновская областная больница",
}


class RegistrationHandlers:
    """
    Handlers for user registration flow.

    Manages the complete registration process including:
    - Consent agreement
    - Demographic data collection (age, gender)
    - Smoking history (years, cigarettes per day)
    - Quit attempts and vape usage
    - Household smoking status
    - Medical help history
    - Fagerstrom and Prochaska questionnaires
    """

    def __init__(
            self,
            orchestrator: RegistrationOrchestrator,
            participant_service: ParticipantService,
    ):
        """
        Initialize registration handlers.

        Args:
            orchestrator: Orchestrator managing registration state machine
            participant_service: Service for participant data management
        """
        self._orchestrator = orchestrator
        self._participant_service = participant_service
        self._text_step_handlers = {
            RegistrationStep.AGE: self.handle_age,
            RegistrationStep.SMOKING_YEARS: self.handle_smoking_years,
            RegistrationStep.CIGS_PER_DAY: self.handle_cigs_per_day,
        }

    @staticmethod
    async def _delete_user_message(
            update: Update,
            _: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Delete user's message to keep chat clean.

        Args:
            update: Telegram update object
            _: Context object (unused)
        """
        try:
            await update.message.delete()
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение пользователя {update.effective_user.id}: {e}")

    async def _edit_last_bot_message(
            self,
            telegram_id: int,
            context: ContextTypes.DEFAULT_TYPE,
            text: str,
            reply_markup: InlineKeyboardMarkup | None = None,
            parse_mode: str | None = None
    ) -> None:
        """
        Edit the last bot message for the specified user.

        Args:
            telegram_id: User's Telegram ID
            context: Telegram context object
            text: New message text
            reply_markup: Optional inline keyboard markup
            parse_mode: Optional parse mode for message formatting
        """
        last_msg_id = await self._orchestrator.get_last_bot_message_id(telegram_id)
        if not last_msg_id:
            logger.error(f"ID последнего сообщения бота не найден для пользователя {telegram_id}")
            return

        try:
            await context.bot.edit_message_text(
                chat_id=telegram_id,
                message_id=last_msg_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        except Exception as e:
            logger.warning(f"Не удалось отредактировать сообщение {last_msg_id} для пользователя: {e}")
            msg = await context.bot.send_message(
                chat_id=telegram_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            await self._orchestrator.set_last_bot_message_id(telegram_id, msg.message_id)

    async def handle_text_for_step(
            self,
            update: Update,
            context: ContextTypes.DEFAULT_TYPE,
            step: RegistrationStep
    ) -> None:
        """
        Handle text input for the specified registration step.

        Routes text input to the appropriate handler for the current step.

        Args:
            update: Telegram update object
            context: Telegram context object
            step: Current registration step
        """
        handler = self._text_step_handlers.get(step)

        if handler:
            await handler(update, context)  # type: ignore
            return

        await update.message.reply_text(
            "📝 Пожалуйста, используйте кнопки для ответа.",
            parse_mode='Markdown'
        )

    async def start(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Handle /start command.

        Shows welcome message and checks if user is already registered.

        Args:
            update: Telegram update object
            _: Context object (unused)
        """
        telegram_id = update.effective_user.id
        logger.info(f"Команда /start от пользователя")

        if await self._participant_service.exists(telegram_id):
            participant = await self._participant_service.get_by_telegram_id(telegram_id)
            keyboard = await self._participant_service.get_main_keyboard(telegram_id)
            logger.info(
                f"Пользователь уже зарегистрирован (participant_code={participant.participant_code})"
            )
            await update.message.reply_text(
                f"✅ Вы уже зарегистрированы!\n"
                f"Код: `{participant.participant_code}`\n",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            return

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ ДА, СОГЛАСЕН", callback_data="consent_yes")],
            [InlineKeyboardButton("❌ НЕТ, ОТКАЗЫВАЮСЬ", callback_data="consent_no")]
        ])

        logger.info(f"Пользователь не зарегистрирован, показано согласие на участие")

        await update.message.reply_text(
            "🎯 **ДОБРО ПОЖАЛОВАТЬ В ИССЛЕДОВАНИЕ TELEGRAM-MI!**\n\n"
            "Это исследование помощи в отказе от курения после перенесенного инфаркта миокарда.\n\n"
            "**УСЛОВИЯ УЧАСТИЯ:**\n"
            "• Исследование длится 6 месяцев\n"
            "• Ваши данные полностью анонимны\n"
            "• Вы можете выйти из исследования в любой момент\n\n"
            "Вы согласны участвовать в исследовании?",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def handle_consent(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Handle user consent response.

        Args:
            update: Telegram update object with callback query
            _: Context object (unused)
        """
        query = update.callback_query
        user_id = query.from_user.id
        await query.answer()

        if query.data == "consent_yes":
            logger.info(f"Пользователь дал согласие на участие в исследовании")
            await self._orchestrator.start_registration(user_id)

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Назад", callback_data="back_registration_consent")]
            ])
            msg = await query.edit_message_text(
                "Отлично! Давайте начнем регистрацию.\n\n"
                "📝 **Введите ваш возраст:**\n"
                "(число от 18 до 120 лет)",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            await self._orchestrator.set_last_bot_message_id(user_id, msg.message_id)
        else:
            logger.info(f"Пользователь отказался от участия в исследовании")
            await query.edit_message_text(
                "Спасибо за ваше время! ❤️\nЕсли передумаете - просто напишите /start"
            )

    async def handle_age(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle age input from user.

        Args:
            update: Telegram update object with message text
            context: Telegram context object
        """
        telegram_id = update.effective_user.id
        user_input = update.message.text

        logger.info(f"Пользователь вводит возраст: '{user_input}'")

        try:
            age = int(user_input)
        except ValueError:
            logger.warning(f"Некорректный ввод возраста от пользователя: '{user_input}'")
            await self._edit_last_bot_message(
                telegram_id,
                context,
                "📝 **Введите ваш возраст:**\n"
                "(число от 18 до 120 лет)\n\n"
                "⚠️ **Ошибка:** пожалуйста, введите число (например: 35)",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="back_registration_consent")]
                ]),
                parse_mode='Markdown'
            )
            await self._delete_user_message(update, context)
            return

        try:
            await self._orchestrator.set_age(telegram_id, age)
        except ValidationError as e:
            logger.warning(f"Ошибка валидации возраста для пользователя: {e}")
            await self._edit_last_bot_message(
                telegram_id,
                context,
                "📝 **Введите ваш возраст:**\n"
                "(число от 18 до 120 лет)\n\n"
                f"{e}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="back_registration_consent")]
                ]),
                parse_mode='Markdown'
            )
            await self._delete_user_message(update, context)
            return

        await self._delete_user_message(update, context)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👨 Мужской", callback_data="gender_male")],
            [InlineKeyboardButton("👩 Женский", callback_data="gender_female")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_registration_age")]
        ])

        await self._edit_last_bot_message(
            telegram_id,
            context,
            "👤 **Выберите ваш пол:**",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def handle_gender(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Handle gender selection from user.

        Args:
            update: Telegram update object with callback query
            _: Context object (unused)
        """
        query = update.callback_query
        telegram_id = query.from_user.id
        await query.answer()

        try:
            await self._orchestrator.set_gender(telegram_id, query.data)
        except ValidationError as e:
            logger.warning(f"Ошибка валидации пола для пользователя: {e}")
            await query.edit_message_text(str(e))
            return

        keyboard_buttons = [[InlineKeyboardButton(name, callback_data=cb_data)] for cb_data, name in
                            CLINIC_CENTERS.items()]
        keyboard_buttons.append([InlineKeyboardButton("◀️ Назад", callback_data="back_registration_gender")])
        keyboard = InlineKeyboardMarkup(keyboard_buttons)

        msg = await query.edit_message_text(
            "🏥 **В каком клиническом центре вы находитесь?**",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

        await self._orchestrator.set_last_bot_message_id(telegram_id, msg.message_id)

    async def handle_clinic_center(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Handle clinic center selection from user.

        Args:
            update: Telegram update object with callback query
            _: Context object (unused)
        """
        query = update.callback_query
        telegram_id = query.from_user.id
        await query.answer()

        try:
            await self._orchestrator.set_clinic_center(telegram_id, CLINIC_CENTERS[query.data])
        except (KeyError, ValidationError) as e:
            logger.warning(f"Ошибка валидации клинического центра для пользователя: {e}")
            await query.edit_message_text("Некорректное значение клинического центра")
            return

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад", callback_data="back_registration_clinic_center")]
        ])

        msg = await query.edit_message_text(
            "🚬 **Расскажите о вашем опыте курения**\n\n"
            "📝 **Сколько лет вы курите?**\n"
            "(введите целое число лет)",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

        await self._orchestrator.set_last_bot_message_id(telegram_id, msg.message_id)

    async def handle_smoking_years(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle smoking years input from user.

        Args:
            update: Telegram update object with message text
            context: Telegram context object
        """
        telegram_id = update.effective_user.id
        user_input = update.message.text

        logger.info(f"Пользователь вводит стаж курения: '{user_input}' лет")

        try:
            years = int(user_input)
        except ValueError:
            logger.warning(f"Некорректный ввод стажа курения от пользователя: '{user_input}'")
            await self._edit_last_bot_message(
                telegram_id,
                context,
                "🚬 **Расскажите о вашем опыте курения**\n\n"
                "📝 **Сколько лет вы курите?**\n"
                "(введите целое число лет)\n\n"
                "⚠️ **Ошибка:** пожалуйста, введите число",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="back_registration_clinic_center")],
                ]),
                parse_mode='Markdown'
            )
            await self._delete_user_message(update, context)
            return

        try:
            await self._orchestrator.set_smoking_years(telegram_id, years)
        except ValidationError as e:
            logger.warning(f"Ошибка валидации стажа курения для пользователя: {e}")
            await self._edit_last_bot_message(
                telegram_id,
                context,
                "🚬 **Расскажите о вашем опыте курения**\n\n"
                "📝 **Сколько лет вы курите?**\n"
                "(введите целое число лет)\n\n"
                f"{e}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="back_registration_clinic_center")],
                ]),
                parse_mode='Markdown'
            )
            await self._delete_user_message(update, context)
            return

        await self._delete_user_message(update, context)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад", callback_data="back_registration_smoking_years")]
        ])
        await self._edit_last_bot_message(
            telegram_id,
            context,
            "📝 **Сколько сигарет в среднем вы выкуриваете в день?**\n"
            "(введите целое число от 0 до 100)",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def handle_cigs_per_day(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle cigarettes per day input from user.

        Args:
            update: Telegram update object with message text
            context: Telegram context object
        """
        telegram_id = update.effective_user.id
        user_input = update.message.text

        logger.info(f"Пользователь вводит количество сигарет в день: '{user_input}'")

        try:
            cigs = int(user_input)
        except ValueError:
            logger.warning(f"Некорректный ввод количества сигарет от пользователя: '{user_input}'")
            await self._edit_last_bot_message(
                telegram_id,
                context,
                "📝 **Сколько сигарет в среднем вы выкуриваете в день?**\n"
                "(введите целое число от 0 до 100)\n\n"
                "⚠️ **Ошибка:** пожалуйста, введите число",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="back_registration_smoking_years")],
                ]),
                parse_mode='Markdown'
            )
            await self._delete_user_message(update, context)
            return

        try:
            await self._orchestrator.set_cigs_per_day(telegram_id, cigs)
        except ValidationError as e:
            logger.warning(f"Ошибка валидации количества сигарет для пользователя: {e}")
            await self._edit_last_bot_message(
                telegram_id,
                context,
                "📝 **Сколько сигарет в среднем вы выкуриваете в день?**\n"
                "(введите целое число от 0 до 100)\n\n"
                f"{e}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="back_registration_smoking_years")],
                ]),
                parse_mode='Markdown'
            )
            await self._delete_user_message(update, context)
            return

        await self._delete_user_message(update, context)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да", callback_data="quit_attempts_yes")],
            [InlineKeyboardButton("❌ Нет", callback_data="quit_attempts_no")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_registration_cigs_per_day")]
        ])
        await self._edit_last_bot_message(
            telegram_id,
            context,
            "📝 **Были ли у вас попытки бросить курить ранее?**",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def handle_quit_attempts(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Handle quit attempts answer.

        Args:
            update: Telegram update object with callback query
            _: Context object (unused)
        """
        query = update.callback_query
        await query.answer()

        has_attempts = query.data == "quit_attempts_yes"
        await self._orchestrator.set_quit_attempts(query.from_user.id, has_attempts)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да", callback_data="vape_yes")],
            [InlineKeyboardButton("❌ Нет", callback_data="vape_no")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_registration_quit_attempts")]
        ])
        await query.edit_message_text(
            "📝 **Используете ли вы электронные сигареты/вейп?**",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def handle_vape_usage(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Handle vape usage answer.

        Args:
            update: Telegram update object with callback query
            _: Context object (unused)
        """
        query = update.callback_query
        await query.answer()

        uses_vape = query.data == "vape_yes"
        await self._orchestrator.set_uses_vape(query.from_user.id, uses_vape)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да", callback_data="smoker_household_yes")],
            [InlineKeyboardButton("❌ Нет", callback_data="smoker_household_no")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_registration_vape_usage")]
        ])
        await query.edit_message_text(
            "📝 **Курит ли кто-то ещё у вас дома/в семье?**",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def handle_smoker_household(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Handle household smoker answer.

        Args:
            update: Telegram update object with callback query
            _: Context object (unused)
        """
        query = update.callback_query
        await query.answer()

        has_smoker = query.data == "smoker_household_yes"
        await self._orchestrator.set_smoker_in_household(query.from_user.id, has_smoker)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да", callback_data="medical_help_yes")],
            [InlineKeyboardButton("❌ Нет", callback_data="medical_help_no")],
            [InlineKeyboardButton("🤔 Не помню", callback_data="medical_help_not_sure")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_registration_smoker_household")]
        ])
        await query.edit_message_text(
            "📝 **Получали ли вы ранее лекарственную помощь или консультацию врача для отказа от курения?**",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def handle_medical_help(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Handle medical help answer.

        Args:
            update: Telegram update object with callback query
            _: Context object (unused)
        """
        query = update.callback_query
        await query.answer()

        mapping = {
            "medical_help_yes": "Да",
            "medical_help_no": "Нет",
            "medical_help_not_sure": "Не помню"
        }
        answer = mapping.get(query.data, "Не помню")
        await self._orchestrator.set_prior_medical_help(query.from_user.id, answer)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ НАЧАТЬ ОПРОС", callback_data="start_fagerstrom")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_registration_medical_help")]
        ])
        await query.edit_message_text(
            "📋 **Отлично! Теперь заполним опросник никотиновой зависимости (Фагерстрём)**\n\n"
            "Это поможет нам лучше понять ваши привычки курения.\n"
            "Опросник состоит из 6 вопросов.\n\n"
            "Готовы начать?",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def start_fagerstrom(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Start Fagerstrom questionnaire.

        Args:
            update: Telegram update object with callback query
            _: Context object (unused)
        """
        query = update.callback_query

        await self._orchestrator.start_questionnaire(query.from_user.id, 'fagerstrom')
        await self._send_current_question(query)

    async def start_prochaska(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Start Prochaska questionnaire.

        Args:
            update: Telegram update object with callback query
            _: Context object (unused)
        """
        query = update.callback_query

        await self._orchestrator.start_questionnaire(query.from_user.id, 'prochaska')
        await self._send_current_question(query)

    async def handle_back(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Handle back navigation.

        Args:
            update: Telegram update object with callback query
            _: Context object (unused)
        """
        query = update.callback_query
        telegram_id = query.from_user.id

        logger.info(f"Пользователь нажал кнопку 'Назад' с данными: {query.data}")

        # Handle registration step back navigation
        back_handlers = {
            "back_registration_consent": self._handle_back_to_consent,
            "back_registration_age": self._handle_back_to_age,
            "back_registration_gender": self._handle_back_to_gender,
            "back_registration_clinic_center": self._handle_back_to_clinic_center,
            "back_registration_smoking_years": self._handle_back_to_smoking_years,
            "back_registration_cigs_per_day": self._handle_back_to_cigs_per_day,
            "back_registration_quit_attempts": self._handle_back_to_quit_attempts,
            "back_registration_vape_usage": self._handle_back_to_vape_usage,
            "back_registration_smoker_household": self._handle_back_to_smoker_household,
            "back_registration_medical_help": self._handle_back_to_medical_help,
        }

        if query.data in back_handlers:
            await back_handlers[query.data](query, telegram_id)  # type:ignore
            return

        # Handle questionnaire back navigation
        try:
            await self._orchestrator.go_to_previous_question(telegram_id)
        except ValidationError as e:
            logger.warning(f"Ошибка при возврате к вопросу для пользователя {telegram_id}: {e}")
            await query.answer(str(e), show_alert=True)
            return

        await self._send_current_question(query)

    async def _handle_back_to_consent(self, query: CallbackQuery, telegram_id: int) -> None:
        """Handle back navigation to consent step."""
        await self._orchestrator.delete_registration_session(telegram_id)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ ДА, СОГЛАСЕН", callback_data="consent_yes")],
            [InlineKeyboardButton("❌ НЕТ, ОТКАЗЫВАЮСЬ", callback_data="consent_no")]
        ])
        await query.edit_message_text(
            "🎯 **ДОБРО ПОЖАЛОВАТЬ В ИССЛЕДОВАНИЕ TELEGRAM-MI!**\n\n"
            "Это исследование помощи в отказе от курения после перенесенного инфаркта миокарда.\n\n"
            "**УСЛОВИЯ УЧАСТИЯ:**\n"
            "• Исследование длится 6 месяцев\n"
            "• Ваши данные полностью анонимны\n"
            "• Вы можете выйти из исследования в любой момент\n\n"
            "Вы согласны участвовать в исследовании?",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def _handle_back_to_age(self, query: CallbackQuery, telegram_id: int) -> None:
        """Handle back navigation to age input step."""
        await self._orchestrator.go_back_to_step(telegram_id, RegistrationStep.AGE)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад", callback_data="back_registration_consent")]
        ])
        msg = await query.edit_message_text(
            "Отлично! Давайте начнем регистрацию.\n\n"
            "📝 **Введите ваш возраст:**\n"
            "(число от 18 до 120 лет)",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        await self._orchestrator.set_last_bot_message_id(telegram_id, msg.message_id)

    async def _handle_back_to_gender(self, query, telegram_id: int) -> None:
        """Handle back navigation to gender selection step."""
        await self._orchestrator.go_back_to_step(telegram_id, RegistrationStep.GENDER)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👨 Мужской", callback_data="gender_male")],
            [InlineKeyboardButton("👩 Женский", callback_data="gender_female")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_registration_age")]
        ])
        msg = await query.edit_message_text(
            "👤 **Выберите ваш пол:**",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        await self._orchestrator.set_last_bot_message_id(telegram_id, msg.message_id)

    async def _handle_back_to_clinic_center(self, query, telegram_id: int) -> None:
        """Handle back navigation to clinic center selection step."""
        await self._orchestrator.go_back_to_step(telegram_id, RegistrationStep.CLINIC_CENTER)

        keyboard_buttons = [[InlineKeyboardButton(name, callback_data=cb_data)] for cb_data, name in
                            CLINIC_CENTERS.items()]
        keyboard_buttons.append([InlineKeyboardButton("◀️ Назад", callback_data="back_registration_gender")])
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        msg = await query.edit_message_text(
            "🏥 **В каком клиническом центре вы находитесь?**",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        await self._orchestrator.set_last_bot_message_id(telegram_id, msg.message_id)

    async def _handle_back_to_smoking_years(self, query, telegram_id: int) -> None:
        """Handle back navigation to smoking years input step."""
        await self._orchestrator.go_back_to_step(telegram_id, RegistrationStep.SMOKING_YEARS)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад", callback_data="back_registration_clinic_center")]
        ])
        msg = await query.edit_message_text(
            "🚬 **Расскажите о вашем опыте курения**\n\n"
            "📝 **Сколько лет вы курите?**\n"
            "(введите целое число лет)",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        await self._orchestrator.set_last_bot_message_id(telegram_id, msg.message_id)

    async def _handle_back_to_cigs_per_day(self, query, telegram_id: int) -> None:
        """Handle back navigation to cigarettes per day input step."""
        await self._orchestrator.go_back_to_step(telegram_id, RegistrationStep.CIGS_PER_DAY)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад", callback_data="back_registration_smoking_years")]
        ])
        msg = await query.edit_message_text(
            "📝 **Сколько сигарет в среднем вы выкуриваете в день?**\n"
            "(введите целое число от 0 до 100)",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        await self._orchestrator.set_last_bot_message_id(telegram_id, msg.message_id)

    async def _handle_back_to_quit_attempts(self, query, telegram_id: int) -> None:
        """Handle back navigation to quit attempts question."""
        await self._orchestrator.go_back_to_step(telegram_id, RegistrationStep.QUIT_ATTEMPTS)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да", callback_data="quit_attempts_yes")],
            [InlineKeyboardButton("❌ Нет", callback_data="quit_attempts_no")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_registration_cigs_per_day")]
        ])
        msg = await query.edit_message_text(
            "📝 **Были ли у вас попытки бросить курить ранее?**",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        await self._orchestrator.set_last_bot_message_id(telegram_id, msg.message_id)

    async def _handle_back_to_vape_usage(self, query, telegram_id: int) -> None:
        """Handle back navigation to vape usage question."""
        await self._orchestrator.go_back_to_step(telegram_id, RegistrationStep.VAPE_USAGE)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да", callback_data="vape_yes")],
            [InlineKeyboardButton("❌ Нет", callback_data="vape_no")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_registration_quit_attempts")]
        ])
        msg = await query.edit_message_text(
            "📝 **Используете ли вы электронные сигареты/вейп?**",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        await self._orchestrator.set_last_bot_message_id(telegram_id, msg.message_id)

    async def _handle_back_to_smoker_household(self, query, telegram_id: int) -> None:
        """Handle back navigation to household smoker question."""
        await self._orchestrator.go_back_to_step(telegram_id, RegistrationStep.SMOKER_HOUSEHOLD)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да", callback_data="smoker_household_yes")],
            [InlineKeyboardButton("❌ Нет", callback_data="smoker_household_no")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_registration_vape_usage")]
        ])
        msg = await query.edit_message_text(
            "📝 **Курит ли кто-то ещё у вас дома/в семье?**",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        await self._orchestrator.set_last_bot_message_id(telegram_id, msg.message_id)

    async def _handle_back_to_medical_help(self, query, telegram_id: int) -> None:
        """Handle back navigation to medical help question."""
        await self._orchestrator.go_back_to_step(telegram_id, RegistrationStep.MEDICAL_HELP)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да", callback_data="medical_help_yes")],
            [InlineKeyboardButton("❌ Нет", callback_data="medical_help_no")],
            [InlineKeyboardButton("🤔 Не помню", callback_data="medical_help_not_sure")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_registration_smoker_household")]
        ])
        msg = await query.edit_message_text(
            "📝 **Получали ли вы ранее лекарственную помощь или консультацию врача для отказа от курения?**",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        await self._orchestrator.set_last_bot_message_id(telegram_id, msg.message_id)

    async def handle_answer(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle questionnaire answer from callback query.

        Args:
            update: Telegram update object with callback query
            _: Context object (unused)
        """
        query = update.callback_query
        telegram_id = query.from_user.id

        parts = query.data.split('_')
        q_type = parts[1]
        q_idx = int(parts[2])
        ans_idx = int(parts[3])

        await self._orchestrator.save_answer(telegram_id, q_type, q_idx, ans_idx)

        if await self._orchestrator.is_questionnaire_completed(telegram_id, q_type):
            if q_type == 'fagerstrom':
                await self._handle_fagerstrom_completion(query, telegram_id)
            elif q_type == 'prochaska':
                await self._handle_prochaska_completion(query, telegram_id)
        else:
            await self._send_current_question(query)

    async def _handle_fagerstrom_completion(self, query, telegram_id: int) -> None:
        """
        Handle Fagerstrom questionnaire completion.

        Args:
            query: Callback query object
            telegram_id: User's Telegram ID
        """
        await query.answer()
        result = await self._orchestrator.complete_fagerstrom(telegram_id)

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("➡️ ПРОДОЛЖИТЬ", callback_data="start_prochaska")
        ]])
        await query.edit_message_text(
            f"📊 **Результаты теста Фагерстрёма:**\n\n"
            f"• **Общий балл:** {result.score}/10\n"
            f"• **Уровень зависимости:** {result.level}\n\n"
            "Теперь заполним опросник мотивации...",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def _handle_prochaska_completion(self, query, telegram_id: int) -> None:
        """
        Handle Prochaska questionnaire completion and finalize registration.

        Args:
            query: Callback query object
            telegram_id: User's Telegram ID
        """
        await self._orchestrator.complete_prochaska(telegram_id)

        participant = await self._orchestrator.finalize_registration(telegram_id)
        keyboard = await self._participant_service.get_main_keyboard(telegram_id)

        await query.message.delete()
        await query.answer()

        sos_command_str = f"• 🆘 SOS - Экстренная помощь — техники по борьбе с тягой к курению\n" if participant.group_name == "B" else ""

        await query.message.reply_text(
            f"✅ **РЕГИСТРАЦИЯ ЗАВЕРШЕНА!**\n\n"
            f"🆔 **Ваш код участника:** `{participant.participant_code}`\n\n"
            f"💙 **Спасибо за участие в исследовании!**\n"
            f"**Доступные команды меню:**\n"
            f"{sos_command_str}"
            f"• ℹ️ Мой код участника — показать ваш код участника исследования\n"
            f"• ℹ️ Помощь — справка по боту",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

    async def _send_current_question(self, query) -> None:
        """
        Send current questionnaire question to user.

        Args:
            query: Callback query object
        """
        telegram_id = query.from_user.id
        q = await self._orchestrator.get_current_question(telegram_id)

        keyboard = self._build_question_keyboard(q)
        await query.answer()

        await query.edit_message_text(
            f"📝 **Вопрос {q.number} из {q.total}**\n\n{q.text}",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    @staticmethod
    def _build_question_keyboard(q: QuestionData) -> InlineKeyboardMarkup:
        """
        Build inline keyboard for questionnaire question.

        Args:
            q: Question data containing options and metadata

        Returns:
            InlineKeyboardMarkup with answer options and back button if allowed
        """
        keyboard = []
        for i, option in enumerate(q.options):
            callback = f"answer_{q.callback_prefix}_{q.number - 1}_{i}"
            keyboard.append([InlineKeyboardButton(option, callback_data=callback)])

        if q.can_go_back:
            keyboard.append([
                InlineKeyboardButton("◀️ Назад", callback_data=f"back_{q.callback_prefix}")
            ])

        return InlineKeyboardMarkup(keyboard)
