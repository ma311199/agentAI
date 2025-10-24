# 移除不必要的tkinter导入
from .db_connection import DatabaseConnection
from log import logger, debug, info, warning, error, critical, exception
from datetime import datetime


class FunctionToolManager(DatabaseConnection):
    """函数工具管理模块，处理函数工具相关的所有操作"""
    
    def add_function_tool(self, user_id, tool_name, description, parameters, is_active=True, tool_flag=0, label='通用', code_content=None):
        """
        添加新的函数工具
        
        Args:   
            user_id: 用户ID (可选)          
            tool_name: 工具名称
            description: 工具描述
            parameters: 参数定义（JSON字符串）
            is_active: 是否启用，默认为True
            code_content: 代码内容，用于保存用户自定义函数工具的代码内容
            
        Returns:
            tuple: (success, tool_id/error_message)
        """
        try:
            self._ensure_connection()
            
            # 检查工具名称是否已存在
            self.cursor.execute("SELECT tool_id FROM function_tools WHERE user_id = ? AND tool_name = ?", (user_id, tool_name,))
            existing_tool = self.cursor.fetchone()
            if existing_tool:
                debug(f"函数工具 {tool_name} 已存在，跳过添加")
                # 对于内部工具初始化，可以直接返回成功，使用已存在的工具ID
                return True, existing_tool[0]
            
            # 获取当前时间
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 插入新工具
            self.cursor.execute(
                "INSERT INTO function_tools (user_id, tool_name, description, parameters, is_active, create_time, update_time, tool_flag, label, code_content) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, tool_name, description, parameters, 1 if is_active else 0, current_time, current_time, tool_flag, label, code_content)
            )
            self.conn.commit()
            tool_id = self.cursor.lastrowid
            
            info(f"函数工具添加成功 - 工具名称: {tool_name}, 工具ID: {tool_id}, 用户ID: {user_id}, 工具类型: {label}")
            return True, tool_id
        except Exception as e:
            exception(f"添加函数工具 {tool_name} 时出错: {e}")
            return False, str(e)
    
    def get_all_function_tools(self, user_id):  
        """
        获取所有函数工具
        
        Returns:
            list: 函数工具列表
        """
        try:
            self._ensure_connection()

            debug("获取所有函数工具")
            self.cursor.execute(
                "SELECT distinct tool_id, tool_name, description, parameters, is_active, create_time, update_time, tool_flag, label, code_content FROM function_tools WHERE user_id = ? or tool_flag = 0 ORDER BY tool_id",
                (user_id,)
            )
            
            tools = []
            for tool in self.cursor.fetchall():
                tools.append({
                    'tool_id': tool[0],
                    'tool_name': tool[1],
                    'description': tool[2],
                    'parameters': tool[3],
                    'is_active': bool(tool[4]),
                    'create_time': tool[5],
                    'update_time': tool[6],
                    'tool_flag': tool[7],
                    'label': tool[8],
                    'code_content': tool[9]
                })
            
            info(f"成功获取函数工具列表 - 工具数: {len(tools)}")
            return tools
        except Exception as e:
            exception(f"获取函数工具列表时出错: {e}")
            return []
    
    def get_function_tool_by_id(self, user_id, tool_id):
        """
        根据ID获取函数工具
        
        Args:
            user_id: 用户ID (可选)              
            tool_id: 工具ID
            
        Returns:
            dict: 函数工具信息，如果不存在则返回None
        """
        try:
            self._ensure_connection()
            
            debug(f"获取函数工具 - 工具ID: {tool_id}, 用户ID: {user_id}")
            self.cursor.execute(
                "SELECT tool_id, tool_name, description, parameters, is_active, create_time, update_time, tool_flag, label, code_content FROM function_tools WHERE user_id = ? AND tool_id = ?",
                (user_id, tool_id,)
            )
            tool = self.cursor.fetchone()
            
            if not tool:
                return None
            
            tool_info = {
                'tool_id': tool[0],
                'tool_name': tool[1],
                'description': tool[2],
                'parameters': tool[3],
                'is_active': bool(tool[4]),
                'create_time': tool[5],
                'update_time': tool[6],
                'tool_flag': tool[7],
                'label': tool[8],
                'code_content': tool[9]
            }
            
            return tool_info
        except Exception as e:
            exception(f"获取函数工具时出错 (tool_id={tool_id}, user_id={user_id}): {e}")
            return None

    def get_function_tool_by_name(self, user_id, tool_name):
        """
        根据工具名获取函数工具
        
        Args:
            user_id: 用户ID (可选)              
            tool_name: 工具名
            
        Returns:
            dict: 函数工具信息，如果不存在则返回None
        """
        try:
            self._ensure_connection()
            
            debug(f"获取函数工具 - 工具名: {tool_name}, 用户ID: {user_id}")
            self.cursor.execute(
                "SELECT tool_id, tool_name, description, parameters, is_active, create_time, update_time, tool_flag, label, code_content FROM function_tools WHERE user_id = ? AND tool_name = ?",
                (user_id, tool_name,)
            )
            tool = self.cursor.fetchone()
            
            if not tool:
                return None
            
            tool_info = {
                'tool_id': tool[0],
                'tool_name': tool[1],
                'description': tool[2],
                'parameters': tool[3],
                'is_active': bool(tool[4]),
                'create_time': tool[5],
                'update_time': tool[6],
                'tool_flag': tool[7],
                'label': tool[8],
                'code_content': tool[9]
            }
            
            return tool_info
        except Exception as e:
            exception(f"获取函数工具时出错 (tool_name={tool_name}): {e}")
            return None
    
    def update_function_tool(self, user_id, tool_id, tool_name=None, description=None, parameters=None, is_active=None, tool_flag=None, label=None, code_content=None):
        """
        更新函数工具
        
        Args:
            user_id: 用户ID (可选)              
            tool_id: 工具ID
            tool_name: 工具名称（可选）
            description: 工具描述（可选）
            parameters: 参数定义（可选）
            is_active: 是否启用（可选）
            tool_flag: 工具类型（可选）
            label: 标签（可选）
            code_content: 代码内容（可选）
            
        Returns:
            bool: 操作是否成功
        """
        try:
            self._ensure_connection()
            
            # 检查工具是否存在
            if not self.get_function_tool_by_id(user_id, tool_id):
                warning(f"未找到函数工具 - 工具ID: {tool_id}, 用户ID: {user_id}")                       
                return False
            
            # 构建更新语句
            update_fields = []
            update_values = []
            
            if tool_name is not None:
                # 检查新名称是否与其他工具重复
                self.cursor.execute("SELECT tool_id FROM function_tools WHERE user_id = ? AND tool_name = ? AND tool_id != ?", (user_id, tool_name, tool_id))
                if self.cursor.fetchone():
                    warning(f"更新函数工具失败 - 工具名称 {tool_name} 已被其他工具使用, 用户ID: {user_id}")
                    return False
                update_fields.append("tool_name = ?")
                update_values.append(tool_name)
            
            if description is not None:
                update_fields.append("description = ?")
                update_values.append(description)
            
            if tool_flag is not None:
                update_fields.append("tool_flag = ?")
                update_values.append(tool_flag)
            
            if label is not None:
                update_fields.append("label = ?")
                update_values.append(label)
            
            if parameters is not None:
                update_fields.append("parameters = ?")
                update_values.append(parameters)
            
            if is_active is not None:
                update_fields.append("is_active = ?")
                update_values.append(1 if is_active else 0)
            
            if code_content is not None:
                update_fields.append("code_content = ?")
                update_values.append(code_content)
            
            # 更新时间戳
            update_fields.append("update_time = ?")
            update_values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            if not update_fields:
                debug("未提供更新字段")
                return True
            
            # 执行更新
            update_sql = f"UPDATE function_tools SET {', '.join(update_fields)} WHERE user_id = ? AND tool_id = ?"
            update_values.append(user_id)
            update_values.append(tool_id)
            
            self.cursor.execute(update_sql, update_values)
            
            if self.cursor.rowcount > 0:
                self.conn.commit()
                info(f"函数工具更新成功 - 工具ID: {tool_id}, 用户ID: {user_id}")
                return True
            else:
                warning(f"函数工具更新失败 - 工具ID: {tool_id}, 用户ID: {user_id}")
                return False
        except Exception as e:
            exception(f"更新函数工具时出错 (工具ID: {tool_id}, 用户ID: {user_id}): {e}")
            return False
    
    def delete_function_tool(self, user_id, tool_id):
        """
        删除函数工具
        
        Args:
            user_id: 用户ID
            tool_id: 工具ID
            
        Returns:
            bool: 操作是否成功
        """
        try:
            self._ensure_connection()
            
            debug(f"删除函数工具 - 工具ID: {tool_id}, 用户ID: {user_id}")   
            
            self.cursor.execute("DELETE FROM function_tools WHERE user_id = ? AND tool_id = ?", (user_id, tool_id))
            
            if self.cursor.rowcount > 0:
                self.conn.commit()
                info(f"函数工具删除成功 - 工具ID: {tool_id}, 用户ID: {user_id}")
                return True
            else:
                warning(f"未找到函数工具 - 工具ID: {tool_id}, 用户ID: {user_id}")
                return False
        except Exception as e:
            exception(f"删除函数工具时出错 (工具ID: {tool_id}, 用户ID: {user_id}): {e}")
            return False
    
    def add_tool_execution(self, user_id, tool_id, tool_name, question=None, execution_steps=None, execution_params=None, execution_result=None, execution_status="success", start_time=None, end_time=None):   
        """
        添加函数工具执行记录
        
        Args:
            user_id: 用户ID
            tool_id: 工具ID
            tool_name: 工具名称
            question: 问题描述（可选）
            execution_steps: 执行步骤（可选）
            execution_params: 执行参数（可选，JSON字符串）
            execution_result: 执行结果（可选，JSON字符串）
            execution_status: 执行状态（可选，默认为'success'），可选值：'success', 'error'
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）
            
            
        Returns:
            tuple: (success, execution_id/error_message)
        """
        try:
            self._ensure_connection()
            
            # 插入执行记录
            self.cursor.execute(
                "INSERT INTO function_tool_executions (user_id, tool_id, tool_name, question, execution_steps, execution_params, execution_result, execution_status, start_time, end_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, tool_id, tool_name, question, execution_steps, execution_params, execution_result, execution_status, start_time,end_time)
            )
            self.conn.commit()
            execution_id = self.cursor.lastrowid
            
            debug(f"函数工具执行记录添加成功 - 执行ID: {execution_id}, 用户ID: {user_id}, 工具ID: {tool_id}")
            return True, execution_id
        except Exception as e:
            exception(f"添加函数工具执行记录时出错: {e}")
            return False, str(e)
    
    def update_tool_execution_result(self, execution_id, execution_result, execution_steps=None, execution_status='success'):
        """
        更新函数工具执行结果
        
        Args:
            execution_id: 执行ID
            execution_result: 执行结果
            execution_steps: 执行步骤（可选，JSON字符串）
            execution_status: 执行状态，默认为'success'
            
        Returns:
            bool: 操作是否成功
        """
        try:
            self._ensure_connection()
            
            # 获取结束时间
            end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 构建更新语句
            update_fields = ["execution_result = ?", "execution_status = ?", "end_time = ?"]
            update_values = [execution_result, execution_status, end_time]
            
            if execution_steps is not None:
                update_fields.append("execution_steps = ?")
                update_values.append(execution_steps)
            
            # 执行更新
            update_sql = f"UPDATE function_tool_executions SET {', '.join(update_fields)} WHERE execution_id = ?"
            update_values.append(execution_id)
            
            self.cursor.execute(update_sql, update_values)
            
            if self.cursor.rowcount > 0:
                self.conn.commit()
                debug(f"函数工具执行结果更新成功 - 执行ID: {execution_id}")
                return True
            else:
                warning(f"未找到函数工具执行记录 - 执行ID: {execution_id}")
                return False
        except Exception as e:
            exception(f"更新函数工具执行结果时出错 (执行ID: {execution_id}): {e}")
            return False
    
    def get_tool_execution_by_id(self, execution_id):
        """
        根据ID获取函数工具执行记录
        
        Args:
            execution_id: 执行ID
            
        Returns:
            dict: 执行记录信息，如果不存在则返回None
        """
        try:
            self._ensure_connection()
            
            debug(f"获取函数工具执行记录 - 执行ID: {execution_id}")
            self.cursor.execute(
                "SELECT execution_id, user_id, tool_id, tool_name, question, execution_steps, execution_params, "
                "execution_result, execution_status, start_time, end_time FROM function_tool_executions WHERE execution_id = ?",
                (execution_id,)
            )
            execution = self.cursor.fetchone()
            
            if not execution:
                return None
            
            execution_info = {
                'execution_id': execution[0],
                'user_id': execution[1],
                'tool_id': execution[2],
                'tool_name': execution[3],
                'question': execution[4],
                'execution_steps': execution[5],
                'execution_params': execution[6],
                'execution_result': execution[7],
                'execution_status': execution[8],
                'start_time': execution[9],
                'end_time': execution[10]
            }
            
            return execution_info
        except Exception as e:
            exception(f"获取函数工具执行记录时出错 (执行ID: {execution_id}): {e}")
            return None
    
    def get_user_tool_executions(self, user_id, limit=50, offset=0):
        """
        获取用户的函数工具执行历史
        
        Args:
            user_id: 用户ID
            limit: 返回记录数限制，默认为50
            offset: 偏移量，默认为0
            
        Returns:
            list: 执行记录列表
        """
        try:
            self._ensure_connection()
            
            debug(f"获取用户函数工具执行历史 - 用户ID: {user_id}, 限制: {limit}, 偏移: {offset}")
            self.cursor.execute(
                "SELECT execution_id, user_id, tool_id, tool_name, question, execution_steps, execution_params, "
                "execution_result, execution_status, start_time, end_time FROM function_tool_executions "
                "WHERE user_id = ? ORDER BY start_time DESC LIMIT ? OFFSET ?",
                (user_id, limit, offset)
            )
            
            executions = []
            for execution in self.cursor.fetchall():
                executions.append({
                    'execution_id': execution[0],
                    'user_id': execution[1],
                    'tool_id': execution[2],
                    'tool_name': execution[3],
                    'question': execution[4],
                    'execution_steps': execution[5],
                    'execution_params': execution[6],
                    'execution_result': execution[7],
                    'execution_status': execution[8],
                    'start_time': execution[9],
                    'end_time': execution[10]
                })
            
            info(f"成功获取用户函数工具执行历史 - 用户ID: {user_id}, 记录数: {len(executions)}")
            return executions
        except Exception as e:
            exception(f"获取用户函数工具执行历史时出错 (用户ID: {user_id}): {e}")
            return []
    
    def get_tool_execution_history(self, tool_id, limit=50, offset=0):
        """
        获取特定工具的执行历史
        
        Args:
            tool_id: 工具ID
            limit: 返回记录数限制，默认为50
            offset: 偏移量，默认为0
            
        Returns:
            list: 执行记录列表
        """
        try:
            self._ensure_connection()
            
            debug(f"获取工具执行历史 - 工具ID: {tool_id}, 限制: {limit}, 偏移: {offset}")
            self.cursor.execute(
                "SELECT execution_id, user_id, tool_id, tool_name, question, execution_steps, execution_params, "
                "execution_result, execution_status, start_time, end_time FROM function_tool_executions "
                "WHERE tool_id = ? ORDER BY start_time DESC LIMIT ? OFFSET ?",
                (tool_id, limit, offset)
            )
            
            executions = []
            for execution in self.cursor.fetchall():
                executions.append({
                    'execution_id': execution[0],
                    'user_id': execution[1],
                    'tool_id': execution[2],
                    'tool_name': execution[3],
                    'question': execution[4],
                    'execution_steps': execution[5],
                    'execution_params': execution[6],
                    'execution_result': execution[7],
                    'execution_status': execution[8],
                    'start_time': execution[9],
                    'end_time': execution[10]
                })
            
            info(f"成功获取工具执行历史 - 工具ID: {tool_id}, 记录数: {len(executions)}")
            return executions
        except Exception as e:
            exception(f"获取工具执行历史时出错 (工具ID: {tool_id}): {e}")
            return []
    
    def delete_tool_execution(self, execution_id):
        """
        删除函数工具执行记录
        
        Args:
            execution_id: 执行ID
            
        Returns:
            bool: 操作是否成功
        """
        try:
            self._ensure_connection()
            
            debug(f"删除函数工具执行记录 - 执行ID: {execution_id}")
            
            self.cursor.execute("DELETE FROM function_tool_executions WHERE execution_id = ?", (execution_id,))
            
            if self.cursor.rowcount > 0:
                self.conn.commit()
                info(f"函数工具执行记录删除成功 - 执行ID: {execution_id}")
                return True
            else:
                warning(f"未找到函数工具执行记录 - 执行ID: {execution_id}")
                return False
        except Exception as e:
            exception(f"删除函数工具执行记录时出错 (执行ID: {execution_id}): {e}")
            return False

    def delete_all_tool_execution(self, user_id):
        """
        删除函数工具执行记录
        
        Args:
            user_id: 执行ID
            
        Returns:
            bool: 操作是否成功
        """
        try:
            self._ensure_connection()
            
            debug(f"删除用户{user_id}函数工具执行记录")
            
            self.cursor.execute("DELETE FROM function_tool_executions WHERE user_id = ?", (user_id,))
            self.conn.commit()
            
            if self.cursor.rowcount > 0:
                info(f"函数工具执行记录删除成功 - 执行用户ID: {user_id}, 删除记录数: {self.cursor.rowcount}")
            else:
                info(f"用户{user_id}没有函数工具执行记录需要删除")
            return True
        except Exception as e:
            exception(f"删除函数工具执行记录时出错 (执行ID: {user_id}): {e}")
            return False
    
    def get_execution_statistics(self, user_id=None, tool_id=None, days=7):
        """
        获取函数工具执行统计信息
        
        Args:
            user_id: 用户ID（可选）
            tool_id: 工具ID（可选）
            days: 统计天数，默认为7天
            
        Returns:
            dict: 统计信息
        """
        try:
            self._ensure_connection()
            
            # 构建查询条件
            conditions = []
            params = []
            
            if user_id is not None:
                conditions.append("user_id = ?")
                params.append(user_id)
            
            if tool_id is not None:
                conditions.append("tool_id = ?")
                params.append(tool_id)
            
            # 添加时间条件
            conditions.append("start_time >= datetime('now', '-' || ? || ' days')")
            params.append(days)
            
            # 总执行次数
            where_clause = " AND ".join(conditions)
            total_query = f"SELECT COUNT(*) FROM function_tool_executions WHERE {where_clause}"
            self.cursor.execute(total_query, params)
            total_executions = self.cursor.fetchone()[0]
            
            # 成功执行次数
            success_params = params.copy()
            success_query = f"SELECT COUNT(*) FROM function_tool_executions WHERE {where_clause} AND execution_status = 'success'"
            self.cursor.execute(success_query, success_params)
            successful_executions = self.cursor.fetchone()[0]
            
            # 失败执行次数
            failed_params = params.copy()
            failed_query = f"SELECT COUNT(*) FROM function_tool_executions WHERE {where_clause} AND execution_status != 'success'"
            self.cursor.execute(failed_query, failed_params)
            failed_executions = self.cursor.fetchone()[0]
            
            statistics = {
                'total_executions': total_executions,
                'successful_executions': successful_executions,
                'failed_executions': failed_executions,
                'success_rate': successful_executions / total_executions if total_executions > 0 else 0,
                'period_days': days
            }
            
            debug(f"成功获取函数工具执行统计信息 - 用户ID: {user_id}, 工具ID: {tool_id}, 天数: {days}")
            return statistics
        except Exception as e:
            exception(f"获取函数工具执行统计信息时出错: {e}")
            return None