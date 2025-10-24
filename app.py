from flask import Flask, request, render_template, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash as verify_password
import os
import json
import time
import functools
import agent
from llmclient import LLMClient
from openai import OpenAI
from tool_process import Toolregister
from agent import ReactAgent
from tools import Tool
from database import db  # 导入数据库实例
from log import logger, debug, info, warning, error, critical, exception, log_user_action, log_api_call, log_db_operation
from internal_tools import in_tools
from security_review import review_tool_code
import secrets


app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-change-mm')  # 用于会话管理的密钥，为 Flask 的 session 、 flash 等生成签名，防止被篡改。更换秘钥会使所有现有会话失效（用户会被退出登录），生产环境谨慎操作。
app.config['SESSION_COOKIE_SECURE'] = False  # 仅在 HTTPS 连接上发送 cookie
app.config['SESSION_COOKIE_HTTPONLY'] = True # 仅通过 HTTP(S) 请求发送 cookie，防止 JavaScript 访问
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # 降低 CSRF 风险

# 生成并获取 CSRF Token（保存在会话中）
def get_csrf_token():
    token = session.get('csrf_token')
    if not token:
        token = secrets.token_hex(32)
        session['csrf_token'] = token
    return token

# 简易 CSRF 保护：拦截所有修改类请求
@app.before_request
def csrf_protect():
    if request.method in ('POST', 'PUT', 'DELETE'):
        # 静态文件忽略
        if request.path.startswith('/static/'):
            return
        # 登录/注册等表单使用 form 字段；JSON 接口使用 header 或 json 字段
        token = None
        content_type = request.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            json_data = request.get_json(silent=True) or {}
            token = request.headers.get('X-CSRF-Token') or json_data.get('csrf_token')
        else:
            token = request.form.get('csrf_token')
        if not token or token != session.get('csrf_token'):
            return jsonify({'error': 'CSRF 校验失败'}), 403

# 登录检查装饰器（需在使用 @login_required 之前定义）
def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# 首次初始化工具实例，且添加内部函数工具到数据库
def  initialize_add_tool_and_admin():
    """初始化管理员和内部工具实例"""
    info("开始自动注册admin")
    try:
        db.register_user(username="admin", password="123456", role_id=1) # 注册admin管理员用户，进入系统修改账号密码
        info("admin用户注册成功")
    except Exception as e:
        error(f"admin用户注册失败: {str(e)}")
        exception("admin用户注册异常")
    info("开始自动注册内部工具")
    try:
        for tool in in_tools:
            debug(f"添加内部工具信息: {tool['tool_name']}")
            db.add_function_tool(user_id=1, tool_name=tool['tool_name'], description=tool['description'], parameters=str(tool['parameters']), tool_flag=0, label='通用', code_content=tool['function']) # 添加内部所有工具到数据库
        info(f"{len(in_tools)}个内部工具添加完成")
    except Exception as e:
        error(f"工具实例初始化失败: {str(e)}")
        exception("工具初始化异常")


        

@app.route('/')
@login_required
def index():
    """主页面"""
    start_time = time.time()
    user_id = session.get('user_id')
    
    try:       
        # 获取可用工具信息
        tools = db.get_all_function_tools(user_id)

        available_tools = [{**tool, 'parameters': eval(tool['parameters'])} for tool in tools]
        # 获取当前用户信息
        user_info = db.get_user_info(session['user_id'])
        
        # 检查用户信息是否获取成功
        if not user_info:
            error(f"无法获取用户信息，用户ID: {session['user_id']}")
            # 清除会话并重定向到登录页面
            session.clear()
            return redirect(url_for('login'))
        
        # 获取对应用户权限下的所有模型信息
        models = db.get_user_model_by_id(user_id)
        # 这里可以再加一个判断，如果是管理员，可以获取所有模型信息
        
        response_time = (time.time() - start_time) * 1000
        log_api_call('/', 'GET', 200, user_id, response_time)
        

        return render_template('index.html', tools=available_tools, username=user_info['username'], models=models, csrf_token=get_csrf_token())
    except Exception as e:
        error(f"访问首页失败: {str(e)}")
        exception("首页访问异常")
        return render_template('login.html', error='系统内部错误，请稍后重试')
    

