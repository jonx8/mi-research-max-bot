import logging
import sys

from src.config import Config


def setup_logging(config: Config) -> None:
    """Настраивает систему логирования для приложения."""

    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)

    ptb_logger = logging.getLogger('telegram.ext')
    ptb_logger.setLevel(logging.WARNING)

    sqlalchemy_logger = logging.getLogger('sqlalchemy')
    sqlalchemy_logger.setLevel(logging.WARNING)

    aiosqlite_logger = logging.getLogger('aiosqlite')
    aiosqlite_logger.setLevel(logging.WARNING)

    httpx_logger = logging.getLogger('httpx')
    httpx_logger.setLevel(logging.WARNING)

    scheduler_logger = logging.getLogger('apscheduler')
    scheduler_logger.setLevel(logging.WARNING)


    logging.info("Система логирования инициализирована")
    logging.info(f"Уровень логирования: {logging.getLevelName(log_level)}")
