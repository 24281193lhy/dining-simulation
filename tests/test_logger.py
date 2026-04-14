
# tests/test_logger.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import tempfile
import logging
import pytest
from utils.logger import get_logger

class TestLogger:
    def test_get_logger_returns_logger(self):
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

    def test_logger_writes_to_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            logger = get_logger("test_file", log_file=log_file, level=logging.INFO)
            logger.info("这是一条测试日志")

            # 强制刷新并关闭所有 handlers 以释放文件
            for handler in logger.handlers[:]:
                handler.flush()
                handler.close()
                logger.removeHandler(handler)

            # 现在可以安全读取文件
            assert os.path.exists(log_file)
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            assert "这是一条测试日志" in content