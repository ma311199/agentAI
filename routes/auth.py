from flask import Blueprint, request, render_template, jsonify, session, redirect, url_for
import time
from database import db
from log import info, warning, error, exception, log_user_action, log_api_call
from .common import get_csrf_token

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        start_time = time.time()
        username = request.form['username']
        password = request.form['password']
        next_url = request.form.get('next', '/')
        info(f"用户登录尝试 - 用户名: {username}")
        try:
            success, result = db.login_user(username, password)
            if success:
                session['user_id'] = result
                session['username'] = username
                log_user_action(username, 'login', '登录成功')
                log_api_call('/login', 'POST', 302, username)
                info(f"用户登录成功 - 用户ID: {result}, 用户名: {username}")
                return redirect(next_url)
            else:
                log_user_action(username, 'login', f'登录失败: {result}')
                log_api_call('/login', 'POST', 200, username, (time.time() - start_time) * 1000)
                warning(f"用户登录失败 - 用户名: {username}, 原因: {result}")
                return render_template('login.html', error=result, next=next_url)
        except Exception as e:
            error(f"登录处理异常 - 用户名: {username}, 错误: {str(e)}")
            exception("登录异常")
            return render_template('login.html', error='系统内部错误，请稍后重试', next=next_url)
    next_url = request.args.get('next', '/')
    log_api_call('/login', 'GET', 200)
    return render_template('login.html', next=next_url, csrf_token=get_csrf_token())

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        start_time = time.time()
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        info(f"用户注册尝试 - 用户名: {username}")
        try:
            if password != confirm_password:
                log_api_call('/register', 'POST', 200, None, (time.time() - start_time) * 1000)
                warning(f"注册失败 - 用户名: {username}, 原因: 密码不一致")
                return render_template('register.html', error='两次输入的密码不一致')
            success, result = db.register_user(username, password)
            if success:
                session['user_id'] = result
                session['username'] = username
                log_user_action(username, 'register', '注册成功')
                log_api_call('/register', 'POST', 302, username, (time.time() - start_time) * 1000)
                info(f"用户注册成功 - 用户ID: {result}, 用户名: {username}")
                return redirect(url_for('auth.login'))
            else:
                log_api_call('/register', 'POST', 200, None, (time.time() - start_time) * 1000)
                warning(f"用户注册失败 - 用户名: {username}, 原因: {result}")
                return render_template('register.html', error=result)
        except Exception as e:
            error(f"注册处理异常 - 用户名: {username}, 错误: {str(e)}")
            exception("注册异常")
            return render_template('register.html', error='系统内部错误，请稍后重试')
    log_api_call('/register', 'GET', 200)
    return render_template('register.html', csrf_token=get_csrf_token())

@auth_bp.route('/logout')
def logout():
    username = session.get('username', '未知用户')
    user_id = session.get('user_id', '未知ID')
    session.clear()
    log_user_action(username, 'logout', '用户登出')
    info(f"用户登出 - 用户ID: {user_id}, 用户名: {username}")
    return redirect(url_for('auth.login'))