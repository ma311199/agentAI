from flask import request, jsonify, session, url_for, current_app
import functools
import secrets

# CSRF token utilities

def get_csrf_token():
    session_key = current_app.config.get('CSRF_SESSION_KEY', 'csrf_token')  # 会话中CSRF键名
    token = session.get(session_key)
    if not token:
        token = secrets.token_hex(32)
        session[session_key] = token
    return token

# Login required decorator

def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            from flask import redirect  # local import to avoid circular deps
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# CSRF protection

def csrf_protect():
    if not current_app.config.get('CSRF_ENABLED', True):
        return
    # 端点豁免（从配置读取）
    try:
        exempt = set(current_app.config.get('CSRF_EXEMPT_ENDPOINTS', []))
        if request.endpoint in exempt:
            return
    except Exception:
        pass
    if request.method in ('POST', 'PUT', 'DELETE'):
        if request.path.startswith('/static/'):
            return
        header_name = current_app.config.get('CSRF_HEADER_NAME', 'X-CSRF-Token')
        json_field = current_app.config.get('CSRF_JSON_FIELD', 'csrf_token')
        form_field = current_app.config.get('CSRF_FORM_FIELD', 'csrf_token')
        session_key = current_app.config.get('CSRF_SESSION_KEY', 'csrf_token')
        token = None
        content_type = request.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            json_data = request.get_json(silent=True) or {}
            token = request.headers.get(header_name) or json_data.get(json_field)
        else:
            token = request.form.get(form_field)
        if not token or token != session.get(session_key):
            return jsonify({'error': 'CSRF 校验失败'}), 403


def init_csrf(app):
    app.before_request(csrf_protect)