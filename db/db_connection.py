import sqlite3
import os
import logging
from datetime import datetime
from log import logger, debug, info, warning, error, critical, exception
from config import Config



class DatabaseConnection:
    """数据库连接基类，处理数据库连接和基础操作"""
    
    def __init__(self, db_path=Config.DB_PATH):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self._ensure_connection()
        self._init_tables()
    
    def _ensure_connection(self):
        """确保数据库连接有效，如果无效则重新连接"""
        try:
            if self.conn is None:
                debug(f"建立数据库连接: {self.db_path}")
                self.conn = sqlite3.connect(self.db_path, check_same_thread=Config.DB_CHECK_SAME_THREAD)
                try:
                    self.conn.execute("PRAGMA journal_mode=WAL")
                    self.conn.execute("PRAGMA busy_timeout=3000")
                except Exception:
                    pass
                self.cursor = self.conn.cursor()
            else:
                with self.conn:
                    self.conn.execute("SELECT 1")
        except sqlite3.Error as e:
            exception(f"数据库连接错误: {e}")
            self.conn = sqlite3.connect(self.db_path, check_same_thread=Config.DB_CHECK_SAME_THREAD)
            try:
                self.conn.execute("PRAGMA journal_mode=WAL")
                self.conn.execute("PRAGMA busy_timeout=3000")
            except Exception:
                pass
            self.cursor = self.conn.cursor()
    
    def _init_tables(self):
        """初始化基础表结构"""
        try:
            self._ensure_connection()
            
            # 创建角色表
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS roles (
                    role_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role_name TEXT UNIQUE NOT NULL,
                    description TEXT
                )
            ''')
            
            # 插入默认角色
            self.cursor.execute("SELECT COUNT(*) FROM roles")
            if self.cursor.fetchone()[0] == 0:
                self.cursor.execute("INSERT INTO roles (role_name, description) VALUES (?, ?)", 
                                   ('admin', '管理员'))
                self.cursor.execute("INSERT INTO roles (role_name, description) VALUES (?, ?)", 
                                   ('user', '普通用户'))
            
            # 创建用户表
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role_id INTEGER DEFAULT 2,
                    is_locked INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (role_id) REFERENCES roles (role_id)
                )
            ''')
            
            # 创建模型信息表
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS model_info (
                    user_id INTEGER NOT NULL,
                    model_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL UNIQUE,
                    model_url TEXT NOT NULL,
                    api_key TEXT,
                    temperature REAL NOT NULL DEFAULT 0.7,
                    max_tokens INTEGER NOT NULL DEFAULT 2048,
                    add_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    desc TEXT,
                    model_flag INTEGER NOT NULL DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # 创建对话记录表
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    model_name TEXT NOT NULL,
                    plan TEXT NOT NULL,
                    user_message TEXT NOT NULL,
                    bot_response TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # 创建函数工具表
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS function_tools (
                    user_id INTEGER NOT NULL,
                    tool_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool_name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    parameters TEXT,
                    is_active INTEGER DEFAULT 1,
                    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    tool_flag INTEGER DEFAULT 0,
                    label TEXT DEFAULT '通用',
                    code_content TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # 创建函数工具执行记录表
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS function_tool_executions (
                    execution_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    tool_id INTEGER,
                    tool_name TEXT NOT NULL,
                    question TEXT,
                    execution_steps TEXT,
                    execution_params TEXT,
                    execution_result TEXT,
                    execution_status TEXT DEFAULT 'success',
                    start_time TIMESTAMP,
                    end_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (tool_id) REFERENCES function_tools (tool_id)
                )
            ''')
            
            self.conn.commit()
            debug("数据库表初始化完成")
        except Exception as e:
            exception(f"初始化数据库表时出错: {e}")
    
    def close(self):
        """关闭数据库连接"""
        try:
            if self.conn:
                self.conn.close()
                self.conn = None
                self.cursor = None
                debug("数据库连接已关闭")
        except Exception as e:
            exception(f"关闭数据库连接时出错: {e}")
    
    def delete_database(self):
        """删除数据库文件（谨慎使用）"""
        try:
            self.close()
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
                info(f"数据库文件已删除: {self.db_path}")
                return True
            else:
                warning(f"数据库文件不存在: {self.db_path}")
                return False
        except Exception as e:
            exception(f"删除数据库文件时出错: {e}")
            return False