@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'POST':
        start_time = time.time()
        username = request.form['username']
        password = request.form['password']
        next_url = request.form.get('next', '/')
        
        info(f"用户登录尝试 - 用户名: {username}")
        
        try:
            # 调用数据库中的登录方法
            success, result = db.login_user(username, password)
            
            if success:
                # 登录成功，设置会话
                session['user_id'] = result
                session['username'] = username
                log_user_action(username, 'login', '登录成功')
                log_api_call('/login', 'POST', 302, username)
                info(f"用户登录成功 - 用户ID: {result}, 用户名: {username}")
                return redirect(next_url)
            else:
                # 登录失败，显示错误信息
                log_user_action(username, 'login', f'登录失败: {result}')
                log_api_call('/login', 'POST', 200, username, (time.time() - start_time) * 1000)
                warning(f"用户登录失败 - 用户名: {username}, 原因: {result}")
                return render_template('login.html', error=result, next=next_url)
        except Exception as e:
            error(f"登录处理异常 - 用户名: {username}, 错误: {str(e)}")
            exception("登录异常")
            return render_template('login.html', error='系统内部错误，请稍后重试', next=next_url)
    
    # GET请求，显示登录页面
    next_url = request.args.get('next', '/')
    log_api_call('/login', 'GET', 200)
    return render_template('login.html', next=next_url, csrf_token=get_csrf_token())

@app.route('/register', methods=['GET', 'POST'])
def register():
    """注册页面"""
    if request.method == 'POST':
        start_time = time.time()
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        info(f"用户注册尝试 - 用户名: {username}")
        
        try:
            # 验证密码一致性
            if password != confirm_password:
                log_api_call('/register', 'POST', 200, None, (time.time() - start_time) * 1000)
                warning(f"注册失败 - 用户名: {username}, 原因: 密码不一致")
                return render_template('register.html', error='两次输入的密码不一致')
            
            # 调用数据库中的注册方法
            success, result = db.register_user(username, password)
            
            if success:
                 # 注册成功，设置会话并重定向到登录页
                 session['user_id'] = result
                 session['username'] = username
                 log_user_action(username, 'register', '注册成功')
                 log_api_call('/register', 'POST', 302, username, (time.time() - start_time) * 1000)
                 info(f"用户注册成功 - 用户ID: {result}, 用户名: {username}")
                 return redirect(url_for('login'))
            else:
                # 注册失败，显示错误信息
                log_api_call('/register', 'POST', 200, None, (time.time() - start_time) * 1000)
                warning(f"用户注册失败 - 用户名: {username}, 原因: {result}")
                return render_template('register.html', error=result)
        except Exception as e:
            error(f"注册处理异常 - 用户名: {username}, 错误: {str(e)}")
            exception("注册异常")
            return render_template('register.html', error='系统内部错误，请稍后重试')
    
    # GET请求，显示注册页面
    log_api_call('/register', 'GET', 200)
    return render_template('register.html', csrf_token=get_csrf_token())

@app.route('/logout')
def logout():
    """登出功能"""
    username = session.get('username', '未知用户')
    user_id = session.get('user_id', '未知ID')
    
    session.clear()
    log_user_action(username, 'logout', '用户登出')
    info(f"用户登出 - 用户ID: {user_id}, 用户名: {username}")
    
    return redirect(url_for('login'))


