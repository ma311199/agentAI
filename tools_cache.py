import time
import json
import threading
from typing import Dict

from database import db
from tool_process import Toolregister
from tools import Tool
from log import debug, info, warning, error, exception
from config import Config
import time

# TTL（秒），默认从配置读取，回退5分钟
DEFAULT_TOOLS_CACHE_TTL_SECONDS = getattr(Config, 'TOOLS_CACHE_TTL_SECONDS', 300)

# 按用户缓存已注册工具，降低并发场景下的重复构建成本
_USER_TOOLS_CACHE: Dict[int, Dict[str, Tool]] = {}
_USER_LOCKS: Dict[int, threading.Lock] = {}
# 每个用户的缓存过期时间戳
_USER_TOOLS_EXPIRY: Dict[int, float] = {}


def _parse_params(val):
    try:
        if isinstance(val, str):
            return json.loads(val)
        return val
    except Exception:
        try:
            import ast
            return ast.literal_eval(val) if isinstance(val, str) else val
        except Exception:
            return None


def _build_tools_for_user(user_id: int) -> Dict[str, Tool]:
    tools = db.get_all_tools(user_id)
    print("数据库返回的内容tools：")
    reg = Toolregister()
    count = 0
    for t in tools:
        try:
            # 仅注册启用的工具
            if not t.get('is_active', True):
                continue
            if t['tool_type'] == "api":
                parameters=json.loads(t.get('parameters'))
                # 根据API工具的method类别生成对应的函数工具
                if isinstance(parameters, dict) and 'method' in parameters:
                    # 动态生成Python函数代码
                    
                    # 获取工具名称
                    tool_name = t.get('tool_name', 'api_tool')
                    # 获取API URL
                    api_url = t.get('code_content', '')
                    # 获取HTTP方法
                    http_method = parameters.get('method', 'get').lower()
                    # 获取参数列表
                    param_list = parameters.get('data', [])
                    # 函数描述
                    desc=t.get('description', '')
                    
                    # 生成函数参数定义
                    param_defs = []
                    for param in param_list:
                        param_name = param.get('name')
                        if param_name:
                            if param.get('required', False):
                                param=f"{param_name} : {param['type']}"
                                param_defs.append(param)
                            else:
                                param_defs.append(f"{param_name}=None")
                    param_str = ', '.join(param_defs)

                    # 根据HTTP方法生成不同的请求代码
                    if http_method == 'get':
                        request_code = f"response = requests.get('{api_url}', params=kwargs, timeout=30)"
                    else:  # post, put, delete, patch
                        request_code = f"response = requests.{http_method}('{api_url}', json=kwargs, timeout=30)"
                    
                    # 生成完整的函数代码
                    func_code = f"""
def {tool_name}({param_str}):
    '''API工具: {tool_name}
    HTTP方法: {http_method.upper()}
    URL: {api_url}
    '''
    import requests
    try:
        # 过滤掉非参数变量
        import inspect
        frame = inspect.currentframe()
        args, _, _, values = inspect.getargvalues(frame)
        kwargs = {{k: values[k] for k in args}}
        
        # 发送API请求
        {request_code}
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {{"error": str(e)}}
    except Exception as e:
        return {{"error": f"处理API响应时出错: {{str(e)}}"}}
    finally:
        del frame
"""             
                # print("函数代码：",func_code)
                reg.register_tool(
                    tool_name,
                    desc,
                    func_code,
                    _parse_params(param_list),
                )
            else:
                reg.register_tool(
                    t['tool_name'],
                    t.get('description', ''),
                    t.get('code_content', ''),
                    _parse_params(t.get('parameters')),
                )
            count += 1
        except Exception as e:
            warning(f"注册工具失败，已跳过 - 用户ID: {user_id}, 工具: {t.get('tool_name')}, 错误: {e}")
    debug(f"构建工具缓存 - 用户ID: {user_id}, 有效工具数: {count}")
    return reg.tools

def get_tools_for_user(user_id: int) -> Dict[str, Tool]:
    """获取用户的已注册工具（带缓存 + TTL）。"""
    lock = _USER_LOCKS.get(user_id)
    if lock is None:
        lock = threading.Lock()
        _USER_LOCKS[user_id] = lock
    with lock:
        now = time.time()
        cached = _USER_TOOLS_CACHE.get(user_id)
        expiry = _USER_TOOLS_EXPIRY.get(user_id, 0)
        if cached is not None and expiry > now:
            debug(f"命中工具缓存 - 用户ID: {user_id}, 工具数: {len(cached)}")
            return cached
        built = _build_tools_for_user(user_id)
        _USER_TOOLS_CACHE[user_id] = built
        _USER_TOOLS_EXPIRY[user_id] = now + DEFAULT_TOOLS_CACHE_TTL_SECONDS
        return built


def invalidate_user_tools(user_id: int) -> None:
    """在工具变更后失效缓存。"""
    if user_id in _USER_TOOLS_CACHE:
        del _USER_TOOLS_CACHE[user_id]
        _USER_TOOLS_EXPIRY.pop(user_id, None)
        debug(f"已失效用户工具缓存 - 用户ID: {user_id}")

# 可选：主动刷新用户工具缓存（重建并续期TTL）
def refresh_user_tools(user_id: int) -> Dict[str, Tool]:
    lock = _USER_LOCKS.get(user_id)
    if lock is None:
        lock = threading.Lock()
        _USER_LOCKS[user_id] = lock
    with lock:
        built = _build_tools_for_user(user_id)
        _USER_TOOLS_CACHE[user_id] = built
        _USER_TOOLS_EXPIRY[user_id] = time.time() + DEFAULT_TOOLS_CACHE_TTL_SECONDS
        return built

# 可选：动态设置TTL（全局）
def set_tools_cache_ttl(seconds: int) -> None:
    global DEFAULT_TOOLS_CACHE_TTL_SECONDS
    try:
        DEFAULT_TOOLS_CACHE_TTL_SECONDS = max(30, int(seconds))
    except Exception:
        warning("设置工具缓存TTL失败：参数非法，保持默认值")