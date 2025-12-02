from flask import Blueprint, request, jsonify, session
import time
from log import logger, debug, error, exception
from agent import ReactAgent
from llmclient import LLMClient
from log import log_db_operation, log_api_call
from tools_cache import get_tools_for_user
from models_cache import get_model_for_user
from database import db

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
    # 使用缓存的工具注册，避免并发下重复构建
    tools_dict = get_tools_for_user(user_id)
    try:
        if model_id:
            # 使用模型缓存获取（支持共享模型 + 私有模型，且只缓存启用）
            model_info = get_model_for_user(user_id, model_id)
            if model_info and model_info['is_active']:
                debug(f"使用指定模型: {model_info['model_name']} (ID: {model_id})")
                llm_client = LLMClient(
                    url=model_info['model_url'],
                    model=model_info['model_name'],
                    api_key=model_info['api_key'] or "",
                    timeout=30
                )
                t_agent = ReactAgent(llm=llm_client, tools=tools_dict)
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
        # 返回结构化的JSON数据，而不是格式化字符串
        return jsonify({
            'status': 'success',
            'total': len(history),
            'items': [
                {
                    'id': i,
                    'model_name': record['model_name'],
                    'user_message': record['user_message'],
                    'bot_response': record['bot_response'],
                    'date': record.get('timestamp', ''),
                    'plan': record.get('plan', '')
                }
                for i, record in enumerate(history, 1)
            ]
        })
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

# 新增：工具执行历史接口，供前端 main.js 调用
@chat_bp.route('/api/execution_history', methods=['GET'])
def get_execution_history():
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    try:
        limit = request.args.get('limit', 10, type=int)
        tool_history = db.get_user_tool_executions(user_id=session['user_id'], limit=limit)
        if not tool_history:
            return jsonify({'response': []})
        result_list = []
        for i, record in enumerate(tool_history, 1):
            execution_result = str(record.get('execution_result', ''))
            # truncated_result = execution_result[:200] + ('...' if len(execution_result) > 200 else '')
            truncated_result = execution_result
            result_list.append({
                'index': i,
                'question': record.get('question'),
                'tool_name': record.get('tool_name'),
                'params': record.get('execution_params'),
                'start_time': record.get('start_time'),
                'end_time': record.get('end_time'),
                'result': truncated_result
            })
        return jsonify({'response': result_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500