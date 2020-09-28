"""
This class holds the logger.
"""

# Handle imports
import logging
import logging.handlers

# Config logger
def setup_logger(path):
    global logger, absolute_path

    # Formatting
    logger = logging.getLogger(__name__)
    format = "[%(asctime)s] %(message)s"
    formatter = logging.Formatter(format, datefmt='%Y-%m-%d %H:%M')

    # Setup handler
    handler = logging.handlers.RotatingFileHandler(path, 'a', 10000, 2)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Final touches
    logger.propagate = False  # Disable console output
    logger.setLevel(logging.INFO)

    return logger