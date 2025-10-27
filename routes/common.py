from flask import request, jsonify, session, url_for
import functools
import secrets

# CSRF token utilities

def get_csrf_token():
    token = session.get('csrf_token')
    if not token:
        token = secrets.token_hex(32)
        session['csrf_token'] = token
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
    if request.method in ('POST', 'PUT', 'DELETE'):
        if request.path.startswith('/static/'):
            return
        token = None
        content_type = request.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            json_data = request.get_json(silent=True) or {}
            token = request.headers.get('X-CSRF-Token') or json_data.get('csrf_token')
        else:
            token = request.form.get('csrf_token')
        if not token or token != session.get('csrf_token'):
            return jsonify({'error': 'CSRF 校验失败'}), 403


def init_csrf(app):
    app.before_request(csrf_protect)