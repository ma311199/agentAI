from llmclient import LLMClient
from tools import Tool
from typing import Dict, Any, List, Optional
import json,re
from prompt import create_prompt, create_planning_prompt,reevaluatee_planning_prompt
from log import logger, debug, info, warning, error, critical, exception
from database import db

import datetime

class ReactAgent:
    """增强型React Agent，包含LLM、记忆、规划和工具使用功能"""
    
    def __init__(self, llm: LLMClient ,tools : Dict[str, Tool]):
        self.llm = llm
        self.tools = tools
        info(f"ReactAgent初始化完成，加载工具数量: {len(tools)}")

    def _create_analysis_prompt(self, user_input: str, user_id: int, previous_step_result: str, current_step: Dict) -> str:
        """创建分析用户输入内容，工具选择和参数输入提示词"""
        tools_schema = []
        for tool in self.tools.values():
            tools_schema.append(tool.get_schema())
        # 历史对话，这里的历史对话是短期记忆，包含最近的3次对话，必须添加，否则LLM会忘记之前的对话，因为这里是基于最近的对话去生成执行的工具信息，
        # 如果不添加，LLM会基于当前对话去生成执行的工具信息，而不是基于之前的对话去生成执行的工具信息，这样会导致工具的参数传递出问题
        # 例如当前问题的请问，是基于上一个问题的结果，现在需要把上一个问题的结果添加为当前问题中工具调用的某一个参数值
        # print("查看第二个提示词的工具schema: ",tools_schema)
        history=self._summarize_conversation(user_id)
        # print("查看第二个提示词的历史记录: ",history)
        # 提示词
        prompt=create_prompt(user_input,tools_schema,history,previous_step_result, current_step)
        return prompt

        
    def _create_planning_prompt(self, user_input: str, conversation_summary: str) -> str:
        """创建规划提示词"""
        tools_schema = []
        for tool in self.tools.values():
            tools_schema.append(tool.get_schema())
        # print("查看第一个提示词的工具schema: ",tools_schema)
        # 下面创建的规划提示词，包含用户输入、工具schema和对话摘要（历史对话，可以不用添加，根据需要添加，对话的次数我限制为3次）
        prompt = create_planning_prompt(user_input, tools_schema, conversation_summary)
        print("查看提示词信息：",prompt) 
        return prompt

        
    def parse_user_input(self, user_input: str, user_id: int,previous_step_result: str, current_step: Dict) -> Dict[str, Any]:
        """使用LLM解析用户输入，选择工具并提取参数（带重试机制）"""
        max_retries = 3 # 最大重试次数
        retry_count = 0 # 当前重试次数
        
        try:
            debug(f"开始执行current_step: {current_step}")
            prompt = self._create_analysis_prompt(user_input, user_id, previous_step_result, current_step)

            while retry_count < max_retries:
                retry_count += 1
                debug(f"第 {retry_count} 次尝试解析LLM返回的工具JSON串")
                
                # LLM问答
                try:
                    response = self.llm.chat(prompt) #获取需要调用的工具和参数
                    debug(f"LLM返回工具JSON串:\n{response}")
                except ConnectionError as ce:
                    error(f"网络连接错误: {ce}")
                    if retry_count == max_retries:
                        return {"tool": None, "parameters": {}, "reasoning": "网络连接失败，请检查LLM服务是否可用", "confidence": 0}
                    else:
                        debug(f"网络连接失败，第 {retry_count} 次尝试，将进行重试")
                        continue
                except Exception as e:
                    error(f"LLM调用错误: {e}")
                    if retry_count == max_retries:
                        return {"tool": None, "parameters": {}, "reasoning": f"LLM调用异常: {str(e)}", "confidence": 0}
                    else:
                        debug(f"LLM调用错误，第 {retry_count} 次尝试，将进行重试")
                        continue

                # 提取JSON
                result = self._extract_json_from_response(response)
                
                if not result:
                    debug(f"第 {retry_count} 次尝试：未提取到有效JSON，将重试")
                    if retry_count == max_retries:
                        return {"tool": None, "parameters": {}, "reasoning": "LLM生成的工具参数json错误", "confidence": 0}
                    continue

                # 验证json格式是否符合工具调用
                if result and self._validate_parsed_result(result):
                    debug(f"第 {retry_count} 次尝试：验证成功，返回结果")
                    return result
                else:
                    debug(f"第 {retry_count} 次尝试：解析结果验证失败")
                    if retry_count == max_retries:
                        return {"tool": None, "parameters": {}, "reasoning": "LLM生成的工具参数json错误", "confidence": 0}
                    continue
            
            # 如果所有重试都失败
            debug(f"所有 {max_retries} 次尝试均失败")
            return {"tool": None, "parameters": {}, "reasoning": "LLM生成的工具参数json错误", "confidence": 0}
                
        except Exception as e:
            error(f"解析错误: {e}")
            exception("用户输入解析异常")
            return {"tool": None, "parameters": {}, "reasoning": f"解析异常: {str(e)}", "confidence": 0}
    
    def create_plan(self, user_input: str, user_id: int) -> List[Dict]:
        """为用户输入创建执行计划"""
        try:
            info(f"开始创建执行计划，用户输入: {user_input[:100]}..." if len(user_input) > 100 else f"开始创建执行计划，用户输入: {user_input}")
            # 获取对话摘要
            conversation_summary = self._summarize_conversation(user_id)
            debug(f"历史对话: {conversation_summary}")
            # 创建规划提示词
            prompt = self._create_planning_prompt(user_input, conversation_summary)
            
            max_retries = 3
            retry_count = 0
            plan = None
            
            while retry_count < max_retries and plan is None:
                # LLM生成计划
                try:
                    response = self.llm.chat(prompt)
                    debug(f"LLM计划生成完成 (尝试 {retry_count + 1}/{max_retries})")
                    
                    # 尝试解析提取计划
                    try:
                        plan = self._extract_plan_from_response(response)
                        debug(f"执行计划解析成功，包含 {len(plan)} 个步骤")
                    except ValueError as parse_error:
                        error(f"计划解析失败 (尝试 {retry_count + 1}/{max_retries}): {parse_error}")
                        retry_count += 1
                        # 如果还有重试机会，修改提示词以改进结果
                        if retry_count < max_retries:
                            continue
                        # 达到最大重试次数，返回错误
                        return [{"step": 1, "action": "最终回复", "reason": "多次尝试后仍无法解析执行计划"}]
                
                except ConnectionError as ce:
                    error(f"网络连接错误: {ce}")
                    return [{"step": 1, "action": "最终回复", "reason": "网络连接失败，无法生成详细计划"}]
                except Exception as e:
                    error(f"LLM调用错误: {e}")
                    retry_count += 1
                    # 如果还有重试机会，继续
                    if retry_count < max_retries:
                        continue
                    return [{"step": 1, "action": "最终回复", "reason": "多次尝试后LLM调用仍异常，无法生成详细计划"}]
            
            return plan if plan is not None else [{"step": 1, "action": "最终回复", "reason": "无法生成有效的执行计划"}]
        except Exception as e:
            error(f"规划错误: {e}")
            exception("执行计划创建异常")
            return [{"step": 1, "action": "最终回复", "reason": "无法生成执行计划"}]

    def create_new_plan(self, user_input: str, user_id: int, completed_steps: list,tool_execution: list,remaining_steps: list) -> List[Dict]:
        """为用户输入创建执行计划"""
        try:
            # 获取对话摘要
            conversation_summary = self._summarize_conversation(user_id)
            # 获取当前会话缓存的可用工具信息
            tools_schema = []
            for tool in self.tools.values():
                tools_schema.append(tool.get_schema())
            # 评估创建的提示词
            prompt = reevaluatee_planning_prompt(user_input,conversation_summary,tools_schema,completed_steps,tool_execution,remaining_steps)
            
            max_retries = 3
            retry_count = 0
            plan = None
            
            while retry_count < max_retries and plan is None:
                # LLM生成评估的执行计划
                try:
                    response = self.llm.chat(prompt)
                    debug(f"LLM评估执行计划生成完成 (尝试 {retry_count + 1}/{max_retries})")
                    
                    # 尝试解析提取计划
                    try:
                        plan = self._extract_plan_from_response(response)
                        debug(f"评估执行计划解析成功，包含 {len(plan)} 个步骤")
                    except ValueError as parse_error:
                        error(f"评估计划解析失败 (尝试 {retry_count + 1}/{max_retries}): {parse_error}")
                        retry_count += 1
                        # 如果还有重试机会，修改提示词以改进结果
                        if retry_count < max_retries:
                            continue
                        # 达到最大重试次数，返回错误
                        return [{"step": 1, "action": "最终回复", "reason": "多次尝试后仍无法解析执行计划"}]
                
                except ConnectionError as ce:
                    error(f"网络连接错误: {ce}")
                    return [{"step": 1, "action": "最终回复", "reason": "网络连接失败，无法生成详细计划"}]
                except Exception as e:
                    error(f"LLM调用错误: {e}")
                    retry_count += 1
                    # 如果还有重试机会，继续
                    if retry_count < max_retries:
                        continue
                    return [{"step": 1, "action": "最终回复", "reason": "多次尝试后LLM调用仍异常，无法生成详细计划"}]
            
            return plan if plan is not None else [{"step": 1, "action": "最终回复", "reason": "无法生成有效的执行计划"}]
        except Exception as e:
            error(f"规划错误: {e}")
            exception("执行计划创建异常")
            raise ValueError("无法返回正确的JSON执行计划")

    # 提取最终结果
    def _parsed_repose(self,response) -> str:
        """从响应中提取最终回答结果，保留</think>标记后的内容"""
        debug(f"开始解析响应内容，长度: {len(response)} 字符")
        try:
            # 提取</think>标签后的内容
            if '</think>' in response:
                response = response.split('</think>')[-1]
            return response.strip()
        except Exception as e:
            debug(f"解析响应时发生错误: {str(e)}")
            return response.strip()

    def _summarize_conversation(self,user_id: int) -> str:
        """总结对话历史"""
        history = db.get_chat_history(user_id,3) # 获取最近的3条历史对话记录
        debug(f"总结对话历史，总记录数: {len(history)}")
        if not history:
            debug("对话历史为空")
            return "暂无历史对话"
        summary = "\n".join([f"[用户问题: {record['user_message']}; AI回应: {record.get('bot_response', '无结果')}]" for record in history])
        # 限制总结的对话数量
        debug(f"对话历史总结完成，摘要长度: {len(summary)} 字符")
        return summary
    
    # 解析LLM返回的执行计划列表
    def _extract_plan_from_response(self, response: str) -> List[Dict]:
        """从LLM响应中提取执行计划"""
        # print(f"LLM制定执行计划返回: {response}")
        try:
            # 尝试直接解析JSON
            try:
                plan = json.loads(response)
                # 验证解析结果是否为列表且包含必要字段
                if isinstance(plan, list) and all(isinstance(item, dict) and 'step' in item and 'action' in item and 'reason' in item for item in plan):
                    return plan
                else:
                    raise ValueError("解析结果格式不符合预期")
            except json.JSONDecodeError:
                # 尝试提取JSON部分
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if json_match:
                    plan = json.loads(json_match.group())
                    # 验证提取后的结果
                    if isinstance(plan, list) and all(isinstance(item, dict) and 'step' in item and 'action' in item and 'reason' in item for item in plan):
                        return plan
                    else:
                        raise ValueError("提取的JSON格式不符合预期")
                else:
                    raise ValueError("无法在响应中找到有效的JSON数组")
        except Exception as e:
            # 解析失败时抛出异常，触发重试机制
            raise ValueError(f"计划解析失败: {str(e)}")


    

    # 提取LLM返回的工具信息
    def _extract_json_from_response(self, response_text: str) -> Optional[Dict]:
        """从响应中提取JSON"""
        try:
            # 清理响应文本
            cleaned_text = response_text.strip()
            
            # 尝试直接解析
            return json.loads(cleaned_text)
        except json.JSONDecodeError:
            # 尝试提取JSON对象
            json_match = re.search(r'```json\s*({.*?})\s*```', cleaned_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            
            # 尝试直接匹配JSON对象（即使没有 ```json 标记）
            json_match = re.search(r'(\{.*?\})', cleaned_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            
            return None
    
    def _validate_parsed_result(self, result: Dict) -> bool:
        """验证解析结果的有效性，格式和tool是否存在"""
        try:
            debug(f"开始验证解析结果，类型: {type(result).__name__}")
            if not isinstance(result, dict):
                debug("验证失败: 解析结果不是字典类型")
                return False
            
            tool_name = result.get("tool")
            parameters = result.get("parameters", {})
            
            if not tool_name:
                debug("验证失败: 工具名称为空")
                return False
                
            if tool_name not in self.tools:
                debug(f"验证失败: 工具 {tool_name} 不存在")
                return False
            
            if not isinstance(parameters, dict):
                debug("验证失败: 参数不是字典类型")
                return False
            
            # 检查必需参数
            tool = self.tools[tool_name]
            
            # 添加原工具参数与生成的JSON参数的对比检查
            original_params = {param["name"]: param for param in tool.parameters}  # 原工具参数定义
            
            # 检查原工具参数是否为空
            if not original_params:
                debug("警告: 原工具参数定义为空")
            
            # 比较原工具参数与生成的JSON参数
            extra_params = [param_name for param_name in parameters if param_name not in original_params]
            if extra_params:
                debug(f"警告: 生成的JSON参数中包含原工具未定义的参数: {extra_params}")
                return False
            
            required_params = [p["name"] for p in tool.parameters if p["required"]] #获取到内存中的tool工具参数（必填）名称
            missing_params = [param for param in required_params if param not in parameters] #遍历参数名和模型返回的参数信息进行对比，查看是否存在，如果不存在，则返回
            # 验证参数类型是否匹配
            type_errors = []  # 存储类型错误信息
            for param_def in tool.parameters:  # 遍历工具的参数定义
                param_name = param_def["name"]
                if param_name in parameters:  # 如果参数有传入值
                    expected_type = param_def.get("type", "any")  # 获取工具定义参数类型
                    actual_value = parameters[param_name]  # 获取LLM实际传入的值
                    actual_type = type(actual_value).__name__  # 获取LLM实际类型名称
                    # 检查类型是否匹配
                    if expected_type == "any":
                        continue  # 任何类型都可以
                    elif expected_type == "list" and not isinstance(actual_value, (list, tuple)):
                        type_errors.append(f"{param_name}: 期望 {expected_type} 类型，实际为 {actual_type}")
                    elif expected_type == "dict" and not isinstance(actual_value, dict):
                        type_errors.append(f"{param_name}: 期望 {expected_type} 类型，实际为 {actual_type}")
                    elif expected_type in ["str", "string"] and not isinstance(actual_value, str):
                        type_errors.append(f"{param_name}: 期望 {expected_type} 类型，实际为 {actual_type}")
                    elif expected_type in ["int", "integer"] and not isinstance(actual_value, int):
                        type_errors.append(f"{param_name}: 期望 {expected_type} 类型，实际为 {actual_type}")
                    elif expected_type in ["float", "number"] and not isinstance(actual_value, (int, float)):
                        type_errors.append(f"{param_name}: 期望 {expected_type} 类型，实际为 {actual_type}")
                    elif expected_type == "bool" and not isinstance(actual_value, bool):
                        type_errors.append(f"{param_name}: 期望 {expected_type} 类型，实际为 {actual_type}")
            
            # 如果有类型错误，记录并返回验证失败
            if type_errors:
                debug(f"验证失败: 参数类型不匹配: {'; '.join(type_errors)}")
                return False

            if missing_params:
                debug(f"验证失败: 缺少必需参数: {missing_params}")
                return False
            
            debug(f"验证成功: 工具 {tool_name} 的参数有效")
            return True
        except Exception as e:
            debug(f"验证异常: {e}")
            return False
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """执行工具"""
        info(f"执行工具{tool_name}, 参数: {parameters}")
        if tool_name not in self.tools:
            error(f"未知工具: {tool_name}")
            raise ValueError(f"未知工具: {tool_name}")
        
        try:
            tool = self.tools[tool_name]  #获取json中的tool(类Tool)
            result = tool.execute(**parameters) # parameters函数参数值
            debug(f"{tool_name}执行结果: \n{str(result)[:200]}..." if len(str(result)) > 200 else f"工具执行结果: {result}")
            return result
        except Exception as e:
            error(f"工具执行失败: {tool_name}, 错误: {str(e)}")
            exception("工具执行异常")
            raise
    
    def process_query(self, user_id :int, user_input: str, model_name: str) -> str:
        """处理用户查询，使用React模式：思考、行动、观察、响应"""
        info(f"开始处理用户查询: {user_input[:100]}..." if len(user_input) > 100 else f"开始处理用户查询: {user_input}")
        # 第一步：创建执行计划
        plan = self.create_plan(user_input,user_id)
        
        # 记录执行计划
        execution_summary = f"执行计划:\n {json.dumps(plan, ensure_ascii=False)}"
        debug(execution_summary)
        
        final_response = ""
        tool_results = []  # 存储所有工具执行结果，用于最终生成回答
        tool_execution=[]  # 存储所有工具执行结果，用于“评估计划生成”
        reasoning="" #保存每一个步骤的执行理由
        previous_step_result=""   #记录每个问题的执行计划上一步骤结果，实现一个问题里面，当前步骤实现有时需要依赖上一个步骤结果
        
        # 跟踪当前执行的步骤索引
        current_step_index = 0
        
        # 第二步：执行计划中的每个步骤
        while current_step_index < len(plan):
            step = plan[current_step_index]
            step_number = step.get("step", 1)
            action = step.get("action", "最终回复")
            reason = step.get("reason", "")
 
            # 根据动作类型执行不同操作
            if action == "使用工具":
                # 解析用户输入以获取工具信息
                # 对于多步骤计划，我们需要根据当前步骤的reason来确定要使用的工具和参数
                if previous_step_result:
                    step_specific_input = f"step {step_number-1} 计划的reason是“{reasoning}” 其执行结果是”{previous_step_result}“；"
                else:
                    step_specific_input="暂无，请先完成第一步待执行计划"
                # 根据执行计划步骤，使用LLM去生成对应的工具和参数信息
                parsed = self.parse_user_input(user_input, user_id, step_specific_input,step)
                tool_name = parsed.get("tool")
                parameters = parsed.get("parameters", {})
                reasoning = reason
                confidence = parsed.get("confidence", 0)
                
                # 如果解析失败，尝试从计划的reason中提取工具名
                if not tool_name and "tool_name" in step:
                    tool_name = step["tool_name"]
                debug(f"调用的工具：{tool_name}, 工具置信度：{confidence}")
                # 获取工具信息以获取tool_id
                tool_info = db.get_tool_name(tool_name)
                tool_id = tool_info['tool_id'] if tool_info else None
                if tool_id and confidence >= 0.3:
                    try:
                        # 根据执行计划中的工具和参数，执行工具
                        execution_start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") # 记录开始时间（年月日时分秒格式）
                        result = self.execute_tool(tool_name, parameters)
                        execution_end_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") # 记录结束时间
                        previous_step_result=result  #保存当前结果
                        
                        # 记录工具执行信息
                        execution_params_str = json.dumps(parameters, ensure_ascii=False)
                        execution_result_str = json.dumps(result, ensure_ascii=False) if not isinstance(result, str) else result
                        execution_steps = json.dumps({
                            'step': step_number,
                            'reasoning': reasoning,
                            'confidence': confidence
                        }, ensure_ascii=False)
                        # 记录工具执行信息
                        db.add_tool_execution(
                            user_id=user_id,
                            tool_id=tool_id,
                            tool_name=tool_name,
                            question=user_input,
                            execution_steps=execution_steps,
                            execution_params=execution_params_str,
                            execution_result=execution_result_str,
                            execution_status="success",
                            start_time=execution_start_time,
                            end_time=execution_end_time
                        )
                        
                        # 格式化存储工具执行结果
                        tool_execution.append({"step":step_number,"tool_name":tool_name,"工具执行结果":result})
                        tool_response = self._format_response(step_number,tool_name, parameters, result, reasoning, confidence)
                        tool_results.append(tool_response)
                        
                    except Exception as e:
                        error_msg = f"执行错误: {str(e)}"
                        tool_results.append(error_msg)
                        error(f"调用工具执行错误: {error_msg}")
                        exception("工具调用异常") 
                else:
                    # 如果没有合适的工具，生成直接回答
                    debug(f"没有合适的工具或数据库中无此工具信息{tool_name}，生成最终回复")
                    fallback_answer = self._generate_direct_answer(user_input,user_id)
                    tool_results.append(fallback_answer)
                    debug(f"最终回复生成完成")
            
            elif action == "最终回复":
                # 对于直接回答，使用所有工具执行结果作为上下文
                try:
                    # 调用LLM生成总结回答,这里不需要添加历史对话，因为直接回答是基于当前问题的工具执行结果，而不是基于之前的对话
                    if tool_results:
                    # 构建包含所有工具结果的提示词文本字符串
                        context = "\n\n".join(tool_results)
                        debug(f"工具返回的结果：\n{context}")
                        direct_answer_prompt = f"""基于以下工具执行结果，总结回答用户问题：
                                                用户问题: {user_input}

                                                工具执行结果:
                                                {context}

                                                请提供一个简洁、友好的总结回答。"""
                        response = self.llm.chat(direct_answer_prompt)
                        final_response = response.strip()
                        debug("根据工具执行结果总结回答生成成功")
                    else:
                        final_response = self._generate_follow_up_question(user_input)
                        debug("没有调用工具，直接总结回答生成成功")

                except Exception as e:
                    error(f"生成总结回答失败: {str(e)}")
                    # 如果LLM调用失败，使用工具结果的简单拼接
                    result_lines = []
                    for r in tool_results:
                        if "**结果**: " in r:
                            result_part = r.split("**结果**: ")[-1]
                            first_line = result_part.split("\n")[0]
                            result_lines.append(f"- {first_line}")
                    final_response = "根据工具处理结果：\n" + "\n".join(result_lines)

                break  # 直接回答步骤是最后一步，执行完后可以跳出循环
            
            elif action == "追问用户":
                # 生成追问
                final_response = self._generate_follow_up_question(user_input)
                # print(final_response)
                break  # 追问后需要用户输入，跳出循环
            
            else:
                # 未知动作类型，默认直接回答
                final_response = self._generate_direct_answer(user_input, user_id)
                # print(final_response)
                break
            
            # 动态调整计划：在步骤执行完成后，如果不是最后一步，重新评估计划
            if action != "最终回复" and action != "追问用户" and current_step_index < len(plan) - 1:
                try:
                    # 调用LLM评估并可能调整后续计划
                    updated_plan = self._reevaluate_plan(
                        user_input, 
                        user_id, 
                        plan, 
                        current_step_index, 
                        tool_execution
                    )
                    if updated_plan and len(updated_plan) > 0:
                        plan = updated_plan
                        debug(f"执行计划已动态调整，新计划包含 {len(plan)} 个步骤")
                except Exception as e:
                    error(f"动态调整计划失败: {str(e)}")
                    # 继续使用原计划
            
            # 移动到下一个步骤
            current_step_index += 1
        
        
        # 先输出当前计划，再输出回答
        plan_text = "\n📋执行计划:\n"
        if plan:
            for i, step in enumerate(plan, 1):
                action = step.get("action", "未知动作")
                reason = step.get("reason", "")
                plan_text += f"步骤{i}：{action}"
                if reason:
                    plan_text += f" - {reason}"
                plan_text += "\n"
        else:
            plan_text += "暂无执行计划\n"
        # 存储对话记录到数据库
        debug("存储Agent记忆")
        db.add_chat_record(
            user_message=user_input,
            plan=plan_text,
            bot_response=self._parsed_repose(final_response),
            user_id=user_id,
            model_name=model_name
        )

        info("用户查询处理完成")
        return plan_text ,final_response
    
    def _generate_direct_answer(self, user_input: str,user_id: int) -> str:
        """直接生成回答，不使用工具"""
        try:
            # 构建直接回答的提示词
            prompt = f"""
            请直接回答用户的问题，不需要调用工具：
            用户问题：{user_input}
            
            历史对话：
            {self._summarize_conversation(user_id)}
            
            请提供一个自然、友好的回答。
            """
            
            try:
                response = self.llm.chat(prompt)
                return response.strip()
            except ConnectionError:
                return "抱歉，我暂时无法连接到语言模型服务。请稍后再试。"
            except Exception as e:
                return f"抱歉，生成回答时出错: {str(e)}"
        except Exception as e:
            return f"生成回答时出错: {str(e)}"
    
    def _reevaluate_plan(self, user_input: str, user_id: int, current_plan: List[Dict], 
                        completed_step_index: int, tool_execution: List[Dict]) -> List[Dict]:
        """重新评估并可能调整执行计划
        
        Args:
            user_input: 用户的原始问题
            user_id: 用户ID
            current_plan: 当前的执行计划
            completed_step_index: 已完成的步骤索引
            tool_execution: 已执行的工具结果列表
            
        Returns:
            调整后的执行计划
        """
        try:
            info("开始重新评估执行计划")
            
            # 准备上下文信息
            completed_steps = current_plan[:completed_step_index + 1]
            remaining_steps = current_plan[completed_step_index + 1:]
            try:
                reevaluate_plan=self.create_new_plan(user_input,user_id,completed_steps,tool_execution,remaining_steps)
                info(f"LLM重新评估计划结果生成完成:\n{reevaluate_plan}")
                return reevaluate_plan
            except ConnectionError as ce:
                error(f"网络连接错误，解析失败，返回原执行计划: {ce}")
                return current_plan
            except Exception as e:
                error(f"LLM调用错误，解析失败，返回原执行计划: {e}")
                return current_plan
        except Exception as e:
            error(f"重新评估计划异常: {str(e)}")
            exception("计划重新评估异常")
            # 发生异常时返回原始计划
            return current_plan
    
    def _generate_follow_up_question(self, user_input: str) -> str:
        """生成追问用户的问题"""
        try:
            # 构建追问提示词
            prompt = f"""
            用户的问题缺少一些必要信息，请生成一个友好的追问：
            用户问题：{user_input}
            
            请生成一个简洁、明确的追问，帮助获取更多信息以便更好地回答问题。
            """
            
            try:
                response = self.llm.chat(prompt)
                return response.strip()
            except ConnectionError:
                return "为了更好地帮助您，我需要一些额外信息。您能提供更多细节吗？"
            except Exception as e:
                return "为了更好地帮助您，我需要一些额外信息。您能提供更多细节吗？"
        except Exception as e:
            return "为了更好地帮助您，我需要一些额外信息。您能提供更多细节吗？"
    
    def _format_response(self, step_number :int,tool_name: str, parameters: Dict, result: Any, 
                        reasoning: str, confidence: float) -> str:
        """格式化响应"""
        tool = self.tools[tool_name]

        response = f"step: {step_number}\n"
        response += f"tool_name: {tool.name}\n"
        response += f"功能描述: {tool.description}\n"
        response += f"参数: {parameters}\n"
        response += f"工具执行结果: {result}\n"
        
        if reasoning:
            response += f"推理过程: {reasoning}\n\n"
        # response += f"置信度: {confidence:.2f}"
        
        return response
    
    
    def get_execution_history(self,user_id: int ,limit: int = 5) -> list:
        """获取工具执行历史（返回列表格式）"""
        tool_history = db.get_user_tool_executions(user_id=user_id, limit=limit)
        if not tool_history:
            return []
        
        # 返回列表格式，每个元素是包含执行历史详情的字典
        result_list = []
        for i, record in enumerate(tool_history, 1):
            # 限制结果显示长度
            execution_result = str(record['execution_result'])
            truncated_result = execution_result[:100] + ('...' if len(execution_result) > 100 else '')
            result_list.append({
                'index': i,
                'question': record['question'],
                'tool_name': record['tool_name'],
                'params': record['execution_params'],
                'start_time': record['start_time'],
                'end_time': record['end_time'],
                'result': truncated_result
            })
        
        return result_list
    
    
    def _get_current_time(self) -> str:
        """获取当前时间"""
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        debug(f"获取当前时间: {current_time}")
        return current_time
    


