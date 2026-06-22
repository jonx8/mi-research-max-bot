import logging

from telegram import Update
from telegram.error import TimedOut, NetworkError
from telegram.ext import ContextTypes

from src.exceptions import ValidationError, SessionNotFoundError, InvalidStepError, UserNotFoundError, \
    TechniqueNotFoundError, CravingSessionNotFoundError

logger = logging.getLogger(__name__)


async def _notify_user(update: Update, text: str) -> None:
    """
    Send error notification to user via Telegram.

    Args:
        update: Telegram update object
        text: Error message text to display
    """
    if not update:
        logger.warning("No update object available for user notification")
        return

    if update.message:
        await update.message.reply_text(text)
    elif update.callback_query:
        try:
            await update.callback_query.edit_message_text(text)
        except Exception as e:
            logger.warning(f"Failed to edit message for error notification: {e}")
            await update.callback_query.answer(text, show_alert=True)


async def global_error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Global handler for all unhandled exceptions in the bot.

    This handler catches and appropriately handles different types of errors,
    logging details and sending user-friendly messages when possible.

    Args:
        update: Telegram update object that caused the error
        context: Telegram context object containing the error
    """
    error = context.error
    user_id = update.effective_user.id if update and update.effective_user else None

    logger.error(
        f"Глобальный обработчик ошибок: {type(error).__name__}: {error} для пользователя",
        exc_info=error
    )

    if isinstance(error, ValidationError):
        logger.warning(f"Ошибка валидации для пользователя: {error}")
        await _notify_user(update, str(error))

    elif isinstance(error, SessionNotFoundError):
        logger.warning(f"Сессия не найдена для пользователя {user_id}")
        await _notify_user(
            update,
            "⏰ Ваша сессия истекла. Пожалуйста, начните заново с команды /start"
        )

    elif isinstance(error, InvalidStepError):
        logger.error(f"Неверный шаг в сессии для пользователя {user_id}: {error}")
        if update and update.callback_query:
            await update.callback_query.answer("Это действие уже недоступно")

    elif isinstance(error, UserNotFoundError):
        logger.error(f"Пользователь {user_id} не найден в базе данных")
        await _notify_user(
            update,
            "👤 Пользователь не найден. Используйте /start для регистрации."
        )

    elif isinstance(error, TechniqueNotFoundError):
        logger.error(
            f"Техника не найдена для пользователя {user_id}: technique_id={error.technique_id}"
        )
        await _notify_user(
            update,
            "🆘 Техника временно недоступна. Попробуйте выбрать другую."
        )

    elif isinstance(error, CravingSessionNotFoundError):
        logger.error(f"Сессия анализа тяги не найдена для пользователя {user_id}")
        await _notify_user(
            update,
            "📝 Сессия анализа тяги не найдена. Начните заново через /sos"
        )

    elif isinstance(error, (TimedOut, NetworkError)):
        logger.warning(
            f"Сетевая ошибка для пользователя {user_id}: {type(error).__name__}: {error}"
        )
        # Don't notify user for network errors as they're often transient
        return

    else:
        logger.exception(
            f"Неожиданная ошибка для пользователя {user_id}: {type(error).__name__}"
        )
        await _notify_user(
            update,
            "❌ Произошла техническая ошибка. Мы уже работаем над её исправлением. "
            "Пожалуйста, попробуйте позже"
        )
