import logging
from pathlib import Path


log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(parents=True, exist_ok=True)


def get_logger(name: str) -> logging.Logger:
    """获取日志记录器，同时输出到文件和控制台"""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(log_dir / "app.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