@app.route('/api/chat', methods=['POST'])
def chat():
    """处理用户聊天请求"""
    start_time = time.time()
    user_id = session.get('user_id')
    username = session.get('username')
    
    # 检查登录状态
    if 'user_id' not in session:
        log_api_call('/api/chat', 'POST', 401)
        return jsonify({'error': '未登录'}), 401
        
    data = request.json
    user_input = data.get('message', '')
    session_id = data.get('session_id', 'default')
    model_id = data.get('model_id')
    
    if not user_input:
        log_api_call('/api/chat', 'POST', 400, user_id, (time.time() - start_time) * 1000)
        return jsonify({'error': '消息不能为空'}), 400
    tool = Toolregister()
    tools = db.get_all_function_tools(user_id)
    for tool_info in tools:
        tool.register_tool(tool_info['tool_name'], tool_info['description'], tool_info['code_content'], eval(tool_info['parameters']))
    try:
        # 根据model_id选择模型
        if model_id:
            # 获取指定模型信息（移除对 'default' 的特殊处理）
            model_info = db.get_model_by_id(model_id)
            if model_info and model_info['is_active']:
                debug(f"使用指定模型: {model_info['model_name']} (ID: {model_id})")
                llm_client = LLMClient(
                    url=model_info['model_url'],
                    model=model_info['model_name'],
                    api_key=model_info['api_key'] or "",
                    timeout=30
                )
                t_agent = ReactAgent(llm=llm_client, tools=tool.tools)
                plan_text, response_text = t_agent.process_query(user_id, user_input, model_info['model_name'])
            else:
                error(f"模型不存在或未启用: {model_id}")
                plan_text = "模型选择无效"
                response_text = "所选模型不存在或未启用，请选择其他模型。"
        else:
            # 未选择模型，直接返回错误
            log_api_call('/api/chat', 'POST', 400, user_id, (time.time() - start_time) * 1000)
            return jsonify({'error': '未选择模型，请在左侧启用并选择模型后再发送'}), 400

        
        log_db_operation('insert', 'chat_records', 'success', f'用户ID: {user_id}, 会话ID: {session_id}')
        log_api_call('/api/chat', 'POST', 200, user_id, (time.time() - start_time) * 1000)
        debug(f"聊天请求处理完成 - 用户ID: {user_id}, 用户名: {username}, 会话ID: {session_id}")

        response = {'response': plan_text+"\n最终回复："+response_text}
        return jsonify(response)
    except Exception as e:
        log_api_call('/api/chat', 'POST', 500, user_id, (time.time() - start_time) * 1000)
        error(f"聊天处理异常 - 用户ID: {user_id}, 错误: {str(e)}")
        exception("聊天处理异常")
        return jsonify({'error': str(e)}), 500


@app.route('/api/clear_memory', methods=['POST'])
def clear_memory():
    """清除记忆"""
    # 检查登录状态
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
        
    try:

        # 获取要清除的记忆类型
        data = request.json
        memory_type = data.get('type', 'all')
        
        # 验证memory_type参数
        valid_types = ['short', 'execution', 'all']
        if memory_type not in valid_types:
            return jsonify({'error': '无效的记忆类型'}), 400
        
        # 根据清除的类型返回不同的消息
        if memory_type == 'short':
            deleted_count = db.delete_chat_history(session['user_id'])
            if deleted_count >= 0:
                response_text = '✅ 对话记录已清除'
            else:
                raise Exception('清除对话记录失败')
        elif memory_type == 'execution':
            success = db.delete_all_tool_execution(session['user_id'])
            if success:
                response_text = '✅ 工具执行历史已清除'
            else:
                raise Exception('清除工具执行历史失败')
        else:
            # 清除所有记忆
            chat_deleted = db.delete_chat_history(session['user_id']) >= 0
            execution_deleted = db.delete_all_tool_execution(session['user_id'])
            if chat_deleted and execution_deleted:
                response_text = '✅ 所有记忆已清除'
            else:
                raise Exception('清除所有记忆失败')
        
        response = {'response': response_text}
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/user_profile')
def get_user_profile():
    """获取用户个人资料信息"""
    # 检查登录状态
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
        
    try:
        # 从数据库获取用户信息
        user_info = db.get_user_info(session['user_id'])
        print("获取的信息：",user_info)
        # 返回用户信息，包括用户名、角色和注册日期
        response = {
            'username': user_info.get('username', '未知用户'),
            'role': user_info.get('description', '普通用户'),
            'registration_date': str(user_info.get('created_at', '未知')),
            'last_login': '今天'  # 可以在后续优化为真实的最后登录时间
        }
        
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/change_password', methods=['POST'])
def change_password():
    """修改用户密码"""
    # 检查登录状态
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    
    try:
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'error': '当前密码和新密码不能为空'}), 400
        
        # 获取用户信息
        user_info = db.get_user_info(session['user_id'])
        if not user_info:
            return jsonify({'error': '用户不存在'}), 404
        
        # 验证当前密码：通过尝试登录来验证
        username = user_info['username']
        login_success, result = db.login_user(username, current_password)
        if not login_success:
            return jsonify({'error': '当前密码错误'}), 401

        # 直接使用新密码（update_user_password方法内部会进行哈希处理）
        if db.update_user_password(session['user_id'], new_password):
            return jsonify({'success': True})
        else:
            return jsonify({'error': '密码更新失败'}), 500
    except Exception as e:
        error(f"修改密码失败: {str(e)}")
        return jsonify({'error': '服务器内部错误'}), 500

