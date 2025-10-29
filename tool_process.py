from tools import Tool
import time
import inspect
from log import logger, debug, info, warning, error, critical, exception
from typing import Dict,Callable, Optional, Any, Union


class Toolregister:
    """通用Agent，支持动态工具注册和自动参数填充"""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        
        # 注册内置工具
        # self._register_builtin_tools()
    
    # 默认的快速注册函数
    def _register_builtin_tools(self):
        """注册内置工具，可在此处继续注册新的内部工具"""
        # 数学工具
        self.register_tool("add", "执行加法运算：a + b", self._add)
        self.register_tool("subtract", "执行减法运算：a - b", self._subtract)
        self.register_tool("multiply", "执行乘法运算：a × b", self._multiply)
        self.register_tool("divide", "执行除法运算：a ÷ b", self._divide)
        
        # 搜索工具
        self.register_tool("search", "使用搜索引擎查询信息", self._search)

        self.register_tool("hana", "执行搜索HANA数据库相关信息", self._search_hana)

    
    def _convert_string_to_function(self, code_content: str, tool_name: Optional[str] = None) -> Callable:
        """将字符串形式的函数代码转换为可调用函数对象
        
        Args:
            code_content: 包含函数定义的字符串代码
            tool_name: 可选，若提供则优先按该名称从命名空间中提取函数
            
        Returns:
            Callable: 转换后的可调用函数对象
        """
        # 创建一个空的命名空间来执行代码
        local_namespace = {}
        
        # 执行代码字符串，将定义的函数加载到命名空间，列：{'multiply': <function multiply at 0x00000204FF705D80>}
        exec(code_content, globals(), local_namespace)
        # info(f"注册的函数空间：{local_namespace}")
        # 优先根据 tool_name 查找函数
        if tool_name:
            candidate = local_namespace.get(tool_name)
            # candidate ：判断按 tool_name 查到的对象存在且非空，避免对 None 或未定义对象继续判断。
            # callable(candidate) ：确保拿到的是“可调用”的对象（函数、方法、带 __call__ 的实例等），而不是常量、模块、类型等。
            # not inspect.isbuiltin(candidate) ：排除内建函数或 C 扩展内建对象，保证我们选取的是用户定义的 Python 函数，避免匹配到环境里意外出现的内建符号。
            # not tool_name.startswith('_') ：过滤以下划线开头的名字，作为“私有/内部”约定，不把它们当作需要注册的工具函数，减少误选内部辅助函数。
            if candidate and callable(candidate) and not inspect.isbuiltin(candidate) and not tool_name.startswith('_'):
                return candidate
        
        # 查找命名空间中定义的第一个函数（假设代码中只定义了一个主函数）
        for name, obj in local_namespace.items():
            if callable(obj) and not inspect.isbuiltin(obj) and not name.startswith('_'):
                return obj
        
        # 如果没有找到函数，抛出异常
        error(f"无法从代码字符串中提取函数: {code_content}")
        raise ValueError("无法从代码字符串中提取函数")

    
    def register_tool(self, tool_name: str, description: str, function: Union[Callable, str], parameters: Optional[Any] = None):
        """注册新工具
        
        Args:
            tool_name: 工具名称
            description: 工具描述
            function: 可调用函数或函数代码字符串
            parameters: 工具参数（可选）
        """
        # 如果function是字符串，则将其转换为可调用函数
        if isinstance(function, str):
            function = self._convert_string_to_function(function, tool_name)
        
        # 加载函数工具到内存，并注册到工具列表中
        self.tools[tool_name] = Tool(tool_name, description, function, parameters)
    
    
    # 数学工具函数
    def _add(self, a: float, b: float) -> float:
        return a + b
    
    def _subtract(self, a: float, b: float) -> float:
        return a - b
    
    def _multiply(self, a: float, b: float) -> float:
        return a * b
    
    def _divide(self, a: float, b: float) -> float:
        if b == 0:
            return "错误：除数不能为零"
        return a / b
    
    # 搜索工具函数
    def _search(self, query: str) -> str:
        """搜索引擎工具"""
        time.sleep(1)  # 模拟搜索延迟
        return f"正在查询中，请稍后...\n查询关键词: {query}\n[模拟搜索结果：找到约 1,000 条相关结果]"
    # 可在此处继续定义内部工具
    def _search_hana(self, query: str) -> str:
        return f"正在搜索{query}...\n[模拟100条HANA信息]"
    
    def delete_tool(self, name: str) -> bool:
        """删除指定名称的工具
        
        Args:
            name: 要删除的工具名称
            
        Returns:
            bool: 如果工具存在并成功删除返回True，否则返回False
        """
        if name in self.tools:
            del self.tools[name]
            return True
        return False
    
    def get_tool_names(self) -> list:
        """获取所有已注册工具的名称列表
        
        Returns:
            list: 工具名称列表
        """
        return list(self.tools.keys())
    

    


