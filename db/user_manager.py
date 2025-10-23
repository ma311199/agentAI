from .db_connection import DatabaseConnection
from log import logger, debug, info, warning, error, critical, exception
import hashlib


class UserManager(DatabaseConnection):
    """用户管理模块，处理用户相关的所有操作"""
    
    def register_user(self, username, password, role_id=2):
        """
        注册新用户
        
        Args:
            username: 用户名
            password: 密码
            role_id: 角色ID，默认为2（普通用户）
            
        Returns:
            tuple: (success, user_id/error_message)
        """
        try:
            self._ensure_connection()
            
            # 检查用户名是否已存在
            self.cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
            if self.cursor.fetchone():
                warning(f"用户注册失败 - 用户名 {username} 已存在")
                return False, "用户名已存在"
            
            # 密码加密
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            # 插入新用户
            self.cursor.execute(
                "INSERT INTO users (username, password_hash, role_id) VALUES (?, ?, ?)",
                (username, password_hash, role_id)
            )
            self.conn.commit()
            user_id = self.cursor.lastrowid
            
            info(f"用户注册成功 - 用户名: {username}, 用户ID: {user_id}")
            return True, user_id
        except Exception as e:
            exception(f"注册用户 {username} 时出错: {e}")
            return False, str(e)
    
    def login_user(self, username, password):
        """
        用户登录验证
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            tuple: (success, user_id/error_message)
        """
        try:
            self._ensure_connection()
            
            # 查询用户信息
            self.cursor.execute(
                "SELECT user_id, password_hash, is_locked FROM users WHERE username = ?",
                (username,)
            )
            user = self.cursor.fetchone()
            
            if not user:
                warning(f"用户登录失败 - 用户 {username} 不存在")
                return False, "用户名或密码错误"
            
            user_id, stored_password_hash, is_locked = user
            
            # 检查用户是否被锁定
            if is_locked:
                warning(f"用户登录失败 - 用户 {username} 已被锁定")
                return False, "用户已被锁定"
            
            # 验证密码
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            if password_hash != stored_password_hash:
                warning(f"用户登录失败 - 用户 {username} 密码错误")
                return False, "用户名或密码错误"
            
            info(f"用户登录成功 - 用户名: {username}, 用户ID: {user_id}")
            return True, user_id
        except Exception as e:
            exception(f"用户 {username} 登录验证时出错: {e}")
            return False, str(e)
    
    def get_user_info(self, user_id):
        """
        获取用户信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            dict: 用户信息，如果不存在则返回None
        """
        try:
            self._ensure_connection()
            
            self.cursor.execute(
                "SELECT u.user_id, u.username, u.role_id, r.description, u.is_locked, u.created_at "
                "FROM users u JOIN roles r ON u.role_id = r.role_id WHERE u.user_id = ?",
                (user_id,)
            )
            user = self.cursor.fetchone()
            
            if not user:
                warning(f"未找到用户信息 - 用户ID: {user_id}")
                return None
            
            return {
                'user_id': user[0],
                'username': user[1],
                'role_id': user[2],
                'description': user[3],
                'is_locked': bool(user[4]),
                'created_at': user[5]
            }
        except Exception as e:
            exception(f"获取用户信息时出错 (user_id={user_id}): {e}")
            return None
    
    def change_user_role(self, user_id, role_id):
        """
        修改用户角色
        
        Args:
            user_id: 用户ID
            role_id: 新角色ID
            
        Returns:
            bool: 操作是否成功
        """
        try:
            self._ensure_connection()
            
            # 检查角色是否存在
            self.cursor.execute("SELECT role_id FROM roles WHERE role_id = ?", (role_id,))
            if not self.cursor.fetchone():
                warning(f"修改用户角色失败 - 角色ID {role_id} 不存在")
                return False
            
            # 检查用户是否存在
            self.cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if not self.cursor.fetchone():
                warning(f"修改用户角色失败 - 用户ID {user_id} 不存在")
                return False
            
            # 更新角色
            self.cursor.execute("UPDATE users SET role_id = ? WHERE user_id = ?", (role_id, user_id))
            if self.cursor.rowcount > 0:
                self.conn.commit()
                info(f"用户角色修改成功 - 用户ID: {user_id}, 新角色ID: {role_id}")
                return True
            else:
                warning(f"用户角色修改失败 - 用户ID: {user_id}")
                return False
        except Exception as e:
            exception(f"修改用户角色时出错 (user_id={user_id}, role_id={role_id}): {e}")
            return False
    
    def get_all_roles(self):
        """
        获取所有角色
        
        Returns:
            list: 角色列表
        """
        try:
            self._ensure_connection()
            
            self.cursor.execute("SELECT role_id, role_name, description FROM roles ORDER BY role_id")
            roles = []
            for role in self.cursor.fetchall():
                roles.append({
                    'role_id': role[0],
                    'role_name': role[1],
                    'description': role[2]
                })
            
            info(f"成功获取角色列表 - 角色数: {len(roles)}")
            return roles
        except Exception as e:
            exception(f"获取角色列表时出错: {e}")
            return []
    
    def change_user_lock_status(self, user_id, is_locked):
        """
        修改用户锁定状态
        
        Args:
            user_id: 用户ID
            is_locked: 是否锁定
            
        Returns:
            bool: 操作是否成功
        """
        try:
            self._ensure_connection()
            
            # 检查用户是否存在
            self.cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if not self.cursor.fetchone():
                warning(f"修改用户锁定状态失败 - 用户ID {user_id} 不存在")
                return False
            
            # 更新锁定状态
            self.cursor.execute("UPDATE users SET is_locked = ? WHERE user_id = ?", 
                               (1 if is_locked else 0, user_id))
            
            if self.cursor.rowcount > 0:
                self.conn.commit()
                action = "锁定" if is_locked else "解锁"
                info(f"用户{action}成功 - 用户ID: {user_id}")
                return True
            else:
                warning(f"用户锁定状态修改失败 - 用户ID: {user_id}")
                return False
        except Exception as e:
            exception(f"修改用户锁定状态时出错 (user_id={user_id}, is_locked={is_locked}): {e}")
            return False
    
    def update_user_password(self, user_id, new_password):
        """
        更新用户密码
        
        Args:
            user_id: 用户ID
            new_password: 新密码
            
        Returns:
            bool: 操作是否成功
        """
        try:
            self._ensure_connection()
            
            # 检查用户是否存在
            self.cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if not self.cursor.fetchone():
                warning(f"更新密码失败 - 用户ID {user_id} 不存在")
                return False
            
            # 密码加密
            password_hash = hashlib.sha256(new_password.encode()).hexdigest()
            
            # 更新密码
            self.cursor.execute("UPDATE users SET password_hash = ? WHERE user_id = ?", 
                               (password_hash, user_id))
            
            if self.cursor.rowcount > 0:
                self.conn.commit()
                info(f"用户密码更新成功 - 用户ID: {user_id}")
                return True
            else:
                warning(f"用户密码更新失败 - 用户ID: {user_id}")
                return False
        except Exception as e:
            exception(f"更新用户密码时出错 (user_id={user_id}): {e}")
            return False