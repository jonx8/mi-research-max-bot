import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from src.services import FinalSurveyService
from src.services import SessionManager

logger = logging.getLogger(__name__)


class FinalSurveyHandlers:
    """
    Handlers for final survey questionnaire.

    Manages the complete final survey flow including:
    - 30-day abstinence question
    - 7-day abstinence question
    - Cigarettes per day input
    - Quit attempt tracking
    - Days to first lapse calculation
    """

    def __init__(self, final_survey_service: FinalSurveyService, session_manager: SessionManager) -> None:
        """
        Initialize final survey handlers.

        Args:
            final_survey_service: Service for managing final survey data
            session_manager: Manager for user session state
        """
        self._final_survey_service = final_survey_service
        self._session_manager = session_manager

    async def handle_final_survey_start(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Step 1: Process 30-day abstinence answer.

        Expected callback data format: "final_{id}_ppa30_{yes/no}"

        Args:
            update: Telegram update object
            _: Context object (unused)
        """
        query = update.callback_query
        await query.answer()
        data = query.data  # "final_{id}_ppa30_{yes/no}"

        parts = data.split('_')
        survey_id = int(parts[1])
        answer = parts[3]  # 'yes' or 'no'

        logger.info(
            f"Пользователь начал финальный опрос (survey_id={survey_id}): 30-дневная абстиненция='{answer}'"
        )

        survey = await self._final_survey_service.get_by_id(survey_id)
        if not survey or survey.completed_at:
            logger.warning(
                f"Пользователь попытался ответить на завершённый или несуществующий финальный опрос (survey_id={survey_id})"
            )
            await query.edit_message_text("Опрос уже завершён или не найден.")
            return

        ppa30 = (answer == 'yes')
        await self._session_manager.create_or_update_final_survey_session(
            telegram_id=update.effective_user.id,
            survey_id=survey_id,
            ppa_30d=ppa30
        )

        logger.info(
            f"Пользователь сохранил 30-дневную абстиненцию для опроса (survey_id={survey_id}): {ppa30}"
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да", callback_data=f"final_{survey_id}_ppa7_yes")],
            [InlineKeyboardButton("❌ Нет", callback_data=f"final_{survey_id}_ppa7_no")]
        ])

        await query.edit_message_text(
            "Курили ли Вы хотя бы одну сигарету за последние 7 дней?",
            reply_markup=keyboard
        )

    async def handle_final_ppa7(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Step 2: Process 7-day abstinence answer.

        Expected callback data format: "final_{id}_ppa7_{yes/no}"

        Args:
            update: Telegram update object
            _: Context object (unused)
        """
        query = update.callback_query
        await query.answer()
        data = query.data  # "final_{id}_ppa7_{yes/no}"

        parts = data.split('_')
        survey_id = int(parts[1])
        answer = parts[3]

        logger.info(
            f"Пользователь отвечает на вопрос о 7-дневной абстиненции для опроса (survey_id={survey_id}): ответ='{answer}'"
        )

        session = await self._session_manager.get_final_survey_session_by_id(survey_id)
        if not session:
            logger.error(
                f"Сессия финального опроса не найдена (survey_id={survey_id}) для пользователя"
            )
            await query.edit_message_text("Ошибка сессии. Попробуйте снова.")
            return

        survey = await self._final_survey_service.get_by_id(survey_id)
        if not survey or survey.completed_at:
            logger.error(
                f"Пользователь попытался ответить на завершённый финальный опрос (survey_id={survey_id})"
            )
            await query.edit_message_text("Опрос уже завершён.")
            return

        ppa7 = (answer == 'yes')
        await self._session_manager.update_final_survey_session(
            survey_id=survey_id,
            ppa_7d=ppa7
        )

        logger.info(
            f"Пользователь указал 7-дневную абстиненцию для опроса (survey_id={survey_id}): {ppa7}"
        )

        if ppa7:
            await query.edit_message_text(
                "📝 Сколько сигарет в день в среднем выкуриваете сейчас? (введите число)"
            )
            return

        await self._ask_quit_attempt(query, survey_id)

    async def handle_final_cigs_input(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """
        Step 3a: Process cigarette count input from user (if still smoking).

        Args:
            update: Telegram update object with message text
            _: Context object (unused)
        """
        user_id = update.effective_user.id
        user_input = update.message.text.strip()

        logger.info(
            f"Пользователь вводит количество сигарет для финального опроса: '{user_input}'"
        )

        session = await self._session_manager.get_final_survey_session_by_telegram_id(user_id)
        if not session:
            logger.error(
                f"Сессия финального опроса не найдена для пользователя {user_id}"
            )
            await update.message.reply_text("Ошибка сессии. Попробуйте снова.")
            return

        try:
            cigs = int(user_input)
        except ValueError:
            logger.warning(
                f"Пользователь ввёл некорректное количество сигарет для опроса (survey_id={session.survey_id}): '{user_input}'"
            )
            await update.message.reply_text("⚠️ Введите целое число.")
            return

        if not (0 <= cigs <= 100):
            logger.warning(
                f"Пользователь ввёл недопустимое количество сигарет для опроса (survey_id={session.survey_id}): {cigs}"
            )
            await update.message.reply_text("⚠️ Введите число от 0 до 100.")
            return

        await self._session_manager.update_final_survey_session(
            session.survey_id,
            cigs_per_day=cigs
        )

        logger.info(
            f"Пользователь указал количество сигарет в день ({cigs}) для опроса (survey_id={session.survey_id})"
        )

        await self._ask_quit_attempt(update, session.survey_id)

    async def _ask_quit_attempt(self, destination, survey_id: int):
        """
        Ask user about quit attempts in last 6 months.

        Args:
            destination: Telegram update or callback query object
            survey_id: ID of the final survey
        """
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да", callback_data=f"final_{survey_id}_quit_yes")],
            [InlineKeyboardButton("❌ Нет", callback_data=f"final_{survey_id}_quit_no")]
        ])

        text = "Были ли у вас попытки бросить курить за последние 6 месяцев?"

        logger.info(
            f"Пользователь переходит к вопросу о попытках бросить для опроса (survey_id={survey_id})"
        )

        if hasattr(destination, 'edit_message_text'):
            await destination.edit_message_text(text, reply_markup=keyboard)
        else:
            await destination.message.reply_text(text, reply_markup=keyboard)

    async def handle_final_quit_attempt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Step 4: Process quit attempt answer.

        Expected callback data format: "final_{id}_quit_{yes/no}"

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        query = update.callback_query
        await query.answer()
        data = query.data  # "final_{id}_quit_{yes/no}"

        parts = data.split('_')
        survey_id = int(parts[1])
        answer = parts[3]

        logger.info(
            f"Пользователь отвечает на вопрос о попытках бросить для опроса (survey_id={survey_id}): ответ='{answer}'"
        )

        session = await self._session_manager.get_final_survey_session_by_id(survey_id)
        if not session:
            logger.error(
                f"Сессия финального опроса не найдена (survey_id={survey_id}) для пользователя"
            )
            await query.edit_message_text("Ошибка сессии.")
            return

        quit_attempt = (answer == 'yes')
        await self._session_manager.update_final_survey_session(
            survey_id=survey_id,
            quit_attempt_made=quit_attempt
        )

        logger.info(
            f"Пользователь сообщил о попытке бросить курить для опроса (survey_id={survey_id}): {quit_attempt}"
        )

        if quit_attempt:
            await query.edit_message_text(
                "Через сколько дней после начала исследования произошёл первый срыв? (введите число дней)"
            )
            return

        await self._complete_final_survey(query, context, survey_id)

    async def handle_final_days_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Step 5: Process days to first lapse input.

        Args:
            update: Telegram update object with message text
            context: Telegram context object
        """
        user_id = update.effective_user.id
        user_input = update.message.text.strip()

        logger.info(
            f"Пользователь вводит количество дней до первого срыва: '{user_input}'"
        )

        session = await self._session_manager.get_final_survey_session_by_telegram_id(user_id)
        if not session:
            logger.error(
                f"Сессия финального опроса не найдена для пользователя {user_id}"
            )
            await update.message.reply_text("Ошибка сессии.")
            return

        try:
            days = int(user_input)
        except ValueError:
            logger.warning(
                f"Пользователь ввёл некорректное количество дней для опроса (survey_id={session.survey_id}): '{user_input}'"
            )
            await update.message.reply_text("⚠️ Введите целое число дней.")
            return

        if days < 0 or days > 180:
            logger.warning(
                f"Пользователь ввёл некорректное количество дней для опроса (survey_id={session.survey_id}): '{user_input}'")

            await update.message.reply_text("⚠️ Количество дней должно быть от 0 до 180.")
            return

        await self._session_manager.update_final_survey_session(
            survey_id=session.survey_id,
            days_to_first_lapse=days
        )

        logger.info(
            f"Пользователь указал количество дней до первого срыва ({days}) для опроса (survey_id={session.survey_id})"
        )

        await self._complete_final_survey(update, context, session.survey_id)

    async def _complete_final_survey(self, destination, _: ContextTypes.DEFAULT_TYPE, survey_id: int):
        """
        Complete final survey and save all collected data.

        Args:
            destination: Telegram update or callback query object
            _: Context object (unused)
            survey_id: ID of the final survey
        """
        session = await self._session_manager.get_final_survey_session_by_id(survey_id)
        survey = await self._final_survey_service.get_by_id(survey_id)

        if not survey or survey.completed_at:
            logger.warning(
                f"Попытка завершить уже завершённый опрос (survey_id={survey_id}) для пользователя"
            )
            if hasattr(destination, 'edit_message_text'):
                await destination.edit_message_text("Опрос уже завершён.")
            else:
                await destination.message.reply_text("Опрос уже завершён.")
            return

        await self._final_survey_service.complete(
            survey=survey,
            ppa_30d=session.ppa_30d,
            ppa_7d=session.ppa_7d,
            cigs_per_day=session.cigs_per_day,
            quit_attempt_made=session.quit_attempt_made,
            days_to_first_lapse=session.days_to_first_lapse
        )

        await self._session_manager.delete_final_survey_session(session.survey_id)

        text = "✅ Спасибо! Финальный опрос завершён. Спасибо за участие в исследовании!\n" \
               f"📋 **Заполните форму обратной связи:**\n" \
               f"https://forms.yandex.ru/u/69ea4864068ff035aa33ec68"

        if hasattr(destination, 'edit_message_text'):
            await destination.edit_message_text(text, parse_mode='Markdown')
        else:
            await destination.message.reply_text(text, parse_mode='Markdown')

        logger.info(f"Финальный опрос (survey_id={survey.id}) успешно завершён")
