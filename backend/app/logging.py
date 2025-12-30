import logging
from typing import Any, Dict, Optional


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("mintagent")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("[%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


logger = setup_logger()


def log(event: str, data: Optional[Dict[str, Any]] = None, level: int = logging.INFO) -> None:
    if data:
        logger.log(level, "%s %s", event, data)
    else:
        logger.log(level, "%s", event)

