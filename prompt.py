import json
from typing import Dict
# 创建提示词模板
def create_prompt(user_input :str,tools_schema :list, history : str, previous_step_result: str, current_step : Dict) -> str:
    """工具调用提示词，用于生成工具调用的提示词"""
    template = f"""请分析对话历史、用户问题、之前步骤执行记录、当前执行计划，选择合适的工具并提取参数。严格按照JSON格式返回：

    对话历史：{history}
    用户问题：{user_input}
    待执行计划：{json.dumps(current_step, ensure_ascii=False)}
    之前步骤执行记录：{previous_step_result}
    可用工具（格式：工具名 - 描述 - 参数）：
    {json.dumps(tools_schema, ensure_ascii=False, indent=2)}

    请分析用户意图，必须根据本次"待执行计划"生成JSON，选择最合适的工具，并提取相应的参数值，严格对应工具的参数类型传递值。
    

    返回格式必须是严格的JSON：
    {{
        "tool": "工具名称",
        "parameters": {{
            "参数名1": 参数值1,
            "参数名2": 参数值2,
            ...
        }},
        "confidence": 置信度(0-1)
    }}

    重要规则：
    1. 参数名必须与工具定义中的参数名完全一致
    2. 参数值必须转换为正确的类型（数字、字符串等）
    3. 如果无法确定参数，请设置合理的默认值或返回confidence=0
    4. 若还有其他问题会在下一步执行计划进行解决，现在只需要完成本次要求“待执行计划”就行

    示例1：
    用户问题："计算20+40-20"
    之前步骤执行记录：step 1 计划的reason是使用加法工具add完成20+40的计算，其计算结果60；
    待执行计划：{{"step": 2, "action": "使用工具", "reason": "需要使用上一步的计算结果减20进行计算", "tool_name": "subtract"}}       
    返回：{{"tool": "subtract", "parameters": {{"a": 60, "b": 20}},  "confidence": 0.95}}

    示例2：
    用户输入："请把统一身份账号cha1、cha2 ,用户组GCSG11、GCSG13 推送到HP7系统"
    之前步骤执行记录：无
    待执行计划：{{"step": 1, "action": "使用工具", "reason": "用工具accountpush把账号cha1、cha2和对应的用户组GCSG11、GCSG13推送到HP7系统", "tool_name": "accountpush"}} 
    返回：{{"tool": "accountpush", "parameters": {{"system_id": "HP7","account_info": ["cha1","cha2"],"group_info": ["GCSG11","GCSG13"],"role_info": []}}, "confidence": 0.9}}

    请直接返回JSON，不要有其他内容。"""
    return template

# 执行计划提示词
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
    2. 判断是否需要使用工具，或者最终回复，或者追问用户
    3. 如果需要使用工具，确定使用哪些工具以及使用顺序
    4. 为每个步骤制定具体的行动方案
    5. 同一个工具如果完成不了用户的需求的话，那就计划多步执行计划调用多次，列如：计算10-5-5就需要调用两次的sub减法工具。

    执行计划必须是一个JSON数组，每个元素包含以下字段：
    - step: 步骤序号（从1开始）
    - action: 行动类型（"使用工具"、"最终回复"或"追问用户"）
    - reason: 采取该行动的理由,尽量把需要的工具调用的参数值描述在里面。
    - tool_name: 如果action是"使用工具"，请指定工具名称（可选）

    示例输出：
    [
      {{
        "step": 1,
        "action": "使用工具",
        "reason": "用户想要将XX账号和YY用户组推送到HPX中",
        "tool_name": "accountpush"
      }},
      {{
        "step": 2,
        "action": "最终回复",
        "reason": "已完成账号推送的操作，可以总结回答用户"
      }}
      
    ]

    请确保返回格式是有效的JSON数组，不要包含其他解释性文本。"""
    return template



# 执行计划评估提示词
def reevaluatee_planning_prompt(user_input: str, conversation_summary: str, tools_schema: list, completed_steps : dict, tool_execution: list, remaining_steps: list) -> str:
  # 构建重新评估的提示词
  
  prompt = f"""基于已完成的执行步骤和结果，请重新评估并调整后续执行计划。            
用户问题: {user_input}
历史对话:{conversation_summary}
可用工具：
{json.dumps(tools_schema, ensure_ascii=False, indent=2)}
已完成的执行步骤:
{json.dumps(completed_steps, ensure_ascii=False, indent=2)}
已完成的执行步骤及对应执行结果:
{json.dumps(tool_execution, ensure_ascii=False, indent=2)}
当前剩余执行步骤:
{json.dumps(remaining_steps, ensure_ascii=False, indent=2)}

请根据已完成的实际执行结果，决定是否需要调整后续执行计划。考虑以下情况:
1. 是否需要新增步骤
2. 是否需要修改现有步骤的参数或顺序
3. 是否需要提前结束执行
4. 同一个工具如果完成不了用户的需求的话，那就计划多步执行计划调用多次，列如：计算10-5-5就需要调用两次的sub减法工具。
5. 如果之前的步骤已经明确的获取到需要执行的参数，那么就不再需要“追问用户”，直接重新生成后续调用工具的执行执行即可。

请返回完整的新执行计划（包括已完成的步骤），格式为JSON数组。每个步骤应包含:
- step: 步骤序号
- action: 动作类型（使用工具、最终回复、追问用户），最后的一个执行计划就是“最终回复”，可以进行总结工具执行的过程和结果
- reason: 执行理由
- tool_name(可选): 如果action是"使用工具"，可以包含预期使用的工具名

请确保返回的JSON格式正确，不要包含额外的解释文字。
"""
  return prompt