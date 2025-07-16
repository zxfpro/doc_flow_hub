import logging
import os
from logging.handlers import RotatingFileHandler

LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "logs/doc_flow_hub.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# 确保日志目录存在
os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)

def get_logger(name: str) -> logging.Logger:
    """
    获取一个配置好的日志记录器。
    """
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # 避免重复添加处理器
    if not logger.handlers:
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(console_handler)

        # 文件处理器 (按大小轮转)
        file_handler = RotatingFileHandler(
            LOG_FILE_PATH,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)

    return logger

# 初始化根日志记录器，确保所有模块都能使用
get_logger("doc_flow_hub")