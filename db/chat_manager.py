from .db_connection import DatabaseConnection
from log import logger, debug, info, warning, error, critical, exception
from datetime import datetime


class ChatManager(DatabaseConnection):
    """对话管理模块，处理对话历史相关的所有操作"""
    
    def add_chat_record(self, user_message, plan, bot_response, user_id=None):
        """
        添加对话记录
        
        Args:
            user_message: 用户消息
            plan: 执行计划
            bot_response: 机器人回复
            user_id: 用户ID（可选）
            
        Returns:
            int: 记录ID，如果失败返回-1
        """
        try:
            self._ensure_connection()
            
            # 获取当前时间
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 插入对话记录
            self.cursor.execute(
                "INSERT INTO chat_history (user_id, user_message, plan, bot_response, timestamp) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, user_message, plan, bot_response, current_time)
            )
            self.conn.commit()
            record_id = self.cursor.lastrowid
            
            debug(f"添加对话记录成功 - 记录ID: {record_id}, 用户ID: {user_id}")
            return record_id
        except Exception as e:
            exception(f"添加对话记录时出错: {e}")
            return -1
    
    def get_chat_history(self, user_id=None, limit=None):
        """
        获取对话历史
        
        Args:
            user_id: 用户ID（可选，如果指定则只获取该用户的对话）
            limit: 返回记录数量限制（可选）
            
        Returns:
            list: 对话记录列表
        """
        try:
            self._ensure_connection()
            
            query = "SELECT id, user_id, plan, user_message, bot_response, timestamp FROM chat_history"
            params = []
            
            # 如果指定了用户ID，添加WHERE条件
            if user_id is not None:
                query += " WHERE user_id = ?"
                params.append(user_id)
            
            # 按时间排序
            query += " ORDER BY timestamp DESC"
            
            # 如果指定了限制，添加LIMIT子句
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
            
            self.cursor.execute(query, params)
            records = []
            
            for record in self.cursor.fetchall():
                records.append({
                    'id': record[0],
                    'user_id': record[1],
                    'plan':record[2],
                    'user_message': record[3],
                    'bot_response': record[4],
                    'timestamp': record[5]
                })
            
            # 反转列表，使最新的记录在最后
            records.reverse()
            
            debug(f"获取对话历史成功 - 记录数: {len(records)}, 用户ID: {user_id}")
            return records
        except Exception as e:
            exception(f"获取对话历史时出错 (user_id={user_id}, limit={limit}): {e}")
            return []
    
    def get_all_sessions(self, user_id=None):
        """
        获取所有会话列表（按用户和日期分组）
        
        Args:
            user_id: 用户ID（可选，如果指定则只获取该用户的会话）
            
        Returns:
            list: 会话列表
        """
        try:
            self._ensure_connection()
            
            query = """
                SELECT 
                    date(timestamp) as session_date, 
                    MIN(timestamp) as first_message, 
                    MAX(timestamp) as last_message,
                    COUNT(*) as message_count,
                    user_id
                FROM chat_history
            """
            
            params = []
            
            # 如果指定了用户ID，添加WHERE条件
            if user_id is not None:
                query += " WHERE user_id = ?"
                params.append(user_id)
            
            query += " GROUP BY date(timestamp), user_id ORDER BY session_date DESC"
            
            self.cursor.execute(query, params)
            sessions = []
            
            for session in self.cursor.fetchall():
                sessions.append({
                    'session_date': session[0],
                    'first_message': session[1],
                    'last_message': session[2],
                    'message_count': session[3],
                    'user_id': session[4]
                })
            
            info(f"获取会话列表成功 - 会话数: {len(sessions)}, 用户ID: {user_id}")
            return sessions
        except Exception as e:
            exception(f"获取会话列表时出错 (user_id={user_id}): {e}")
            return []
    
    def delete_chat_history(self, user_id=None):
        """
        删除对话历史
        
        Args:
            user_id: 用户ID（可选，如果指定则只删除该用户的对话）
            
        Returns:
            int: 删除的记录数
        """
        try:
            self._ensure_connection()
            
            query = "DELETE FROM chat_history"
            params = []
            
            # 如果指定了用户ID，添加WHERE条件
            if user_id is not None:
                query += " WHERE user_id = ?"
                params.append(user_id)
            
            self.cursor.execute(query, params)
            deleted_count = self.cursor.rowcount
            self.conn.commit()
            
            info(f"删除对话历史成功 - 删除记录数: {deleted_count}, 用户ID: {user_id}")
            return deleted_count
        except Exception as e:
            exception(f"删除对话历史时出错 (user_id={user_id}): {e}")
            return 0