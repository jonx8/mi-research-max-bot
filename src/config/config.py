import os
from datetime import time

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Конфигурация приложения"""

    # Telegram Bot
    BOT_TOKEN = os.getenv('BOT_TOKEN')

    # Database
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')

    DB_NAME = os.getenv('DB_NAME', 'database/participants.db')
    DATABASE_URL = f'sqlite+aiosqlite:///{DB_NAME}'

    # Интервалы для тестирования (в минутах)
    FOLLOW_UP_INTERVALS = (60 * 24, 3 * 60 * 24)
    WEEKLY_CHECKIN_INTERVAL = 60 * 24
    FINAL_SURVEY_INTERVAL = 60 * 24 * 6
    DAILY_MORNING_SENDING_TIME = time(10, 00)  # 10:00
    DAILY_HIGH_DEP_SENDING_TIME = time(13, 00)  # 13:00
    DAILY_EVENING_SENDING_TIME = time(20, 0)  # 20:00

    # Для продакшена
    # FOLLOW_UP_INTERVALS = [30 * 24 * 60, 90 * 24 * 60]  # 30 и 90 дней в минутах
    # WEEKLY_CHECKIN_INTERVAL = 7 * 24 * 60               # 7 дней в минутах
    # FINAL_SURVEY_INTERVAL = 180 * 24 * 60               # 180 дней в минутах
    # DAILY_MORNING_SENDING_TIME = time(10, 0)  # 10:00
    # DAILY_EVENING_SENDING_TIME = time(20, 0)  # 20:00

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    # Google Sheets
    GOOGLE_SHEETS_CREDENTIALS_PATH = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH', "config/mi-research-tg-bot.json")
    GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
    GOOGLE_SHEETS_EXPORT_INTERVAL = int(os.getenv('GOOGLE_SHEETS_EXPORT_INTERVAL', '60'))
    GOOGLE_SHEETS_EXPORT_TIMEOUT = int(os.getenv('GOOGLE_SHEETS_EXPORT_TIMEOUT', '300'))

    # Scheduler intervals (in seconds)
    SURVEY_CHECK_INTERVAL = int(os.getenv('SURVEY_CHECK_INTERVAL', '60'))
    DAILY_LOG_CHECK_INTERVAL = int(os.getenv('DAILY_LOG_CHECK_INTERVAL', '60'))
    INTERVENTION_CONTENT_INTERVAL = int(os.getenv('INTERVENTION_CONTENT_INTERVAL', '3600'))

    # Principal Investigator Contact
    PRINCIPAL_INVESTIGATOR_NAME = os.getenv('PRINCIPAL_INVESTIGATOR_NAME', 'Исследователь')
    PRINCIPAL_INVESTIGATOR_CONTACT = os.getenv('PRINCIPAL_INVESTIGATOR_CONTACT', '')