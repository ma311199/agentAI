from typing import Dict, Optional
import threading
from log import debug, warning
from database import db
from config import Config
import time

# TTL（秒），默认从配置读取，回退5分钟
DEFAULT_MODELS_CACHE_TTL_SECONDS = getattr(Config, 'MODELS_CACHE_TTL_SECONDS', 300)

# 每个用户的模型缓存：user_id -> { model_id -> model_info }
_USER_MODELS_CACHE: Dict[int, Dict[int, dict]] = {}
# 每个用户独立的锁，避免并发下重复构建
_USER_LOCKS: Dict[int, threading.Lock] = {}
# 每个用户的缓存过期时间戳
_USER_MODELS_EXPIRY: Dict[int, float] = {}


def _build_models_for_user(user_id: int) -> Dict[int, dict]:
    """构建用户的模型字典，键为model_id，仅包含启用(is_active)的模型。
    包含私有模型与共享模型（model_flag=0）。
    """
    models = db.get_user_model_by_id(user_id) or []
    built: Dict[int, dict] = {}
    for m in models:
        try:
            # 只缓存启用的模型，减少后续判断与错误使用
            if m.get('is_active'):
                mid = int(m.get('model_id'))
                built[mid] = m
        except Exception:
            # 忽略单条异常，继续构建
            continue
    debug(f"构建模型缓存 - 用户ID: {user_id}, 启用模型数: {len(built)}")
    return built


def get_models_for_user(user_id: int) -> Dict[int, dict]:
    """获取用户可用模型的字典（带缓存 + TTL）。"""
    lock = _USER_LOCKS.get(user_id)
    if lock is None:
        lock = threading.Lock()
        _USER_LOCKS[user_id] = lock
    with lock:
        now = time.time()
        cached = _USER_MODELS_CACHE.get(user_id)
        expiry = _USER_MODELS_EXPIRY.get(user_id, 0)
        if cached is not None and expiry > now:
            debug(f"命中模型缓存 - 用户ID: {user_id}, 模型数: {len(cached)}")
            return cached
        built = _build_models_for_user(user_id)
        _USER_MODELS_CACHE[user_id] = built
        _USER_MODELS_EXPIRY[user_id] = now + DEFAULT_MODELS_CACHE_TTL_SECONDS
        return built


def get_model_for_user(user_id: int, model_id: int) -> Optional[dict]:
    """从缓存中获取用户可用的某个模型信息（包含共享模型）。
    若缓存不存在则构建后再取。
    """
    models = get_models_for_user(user_id)
    try:
        mid = int(model_id)
    except Exception:
        warning(f"模型ID非法: {model_id}")
        return None
    return models.get(mid)


def invalidate_user_models(user_id: int) -> None:
    """失效指定用户的模型缓存。"""
    lock = _USER_LOCKS.get(user_id)
    if lock is None:
        lock = threading.Lock()
        _USER_LOCKS[user_id] = lock
    with lock:
        if user_id in _USER_MODELS_CACHE:
            debug(f"失效模型缓存 - 用户ID: {user_id}")
            _USER_MODELS_CACHE.pop(user_id, None)
            _USER_MODELS_EXPIRY.pop(user_id, None)

# 可选：主动刷新用户模型缓存（重建并续期TTL）
def refresh_user_models(user_id: int) -> Dict[int, dict]:
    lock = _USER_LOCKS.get(user_id)
    if lock is None:
        lock = threading.Lock()
        _USER_LOCKS[user_id] = lock
    with lock:
        built = _build_models_for_user(user_id)
        _USER_MODELS_CACHE[user_id] = built
        _USER_MODELS_EXPIRY[user_id] = time.time() + DEFAULT_MODELS_CACHE_TTL_SECONDS
        return built

# 可选：动态设置TTL（全局）
def set_models_cache_ttl(seconds: int) -> None:
    global DEFAULT_MODELS_CACHE_TTL_SECONDS
    try:
        DEFAULT_MODELS_CACHE_TTL_SECONDS = max(30, int(seconds))
    except Exception:
        warning("设置模型缓存TTL失败：参数非法，保持默认值")