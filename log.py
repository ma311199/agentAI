import logging
import os
import glob
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from config import Config

# 确保logs目录存在（从配置读取）
LOG_DIR = Config.LOG_DIR
os.makedirs(LOG_DIR, exist_ok=True)

# 清理超过指定天数的日志文件（从配置读取）
def clean_old_logs(days_to_keep=Config.LOG_RETENTION_DAYS):
    """清理超过指定天数的旧日志文件
    
    Args:
        days_to_keep: 保留日志的天数
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        log_files = glob.glob(os.path.join(LOG_DIR, f"{Config.LOG_FILE_PREFIX}*.log*"))
        for log_file in log_files:
            file_mod_time = datetime.fromtimestamp(os.path.getmtime(log_file))
            if file_mod_time < cutoff_date:
                os.remove(log_file)
                print(f"Deleted old log file: {log_file}")
    except Exception as e:
        print(f"Error cleaning old logs: {e}")

# 当前日期作为日志文件名的一部分（从配置读取前缀）
current_date = datetime.now().strftime('%Y-%m-%d')
LOG_FILE = os.path.join(LOG_DIR, f"{Config.LOG_FILE_PREFIX}{current_date}.log")

# 创建logger实例（名称从配置读取）
logger = logging.getLogger(Config.LOGGER_NAME)
logger.setLevel(logging.DEBUG)  # 保留最低级别，便于捕获所有日志

# 创建日志格式化器（格式与时间格式从配置读取）
formatter = logging.Formatter(
    Config.LOG_FORMAT,
    datefmt=Config.LOG_DATEFMT
)

# 创建文件处理器 - 使用RotatingFileHandler实现日志轮转（参数从配置读取）
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=Config.LOG_MAX_BYTES,
    backupCount=Config.LOG_BACKUP_COUNT,
    encoding='utf-8'
)
file_handler.setLevel(getattr(logging, Config.LOG_LEVEL_FILE, logging.INFO))
file_handler.setFormatter(formatter)

# 创建控制台处理器（级别从配置读取）
console_handler = logging.StreamHandler()
console_handler.setLevel(getattr(logging, Config.LOG_LEVEL_CONSOLE, logging.DEBUG))
console_handler.setFormatter(formatter)

# 将处理器添加到logger（避免重复添加）
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

# 日志功能封装函数
def debug(message):
    """记录调试级别日志"""
    logger.debug(message, stacklevel=2)

def info(message):
    """记录信息级别日志"""
    logger.info(message, stacklevel=2)

def warning(message):
    """记录警告级别日志"""
    logger.warning(message, stacklevel=2)

def error(message):
    """记录错误级别日志"""
    logger.error(message, stacklevel=2)

def critical(message):
    """记录严重错误级别日志"""
    logger.critical(message, stacklevel=2)

def exception(message):
    """记录异常信息，自动包含堆栈跟踪"""
    logger.exception(message, stacklevel=2)

# 用户操作日志函数
def log_user_action(user_id, action, details=None):
    """记录用户操作日志
    
    Args:
        user_id: 用户ID或用户名
        action: 用户执行的操作
        details: 操作的详细信息（可选）
    """
    log_message = f"User Action - User: {user_id}, Action: {action}"
    if details:
        log_message += f", Details: {details}"
    logger.info(log_message)

# API调用日志函数
def log_api_call(endpoint, method, status_code, user_id=None, response_time=None):
    """记录API调用日志
    
    Args:
        endpoint: API端点
        method: HTTP方法
        status_code: 响应状态码
        user_id: 用户ID（可选）
        response_time: 响应时间（毫秒，可选）
    """
    log_message = f"API Call - {method} {endpoint}, Status: {status_code}"
    if user_id:
        log_message += f", User: {user_id}"
    if response_time:
        log_message += f", Response Time: {response_time}ms"
    
    if status_code >= 500:
        logger.error(log_message, stacklevel=2)
    elif status_code >= 400:
        logger.warning(log_message, stacklevel=2)
    else:
        logger.info(log_message, stacklevel=2)

# 数据库操作日志函数
def log_db_operation(operation, table, status="success", details=None):
    """记录数据库操作日志
    
    Args:
        operation: 数据库操作类型（如select, insert, update, delete）
        table: 操作的表名
        status: 操作状态（success/failed）
        details: 操作的详细信息（可选）
    """
    log_message = f"Database - Operation: {operation}, Table: {table}, Status: {status}"
    if details:
        log_message += f", Details: {details}"
    
    if status == "failed":
        logger.error(log_message, stacklevel=2)
    else:
        logger.info(log_message, stacklevel=2)

# 清理旧日志（保留天数从配置读取）
clean_old_logs(Config.LOG_RETENTION_DAYS)

# 初始化时记录日志
logger.info("Logger initialized successfully")