@app.route('/api/chat_history', methods=['GET'])
def get_chat_history():
    """获取用户的对话历史"""
    # 检查登录状态
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
        
    try:
        session_id = request.args.get('session_id', 'default')
        limit = request.args.get('limit', 10, type=int) # 默认限制为10条.可以指定limit参数来获取更多或更少的记录
        
        history = db.get_chat_history(
            user_id=session['user_id'],
            limit=limit
        )
        response = "📝 **记忆摘要**\n\n展示最近的10次对话历史记录：\n"
        if not history:
            response += "**没有找到对话历史记录。**"
        else:
            for i, record in enumerate(history, 1):
                response += f"记忆 ({i})->模型：{record['model_name']} 【用户问题：“{record['user_message']}”；AGENT回答：“{record['bot_response']}”】\n"; 
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/@vite/client', methods=['GET'])
def vite_client():
    """可能是由于浏览器或前端框架自动尝试加载Vite开发工具导致的请求，处理Vite客户端请求，避免404错误"""
    return app.response_class(response='', mimetype='application/javascript')

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """获取用户的所有会话"""
    # 检查登录状态
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
        
    try:
        sessions = db.get_all_sessions(user_id=session['user_id'])
        return jsonify({'sessions': sessions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 模型管理相关API

# moved: /api/models/available defined earlier near the model API header
@app.route('/api/models', methods=['GET'])
@login_required
def get_models():
    try:
        models = db.get_user_model_by_id(session['user_id'])
        # 直接返回models，因为它已经是字典列表格式
        return jsonify({'models': models})
    except Exception as e:
        app.logger.error(f"获取模型列表失败: {str(e)}")
        return jsonify({'error': '获取模型列表失败'}), 500

@app.route('/api/models/<int:modelId>', methods=['GET'])
@login_required
def get_model(modelId):
    try:
        model = db.get_model_by_id(modelId)
        if model:
            # 直接返回字典，因为database.py中的get_model_by_id已经返回字典格式
            return jsonify(model)
        else:
            return jsonify({'error': '模型不存在'}), 404
    except Exception as e:
        app.logger.error(f"获取模型信息失败: {str(e)}")
        return jsonify({'error': '获取模型信息失败'}), 500

@app.route('/api/models', methods=['POST'])
@login_required
def add_model():
    try:
        data = request.get_json()
        model_name = data.get('model_name')
        model_url = data.get('model_url')
        api_key = data.get('api_key')
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens', 4096)
        desc = data.get('desc', "暂无")
        
        if not model_name or not model_url or not api_key:
            return jsonify({'error': '模型名称、地址和API Key为必填项'}), 400
        
        success, result = db.add_model(session['user_id'], model_name, model_url, api_key, temperature, max_tokens, desc)
        
        if success:
            return jsonify({'success': True, 'model_id': result})
        else:
            return jsonify({'error': result}), 400
    except Exception as e:
        app.logger.error(f"添加模型失败: {str(e)}")
        return jsonify({'error': '添加模型失败'}), 500

@app.route('/api/models/<int:model_id>', methods=['PUT'])
@login_required
def update_model(model_id):
    try:
        data = request.get_json()
        
        # 获取更新字段
        model_name = data.get('model_name')
        model_url = data.get('model_url')
        api_key = data.get('api_key')
        temperature = data.get('temperature')
        max_tokens = data.get('max_tokens')
        is_active = data.get('is_active')
        desc = data.get('desc')
        
        # 如果只是更新is_active字段，则不需要其他必填项
        if 'is_active' in data and model_name is None and model_url is None and api_key is None:
            # 只更新启用状态
            success = db.update_model(
                user_id=session['user_id'],
                model_id=model_id,
                is_active=is_active
            )
        else:
            # 完整更新需要必填项
            if not model_name or not model_url or not api_key:
                return jsonify({'error': '模型名称、地址和API Key为必填项'}), 400
            
            success = db.update_model(
                user_id=session['user_id'],
                model_id=model_id,
                model_name=model_name,
                model_url=model_url,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
                is_active=is_active,
                desc=desc
            )
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': '模型不存在或更新失败'}), 404
    except Exception as e:
        app.logger.error(f"更新模型失败: {str(e)}")
        return jsonify({'error': '更新模型失败'}), 500

@app.route('/api/models/<int:model_id>', methods=['DELETE'])
@login_required
def delete_model(model_id):
    try:
        success = db.delete_model(model_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': '模型不存在'}), 404
    except Exception as e:
        app.logger.error(f"删除模型失败: {str(e)}")
        return jsonify({'error': '删除模型失败'}), 500

# 工具管理相关API
@app.route('/api/execution_history', methods=['GET'])
def get_execution_history_api():
    """获取当前用户的工具执行历史"""
    start_time = time.time()
    # 检查登录状态
    if 'user_id' not in session:
        log_api_call('/api/execution_history', 'GET', 401)
        return jsonify({'error': '未登录'}), 401

    try:
        user_id = session['user_id']
        limit = request.args.get('limit', 10, type=int)
        tool_history = db.get_user_tool_executions(user_id=user_id, limit=limit)
        # 格式化为前端main.js期望的结构
        result_list = []
        for i, record in enumerate(tool_history, 1):
            execution_result = str(record.get('execution_result', ''))
            truncated_result = execution_result[:100] + ('...' if len(execution_result) > 100 else '')
            result_list.append({
                'index': i,
                'question': record.get('question'),
                'tool_name': record.get('tool_name'),
                'params': record.get('execution_params'),
                'start_time': record.get('start_time'),
                'end_time': record.get('end_time'),
                'result': truncated_result
            })
        log_api_call('/api/execution_history', 'GET', 200, user_id, (time.time() - start_time) * 1000)
        return jsonify({'response': result_list})
    except Exception as e:
        error(f"获取执行历史异常 - 用户ID: {session.get('user_id')}, 错误: {str(e)}")
        exception("获取执行历史异常")
        log_api_call('/api/execution_history', 'GET', 500, session.get('user_id'), (time.time() - start_time) * 1000)
        return jsonify({'error': '获取执行历史失败'}), 500

@app.route('/api/tools')
def get_tools():
    """获取可用工具列表"""
    # 检查登录状态
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401

    tools = db.get_all_function_tools(session['user_id'])
    available_tools = [{**tool, 'parameters': eval(tool['parameters'])} for tool in tools]
    return jsonify(available_tools)

@app.route('/api/tools', methods=['POST'])
@login_required
def add_tool():
    """添加新工具"""
    start_time = time.time()
    user_id = session.get('user_id')
    
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
        
        # 检查名称是否已存在
        existing_tool = db.get_function_tool_by_name(user_id,tool_name)
        if existing_tool:
            log_api_call('/api/tools', 'POST', 400, user_id, (time.time() - start_time) * 1000)
            return jsonify({'error': '工具名称已存在'}), 400
        
        # 将参数定义转换为字符串
        parameters_json = str(parameters)

        # 校验tool_flag（0共享，1私有），可选
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
            tool_flag = 0  # 默认共享

        # 规范化label，可选
        if label is not None:
            label = str(label).strip() or '通用'
        else:
            label = '通用'

        # 安全性代码审查（仅针对函数型工具且提交了代码字符串）
        if tool_type == 'function' and isinstance(code_or_url, str) and code_or_url.strip():
            review = review_tool_code(code_or_url)
            if not review.get('safe', False):
                log_api_call('/api/tools', 'POST', 400, user_id, (time.time() - start_time) * 1000)
                warning(f"工具安全审查未通过 - 用户ID: {user_id}, 工具名: {tool_name}, 问题: {review.get('issues')}")
                return jsonify({'error': '安全审查未通过', 'issues': review.get('issues'), 'summary': review.get('summary')}), 400
        
        # 添加工具到数据库（支持tool_flag与label）
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

# 新增：获取指定工具详情
@app.route('/api/tools/<int:tool_id>', methods=['GET'])
@login_required
def get_tool_by_id(tool_id):
    start_time = time.time()
    user_id = session.get('user_id')
    try:
        tool_info = db.get_function_tool_by_id(user_id, tool_id)
        if not tool_info:
            log_api_call(f'/api/tools/{tool_id}', 'GET', 404, user_id, (time.time() - start_time) * 1000)
            return jsonify({'error': '工具不存在'}), 404
        # 解析参数为列表
        params_val = tool_info.get('parameters')
        try:
            parsed_params = eval(params_val) if isinstance(params_val, str) else params_val
        except Exception:
            parsed_params = None
        tool_info['parameters'] = parsed_params
        log_api_call(f'/api/tools/{tool_id}', 'GET', 200, user_id, (time.time() - start_time) * 1000)
        return jsonify(tool_info)
    except Exception as e:
        log_api_call(f'/api/tools/{tool_id}', 'GET', 500, user_id, (time.time() - start_time) * 1000)
        error(f"获取工具异常 - 用户ID: {user_id}, 工具ID: {tool_id}, 错误: {str(e)}")
        exception("获取工具异常")
        return jsonify({'error': '获取工具失败，无权限'}), 500

# 新增：更新指定工具
@app.route('/api/tools/<int:tool_id>', methods=['PUT'])
@login_required
def update_tool(tool_id):
    start_time = time.time()
    user_id = session.get('user_id')
    try:
        data = request.get_json()
        tool_name = data.get('tool_name')
        description = data.get('description')
        parameters = data.get('parameters')
        is_active = data.get('is_active')
        code_or_url = data.get('code_or_url')
        tool_flag = data.get('tool_flag')
        label = data.get('label')

        # 把参数转字符串保存
        parameters_json = str(parameters) if parameters is not None else None

        # 校验tool_flag（0共享，1私有），可选
        if tool_flag is not None:
            try:
                tool_flag = int(tool_flag)
            except Exception:
                log_api_call(f'/api/tools/{tool_id}', 'PUT', 400, user_id, (time.time() - start_time) * 1000)
                return jsonify({'error': 'tool_flag必须为数字0或1'}), 400
            if tool_flag not in (0, 1):
                log_api_call(f'/api/tools/{tool_id}', 'PUT', 400, user_id, (time.time() - start_time) * 1000)
                return jsonify({'error': 'tool_flag必须为0（共享）或1（私有）'}), 400

        # 规范化label，可选
        if label is not None:
            label = str(label).strip()

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

@app.route('/api/tools/<int:tool_id>', methods=['DELETE'])
@login_required
def delete_tool(tool_id):
    """删除指定ID的工具"""
    start_time = time.time()
    user_id = session.get('user_id')
    
    try:
        # 获取工具信息
        tool_info = db.get_function_tool_by_id(user_id,tool_id)
        if not tool_info:
            log_api_call(f'/api/tools/{tool_id}', 'DELETE', 404, user_id, (time.time() - start_time) * 1000)
            return jsonify({'error': '工具删除失败，创建者可删除'}), 404
        
        # 从数据库中删除工具
        success, result = db.delete_function_tool(user_id,tool_id)
        if success:
            # 同时从全局tool对象中删除对应的工具
            log_api_call(f'/api/tools/{tool_id}', 'DELETE', 200, user_id, (time.time() - start_time) * 1000)
            return jsonify({'message': '工具删除成功'}), 200
        else:
            log_api_call(f'/api/tools/{tool_id}', 'DELETE', 400, user_id, (time.time() - start_time) * 1000)
            return jsonify({'error': result}), 400
            
    except Exception as e:
        log_api_call(f'/api/tools/{tool_id}', 'DELETE', 500, user_id, (time.time() - start_time) * 1000)
        error(f"删除工具异常 - 用户ID: {user_id}, 工具ID: {tool_id}, 错误: {str(e)}")
        exception("删除工具异常")
        return jsonify({'error': str(e)}), 500

@app.route('/api/models/available', methods=['POST'])
@login_required
def get_available_models():
    try:
        data = request.get_json() or {}
        model_url = data.get('model_url')
        api_key = data.get('api_key')
        if not model_url or not api_key:
            return jsonify({'error': '模型地址和API Key为必填项'}), 400
        try:
            client = OpenAI(base_url=model_url, api_key=api_key)
            resp = client.models.list()
        except Exception as e:
            app.logger.error(f"调用模型列表失败: {str(e)}")
            return jsonify({'error': f'调用模型列表失败: {str(e)}'}), 400
        names = []
        try:
            for m in getattr(resp, 'data', []):
                mid = getattr(m, 'id', None)
                if mid:
                    names.append(mid)
        except Exception:
            pass
        if not names:
            try:
                data_list = resp.get('data', []) if isinstance(resp, dict) else []
                for m in data_list:
                    mid = m.get('id') or m.get('model')
                    if mid:
                        names.append(mid)
            except Exception:
                pass
        return jsonify({'models': names})
    except Exception as e:
        app.logger.error(f"获取可用模型失败: {str(e)}")
        return jsonify({'error': '获取可用模型失败'}), 500

if __name__ == '__main__':
    info("启动Flask应用服务...")
    initialize_add_tool_and_admin()
    info("Flask应用服务启动完成，监听地址: 0.0.0.0:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)

