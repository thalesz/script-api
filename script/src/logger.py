import logging
from pathlib import Path


def get_logger(name: str, log_file: Path) -> logging.Logger:
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


class LoggerFactory:
    """Factory para criação de loggers; fornece método compatível com `get_logger`.
    """

    @staticmethod
    def get_logger(name: str, log_file: Path) -> logging.Logger:
        return get_logger(name, log_file)
