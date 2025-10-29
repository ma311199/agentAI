from datetime import timedelta
import os

class Config:
    # 基础路径配置：用于拼接默认数据库与日志目录
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # 项目根目录

    # 基础安全配置
    SECRET_KEY = 'dev-secret-change-mm'  # Flask会话签名密钥（生产环境务必改为安全随机值）
    SESSION_COOKIE_SECURE = False  # 是否仅在HTTPS下发送Cookie（开发环境False，生产建议True）
    SESSION_COOKIE_HTTPONLY = True  # 防止JS读取Cookie，提升安全性
    SESSION_COOKIE_SAMESITE = 'Lax'  # 防止跨站请求伪造（可选Strict/None，根据业务需求调整）

    # 会话配置
    SESSION_TIMEOUT_MINUTES = 60  # 会话过期时间（分钟），统一控制后端登录有效期
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=SESSION_TIMEOUT_MINUTES)  # 永久会话的过期时间
    SESSION_REFRESH_EACH_REQUEST = True  # True=滑动过期（每次请求刷新过期时间）；False=固定过期

    # 数据库配置
    DB_PATH = os.path.join(BASE_DIR, 'db', 'db.sqlite3')  # SQLite数据库文件路径
    DB_CHECK_SAME_THREAD = False  # 允许跨线程访问同一连接（与当前实现一致）

    # 日志配置
    LOG_DIR = os.path.join(BASE_DIR, 'logs')  # 日志目录
    LOG_FILE_PREFIX = 'agent_ai_'  # 日志文件名前缀（会自动追加日期）
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 单个日志文件最大大小（字节），默认10MB
    LOG_BACKUP_COUNT = 5  # 日志轮转备份文件数量
    LOG_RETENTION_DAYS = 3  # 日志保留天数（清理策略）
    LOG_LEVEL_FILE = 'INFO'  # 文件日志记录级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    LOG_LEVEL_CONSOLE = 'DEBUG'  # 控制台日志显示级别
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'  # 日志格式
    LOG_DATEFMT = '%Y-%m-%d %H:%M:%S'  # 日志时间格式
    LOGGER_NAME = 'AgentAI'  # 根Logger名称

    # CSRF配置
    CSRF_ENABLED = True  # 是否启用CSRF保护
    CSRF_HEADER_NAME = 'X-CSRF-Token'  # 前端通过请求头传递CSRF的名称
    CSRF_JSON_FIELD = 'csrf_token'  # JSON请求体中CSRF字段名称
    CSRF_FORM_FIELD = 'csrf_token'  # 表单请求中的CSRF字段名称
    CSRF_SESSION_KEY = 'csrf_token'  # 会话中存储CSRF的键名
    CSRF_EXEMPT_ENDPOINTS = {'auth.login', 'auth.register'}  # CSRF豁免端点集合

    # 缓存TTL配置（秒）
    TOOLS_CACHE_TTL_SECONDS = 300  # 工具缓存TTL默认5分钟
    MODELS_CACHE_TTL_SECONDS = 300  # 模型缓存TTL默认5分钟

    # 应用运行配置（按需使用）
    DEBUG = True  # Flask调试模式
    HOST = '0.0.0.0'  # 服务监听地址
    PORT = 5000  # 服务监听端口