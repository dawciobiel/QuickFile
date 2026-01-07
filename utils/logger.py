# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    """
    Configures the logging for the application.
    Logs are saved to ~/.config/QuickFile/main.log.
    """
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, "main.log")

    # If the log file exists, clear it
    if os.path.exists(log_file):
        with open(log_file, "w", encoding='utf-8') as f:
            f.truncate(0)

    # Configure the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG) # Reverted to logging.DEBUG

    # Create a rotating file handler
    # 1MB per file, keep 5 backup files
    file_handler = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)

    # Create a formatter and set it for the handlers
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(file_handler)

    # Suppress debug logs from PyQt6.uic
    logging.getLogger("PyQt6.uic").setLevel(logging.WARNING)

    # Return the logger instance
    return logger
