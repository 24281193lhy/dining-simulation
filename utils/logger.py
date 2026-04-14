# utils/logger.py
import logging
import os
import sys
from typing import Optional

# 默认日志格式
DEFAULT_LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_loggers = {}  # 缓存已创建的 logger

def get_logger(
    name: str,
    log_file: Optional[str] = None,
    level: int = logging.INFO,
    console: bool = True,
    file_mode: str = "a"
) -> logging.Logger:
    """
    获取一个配置好的 logger 实例。

    :param name: logger 名称（通常为模块名）
    :param log_file: 日志文件路径，如果为 None 则不输出到文件
    :param level: 日志级别，默认为 INFO
    :param console: 是否输出到控制台，默认为 True
    :param file_mode: 文件打开模式，默认为追加 'a'
    :return: Logger 实例
    """
    # 如果已经创建过，直接返回
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # 避免重复输出

    # 清除已有的 handlers（避免重复添加）
    if logger.handlers:
        logger.handlers.clear()

    formatter = logging.Formatter(DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)

    # 控制台 handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # 文件 handler
    if log_file:
        # 确保目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(log_file, mode=file_mode, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    _loggers[name] = logger
    return logger