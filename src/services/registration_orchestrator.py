import logging
import random
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List

from src.config import Config
from src.exceptions import (
    SessionNotFoundError,
    ValidationError,
    InvalidStepError,
)
from src.models import Participant, BaselineQuestionnaire, RegistrationSession
from src.questionnaires import (
    get_fagerstrom_questions,
    calculate_fagerstrom_score,
    get_prochaska_questions,
    calculate_prochaska_score
)
from .final_service import FinalSurveyService
from .baseline_questionnaire_service import BaselineQuestionnaireService
from .session_manager import SessionManager
from .participant_service import ParticipantService
from .follow_up_service import FollowUpService
from .weekly_check_in_service import WeeklyCheckInService
from src.utils import get_encryption_service

logger = logging.getLogger(__name__)


class RegistrationStep(Enum):
    """
    Enumeration of all possible steps in the registration flow.

    Defines the sequential stages a user goes through during registration,
    from initial data collection to questionnaire completion.
    """
    AGE = "age"
    GENDER = "gender"
    CLINIC_CENTER = "clinic_center"
    SMOKING_YEARS = "smoking_years"
    CIGS_PER_DAY = "cigs_per_day"
    QUIT_ATTEMPTS = "quit_attempts"
    VAPE_USAGE = "vape_usage"
    SMOKER_HOUSEHOLD = "smoker_household"
    MEDICAL_HELP = "medical_help"
    FAGERSTROM = "fagerstrom"
    PROCHASKA = "prochaska"
    COMPLETED = "completed"


@dataclass
class QuestionData:
    """DTO for question data used in questionnaire presentation."""
    number: int
    total: int
    text: str
    options: List[str]
    field_name: str
    can_go_back: bool
    callback_prefix: str


@dataclass
class QuestionnaireResult:
    """DTO for questionnaire calculation results."""
    score: int
    level: str
    is_fagerstrom: bool


