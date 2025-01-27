import logging
import sys


def setup_logger(name: str) -> logging.Logger:
    """Configure logger to output to stdout/stderr for Docker."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Console handler for stdout
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # Format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    return logger
