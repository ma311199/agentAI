from flask import Blueprint, request, jsonify, session
import json
import time
from database import db
from log import debug, info, warning, error, exception, log_api_call
from security_review import review_tool_code
# 新增：用于Python代码语法与依赖校验
import ast
import re
import importlib.util

# 简易合规校验：语法、函数名、参数匹配、依赖模块存在
def _extract_import_modules(tree: ast.AST):
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add((alias.name or '').split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mods.add(node.module.split('.')[0])
    return mods


def validate_python_tool(code: str, tool_name: str | None, parameters):
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"代码语法错误：{e}"

    # 如提供了工具名称，校验命名规则并确保存在同名函数定义
    if tool_name:
        name_val = str(tool_name).strip()
        if not name_val:
            return False, '工具名称为必填项'
        if name_val.startswith('_') or (not re.fullmatch(r'[A-Za-z_]+', name_val)) or (not re.search(r'[A-Za-z]', name_val)):
            return False, '工具名称不符合规则：只能包含英文字符和下划线，不能以下划线开头，且至少包含一个英文字符'
        func_def = None
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == name_val:
                func_def = node
                break
        if not func_def:
            return False, f'工具代码必须定义同名函数"{name_val}"'
        # 参数匹配（如提供了参数数组）
        try:
            arg_names = [a.arg for a in getattr(func_def.args, 'args', [])] + [a.arg for a in getattr(func_def.args, 'kwonlyargs', [])]
            param_list = []
            if isinstance(parameters, list):
                for p in parameters:
                    if isinstance(p, dict):
                        n = p.get('name') or p.get('param')
                        if n:
                            param_list.append(str(n))
            missing = [n for n in param_list if n not in arg_names]
            if param_list and missing:
                return False, '参数列表与函数签名不匹配，函数缺少参数: ' + ', '.join(missing)
        except Exception:
            pass

    # 依赖模块检查（静态import，不执行代码）
    missing_mods = []
    for m in _extract_import_modules(tree):
        try:
            spec = importlib.util.find_spec(m)
        except Exception:
            spec = None
        if spec is None:
            missing_mods.append(m)
    if missing_mods:
        return False, '缺少依赖模块：' + ', '.join(missing_mods) + '，请先安装或移除该依赖'

    return True, None


tools_bp = Blueprint('tools', __name__)

@tools_bp.route('/api/tools')
def get_tools():
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    tools = db.get_all_function_tools(session['user_id'])
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
    available_tools = [{**tool, 'parameters': _parse_params(tool.get('parameters'))} for tool in tools]
    return jsonify(available_tools)

@tools_bp.route('/api/tools', methods=['POST'])
def add_tool():
    start_time = time.time()
    user_id = session.get('user_id')
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    try:
        data = request.get_json()
        tool_name = data.get('tool_name')
        description = data.get('description', '')
        tool_type = data.get('tool_type', 'function')
        parameters = data.get('parameters')
        code_or_url = data.get('code_or_url', '')
        tool_flag = data.get('tool_flag')
        label = data.get('label')
        if not tool_name:
            return jsonify({'error': '工具名称为必填项'}), 400
        existing_tool = db.get_function_tool_by_name(user_id, tool_name)
        if existing_tool:
            log_api_call('/api/tools', 'POST', 400, user_id, (time.time() - start_time) * 1000)
            return jsonify({'error': '工具名称已存在'}), 400
        parameters_json = json.dumps(parameters) if parameters is not None else None
        if tool_flag is not None:
            try:
                tool_flag = int(tool_flag)
            except Exception:
                log_api_call('/api/tools', 'POST', 400, user_id, (time.time() - start_time) * 1000)
                return jsonify({'error': 'tool_flag必须为数字0或1'}), 400
            if tool_flag not in (0, 1):
                log_api_call('/api/tools', 'POST', 400, user_id, (time.time() - start_time) * 1000)
                return jsonify({'error': 'tool_flag必须为0（共享）或1（私有）'}), 400
        else:
            tool_flag = 0
        if label is not None:
            label = str(label).strip() or '通用'
        else:
            label = '通用'
        # 新增：Python代码合规校验（语法/函数名/参数/依赖）
        if tool_type == 'function' and isinstance(code_or_url, str) and code_or_url.strip():
            ok, msg = validate_python_tool(code_or_url, tool_name, parameters)
            if not ok:
                log_api_call('/api/tools', 'POST', 400, user_id, (time.time() - start_time) * 1000)
                warning(f"工具合规校验失败 - 用户ID: {user_id}, 工具名: {tool_name}, 错误: {msg}")
                return jsonify({'error': msg}), 400
            # 现有安全审查
            review = review_tool_code(code_or_url)
            if not review.get('safe', False):
                log_api_call('/api/tools', 'POST', 400, user_id, (time.time() - start_time) * 1000)
                warning(f"工具安全审查未通过 - 用户ID: {user_id}, 工具名: {tool_name}, 问题: {review.get('issues')}")
                return jsonify({'error': '安全审查未通过', 'issues': review.get('issues'), 'summary': review.get('summary')}), 400
        success, result = db.add_function_tool(
            user_id,
            tool_name,
            description,
            parameters_json,
            True,
            tool_flag=tool_flag,
            label=label,
            code_content=code_or_url
        )
        if success:
            log_api_call('/api/tools', 'POST', 201, user_id, (time.time() - start_time) * 1000)
            return jsonify({'success': True, 'tool_id': result})
        else:
            log_api_call('/api/tools', 'POST', 400, user_id, (time.time() - start_time) * 1000)
            return jsonify({'error': result}), 400
    except Exception as e:
        log_api_call('/api/tools', 'POST', 500, user_id, (time.time() - start_time) * 1000)
        error(f"添加工具异常 - 用户ID: {user_id}, 错误: {str(e)}")
        exception("添加工具异常")
        return jsonify({'error': '添加工具失败'}), 500

@tools_bp.route('/api/tools/<int:tool_id>', methods=['GET'])
def get_tool_by_id(tool_id):
    start_time = time.time()
    user_id = session.get('user_id')
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    try:
        tool_info = db.get_function_tool_by_id(user_id, tool_id)
        if not tool_info:
            log_api_call(f'/api/tools/{tool_id}', 'GET', 404, user_id, (time.time() - start_time) * 1000)
            return jsonify({'error': '工具不存在'}), 404
        params_val = tool_info.get('parameters')
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
        tool_info['parameters'] = _parse_params(params_val)
        log_api_call(f'/api/tools/{tool_id}', 'GET', 200, user_id, (time.time() - start_time) * 1000)
        return jsonify(tool_info)
    except Exception as e:
        log_api_call(f'/api/tools/{tool_id}', 'GET', 500, user_id, (time.time() - start_time) * 1000)
        error(f"获取工具异常 - 用户ID: {user_id}, 工具ID: {tool_id}, 错误: {str(e)}")
        exception("获取工具异常")
        return jsonify({'error': '获取工具失败，无权限'}), 500

@tools_bp.route('/api/tools/<int:tool_id>', methods=['PUT'])
def update_tool(tool_id):
    start_time = time.time()
    user_id = session.get('user_id')
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    try:
        data = request.get_json()
        tool_name = data.get('tool_name')
        description = data.get('description')
        parameters = data.get('parameters')
        is_active = data.get('is_active')
        code_or_url = data.get('code_or_url')
        tool_flag = data.get('tool_flag')
        label = data.get('label')
        parameters_json = json.dumps(parameters) if parameters is not None else None
        if tool_flag is not None:
            try:
                tool_flag = int(tool_flag)
            except Exception:
                log_api_call(f'/api/tools/{tool_id}', 'PUT', 400, user_id, (time.time() - start_time) * 1000)
                return jsonify({'error': 'tool_flag必须为数字0或1'}), 400
            if tool_flag not in (0, 1):
                log_api_call(f'/api/tools/{tool_id}', 'PUT', 400, user_id, (time.time() - start_time) * 1000)
                return jsonify({'error': 'tool_flag必须为0（共享）或1（私有）'}), 400
        if label is not None:
            label = str(label).strip()
        # 新增：更新时也进行Python代码合规与安全校验（如提交了代码）
        if isinstance(code_or_url, str) and code_or_url and code_or_url.strip():
            ok, msg = validate_python_tool(code_or_url, tool_name, parameters)
            if not ok:
                log_api_call(f'/api/tools/{tool_id}', 'PUT', 400, user_id, (time.time() - start_time) * 1000)
                warning(f"工具合规校验失败 - 用户ID: {user_id}, 工具ID: {tool_id}, 错误: {msg}")
                return jsonify({'error': msg}), 400
            review = review_tool_code(code_or_url)
            if not review.get('safe', False):
                log_api_call(f'/api/tools/{tool_id}', 'PUT', 400, user_id, (time.time() - start_time) * 1000)
                warning(f"工具安全审查未通过 - 用户ID: {user_id}, 工具ID: {tool_id}, 问题: {review.get('issues')}")
                return jsonify({'error': '安全审查未通过', 'issues': review.get('issues'), 'summary': review.get('summary')}), 400
        success = db.update_function_tool(
            user_id,
            tool_id,
            tool_name=tool_name,
            description=description,
            parameters=parameters_json,
            is_active=is_active,
            tool_flag=tool_flag,
            label=label,
            code_content=code_or_url
        )
        if success:
            log_api_call(f'/api/tools/{tool_id}', 'PUT', 200, user_id, (time.time() - start_time) * 1000)
            return jsonify({'message': '工具更新成功'})
        else:
            log_api_call(f'/api/tools/{tool_id}', 'PUT', 400, user_id, (time.time() - start_time) * 1000)
            return jsonify({'error': '更新失败或名称重复'}), 400
    except Exception as e:
        log_api_call(f'/api/tools/{tool_id}', 'PUT', 500, user_id, (time.time() - start_time) * 1000)
        error(f"更新工具异常 - 用户ID: {user_id}, 工具ID: {tool_id}, 错误: {str(e)}")
        exception("更新工具异常")
        return jsonify({'error': '更新工具失败'}), 500

@tools_bp.route('/api/tools/<int:tool_id>', methods=['DELETE'])
def delete_tool(tool_id):
    start_time = time.time()
    user_id = session.get('user_id')
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    try:
        tool_info = db.get_function_tool_by_id(user_id, tool_id)
        if not tool_info:
            log_api_call(f'/api/tools/{tool_id}', 'DELETE', 404, user_id, (time.time() - start_time) * 1000)
            return jsonify({'error': '工具不存在或无权限删除'}), 404
        success = db.delete_function_tool(user_id, tool_id)
        if success:
            log_api_call(f'/api/tools/{tool_id}', 'DELETE', 200, user_id, (time.time() - start_time) * 1000)
            return jsonify({'message': '工具删除成功'}), 200
        else:
            log_api_call(f'/api/tools/{tool_id}', 'DELETE', 400, user_id, (time.time() - start_time) * 1000)
            return jsonify({'error': '删除失败或无权限'}), 400
    except Exception as e:
        log_api_call(f'/api/tools/{tool_id}', 'DELETE', 500, user_id, (time.time() - start_time) * 1000)
        error(f"删除工具异常 - 用户ID: {user_id}, 工具ID: {tool_id}, 错误: {str(e)}")
        exception("删除工具异常")
        return jsonify({'error': str(e)}), 500