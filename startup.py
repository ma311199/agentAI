import json
from database import db
from log import debug, info, error, exception
from internal_tools import in_tools


def initialize_add_tool_and_admin():
    info("开始自动注册admin")
    try:
        db.register_user(username="admin", password="123456", role_id=1)
        info("admin用户注册成功")
    except Exception as e:
        error(f"admin用户注册失败: {str(e)}")
        exception("admin用户注册异常")
    info("开始自动注册内部工具")
    try:
        for tool in in_tools:
            debug(f"添加内部工具信息: {tool['tool_name']}")
            db.add_function_tool(
                user_id=1,
                tool_name=tool['tool_name'],
                description=tool['description'],
                parameters=json.dumps(tool['parameters']),
                tool_flag=0,
                label='通用',
                code_content=tool['function']
            )
        info(f"{len(in_tools)}个内部工具添加完成")
    except Exception as e:
        error(f"工具实例初始化失败: {str(e)}")
        exception("工具初始化异常")