# 导入系统模块
import sys
import os

# 将当前目录添加到Python路径中，确保模块可以被正确导入
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入所有拆分的模块
from db.db_connection import DatabaseConnection
from log import logger, debug, info, warning, error, critical, exception
from db.user_manager import UserManager
from db.chat_manager import ChatManager
from db.model_manager import ModelManager
from db.function_tool_manager import FunctionToolManager


# 修改设计模式，使用单一继承方式，避免多次初始化数据库连接，SQLite不允许在同一个连接中递归创建游标，所以避免页面初始化刷新创建游标，使用如下方式。
class ChatDatabase(DatabaseConnection):
    """聊天数据库类，集成所有数据库功能，保持向后兼容性"""
    
    def __init__(self, db_path="db.sqlite3"):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径
        """
        # 只初始化一次DatabaseConnection，避免在每个方法中重复初始化，导致SQLite错误，因为SQLite不允许在同一个连接中递归创建游标。
        super().__init__(db_path)
        
        logger.info("Database initialized successfully")
    
    # 从各个管理器类导入核心功能方法
    def register_user(self, username, password, role_id=2):
        manager = UserManager(self.db_path)
        # 共享当前连接，避免创建新连接
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.register_user(username, password, role_id)
        
    def login_user(self, username, password):
        manager = UserManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.login_user(username, password)
        
    def add_chat_record(self, user_message, plan, bot_response, user_id, model_name):
        manager = ChatManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.add_chat_record(user_message, plan, bot_response, user_id, model_name)
        
    def get_chat_history(self, user_id=None, limit=None):
        manager = ChatManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.get_chat_history(user_id, limit)
        
    def add_model(self, user_id, model_name, model_url, api_key=None, temperature=0.7, max_tokens=2048, desc=None):
        manager = ModelManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.add_model(user_id, model_name, model_url, api_key, temperature, max_tokens, desc)
        
    def get_all_models(self):
        manager = ModelManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.get_all_models()
        
    def delete_model(self, model_id):
        manager = ModelManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.delete_model(model_id)
        
    def get_all_function_tools(self, user_id):
        manager = FunctionToolManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.get_all_function_tools(user_id)
        
    def add_function_tool(self, user_id, tool_name, description, parameters, is_active=True, tool_flag=0, label='通用', code_content=None):
        manager = FunctionToolManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.add_function_tool(user_id=user_id, tool_name=tool_name, description=description, parameters=parameters, is_active=is_active, tool_flag=tool_flag, label=label, code_content=code_content)
        
    def get_user_info(self, user_id):
        manager = UserManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.get_user_info(user_id)
        
    def update_user_password(self, user_id, new_password):
        manager = UserManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.update_user_password(user_id, new_password)
        
    def change_user_role(self, user_id, role_id):
        manager = UserManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.change_user_role(user_id, role_id)
        
    def get_all_roles(self):
        manager = UserManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.get_all_roles()
        
    def change_user_lock_status(self, user_id, is_locked):
        manager = UserManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.change_user_lock_status(user_id, is_locked)
        
    def get_all_sessions(self, user_id=None):
        manager = ChatManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.get_all_sessions(user_id)
        
    def delete_chat_history(self, user_id=None):
        manager = ChatManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.delete_chat_history(user_id)
        
    def get_model_by_id(self, model_id):
        manager = ModelManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.get_model_by_id(model_id)

    def get_user_model_by_id(self, user_id):
        manager = ModelManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.get_user_model_by_id(user_id)
        
    def update_model(self, user_id, model_id, model_name=None, model_url=None, api_key=None, temperature=None, max_tokens=None, is_active=None, desc=None):
        manager = ModelManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.update_model(user_id, model_id, model_name, model_url, api_key, temperature, max_tokens, is_active, desc)
        
    def get_function_tool_by_id(self, user_id, tool_id):
        manager = FunctionToolManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.get_function_tool_by_id(user_id, tool_id)
        
    def get_function_tool_by_name(self, user_id, tool_name):
        manager = FunctionToolManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.get_function_tool_by_name(user_id, tool_name)
        
    def update_function_tool(self, user_id, tool_id, tool_name=None, description=None, parameters=None, is_active=None, tool_flag=None, label=None, code_content=None):
        manager = FunctionToolManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.update_function_tool(user_id, tool_id, tool_name, description, parameters, is_active, tool_flag, label, code_content)
        
    def delete_function_tool(self, user_id, tool_id):
        manager = FunctionToolManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.delete_function_tool(user_id, tool_id)
        
    def add_tool_execution(self, user_id, tool_id, tool_name, question=None, execution_steps=None, execution_params=None, execution_result=None, execution_status="success", start_time=None, end_time=None):
        manager = FunctionToolManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.add_tool_execution(user_id, tool_id, tool_name, question, execution_steps, execution_params, execution_result, execution_status, start_time, end_time)
        
    def update_tool_execution_result(self, execution_id, execution_result, execution_steps=None, execution_status='success'):
        manager = FunctionToolManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.update_tool_execution_result(execution_id, execution_result, execution_steps, execution_status)
        
    def get_tool_execution_by_id(self, execution_id):
        manager = FunctionToolManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.get_tool_execution_by_id(execution_id)
        
    def get_user_tool_executions(self, user_id, limit=50, offset=0):
        manager = FunctionToolManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.get_user_tool_executions(user_id, limit, offset)
        
    def get_tool_execution_history(self, tool_id, limit=50, offset=0):
        manager = FunctionToolManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.get_tool_execution_history(tool_id, limit, offset)
        
    def delete_tool_execution(self, execution_id):
        manager = FunctionToolManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.delete_tool_execution(execution_id)
    
    def delete_all_tool_execution(self, user_id):
        manager = FunctionToolManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.delete_all_tool_execution(user_id)
        
    def get_execution_statistics(self, user_id=None, tool_id=None, days=7):
        manager = FunctionToolManager(self.db_path)
        manager.conn = self.conn
        manager.cursor = self.cursor
        return manager.get_execution_statistics(user_id, tool_id, days)


# 确保全局数据库实例已初始化
global db
db = ChatDatabase()