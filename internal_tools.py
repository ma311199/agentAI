in_tools=[
    # {
    # "tool_name": "add",
    # "description": "执行加法运算：a + b",
    # "parameters": [{'name': 'a', 'type': 'float', 'description': '第一个加数 a', 'required': True}, {'name': 'b', 'type': 'float', 'description': '第二个加数 b', 'required': True}],
    # "function": "def add(a: float, b: float) -> float:\n    return a + b"
    # },
    # {
    # "tool_name": "subtract",
    # "description": "执行减法运算：a - b",
    # "parameters": [{'name': 'a', 'type': 'float', 'description': '被减数 a', 'required': True}, {'name': 'b', 'type': 'float', 'description': '减数 b', 'required': True}],
    # "function": "def subtract(a: float, b: float) -> float:\n    return a - b"
    # },
    # {
    # "tool_name": "multiply",
    # "description": "执行乘法运算：a × b",
    # "parameters": [{'name': 'a', 'type': 'float', 'description': '第一个乘数 a', 'required': True}, {'name': 'b', 'type': 'float', 'description': '第二个乘数 b', 'required': True}],
    # "function": "def multiply(a: float, b: float) -> float:\n    return a * b"
    # },
    # {
    # "tool_name": "divide",
    # "description": "执行除法运算：a ÷ b",
    # "parameters": [{'name': 'a', 'type': 'float', 'description': '被除数 a', 'required': True}, {'name': 'b', 'type': 'float', 'description': '除数 b', 'required': True}],
    # "function": "def divide(a: float, b: float) -> float:\n    if b == 0:\n        return \"错误：除数不能为零\"\n    return a / b"
    # },
    # {
    # "tool_name": "search",
    # "description": "在互联网上搜索信息",
    # "parameters": [{'name': 'query', 'type': 'str', 'description': '搜索关键词', 'required': True}],
    # "function": "def search(query: str) -> str:\n    time.sleep(1)  # 模拟搜索延迟\n    return f\"正在查询中，请稍后...\\n查询关键词: {query}\\n[模拟搜索结果：找到约 1,000 条相关结果]\""
    # },
    # {
    #     "tool_name": "search_hana",
    #     "description": "在HANA数据库中搜索信息",
    #     "parameters": [{'name': 'query', 'type': 'str', 'description': '搜索关键词', 'required': True}],
    #     "function": "def search_hana(query: str) -> str:\n    return f\"正在搜索{query}...\\n[模拟100条HANA信息]\""
    # },
    {
        "tool_name": "accountpush",
        "description": "可以根据用户问题或邮件获取到系统id、用户、用户组、权限角色、邮件id等信息，每次可以推送对应的1个系统；注意：邮件工具返回的每个邮件都必须单独进行推送，不能合并进行推送",
        "parameters":[
            {'name':'system_id','type': 'str', 'description': '推送的系统id名称，如HP0、HP7', 'required': True},
            {'name':'account_info','type': 'list[str]', 'description': '需要推送的用户id账号列表', 'required': True},
            {'name':'group_info','type': 'list[str]', 'description': '需要推送的用户组列表', 'required': False},
            {'name':'role_info','type': 'list[str]', 'description': '需要推送的权限角色列表', 'required': False},
            {'name':'mail_id','type': 'int', 'description': '推送（新增）账号信息的邮件id', 'required': False}],
        "function":"def accountpush(system_id:str, account_info:list[str], group_info:list[str]=None, role_info:list[str]=None, mail_id: int=0):\n    \"\"\"执行工具的核心逻辑\"\"\"\n    from function_call.account_fenlei import has_chinese_re,account_role,account_usergroup,account_usergroup_role\n    bw_han_system=(\"HP7\",\"HP0\",\"HPX\",\"BO\")\n    \n    # 确保system_id是字符串类型并转换为大写\n    if not isinstance(system_id, str) or system_id.upper() not in bw_han_system:\n        print(system_id)\n        return {\"status\": \"error\", \"message\": \"推送的系统id不存在或者不正确，请重新检查调用工具\"}\n    \n    # 确保account_info是列表类型\n    if not isinstance(account_info, list):\n        return {\"status\": \"error\", \"message\": \"账号列表必须是数组类型\"}\n    \n    # 处理None值，转换为空列表\n    if group_info is None:\n        group_info = []\n    if role_info is None:\n        role_info = []\n    \n    # 确保group_info和role_info是列表类型\n    if not isinstance(group_info, list):\n        return {\"status\": \"error\", \"message\": \"用户组列表必须是数组类型\"}\n    if not isinstance(role_info, list):\n        return {\"status\": \"error\", \"message\": \"权限列表必须是数组类型\"}\n    \n    # 检查是否包含中文字符（仅当列表不为空时）\n    if account_info and has_chinese_re(\" \".join(account_info)):\n        return {\"status\": \"error\", \"message\": \"账号列表中存在中文字符，请重新确认值\"}\n    if group_info and has_chinese_re(\" \".join(group_info)):\n        return {\"status\": \"error\", \"message\": \"用户组列表中存在中文字符，请重新确认值\"}\n    if role_info and has_chinese_re(\" \".join(role_info)):\n        return {\"status\": \"error\", \"message\": \"权限列表中存在中文字符，请重新确认值\"}\n    if not account_info:\n        return {\"status\": \"error\", \"message\": \"用户账号为空，请重新确认值\"}\n    elif not group_info and not role_info:\n        return {\"status\": \"error\", \"message\": \"用户组和权限角色都为空，请重新确认值\"}\n    elif not group_info:\n        result = account_role(mail_id, system_id, account_info, role_info)\n        return result\n    elif not role_info:\n        result = account_usergroup(mail_id, system_id, account_info, group_info)\n        return result\n    else:\n        result = account_usergroup_role(mail_id, system_id, account_info, group_info, role_info)\n        return result"
    },
    {
        "tool_name": "getmail",
        "description": "该工具可以获取邮件中需要推送的系统id、用户、用户组、权限角色信息",
        "parameters":[],
        "function":"def getmail():\n    from function_call.receive_mail import mail_processed\n    return mail_processed()"
    },
    {
        "tool_name": "sendmail",
        "description": "该工具可以将推送的账号信息进行邮件回复",
        "parameters":[],
        "function":"def sendmail():\n    from function_call.receive_mail import get_re_mail\n    return get_re_mail()"
    }
]



