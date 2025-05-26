import logging
from logging.handlers import RotatingFileHandler
import os
import sys

# Constants
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "logs/app.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Create logs directory if not present
os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)

# Singleton logger instance
_logger = None

def setup_logger(name: str) -> logging.Logger:
    global _logger
    if _logger:
        return _logger

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    logger.propagate = False  # Avoid duplicate logs in some setups

    # Formatter
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Avoid adding handlers multiple times
    if not logger.handlers:
        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File Handler with rotation
        file_handler = RotatingFileHandler(
            LOG_FILE_PATH,
            maxBytes=5_000_000,  # 5 MB
            backupCount=3,
            encoding="utf-8"
        )
        # file_handler.setFormatter(formatter)
        # logger.addHandler(file_handler)
        
        # File Handler that overwrites each time
        file_handler = logging.FileHandler(LOG_FILE_PATH, mode='w', encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        open(LOG_FILE_PATH, 'w').close()


    _logger = logger
    return logger
