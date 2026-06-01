"""
logger.py — 日志工具模块
输出到两个地方：终端（实时查看）+ 内存缓冲区（供 Allure 报告附加）
"""

import io
import logging
import sys
from logging import Handler, LogRecord


class AllureLogHandler(Handler):
    """自定义日志 Handler，将日志写入内存缓冲区供 Allure 报告使用"""

    def __init__(self):
        super().__init__()
        self._buffer = io.StringIO()

    def emit(self, record: LogRecord):
        try:
            msg = self.format(record)
            self._buffer.write(msg + "\n")
        except Exception:
            self.handleError(record)

    def get_log_text(self) -> str:
        return self._buffer.getvalue()

    def clear(self):
        self._buffer = io.StringIO()


# ── 全局日志格式和 Handler 实例（所有 logger 共享）───────────────

_LOG_FMT = logging.Formatter(
    fmt="%(asctime)s [%(levelname)-8s] %(name)s :: %(message)s",
    datefmt="%H:%M:%S",
)

_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(_LOG_FMT)
_console_handler.setLevel(logging.DEBUG)

_allure_handler = AllureLogHandler()
_allure_handler.setFormatter(_LOG_FMT)
_allure_handler.setLevel(logging.DEBUG)


def get_logger(name: str) -> logging.Logger:
    """获取带双通道输出的 logger 实例（终端 + Allure 缓冲区）"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # 防重复添加 Handler
    if not any(isinstance(h, AllureLogHandler) for h in logger.handlers):
        logger.addHandler(_allure_handler)
    if not any(isinstance(h, logging.StreamHandler) and h.stream is sys.stdout
                  for h in logger.handlers):
        logger.addHandler(_console_handler)

    logger.propagate = False
    return logger


def get_allure_log_text() -> str:
    """取出缓冲区中的全部日志文本（conftest.py 调用）"""
    return _allure_handler.get_log_text()


def clear_allure_logs():
    """清空 Allure 日志缓冲区（每个测试开始前调用）"""
    _allure_handler.clear()