# 账号推送内置工具
# def accountpush(system_id:str ,account_info:list[str], group_info:list[str]=None, role_info:list[str]=None, mail_id: int=0):
#     """执行工具的核心逻辑"""
#     from function_call.account_fenlei import has_chinese_re,account_role,account_usergroup,account_usergroup_role
#     bw_han_system=("HP7","HP0","HPX","BO")
    
#     # 确保system_id是字符串类型并转换为大写
#     if not isinstance(system_id, str) or system_id.upper() not in bw_han_system:
#         return {"status": "error", "message": "推送的系统id不存在或者不正确，请重新检查调用工具"}
    
#     # 确保account_info是列表类型
#     if not isinstance(account_info, list):
#         return {"status": "error", "message": "账号列表必须是数组类型"}
    
#     # 处理None值，转换为空列表
#     if group_info is None:
#         group_info = []
#     if role_info is None:
#         role_info = []
    
#     # 确保group_info和role_info是列表类型
#     if not isinstance(group_info, list):
#         return {"status": "error", "message": "用户组列表必须是数组类型"}
#     if not isinstance(role_info, list):
#         return {"status": "error", "message": "权限列表必须是数组类型"}
    
#     # 检查是否包含中文字符（仅当列表不为空时）
#     if account_info and has_chinese_re(" ".join(account_info)):
#         return {"status": "error", "message": "账号列表中存在中文字符，请重新确认值"}
#     if group_info and has_chinese_re(" ".join(group_info)):
#         return {"status": "error", "message": "用户组列表中存在中文字符，请重新确认值"}
#     if role_info and has_chinese_re(" ".join(role_info)):
#         return {"status": "error", "message": "权限列表中存在中文字符，请重新确认值"}
#     if not account_info:
#         return {"status": "error", "message": "用户账号为空，请重新确认值"}
#     elif not group_info and not role_info:
#         return {"status": "error", "message": "用户组和权限角色都为空，请重新确认值"}
#     elif not group_info:
#         result = account_role(mail_id,system_id, account_info, role_info)
#         return result
#     elif not role_info:
#         result = account_usergroup(mail_id,system_id, account_info, group_info)
#         return result
#     else:
#         result = account_usergroup_role(mail_id,system_id, account_info, group_info, role_info)
#         return result

# 账号推送邮件信息获取
# def getmail():
#     from function_call.receive_mail import mail_processed
#     return mail_processed()

# 发送邮件信息
# def sendmail():
#     from function_call.receive_mail import get_re_mail
#     return get_re_mail()