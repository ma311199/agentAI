from flask import Blueprint, render_template, redirect, url_for, session, current_app
import time
import json
from database import db
from log import debug, info, warning, error, exception, log_api_call
from .common import login_required, get_csrf_token

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    start_time = time.time()
    user_id = session.get('user_id')
    try:
        tools = db.get_all_function_tools(user_id)
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
        user_info = db.get_user_info(session['user_id'])
        if not user_info:
            error(f"无法获取用户信息，用户ID: {session['user_id']}")
            session.clear()
            return redirect(url_for('auth.login'))
        models = db.get_user_model_by_id(user_id)
        response_time = (time.time() - start_time) * 1000
        log_api_call('/', 'GET', 200, user_id, response_time)
        return render_template('index.html', tools=available_tools, username=user_info['username'], models=models, csrf_token=get_csrf_token())
    except Exception as e:
        error(f"访问首页失败: {str(e)}")
        exception("首页访问异常")
        return render_template('login.html', error='系统内部错误，请稍后重试')

@main_bp.route('/@vite/client', methods=['GET'])
def vite_client():
    return current_app.response_class(response='', mimetype='application/javascript')