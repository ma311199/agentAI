import inspect
from typing import Dict, Any, List, Callable, Optional

# 工具参数自动化，创建一个工具包装器，通过反射自动分析函数参数
# Callable 表示"可调用对象"，即任何可以通过 () 来调用的对象
# 指定参数和返回值类型
# function: Callable[[int, str], bool]  # 接受 (int, str) 参数，返回 bool
class Tool:
    """工具基类"""
    def __init__(self, name: str, description: str, function: Callable, parameters: Optional[List[Dict]] = None):
        self.name = name
        self.description = description
        self.function = function  #这个值确保了不同工具创建的Tool实列对应的函数工具，在execute中执行
        self.parameters = parameters or self._extract_parameters() # 也可以根据用户传人
        # self.parameters = self._extract_parameters() # 也可以根据用户传人
    
    def _extract_parameters(self) -> List[Dict]:
        """从函数签名中提取其参数信息"""
        sig = inspect.signature(self.function) #得到对应函数的签名
        parameters = []
        
        for param_name, param in sig.parameters.items(): # 迭代获取其参数，为每个参数创建一个字典
            param_info = {
                "name": param_name,
                "type": self._get_parameter_type(param),
                "description": f"参数 {param_name}",
                "required": param.default == param.empty
            }
            parameters.append(param_info)
        
        return parameters
    
    def _get_parameter_type(self, param) -> str:  #检查参数是否有类型注解
        """获取参数类型"""
        if param.annotation != param.empty:  #如果有，返回类型注解的名称（例如，如果注解是str，则返回"str"）。
            return param.annotation.__name__
        return "any" # 如果没有，返回字符串"any"。
    # 执行对应的工具函数
    def execute(self, **kwargs) -> Any:
        """执行工具"""
        return self.function(**kwargs)  # 对应的执行参数**kwargs
    
    def get_schema(self) -> Dict:
        """获取工具的JSON Schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }
