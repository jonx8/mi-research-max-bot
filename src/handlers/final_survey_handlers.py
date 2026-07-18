import logging

from maxapi.enums import ParseMode
from maxapi.types import MessageCallback, CallbackButton, MessageCreated
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from src.payloads import FinalPPA30Payload, FinalPPA7Payload, FinalQuitAttemptsPayload
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

    async def handle_final_survey_start(self, event: MessageCallback, payload: FinalPPA30Payload):
        """Step 1: Process 30-day abstinence answer."""
        logger.info(
            f"Пользователь начал финальный опрос (survey_id={payload.survey_id}): 30-дневная абстиненция='{payload.answer}'"
        )

        survey = await self._final_survey_service.get_by_id(payload.survey_id)
        if not survey or survey.completed_at:
            logger.warning(
                f"Пользователь попытался ответить на завершённый или несуществующий финальный опрос (survey_id={payload.survey_id})"
            )
            await event.message.edit("Опрос уже завершён или не найден.", attachments=[])
            return

        ppa30 = (payload.answer == 'yes')
        await self._session_manager.create_or_update_final_survey_session(
            max_id=event.from_user.user_id,
            survey_id=payload.survey_id,
            ppa_30d=ppa30
        )

        logger.info(
            f"Пользователь сохранил 30-дневную абстиненцию для опроса (survey_id={payload.survey_id}): {ppa30}"
        )

        builder = InlineKeyboardBuilder()
        builder.row(CallbackButton(text="✅ Да", payload=FinalPPA7Payload(survey_id=survey.id, answer="yes").pack()))
        builder.row(CallbackButton(text="❌ Нет", payload=FinalPPA7Payload(survey_id=survey.id, answer="no").pack()))

        await event.message.edit(
            "Курили ли Вы хотя бы одну сигарету за последние 7 дней?",
            attachments=[builder.as_markup()],
            format=ParseMode.MARKDOWN
        )

    async def handle_final_ppa7(self, event: MessageCallback, payload: FinalPPA30Payload):
        """ Step 2: Process 7-day abstinence answer. """

        logger.info(
            f"Пользователь отвечает на вопрос о 7-дневной абстиненции для опроса (survey_id={payload.survey_id}): ответ='{payload.answer}'"
        )

        session = await self._session_manager.get_final_survey_session_by_id(payload.survey_id)
        if not session:
            logger.error(
                f"Сессия финального опроса не найдена (survey_id={payload.survey_id}) для пользователя"
            )
            await event.message.edit("Ошибка сессии. Попробуйте снова.", attachments=[])
            return

        survey = await self._final_survey_service.get_by_id(payload.survey_id)
        if not survey or survey.completed_at:
            logger.error(
                f"Пользователь попытался ответить на завершённый финальный опрос (survey_id={payload.survey_id})"
            )
            await event.message.edit("Опрос уже завершён.", attachments=[])
            return

        ppa7 = (payload.answer == 'yes')
        await self._session_manager.update_final_survey_session(
            survey_id=payload.survey_id,
            ppa_7d=ppa7
        )

        logger.info(
            f"Пользователь указал 7-дневную абстиненцию для опроса (survey_id={session.survey_id}): {ppa7}"
        )

        if ppa7:
            await event.message.edit(
                "📝 Сколько сигарет в день в среднем выкуриваете сейчас? (введите число)",
                attachments=[]
            )
            return

        await self._ask_quit_attempt(event, payload.survey_id)

    async def handle_final_cigs_input(self, event: MessageCreated):
        """ Step 3a: Process cigarette count input from user (if still smoking)."""
        user_input = event.message.body.text.strip()

        logger.info(
            f"Пользователь вводит количество сигарет для финального опроса: '{user_input}'"
        )

        max_id = event.from_user.user_id
        session = await self._session_manager.get_final_survey_session_by_max_id(max_id)
        if not session:
            logger.error(
                f"Сессия финального опроса не найдена для пользователя {max_id}"
            )
            await event.message.edit("Ошибка сессии. Попробуйте снова.", attachments=[])
            return

        try:
            cigs = int(user_input)
        except ValueError:
            logger.warning(
                f"Пользователь ввёл некорректное количество сигарет для опроса (survey_id={session.survey_id}): '{user_input}'"
            )
            await event.message.answer("⚠️ Введите целое число.")
            return

        if not (0 <= cigs <= 100):
            logger.warning(
                f"Пользователь ввёл недопустимое количество сигарет для опроса (survey_id={session.survey_id}): {cigs}"
            )
            await event.message.answer("⚠️ Введите число от 0 до 100.")
            return

        await self._session_manager.update_final_survey_session(
            session.survey_id,
            cigs_per_day=cigs
        )

        logger.info(
            f"Пользователь указал количество сигарет в день ({cigs}) для опроса (survey_id={session.survey_id})"
        )

        await self._ask_quit_attempt(event, session.survey_id)

    async def _ask_quit_attempt(self, event: MessageCallback | MessageCreated, survey_id: int):
        """ Ask user about quit attempts in last 6 months."""

        builder = InlineKeyboardBuilder()
        builder.row(
            CallbackButton(text="✅ Да", payload=FinalQuitAttemptsPayload(survey_id=survey_id, answer='yes').pack()))
        builder.row(
            CallbackButton(text="❌ Нет", payload=FinalQuitAttemptsPayload(survey_id=survey_id, answer='no').pack()))

        logger.info(
            f"Пользователь переходит к вопросу о попытках бросить для опроса (survey_id={survey_id})"
        )

        text = "Были ли у вас попытки бросить курить за последние 6 месяцев?"

        if isinstance(event, MessageCreated):
            await event.message.answer(text=text, attachments=[builder.as_markup()])
        else:
            await event.message.edit(text=text, attachments=[builder.as_markup()])

    async def handle_final_quit_attempt(self, event: MessageCallback, payload: FinalQuitAttemptsPayload):
        """Step 4: Process quit attempt answer."""
        logger.info(
            f"Пользователь отвечает на вопрос о попытках бросить для опроса (survey_id={payload.survey_id}): ответ='{payload.answer}'"
        )

        session = await self._session_manager.get_final_survey_session_by_id(payload.survey_id)
        if not session:
            logger.error(
                f"Сессия финального опроса не найдена (survey_id={payload.survey_id}) для пользователя"
            )
            await event.message.edit("Ошибка сессии.", attachments=[])
            return

        quit_attempt = (payload.answer == 'yes')
        await self._session_manager.update_final_survey_session(
            survey_id=payload.survey_id,
            quit_attempt_made=quit_attempt
        )

        logger.info(
            f"Пользователь сообщил о попытке бросить курить для опроса (survey_id={payload.survey_id}): {quit_attempt}"
        )

        if quit_attempt:
            await event.message.edit(
                "Через сколько дней после начала исследования произошёл первый срыв? (введите число дней)",
                attachments=[]
            )
            return

        await self._complete_final_survey(event, payload.survey_id)

    async def handle_final_days_input(self, event: MessageCreated):
        """Step 5: Process days to first lapse input."""
        max_id = event.from_user.user_id
        user_input = event.message.body.text.strip()

        logger.info(
            f"Пользователь вводит количество дней до первого срыва: '{user_input}'"
        )

        session = await self._session_manager.get_final_survey_session_by_max_id(max_id)
        if not session:
            logger.error(
                f"Сессия финального опроса не найдена для пользователя {max_id}"
            )
            await event.message.edit("Ошибка сессии.", attachments=[])
            return

        try:
            days = int(user_input)
        except ValueError:
            logger.warning(
                f"Пользователь ввёл некорректное количество дней для опроса (survey_id={session.survey_id}): '{user_input}'"
            )
            await event.message.answer("⚠️ Введите целое число дней.")
            return

        if days < 0 or days > 180:
            logger.warning(
                f"Пользователь ввёл некорректное количество дней для опроса (survey_id={session.survey_id}): '{user_input}'")

            await event.message.answer("⚠️ Количество дней должно быть от 0 до 180.")
            return

        await self._session_manager.update_final_survey_session(
            survey_id=session.survey_id,
            days_to_first_lapse=days
        )

        logger.info(
            f"Пользователь указал количество дней до первого срыва ({days}) для опроса (survey_id={session.survey_id})"
        )

        await self._complete_final_survey(event, session.survey_id)

    async def _complete_final_survey(self, event: MessageCallback | MessageCreated, survey_id: int):
        """Complete final survey and save all collected data."""
        session = await self._session_manager.get_final_survey_session_by_id(survey_id)
        survey = await self._final_survey_service.get_by_id(survey_id)

        if not survey or survey.completed_at:
            await event.message.edit("Опрос уже завершён.", attachments=[])
            return

        await self._final_survey_service.complete(
            survey=survey,
            ppa_30d=session.ppa_30d,
            ppa_7d=session.ppa_7d,
            cigs_per_day=session.cigs_per_day,
            quit_attempt_made=session.quit_attempt_made,
            days_to_first_lapse=session.days_to_first_lapse
        )

        await self._session_manager.delete_final_survey_session(event.from_user.user_id)

        text = "✅ Спасибо! Финальный опрос завершён. Спасибо за участие в исследовании!\n"

        if isinstance(event, MessageCreated):
            await event.message.answer(text, attachments=[])
        else:
            await event.message.edit(text, attachments=[])

        logger.info(f"Финальный опрос (survey_id={survey.id}) успешно завершён")