class RegistrationOrchestrator:
    """
    Orchestrator for the registration process.

    Manages the complete user registration workflow including:
    - Demographic data collection (age, gender)
    - Smoking history and habits
    - Medical history related to smoking cessation
    - Fagerstrom and Prochaska questionnaires
    - Participant creation and baseline data storage
    - Survey scheduling for the study period

    This class works directly with the ORM model and coordinates
    multiple services to complete the registration process.
    """

    def __init__(
            self,
            session_manager: SessionManager,
            participant_service: ParticipantService,
            baseline_service: BaselineQuestionnaireService,
            follow_up_service: FollowUpService,
            weekly_check_in_service: WeeklyCheckInService,
            final_survey_service: FinalSurveyService,
            config: Config
    ):
        """
        Initialize the registration orchestrator.

        Args:
            session_manager: Manager for user session state
            participant_service: Service for participant data management
            baseline_service: Service for baseline questionnaire data
            follow_up_service: Service for follow-up survey scheduling
            weekly_check_in_service: Service for weekly check-in scheduling
            final_survey_service: Service for final survey scheduling
            config: Application configuration containing timing intervals
        """
        self._session_manager = session_manager
        self._baseline_service = baseline_service
        self._participant_service = participant_service
        self._follow_up_service = follow_up_service
        self._weekly_check_in_service = weekly_check_in_service
        self._final_survey_service = final_survey_service
        self._config = config

    async def _get_session_or_raise(self, telegram_id: int) -> RegistrationSession:
        """
        Retrieve a registration session from database or raise exception.

        Args:
            telegram_id: User's Telegram ID

        Returns:
            RegistrationSession object

        Raises:
            SessionNotFoundError: If session does not exist
        """
        session = await self._session_manager.get_registration_session_by_telegram_id(telegram_id)
        if not session:
            logger.error(f"Сессия регистрации не найдена: пользователь {telegram_id}")
            raise SessionNotFoundError(telegram_id)
        return session

    async def _save_session(self, session_obj: RegistrationSession) -> None:
        """
        Save registration session changes to database.

        Args:
            session_obj: Registration session object to save
        """
        await self._session_manager.update_registration_session(session_obj)

    @staticmethod
    def _ensure_step(session: RegistrationSession, expected_step: RegistrationStep) -> None:
        """
        Verify that the session is at the expected registration step.

        Args:
            session: Registration session object
            expected_step: Expected registration step

        Raises:
            InvalidStepError: If current step does not match expected step
        """
        current_step_str = session.step if isinstance(session.step, str) else session.step.value
        if current_step_str != expected_step.value:
            raise InvalidStepError(
                f"Ожидался шаг '{expected_step.value}', текущий шаг '{current_step_str}'"
            )

    async def start_registration(self, telegram_id: int) -> None:
        """
        Start a new registration process for a user.

        If an existing registration session exists, it is deleted first.

        Args:
            telegram_id: User's Telegram ID
        """
        if await self._session_manager.has_registration_session(telegram_id):
            logger.info("Удаление существующей сессии регистрации")
            await self.delete_registration_session(telegram_id)
        await self._session_manager.create_registration_session(telegram_id)

        logger.info(f"Начата новая регистрация")

    async def get_current_step(self, telegram_id: int) -> Optional[RegistrationStep]:
        """
        Get the current registration step for a user.

        Args:
            telegram_id: User's Telegram ID

        Returns:
            Current RegistrationStep or None if no active session
        """
        session = await self._session_manager.get_registration_session_by_telegram_id(telegram_id)
        if not session:
            return None

        step_value = session.step if isinstance(session.step, str) else session.step.value
        return RegistrationStep(step_value)

    async def set_age(self, telegram_id: int, age: int) -> None:
        """
        Set user's age and advance to gender step.

        Args:
            telegram_id: User's Telegram ID
            age: User's age in years

        Raises:
            ValidationError: If age is out of valid range (18-120)
        """
        session = await self._get_session_or_raise(telegram_id)
        self._ensure_step(session, RegistrationStep.AGE)

        if not (18 <= age <= 120):
            logger.warning(f"Неверный возраст: age={age}")
            raise ValidationError("⚠️ Возраст должен быть от 18 до 120 лет")

        session.age = age
        session.step = RegistrationStep.GENDER.value
        await self._save_session(session)
        logger.info(f"Установлен возраст: age={age}")

    async def set_gender(self, telegram_id: int, gender_key: str) -> None:
        """
        Set user's gender and advance to clinic center step.

        Args:
            telegram_id: User's Telegram ID
            gender_key: Callback data identifier ('gender_male' or 'gender_female')

        Raises:
            ValidationError: If gender_key is invalid
        """
        session = await self._get_session_or_raise(telegram_id)
        self._ensure_step(session, RegistrationStep.GENDER)

        if gender_key not in ('gender_male', 'gender_female'):
            logger.warning(f"Неверное значение пола: gender_key={gender_key}")
            raise ValidationError("Некорректное значение пола")

        session.gender = "мужской" if gender_key == "gender_male" else "женский"
        session.step = RegistrationStep.CLINIC_CENTER.value
        await self._save_session(session)
        logger.info(f"Установлен пол: gender={session.gender}")

    async def set_clinic_center(self, telegram_id: int, center: str) -> None:
        """
        Set clinic center and advance to smoking years step.

        Args:
            telegram_id: User's Telegram ID
            center: Selected clinic center name
        """
        session = await self._get_session_or_raise(telegram_id)
        self._ensure_step(session, RegistrationStep.CLINIC_CENTER)

        session.clinic_center = center
        session.step = RegistrationStep.SMOKING_YEARS.value
        await self._save_session(session)
        logger.info(f"Установлен клинический центр: center={center}")

    async def set_smoking_years(self, telegram_id: int, years: int) -> None:
        """
        Set user's smoking duration and advance to cigarettes per day step.

        Args:
            telegram_id: User's Telegram ID
            years: Number of years the user has been smoking

        Raises:
            ValidationError: If years is out of valid range (0-120)
        """
        session = await self._get_session_or_raise(telegram_id)
        self._ensure_step(session, RegistrationStep.SMOKING_YEARS)

        if not (0 <= years <= 120):
            logger.warning(f"Неверный стаж курения:, years={years}")
            raise ValidationError(f"⚠️ Количество лет курения должно быть от 0 до 120")

        session.smoking_years = years
        session.step = RegistrationStep.CIGS_PER_DAY.value
        await self._save_session(session)
        logger.info(f"Установлен стаж курения, years={years}")

    async def set_cigs_per_day(self, telegram_id: int, cigs: int) -> None:
        """
        Set user's daily cigarette consumption and advance to quit attempts step.

        Args:
            telegram_id: User's Telegram ID
            cigs: Number of cigarettes smoked per day

        Raises:
            ValidationError: If cigs is out of valid range (0-100)
        """
        session = await self._get_session_or_raise(telegram_id)
        self._ensure_step(session, RegistrationStep.CIGS_PER_DAY)

        if not (0 <= cigs <= 100):
            logger.warning(f"Неверное количество сигарет: cigs={cigs}")
            raise ValidationError("⚠️ Количество сигарет должно быть от 0 до 100")

        session.cigs_per_day = cigs
        session.step = RegistrationStep.QUIT_ATTEMPTS.value
        await self._save_session(session)
        logger.info(f"Установлено количество сигарет: cigs={cigs}")

    async def set_quit_attempts(self, telegram_id: int, has_attempts: bool) -> None:
        """
        Set user's quit attempt history and advance to vape usage step.

        Args:
            telegram_id: User's Telegram ID
            has_attempts: Whether user has previously attempted to quit
        """
        session = await self._get_session_or_raise(telegram_id)
        self._ensure_step(session, RegistrationStep.QUIT_ATTEMPTS)

        session.quit_attempts_before = has_attempts
        session.step = RegistrationStep.VAPE_USAGE.value
        await self._save_session(session)
        logger.info(f"Установлены попытки бросить: has_attempts={has_attempts}")

    async def set_uses_vape(self, telegram_id: int, uses_vape: bool) -> None:
        """
        Set user's vape/e-cigarette usage and advance to household smokers step.

        Args:
            telegram_id: User's Telegram ID
            uses_vape: Whether user uses vape or e-cigarettes
        """
        session = await self._get_session_or_raise(telegram_id)
        self._ensure_step(session, RegistrationStep.VAPE_USAGE)

        session.uses_vape = uses_vape
        session.step = RegistrationStep.SMOKER_HOUSEHOLD.value
        await self._save_session(session)
        logger.info(f"Установлено использование вейпа: uses_vape={uses_vape}")

    async def set_smoker_in_household(self, telegram_id: int, has_smoker: bool) -> None:
        """
        Set household smoking status and advance to medical help step.

        Args:
            telegram_id: User's Telegram ID
            has_smoker: Whether someone else in household smokes
        """
        session = await self._get_session_or_raise(telegram_id)
        self._ensure_step(session, RegistrationStep.SMOKER_HOUSEHOLD)

        session.smoker_in_household = has_smoker
        session.step = RegistrationStep.MEDICAL_HELP.value
        await self._save_session(session)
        logger.info(f"Установлены курящие в семье: has_smoker={has_smoker}")

    async def set_prior_medical_help(self, telegram_id: int, answer: str) -> None:
        """
        Set prior medical help for smoking cessation and advance to Fagerstrom questionnaire.

        Args:
            telegram_id: User's Telegram ID
            answer: Response about prior medical help ('Да', 'Нет', or 'Не помню')
        """
        session = await self._get_session_or_raise(telegram_id)
        self._ensure_step(session, RegistrationStep.MEDICAL_HELP)

        session.prior_medical_help = answer
        session.step = RegistrationStep.FAGERSTROM.value
        await self._save_session(session)
        logger.info(f"Установлена медицинская помощь: answer={answer}")

    async def start_questionnaire(self, telegram_id: int, questionnaire_type: str) -> None:
        """
        Start a questionnaire (Fagerstrom or Prochaska).

        Args:
            telegram_id: User's Telegram ID
            questionnaire_type: Type of questionnaire ('fagerstrom' or 'prochaska')

        Raises:
            ValidationError: If questionnaire_type is invalid
        """
        if questionnaire_type not in ('fagerstrom', 'prochaska'):
            logger.warning(f"Неверный тип опросника: type={questionnaire_type}")
            raise ValidationError("Тип опросника должен быть 'fagerstrom' или 'prochaska'")

        session = await self._get_session_or_raise(telegram_id)

        if questionnaire_type == 'fagerstrom':
            self._ensure_step(session, RegistrationStep.FAGERSTROM)
        else:
            self._ensure_step(session, RegistrationStep.PROCHASKA)

        session.current_questionnaire = questionnaire_type
        session.current_question_index = 0
        await self._save_session(session)
        logger.info(f"Начат опросник: type={questionnaire_type}")

    async def get_current_question(self, telegram_id: int) -> QuestionData:
        """
        Get the current questionnaire question for the user.

        Args:
            telegram_id: User's Telegram ID

        Returns:
            QuestionData object containing question details

        Raises:
            InvalidStepError: If no questionnaire is active or questionnaire is completed
        """
        session = await self._get_session_or_raise(telegram_id)

        if not session.current_questionnaire:
            raise InvalidStepError("Опросник не активен")

        questions = (
            get_fagerstrom_questions()
            if session.current_questionnaire == 'fagerstrom'
            else get_prochaska_questions()
        )

        idx = session.current_question_index

        if idx >= len(questions):
            logger.error(f"Опросник уже завершён: index={idx}, total={len(questions)}")
            raise InvalidStepError("Опросник уже завершён")

        q = questions[idx]
        return QuestionData(
            number=q['number'],
            total=len(questions),
            text=q['question'],
            options=q['options'],
            field_name=q['field'],
            can_go_back=(idx > 0),
            callback_prefix=session.current_questionnaire
        )

    async def save_answer(
            self,
            telegram_id: int,
            questionnaire_type: str,
            question_index: int,
            answer_index: int
    ) -> None:
        """
        Save user's answer to a questionnaire question.

        Args:
            telegram_id: User's Telegram ID
            questionnaire_type: Type of questionnaire being answered
            question_index: Index of the question being answered
            answer_index: Index of the selected answer option

        Raises:
            InvalidStepError: If questionnaire type mismatch or indices are invalid
        """
        session = await self._get_session_or_raise(telegram_id)

        if session.current_questionnaire != questionnaire_type:
            logger.error(
                f"Несоответствие типа опросника:"
                f"expected={session.current_questionnaire}, received={questionnaire_type}"
            )
            raise InvalidStepError(
                f"Активен опросник '{session.current_questionnaire}', получен ответ для '{questionnaire_type}'"
            )

        questions = (
            get_fagerstrom_questions()
            if questionnaire_type == 'fagerstrom'
            else get_prochaska_questions()
        )

        if question_index >= len(questions):
            logger.warning(
                f"Неверный индекс вопроса: index={question_index}, total={len(questions)}")
            raise InvalidStepError(f"Вопрос {question_index} не существует")

        question = questions[question_index]

        if answer_index >= len(question['options']):
            logger.warning(
                f"Неверный индекс ответа: answer_index={answer_index}, options={len(question['options'])}")
            raise InvalidStepError(f"Ответ {answer_index} не существует")

        score = question['scores'][answer_index]

        if questionnaire_type == 'fagerstrom':
            if session.fagerstrom_answers is None:
                session.fagerstrom_answers = {}
            session.fagerstrom_answers[question['field']] = score
        else:
            if session.prochaska_answers is None:
                session.prochaska_answers = {}
            session.prochaska_answers[question['field']] = score

        session.current_question_index += 1
        await self._save_session(session)

    async def go_to_previous_question(self, telegram_id: int) -> None:
        """
        Navigate back to the previous questionnaire question.

        Args:
            telegram_id: User's Telegram ID

        Raises:
            InvalidStepError: If no questionnaire is active
            ValidationError: If already at the first question
        """
        session = await self._get_session_or_raise(telegram_id)

        if not session.current_questionnaire:
            logger.warning(f"Попытка возврата при неактивном опроснике")
            raise InvalidStepError("Опросник не активен")

        if session.current_question_index <= 0:
            logger.warning(f"Попытка возврата с первого вопроса:")
            raise ValidationError("Нельзя вернуться назад с первого вопроса")

        session.current_question_index -= 1
        await self._save_session(session)
        logger.info(f"Возврат к предыдущему вопросу: new_index={session.current_question_index}")

    async def is_questionnaire_completed(self, telegram_id: int, questionnaire_type: str) -> bool:
        """
        Check if a questionnaire has been completed.

        Args:
            telegram_id: User's Telegram ID
            questionnaire_type: Type of questionnaire to check

        Returns:
            True if questionnaire is completed, False otherwise
        """
        session = await self._get_session_or_raise(telegram_id)

        if questionnaire_type == 'fagerstrom':
            total_questions = len(get_fagerstrom_questions())
            answers_count = len(session.fagerstrom_answers or {})
            return total_questions == answers_count
        else:
            total_questions = len(get_prochaska_questions())
            answers_count = len(session.prochaska_answers or {})
            return total_questions == answers_count

    async def complete_fagerstrom(self, telegram_id: int) -> QuestionnaireResult:
        """
        Complete the Fagerstrom questionnaire and calculate results.

        Args:
            telegram_id: User's Telegram ID

        Returns:
            QuestionnaireResult with score and dependency level

        Raises:
            InvalidStepError: If Fagerstrom is not active or already completed
        """
        session = await self._get_session_or_raise(telegram_id)

        if session.current_questionnaire != 'fagerstrom':
            logger.warning(f"Завершение Фагерстрёма при неактивном опроснике: active={session.current_questionnaire}")
            raise InvalidStepError("Опросник Фагерстрёма не активен")

        if session.fagerstrom_score is not None:
            logger.warning(f"Повторное завершение Фагерстрёма: score={session.fagerstrom_score}")
            raise InvalidStepError("Опросник Фагерстрёма уже завершён")

        score, level = calculate_fagerstrom_score(session.fagerstrom_answers or {})
        session.fagerstrom_score = score
        session.fagerstrom_level = level
        session.current_questionnaire = None
        session.current_question_index = 0
        session.step = RegistrationStep.PROCHASKA.value

        await self._save_session(session)
        logger.info(f"Завершён Фагерстрём: score={score}/10, level={level}")

        return QuestionnaireResult(score=score, level=level, is_fagerstrom=True)

    async def complete_prochaska(self, telegram_id: int) -> QuestionnaireResult:
        """
        Complete the Prochaska questionnaire and calculate results.

        Args:
            telegram_id: User's Telegram ID

        Returns:
            QuestionnaireResult with score and motivation stage

        Raises:
            InvalidStepError: If Prochaska is not active or already completed
        """
        session = await self._get_session_or_raise(telegram_id)

        if session.current_questionnaire != 'prochaska':
            logger.warning(f"Завершение Прохаски при неактивном опроснике: active={session.current_questionnaire}")
            raise InvalidStepError("Опросник Прохаски не активен")

        if session.prochaska_score is not None:
            logger.warning(f"Повторное завершение Прохаски: score={session.prochaska_score}")
            raise InvalidStepError("Опросник Прохаски уже завершён")

        score, level = calculate_prochaska_score(session.prochaska_answers or {})
        session.prochaska_score = score
        session.prochaska_level = level
        session.step = RegistrationStep.COMPLETED.value
        session.current_questionnaire = None

        await self._save_session(session)
        logger.info(f"Завершена Прохаска: score={score}/8, level={level}")

        return QuestionnaireResult(score=score, level=level, is_fagerstrom=False)

    async def _schedule_all_surveys(self, participant: Participant) -> None:
        """Планирует все опросы для участника"""
        await self._follow_up_service.create_scheduled(
            participant.participant_code,
            participant.registration_date,
            self._config.FOLLOW_UP_INTERVALS
        )

        if participant.group_name == 'B':
            await self._weekly_check_in_service.create_scheduled(
                participant.participant_code,
                participant.registration_date,
                self._config.WEEKLY_CHECKIN_INTERVAL,
                24
            )

        await self._final_survey_service.create_scheduled(
            participant.participant_code,
            participant.registration_date,
            self._config.FINAL_SURVEY_INTERVAL
        )

    async def finalize_registration(self, telegram_id: int) -> Participant:
        """
        Complete the registration process and create the participant.

        This method:
        1. Creates a unique participant code
        2. Assigns user randomly to group A or B
        3. Saves participant data
        4. Stores baseline questionnaire answers
        5. Schedules all future surveys
        6. Cleans up the registration session

        Args:
            telegram_id: User's Telegram ID

        Returns:
            Created Participant object

        Raises:
            ValidationError: If user is already registered
        """
        session = await self._get_session_or_raise(telegram_id)
        self._ensure_step(session, RegistrationStep.COMPLETED)

        if await self._participant_service.exists(telegram_id):
            logger.error(f"Попытка повторной регистрации")
            raise ValidationError("Пользователь уже зарегистрирован")

        # Generate participant code and assign group
        participant_code = await self._participant_service.generate_unique_participant_code(telegram_id)
        group = 'A' if random.random() < 0.5 else 'B'
        registration_date = datetime.now()

        logger.info(f"Создание участника: participant_code={participant_code}, group={group}")

        # Create and save participant
        encryption_service = get_encryption_service()
        telegram_id_encrypted = encryption_service.encrypt(telegram_id)

        participant = Participant(
            participant_code=participant_code,
            telegram_id_encrypted=telegram_id_encrypted,
            group_name=group,
            registration_date=registration_date,
            age=session.age,
            gender=session.gender,
            clinic_center=session.clinic_center
        )
        await self._participant_service.save(participant)
        logger.info(f"Сохранён участник: participant_code={participant_code}")

        baseline = BaselineQuestionnaire(
            participant_code=participant_code,
            completed_at=registration_date,
            smoking_years=session.smoking_years,
            cigs_per_day=session.cigs_per_day,
            quit_attempts_before=session.quit_attempts_before,
            uses_vape=session.uses_vape,
            smoker_in_household=session.smoker_in_household,
            prior_medical_help=session.prior_medical_help,
            fagerstrom_score=session.fagerstrom_score,
            fagerstrom_level=session.fagerstrom_level,
            prochaska_score=session.prochaska_score,
            prochaska_level=session.prochaska_level,
            **(session.fagerstrom_answers or {}),
            **(session.prochaska_answers or {})
        )
        await self._baseline_service.save(baseline)

        await self._schedule_all_surveys(participant)
        await self._session_manager.delete_registration_session(telegram_id)
        logger.info(f"Регистрация успешно завершена: participant_code={participant_code}, group={group}")

        return participant

    async def delete_registration_session(self, telegram_id: int) -> None:
        """
        Delete a registration session.

        Args:
            telegram_id: User's Telegram ID
        """
        await self._session_manager.delete_registration_session(telegram_id)
        logger.info(f"Удалена сессия регистрации")

    async def set_registration_step(self, telegram_id: int, step: RegistrationStep) -> None:
        """
        Set the current registration step directly.

        Args:
            telegram_id: User's Telegram ID
            step: Target registration step
        """
        session = await self._get_session_or_raise(telegram_id)
        session.step = step.value
        await self._save_session(session)
        logger.info(f"Установлен шаг регистрации: step={step.value}")

    async def go_back_to_step(self, telegram_id: int, target_step: RegistrationStep) -> None:
        """
        Navigate back to a specific registration step (for "Back" buttons).

        Args:
            telegram_id: User's Telegram ID
            target_step: Step to return to
        """
        session = await self._get_session_or_raise(telegram_id)
        session.step = target_step.value
        await self._save_session(session)
        logger.info(f"Возврат к шагу регистрации: target_step={target_step.value}")

    async def set_last_bot_message_id(self, telegram_id: int, message_id: int) -> None:
        """
        Store the last bot message ID for future editing/deletion.

        Args:
            telegram_id: User's Telegram ID
            message_id: ID of the last bot message
        """
        await self._session_manager.set_last_bot_message_id(telegram_id, message_id)

    async def get_last_bot_message_id(self, telegram_id: int) -> Optional[int]:
        """
        Retrieve the last bot message ID.

        Args:
            telegram_id: User's Telegram ID

        Returns:
            Last bot message ID or None if not found
        """
        return await self._session_manager.get_last_bot_message_id(telegram_id)
