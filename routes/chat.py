from flask import Blueprint, request, jsonify, session
import time
import json
from database import db
from log import debug, info, warning, error, exception, log_api_call, log_db_operation
from llmclient import LLMClient
from agent import ReactAgent
from tool_process import Toolregister

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/api/chat', methods=['POST'])
def chat():
    start_time = time.time()
    user_id = session.get('user_id')
    username = session.get('username')
    if 'user_id' not in session:
        log_api_call('/api/chat', 'POST', 401)
        return jsonify({'error': '未登录'}), 401
    data = request.json
    user_input = data.get('message', '')
    session_id = data.get('session_id', 'default')
    model_id = data.get('model_id')
    if not user_input:
        log_api_call('/api/chat', 'POST', 400, user_id, (time.time() - start_time) * 1000)
        return jsonify({'error': '消息不能为空'}), 400
    tool = Toolregister()
    tools = db.get_all_function_tools(user_id)
    def _parse_params(val):
        try:
            if isinstance(val, str):
                return json.loads(val)
            return val
        except Exception:
            try:
                import ast
                return ast.literal_eval(val) if isinstance(val, str) else val
            except Exception:
                return None
    for tool_info in tools:
        tool.register_tool(
            tool_info['tool_name'],
            tool_info['description'],
            tool_info['code_content'],
            _parse_params(tool_info.get('parameters'))
        )
    try:
        if model_id:
            model_info = db.get_model_by_id(model_id)
            if model_info and model_info['is_active']:
                debug(f"使用指定模型: {model_info['model_name']} (ID: {model_id})")
                llm_client = LLMClient(
                    url=model_info['model_url'],
                    model=model_info['model_name'],
                    api_key=model_info['api_key'] or "",
                    timeout=30
                )
                t_agent = ReactAgent(llm=llm_client, tools=tool.tools)
                plan_text, response_text = t_agent.process_query(user_id, user_input, model_info['model_name'])
            else:
                error(f"模型不存在或未启用: {model_id}")
                plan_text = "模型选择无效"
                response_text = "所选模型不存在或未启用，请选择其他模型。"
        else:
            log_api_call('/api/chat', 'POST', 400, user_id, (time.time() - start_time) * 1000)
            return jsonify({'error': '未选择模型，请在左侧启用并选择模型后再发送'}), 400
        log_db_operation('insert', 'chat_records', 'success', f'用户ID: {user_id}, 会话ID: {session_id}')
        log_api_call('/api/chat', 'POST', 200, user_id, (time.time() - start_time) * 1000)
        debug(f"聊天请求处理完成 - 用户ID: {user_id}, 用户名: {username}, 会话ID: {session_id}")
        response = {'response': plan_text+"\n最终回复："+response_text}
        return jsonify(response)
    except Exception as e:
        log_api_call('/api/chat', 'POST', 500, user_id, (time.time() - start_time) * 1000)
        error(f"聊天处理异常 - 用户ID: {user_id}, 错误: {str(e)}")
        exception("聊天处理异常")
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/api/clear_memory', methods=['POST'])
def clear_memory():
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    try:
        data = request.json
        memory_type = data.get('type', 'all')
        valid_types = ['short', 'execution', 'all']
        if memory_type not in valid_types:
            return jsonify({'error': '无效的记忆类型'}), 400
        if memory_type == 'short':
            deleted_count = db.delete_chat_history(session['user_id'])
            if deleted_count >= 0:
                response_text = '✅ 对话记录已清除'
            else:
                raise Exception('清除对话记录失败')
        elif memory_type == 'execution':
            success = db.delete_all_tool_execution(session['user_id'])
            if success:
                response_text = '✅ 工具执行历史已清除'
            else:
                raise Exception('清除工具执行历史失败')
        else:
            chat_deleted = db.delete_chat_history(session['user_id']) >= 0
            execution_deleted = db.delete_all_tool_execution(session['user_id'])
            if chat_deleted and execution_deleted:
                response_text = '✅ 所有记忆已清除'
            else:
                raise Exception('清除所有记忆失败')
        return jsonify({'response': response_text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/api/chat_history', methods=['GET'])
def get_chat_history():
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    try:
        session_id = request.args.get('session_id', 'default')
        limit = request.args.get('limit', 10, type=int)
        history = db.get_chat_history(user_id=session['user_id'], limit=limit)
        response = "📝 **记忆摘要**\n\n展示最近的10次对话历史记录：\n"
        if not history:
            response += "**没有找到对话历史记录。**"
        else:
            for i, record in enumerate(history, 1):
                response += f"记忆 ({i})->模型：{record['model_name']} 【用户问题：“{record['user_message']}”；AGENT回答：“{record['bot_response']}”】\n"
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/api/sessions', methods=['GET'])
def get_sessions():
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    try:
        sessions = db.get_all_sessions(user_id=session['user_id'])
        return jsonify({'sessions': sessions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500