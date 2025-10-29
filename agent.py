from llmclient import LLMClient
from tools import Tool
from typing import Dict, Any, List, Optional
import json,re
from prompt import create_prompt, create_planning_prompt
from log import logger, debug, info, warning, error, critical, exception
from database import db

import datetime

class ReactAgent:
    """增强型React Agent，包含LLM、记忆、规划和工具使用功能"""
    
    def __init__(self, llm: LLMClient ,tools : Dict[str, Tool]):
        self.llm = llm
        self.tools = tools
        info(f"ReactAgent初始化完成，加载工具数量: {len(tools)}")

    def _create_analysis_prompt(self, user_input: str, user_id: int) -> str:
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
        prompt=create_prompt(user_input,tools_schema,history)
        return prompt
        
    def _create_planning_prompt(self, user_input: str, conversation_summary: str) -> str:
        """创建规划提示词"""
        tools_schema = []
        for tool in self.tools.values():
            tools_schema.append(tool.get_schema())
        # print("查看第一个提示词的工具schema: ",tools_schema)
        # 下面创建的规划提示词，包含用户输入、工具schema和对话摘要（历史对话，可以不用添加，根据需要添加，对话的次数我限制为3次）
        prompt = create_planning_prompt(user_input, tools_schema, conversation_summary) 
        return prompt

        
    def parse_user_input(self, user_input: str, user_id: int) -> Dict[str, Any]:
        """使用LLM解析用户输入，选择工具并提取参数"""
        try:
            debug(f"开始解析用户输入: {user_input[:100]}..." if len(user_input) > 100 else f"开始解析用户输入: {user_input}")
            prompt = self._create_analysis_prompt(user_input, user_id)
            # LLM问答
            try:
                response = self.llm.chat(prompt) #获取需要调用的工具和参数
                debug("LLM解析响应获取成功")
            except ConnectionError as ce:
                error(f"网络连接错误: {ce}")
                return {"tool": None, "parameters": {}, "reasoning": "网络连接失败，请检查LLM服务是否可用", "confidence": 0}
            except Exception as e:
                error(f"LLM调用错误: {e}")
                return {"tool": None, "parameters": {}, "reasoning": f"LLM调用异常: {str(e)}", "confidence": 0}

            # 提取JSON
            result = self._extract_json_from_response(response)

            # 验证json格式是否符合工具调用
            if result and self._validate_parsed_result(result):
                return result
            else:
                debug("解析结果验证失败")
                return {"tool": None, "parameters": {}, "reasoning": "解析失败", "confidence": 0}
                
        except Exception as e:
            error(f"解析错误: {e}")
            exception("用户输入解析异常")
            return {"tool": None, "parameters": {}, "reasoning": f"解析异常: {str(e)}", "confidence": 0}
    
    def create_plan(self, user_input: str, user_id: int) -> List[Dict]:
        """为用户输入创建执行计划"""
        try:
            info(f"开始创建执行计划，用户输入: {user_input[:50]}..." if len(user_input) > 50 else f"开始创建执行计划，用户输入: {user_input}")
            # 获取对话摘要
            conversation_summary = self._summarize_conversation(user_id)
            debug(f"对话摘要: {conversation_summary}")
            # 创建规划提示词
            prompt = self._create_planning_prompt(user_input, conversation_summary)
            
            # LLM生成计划
            try:
                response = self.llm.chat(prompt)
                debug("LLM计划生成完成")
            except ConnectionError as ce:
                error(f"网络连接错误: {ce}")
                return [{"step": 1, "action": "直接回答", "reason": "网络连接失败，无法生成详细计划"}]
            except Exception as e:
                error(f"LLM调用错误: {e}")
                return [{"step": 1, "action": "直接回答", "reason": "LLM调用异常，无法生成详细计划"}]
            
            # 解析提取计划
            plan = self._extract_plan_from_response(response)
            debug(f"执行计划创建成功，包含 {len(plan)} 个步骤")
            return plan
        except Exception as e:
            error(f"规划错误: {e}")
            exception("执行计划创建异常")
            return [{"step": 1, "action": "直接回答", "reason": "无法生成执行计划"}]

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
                return json.loads(response)
            except json.JSONDecodeError:
                # 尝试提取JSON部分
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
        except:
            pass
        
        # 如果解析失败，返回默认计划
        return [{"step": 1, "action": "直接回答", "reason": "无法解析计划"}]


    

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
            required_params = [p["name"] for p in tool.parameters if p["required"]]
            missing_params = [param for param in required_params if param not in parameters]
            
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
        info(f"执行工具: {tool_name}, 参数: {parameters}")
        if tool_name not in self.tools:
            error(f"未知工具: {tool_name}")
            raise ValueError(f"未知工具: {tool_name}")
        
        try:
            tool = self.tools[tool_name]  #获取json中的tool(类Tool)
            result = tool.execute(**parameters) # parameters函数参数值
            info(f"工具执行成功: {tool_name}")
            debug(f"工具执行结果: {str(result)[:200]}..." if len(str(result)) > 200 else f"工具执行结果: {result}")
            return result
        except Exception as e:
            error(f"工具执行失败: {tool_name}, 错误: {str(e)}")
            exception("工具执行异常")
            raise
    
    def process_query(self, user_id :int, user_input: str, model_name: str) -> str:
        """处理用户查询，使用React模式：思考、行动、观察、响应"""
        info(f"开始处理用户查询: {user_input[:50]}..." if len(user_input) > 50 else f"开始处理用户查询: {user_input}")
        # 第一步：创建执行计划
        plan = self.create_plan(user_input,user_id)
        
        # 记录执行计划
        execution_summary = f"执行计划: {json.dumps(plan, ensure_ascii=False)}"
        debug(execution_summary)
        
        final_response = ""
        tool_results = []  # 存储所有工具执行结果
        previous_step_result=""   #记录每个问题的执行计划上一步骤结果，实现一个问题里面，当前步骤实现有时需要依赖上一个步骤结果
        # 第二步：执行计划中的每个步骤
        for step in plan:
            step_number = step.get("step", 1)
            action = step.get("action", "直接回答")
            reason = step.get("reason", "")
 
            # 根据动作类型执行不同操作
            if action == "使用工具":
                # 解析用户输入以获取工具信息
                # 对于多步骤计划，我们需要根据当前步骤的reason来确定要使用的工具
                if not previous_step_result:
                    step_specific_input = f"{user_input} (根据计划开始执行第{step_number}步：{reason})"
                else :
                    step_specific_input = f"{user_input} (第{step_number-1}步执行结果：{previous_step_result}；根据计划开始执行第{step_number}步：{reason})"
                # 根据执行计划步骤，使用LLM去生成对应的工具和参数信息
                parsed = self.parse_user_input(step_specific_input, user_id)
                tool_name = parsed.get("tool")
                parameters = parsed.get("parameters", {})
                reasoning = parsed.get("reasoning", "")
                confidence = parsed.get("confidence", 0)
                
                # 如果解析失败，尝试从计划的reason中提取工具名
                if not tool_name and "tool_name" in step:
                    tool_name = step["tool_name"]
                debug(f"调用的工具：{tool_name}, 工具置信度：{confidence}")
                # 获取工具信息以获取tool_id
                tool_info = db.get_function_tool_name(tool_name)
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
                        tool_response = self._format_response(tool_name, parameters, result, reasoning, confidence)
                        tool_results.append(tool_response)
                        
                    except Exception as e:
                        error_msg = f"执行错误: {str(e)}"
                        tool_results.append(error_msg)
                        error(f"调用工具执行错误: {error_msg}")
                        exception("工具调用异常") 
                else:
                    # 如果没有合适的工具，生成直接回答
                    debug(f"没有合适的工具或数据库中无此工具信息{tool_name}，生成直接回答")
                    fallback_answer = self._generate_direct_answer(step_specific_input,user_id)
                    tool_results.append(fallback_answer)
                    debug(f"直接回答生成完成")
            
            elif action == "直接回答":
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
        
        # self.update_memory(user_input, final_response)
        
        # 先输出当前计划，再输出回答
        plan_text = "\n**📋当前执行计划**:\n"
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
    
    def _generate_direct_answer(self, user_input: str, user_id: int) -> str:
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
    
    def _format_response(self, tool_name: str, parameters: Dict, result: Any, 
                        reasoning: str, confidence: float) -> str:
        """格式化响应"""
        tool = self.tools[tool_name]
        
        response = f"\n**🔧工具执行结果如下**: \n"
        response = f"**工具名**: {tool.name}\n"
        response += f"**功能描述**: {tool.description}\n"
        response += f"**参数**: {parameters}\n"
        response += f"**结果**: {result}\n"
        
        if reasoning:
            response += f"**推理过程**: {reasoning}\n"
        response += f"**置信度**: {confidence:.2f}"
        
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
    


