from .db_connection import DatabaseConnection
from log import logger, debug, info, warning, error, critical, exception
import datetime


class ModelManager(DatabaseConnection):
    """模型管理模块，处理模型相关的所有操作"""
    
    def add_model(self, user_id, model_name, model_url, api_key=None, temperature=0.7, max_tokens=2048, desc=None):
        """添加新模型
        
        Args:
            user_id : 用户id
            model_name: 模型名称
            model_url: 模型地址
            api_key: API密钥（可选）
            temperature: 温度参数，默认为0.7
            max_tokens: 最大生成 tokens 数，默认为2048
            desc : 模型描述
            
        Returns:
            tuple: (success, model_id/error_message)
        """
        try:
            # 确保连接有效
            self._ensure_connection()
            
            # 检查模型名称是否已存在
            self.cursor.execute("SELECT model_id FROM model_info WHERE model_name = ? and user_id= ? ", (model_name,user_id))
            if self.cursor.fetchone():
                debug(f"模型添加失败 - 用户{user_id}已添加过模型{model_name}")
                return False, "模型名称已存在"
            
            # 获取当前时间作为添加时间
            add_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 插入新模型
            self.cursor.execute(
                "INSERT INTO model_info (user_id, model_name, model_url, api_key, temperature, max_tokens, add_time,desc) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, model_name, model_url, api_key, temperature, max_tokens, add_time, desc)
            )
            self.conn.commit()
            model_id = self.cursor.lastrowid
            
            info(f"模型添加成功 - 模型名称: {model_name}, 模型ID: {model_id}")
            return True, model_id
        except Exception as e:
            exception(f"添加模型 {model_name} 时出错: {e}")
            return False, str(e)
    
    def get_all_models(self):
        """获取所有模型信息
        
        Returns:
            list: 模型信息列表
        """
        try:
            # 确保连接有效
            self._ensure_connection()
            
            debug("获取所有模型信息")
            self.cursor.execute("SELECT model_id, model_name, model_url, api_key, temperature, max_tokens, add_time, is_active, user_id, desc FROM model_info ORDER BY model_id")
            
            models = []
            for model in self.cursor.fetchall():
                models.append({
                    'model_id': model[0],
                    'model_name': model[1],
                    'model_url': model[2],
                    'api_key': model[3],
                    'temperature': model[4],
                    'max_tokens': model[5],
                    'add_time': model[6],
                    'is_active': bool(model[7]),
                    'user_id': model[8],
                    'desc': model[9]
                })
            
            info(f"成功获取模型列表 - 模型数: {len(models)}")
            return models
        except Exception as e:
            exception(f"获取模型列表时出错: {e}")
            return []
    
    def get_model_by_id(self, model_id):
        """根据模型ID获取模型信息
        
        Args:
            model_id: 模型ID
            
        Returns:
            dict: 模型信息字典，如果不存在则返回None
        """
        try:
            # 确保连接有效
            self._ensure_connection()
            
            debug(f"获取模型信息 - 模型ID: {model_id}")
            self.cursor.execute(
                "SELECT model_id, model_name, model_url, api_key, temperature, max_tokens, add_time, is_active, user_id, desc FROM model_info WHERE model_id = ?",
                (model_id,)
            )
            model = self.cursor.fetchone()
            
            if not model:
                return None
            
            model_info = {
                'model_id': model[0],
                'model_name': model[1],
                'model_url': model[2],
                'api_key': model[3],
                'temperature': model[4],
                'max_tokens': model[5],
                'add_time': model[6],
                'is_active': bool(model[7]),
                'user_id': model[8],
                'desc': model[9]
            }
            
            return model_info
        except Exception as e:
            exception(f"获取模型信息时出错 (model_id={model_id}): {e}")
            return None

