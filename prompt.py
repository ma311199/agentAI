import json
# 创建提示词模板
def create_prompt(user_input :str,tools_schema :list, history : str) -> str:
    """工具调用提示词，用于生成工具调用的提示词"""
    template = f"""请分析用户问题和之前对话历史，选择合适的工具并提取参数。严格按照JSON格式返回：

    用户问题："{user_input}"
    对话历史: {history}
    可用工具（格式：工具名 - 描述 - 参数）：
    {json.dumps(tools_schema, ensure_ascii=False, indent=2)}

    请分析用户意图，选择最合适的工具，并提取相应的参数值。
    

    返回格式必须是严格的JSON：
    {{
        "tool": "工具名称",
        "parameters": {{
            "参数名1": 参数值1,
            "参数名2": 参数值2,
            ...
        }},
        "reasoning": "选择该工具和参数的理由",
        "confidence": 置信度(0-1)
    }}

    重要规则：
    1. 参数名必须与工具定义中的参数名完全一致
    2. 参数值必须转换为正确的类型（数字、字符串等）
    3. 如果无法确定参数，请设置合理的默认值或返回confidence=0

    示例1：
    用户输入："计算20+40-20 （第1步执行结果：60；根据计划开始执行第2步计算60减20）"
    返回：{{"tool": "subtract", "parameters": {{"a": 60, "b": 20}}, "reasoning": "用户要求加法运算", "confidence": 0.95}}

    示例2：
    用户输入："查看人工智能信息 （根据计划开始执行第1步，搜索人工智能）"
    返回：{{"tool": "search", "parameters": {{"query": "人工智能"}}, "reasoning": "用户要求搜索信息", "confidence": 0.9}}

    请直接返回JSON，不要有其他内容。"""
    return template


def create_planning_prompt(user_input: str, tools_schema: list, conversation_summary: str) -> str:
    """创建规划提示词，用于生成执行计划"""
    template = f"""请根据用户问题、对话历史和可用工具，为AI助手创建一个详细的执行计划。

    用户问题："{user_input}"

    对话历史摘要：
    {conversation_summary}

    可用工具：
    {json.dumps(tools_schema, ensure_ascii=False, indent=2)}

    请按照以下步骤思考：
    1. 分析用户的真实意图和需求
    2. 判断是否需要使用工具，或者直接回答，或者追问用户
    3. 如果需要使用工具，确定使用哪些工具以及使用顺序
    4. 为每个步骤制定具体的行动方案

    执行计划必须是一个JSON数组，每个元素包含以下字段：
    - step: 步骤序号（从1开始）
    - action: 行动类型（"使用工具"、"直接回答"或"追问用户"）
    - reason: 采取该行动的理由
    - tool_name: 如果action是"使用工具"，请指定工具名称（可选）

    示例输出：
    [
      {{
        "step": 1,
        "action": "使用工具",
        "reason": "用户需要天气信息，使用weather工具查询天气",
        "tool_name": "weather"
      }},
      {{
        "step": 2,
        "action": "直接回答",
        "reason": "已获取天气信息，可以总结回答用户"
      }}
      
    ]

    请确保返回格式是有效的JSON数组，不要包含其他解释性文本。"""
    return template


def create_memory_prompt(user_input: str, conversation_history: list) -> str:
    """创建记忆处理提示词，用于分析和处理长期重要记忆"""
    template = f"""请分析以下对话内容，提取重要信息用于记忆存储：

    用户最新问题："{user_input}"

    对话历史：
    {json.dumps(conversation_history, ensure_ascii=False, indent=2)}

    请分析：
    1. 对话中是否包含需要长期记忆的重要信息
    2. 如果有，这些信息的关键要点是什么
    3. 这些信息的重要程度如何（1-5分）

    返回格式：
    {{
      "important": true/false,
      "key_points": ["要点1", "要点2", ...],
      "importance_score": 1-5
    }}

    请直接返回JSON，不要有其他内容。"""
    return template



