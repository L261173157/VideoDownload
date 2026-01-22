"""日志工具模块"""

import logging
import os
from datetime import datetime


class Logger:
    """日志记录器"""

    def __init__(self, log_dir='logs'):
        """
        初始化日志记录器

        Args:
            log_dir: 日志目录
        """
        # 确保日志目录存在
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 创建日志文件名（使用当前日期）
        log_filename = os.path.join(
            log_dir,
            f"video_downloader_{datetime.now().strftime('%Y%m%d')}.log"
        )

        # 配置日志记录器
        self.logger = logging.getLogger('VideoDownloader')
        self.logger.setLevel(logging.DEBUG)

        # 如果已经有处理器，先清除
        if self.logger.handlers:
            self.logger.handlers.clear()

        # 文件处理器 - 记录所有级别的日志
        file_handler = logging.FileHandler(
            log_filename,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)

        # 控制台处理器 - 只记录WARNING及以上级别
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)

        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 添加处理器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        self.logger.info("=" * 60)
        self.logger.info("日志系统初始化完成")
        self.logger.info("=" * 60)

    def debug(self, message):
        """记录DEBUG级别日志"""
        self.logger.debug(message)

    def info(self, message):
        """记录INFO级别日志"""
        self.logger.info(message)

    def warning(self, message):
        """记录WARNING级别日志"""
        self.logger.warning(message)

    def error(self, message, exc_info=False):
        """
        记录ERROR级别日志

        Args:
            message: 错误消息
            exc_info: 是否包含异常信息
        """
        self.logger.error(message, exc_info=exc_info)

    def critical(self, message, exc_info=False):
        """
        记录CRITICAL级别日志

        Args:
            message: 严重错误消息
            exc_info: 是否包含异常信息
        """
        self.logger.critical(message, exc_info=exc_info)

    def exception(self, message):
        """记录异常信息（自动包含堆栈跟踪）"""
        self.logger.exception(message)


# 创建全局日志实例
_global_logger = None


def get_logger():
    """获取全局日志实例"""
    global _global_logger
    if _global_logger is None:
        _global_logger = Logger()
    return _global_logger
