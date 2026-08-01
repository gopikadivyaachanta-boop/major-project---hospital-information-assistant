# hospital-information-assistant/utils/logger.py

import logging
import sys

def get_logger(name: str = "HospitalAssistant") -> logging.Logger:
    """Provides a unified logger that outputs formatted messages to standard output."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
