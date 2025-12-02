from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from database import db
from log import logger, error
from tools_cache import get_tools_for_user
from models_cache import get_models_for_user
from .common import get_csrf_token

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET'])
def login_page():
    if 'user_id' in session:
        return redirect(url_for('main.index'))
    next_url = request.args.get('next', '/')
    return render_template('login.html', next=next_url, csrf_token=get_csrf_token())

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        is_json = 'application/json' in (request.headers.get('Content-Type') or '')
        data = request.get_json(silent=True) if is_json else request.form
        username = data.get('username')
        password = data.get('password')
        success, payload = db.login_user(username, password)
        if success:
            user_id = payload
            session['user_id'] = user_id
            session['username'] = username
            session.permanent = True
            try:
                # 预热工具与模型缓存，减少首次请求冷启动
                get_tools_for_user(user_id)
                get_models_for_user(user_id)
            except Exception:
                pass
            if is_json:
                return jsonify({'success': True})
            # 表单提交走页面跳转
            next_url = data.get('next') or url_for('main.index')
            return redirect(next_url)
        else:
            error_msg = payload or '用户名或密码错误'
            if is_json:
                return jsonify({'error': error_msg}), 401
            return render_template('login.html', error=error_msg, csrf_token=get_csrf_token(), next=data.get('next') or '/')
    except Exception as e:
        logger.error(f"登录失败: {str(e)}")
        if 'application/json' in (request.headers.get('Content-Type') or ''):
            return jsonify({'error': '登录失败'}), 500
        return render_template('login.html', error='登录失败，请稍后重试', csrf_token=get_csrf_token(), next=request.form.get('next') or '/')

@auth_bp.route('/register', methods=['GET'])
def register_page():
    if 'user_id' in session:
        return redirect(url_for('main.index'))
    return render_template('register.html', csrf_token=get_csrf_token())

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        is_json = 'application/json' in (request.headers.get('Content-Type') or '')
        data = request.get_json(silent=True) if is_json else request.form
        username = data.get('username')
        password = data.get('password')
        success, result = db.register_user(username, password)
        if success:
            session['user_id'] = result
            session['username'] = username
            session.permanent = True
            try:
                # 预热工具与模型缓存，减少首次请求冷启动
                get_tools_for_user(result)
                get_models_for_user(result)
            except Exception:
                pass
            if is_json:
                return jsonify({'success': True})
            return redirect(url_for('main.index'))
        else:
            if is_json:
                return jsonify({'error': result}), 400
            return render_template('register.html', error=result, csrf_token=get_csrf_token())
    except Exception as e:
        logger.error(f"注册失败: {str(e)}")
        if 'application/json' in (request.headers.get('Content-Type') or ''):
            return jsonify({'error': '注册失败'}), 500
        return render_template('register.html', error='注册失败，请稍后重试', csrf_token=get_csrf_token())

@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    try:
        session.clear()
        # POST/AJAX 返回 JSON，GET 直接跳转登录页，方便菜单链接使用
        if request.method == 'POST' or 'application/json' in (request.headers.get('Accept') or ''):
            return jsonify({'success': True})
        return redirect(url_for('auth.login_page'))
    except Exception as e:
        logger.error(f"登出失败: {str(e)}")
        if request.method == 'POST' or 'application/json' in (request.headers.get('Accept') or ''):
            return jsonify({'error': '登出失败'}), 500
        return redirect(url_for('main.index'))


@auth_bp.route('/api/user_profile', methods=['GET'])
def get_user_profile():
    """获取用户个人资料"""
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    try:
        user_id = session['user_id']
        # 使用数据库方法获取用户资料
        user_info = db.get_user_info(user_id)
        if not user_info:
            return jsonify({'error': '用户资料不存在'}), 404
        # 返回用户资料，注意不返回密码等敏感信息
        return jsonify({
            'user_id': user_info.get('user_id',user_id),
            'username': user_info.get('username'),
            'role': user_info.get('description'),
            'registration_date': user_info.get('created_at')
        })
    except Exception as e:
        logger.error(f"获取用户资料失败: {str(e)}")
        return jsonify({'error': '获取用户资料失败'}), 500