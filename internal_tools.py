in_tools=[
    {
    "tool_name": "add",
    "description": "执行加法运算：a + b",
    "parameters": [{'name': 'a', 'type': 'float', 'description': '第一个加数 a', 'required': True}, {'name': 'b', 'type': 'float', 'description': '第二个加数 b', 'required': True}],
    "function": "def add(a: float, b: float) -> float:\n    return a + b"
    },
    {
    "tool_name": "subtract",
    "description": "执行减法运算：a - b",
    "parameters": [{'name': 'a', 'type': 'float', 'description': '被减数 a', 'required': True}, {'name': 'b', 'type': 'float', 'description': '减数 b', 'required': True}],
    "function": "def subtract(a: float, b: float) -> float:\n    return a - b"
    },
    {
    "tool_name": "multiply",
    "description": "执行乘法运算：a × b",
    "parameters": [{'name': 'a', 'type': 'float', 'description': '第一个乘数 a', 'required': True}, {'name': 'b', 'type': 'float', 'description': '第二个乘数 b', 'required': True}],
    "function": "def multiply(a: float, b: float) -> float:\n    return a * b"
    },
    {
    "tool_name": "divide",
    "description": "执行除法运算：a ÷ b",
    "parameters": [{'name': 'a', 'type': 'float', 'description': '被除数 a', 'required': True}, {'name': 'b', 'type': 'float', 'description': '除数 b', 'required': True}],
    "function": "def divide(a: float, b: float) -> float:\n    if b == 0:\n        return \"错误：除数不能为零\"\n    return a / b"
    },
    {
    "tool_name": "search",
    "description": "在互联网上搜索信息",
    "parameters": [{'name': 'query', 'type': 'str', 'description': '搜索关键词', 'required': True}],
    "function": "def search(query: str) -> str:\n    time.sleep(1)  # 模拟搜索延迟\n    return f\"正在查询中，请稍后...\\n查询关键词: {query}\\n[模拟搜索结果：找到约 1,000 条相关结果]\""
    },
    {
    "tool_name": "search_hana",
    "description": "在HANA数据库中搜索信息",
    "parameters": [{'name': 'query', 'type': 'str', 'description': '搜索关键词', 'required': True}],
    "function": "def search_hana(query: str) -> str:\n    return f\"正在搜索{query}...\\n[模拟100条HANA信息]\""
    }
]