# 新增，根据用户id获取模型信息
    def get_user_model_by_id(self, user_id):
        """根据用户ID获取该用户的所有模型信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            list: 模型信息字典列表，如果不存在则返回空列表
        """
        try:
            # 确保连接有效
            self._ensure_connection()
            
            debug(f"获取模型信息 - 用户ID: {user_id}")
            self.cursor.execute(
                "SELECT model_id, model_name, model_url, api_key, temperature, max_tokens, add_time, is_active, desc FROM model_info WHERE user_id = ?",
                (user_id,)
            )
            models = self.cursor.fetchall()
            
            if not models:
                return []
            
            model_list = []
            for model in models:
                model_info = {
                    'model_id': model[0],
                    'model_name': model[1],
                    'model_url': model[2],
                    'api_key': model[3],
                    'temperature': model[4],
                    'max_tokens': model[5],
                    'add_time': model[6],
                    'is_active': bool(model[7]),
                    'desc': model[8]
                }
                model_list.append(model_info)
            
            return model_list
        except Exception as e:
            exception(f"获取模型信息时出错 (user_id={user_id}): {e}")
            return []
    
    def update_model(self, user_id, model_id, model_name=None, model_url=None, api_key=None, temperature=None, max_tokens=None, is_active=None, desc=None):
        """更新模型信息
        
        Args:
            user_id: 用户ID
            model_id: 模型ID
            model_name: 模型名称（可选）
            model_url: 模型地址（可选）
            api_key: API密钥（可选）
            temperature: 温度参数（可选）
            max_tokens: 最大生成 tokens 数（可选）
            is_active: 是否启用（可选）
            desc: 模型描述
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 确保连接有效
            self._ensure_connection()
            
            # 检查模型是否存在
            if not self.get_model_by_id(model_id):
                warning(f"未找到模型 - 模型ID: {model_id}")
                return False
            
            # 构建更新语句
            update_fields = []
            update_values = []
            
            if model_name is not None:
                # 检查新名称是否与其他模型重复
                self.cursor.execute("SELECT model_id FROM model_info WHERE model_name = ? AND model_id != ? AND user_id = ?", (model_name, model_id, user_id))
                if self.cursor.fetchone():
                    warning(f"更新模型失败 - 模型名称 {model_name} 已被其他模型使用")
                    return False
                update_fields.append("model_name = ?")
                update_values.append(model_name)
            
            if model_url is not None:
                update_fields.append("model_url = ?")
                update_values.append(model_url)
            
            if api_key is not None:
                update_fields.append("api_key = ?")
                update_values.append(api_key)
            
            if temperature is not None:
                update_fields.append("temperature = ?")
                update_values.append(temperature)
            
            if max_tokens is not None:
                update_fields.append("max_tokens = ?")
                update_values.append(max_tokens)
            
            if is_active is not None:
                update_fields.append("is_active = ?")
                update_values.append(1 if is_active else 0)

            if desc is not None:
                update_fields.append("desc = ?")
                update_values.append(desc)
            
            if not update_fields:
                debug("未提供更新字段")
                return True
            
            # 执行更新
            update_sql = f"UPDATE model_info SET {', '.join(update_fields)} WHERE model_id = ?"
            update_values.append(model_id)
            
            self.cursor.execute(update_sql, update_values)
            
            if self.cursor.rowcount > 0:
                self.conn.commit()
                info(f"模型更新成功 - 模型ID: {model_id}")
                return True
            else:
                warning(f"模型更新失败 - 模型ID: {model_id}")
                return False
        except Exception as e:
            exception(f"更新模型时出错 (模型ID: {model_id}): {e}")
            return False
    
    def delete_model(self, model_id):
        """删除模型
        
        Args:
            model_id: 模型ID
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 确保连接有效
            self._ensure_connection()
            
            debug(f"删除模型 - 模型ID: {model_id}")
            
            self.cursor.execute("DELETE FROM model_info WHERE model_id = ?", (model_id,))
            
            if self.cursor.rowcount > 0:
                self.conn.commit()
                info(f"模型删除成功 - 模型ID: {model_id}")
                return True
            else:
                warning(f"未找到模型 - 模型ID: {model_id}")
                return False
        except Exception as e:
            exception(f"删除模型时出错 (模型ID: {model_id}): {e}")
            return False