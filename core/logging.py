import logging

import colorlog

from core.config import settings


def config_logging() -> None:
    colored_handler = colorlog.StreamHandler()
    colored_handler.setFormatter(colorlog.ColoredFormatter(
        fmt="%(asctime)s - %(log_color)s%(levelname)-4s%(reset)s - %(filename)s:%(lineno)-8d - %(funcName)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }
    ))
    logging.basicConfig(
        level=settings.LOG_LEVEL.upper(),
        handlers=[colored_handler],
        force=True,
    )

    third_party_loggers = [
        "web3",
        "urllib3",
        "sqlalchemy",
        "asyncio",
        "apscheduler",
        "tzlocal"
    ]
    for logger_name in third_party_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    logging.info("Logging initialized with level: %s", settings.LOG_LEVEL)
