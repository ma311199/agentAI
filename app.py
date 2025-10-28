from flask import Flask
import os
from datetime import timedelta
from config import Config

# 蓝图模块
from routes.common import init_csrf
from routes.main import main_bp
from routes.auth import auth_bp
from routes.chat import chat_bp
from routes.models import models_bp
from routes.tools import tools_bp

# 启动初始化逻辑
from startup import initialize_add_tool_and_admin
from log import info


def create_app():
    app = Flask(__name__)
    # 从集中配置文件加载配置
    app.config.from_object(Config)

    # 注册CSRF保护
    init_csrf(app)

    # 注册蓝图
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(models_bp)
    app.register_blueprint(tools_bp)

    return app


if __name__ == '__main__':
    info("启动Flask应用服务...")
    app = create_app()
    initialize_add_tool_and_admin()
    info("Flask应用服务启动完成，监听地址: 0.0.0.0:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)

