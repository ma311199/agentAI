from flask import Blueprint, request, jsonify, session
from openai import OpenAI
from database import db
from log import logger, error
from models_cache import invalidate_user_models

models_bp = Blueprint('models', __name__)

@models_bp.route('/api/models', methods=['GET'])
def get_models():
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    try:
        models = db.get_user_model_by_id(session['user_id'])
        return jsonify({'models': models})
    except Exception as e:
        logger.error(f"获取模型列表失败: {str(e)}")
        return jsonify({'error': '获取模型列表失败'}), 500

@models_bp.route('/api/models/<int:modelId>', methods=['GET'])
def get_model(modelId):
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    try:
        model = db.get_model_by_id(session['user_id'],modelId)
        if model:
            return jsonify(model)
        else:
            return jsonify({'error': '模型不存在'}), 404
    except Exception as e:
        logger.error(f"获取模型信息失败，无权限处理: {str(e)}")
        return jsonify({'error': '获取模型信息失败，无权限处理'}), 500

@models_bp.route('/api/models', methods=['POST'])
def add_model():
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    try:
        data = request.get_json()
        model_name = data.get('model_name')
        model_url = data.get('model_url')
        api_key = data.get('api_key')
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens', 4096)
        desc = data.get('desc', "暂无")
        # 新增共享标识（0共享，1私有，默认1）
        raw_flag = data.get('model_flag', 1)
        try:
            model_flag = int(raw_flag)
        except Exception:
            model_flag = 1
        model_flag = 0 if model_flag == 0 else 1
        if not model_name or not model_url or not api_key:
            return jsonify({'error': '模型名称、地址和API Key为必填项'}), 400
        success, result = db.add_model(session['user_id'], model_name, model_url, api_key, temperature, max_tokens, desc, model_flag)
        if success:
            # 模型添加成功后失效当前用户的模型缓存
            invalidate_user_models(session['user_id'])
            return jsonify({'success': True, 'model_id': result})
        else:
            return jsonify({'error': result}), 400
    except Exception as e:
        logger.error(f"添加模型失败: {str(e)}")
        return jsonify({'error': '添加模型失败'}), 500

@models_bp.route('/api/models/<int:model_id>', methods=['PUT'])
def update_model(model_id):
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    try:
        data = request.get_json()
        model_name = data.get('model_name')
        model_url = data.get('model_url')
        api_key = data.get('api_key')
        temperature = data.get('temperature')
        max_tokens = data.get('max_tokens')
        is_active = data.get('is_active')
        desc = data.get('desc')
        raw_flag = data.get('model_flag')
        model_flag = None
        if raw_flag is not None:
            try:
                model_flag = int(raw_flag)
            except Exception:
                model_flag = 1
            model_flag = 0 if model_flag == 0 else 1
        if 'is_active' in data and model_name is None and model_url is None and api_key is None and raw_flag is None and desc is None and temperature is None and max_tokens is None:
            success = db.update_model(user_id=session['user_id'], model_id=model_id, is_active=is_active)
        else:
            if not model_name or not model_url or not api_key:
                return jsonify({'error': '模型名称、地址和API Key为必填项'}), 400
            success = db.update_model(user_id=session['user_id'], model_id=model_id, model_name=model_name, model_url=model_url, api_key=api_key, temperature=temperature, max_tokens=max_tokens, is_active=is_active, desc=desc, model_flag=model_flag)
        if success:
            # 模型更新成功后失效当前用户的模型缓存
            invalidate_user_models(session['user_id'])
            return jsonify({'success': True})
        else:
            return jsonify({'error': '模型不存在或更新失败'}), 404
    except Exception as e:
        logger.error(f"更新模型失败: {str(e)}")
        return jsonify({'error': '更新模型失败'}), 500

@models_bp.route('/api/models/<int:model_id>', methods=['DELETE'])
def delete_model(model_id):
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    try:
        user_id = session['user_id']
        # 先检查是否为该用户的模型（或是否存在权限）
        model = db.get_model_by_id(user_id, model_id)
        if not model:
            return jsonify({'error': '模型不存在或无权限删除'}), 404
        success = db.delete_model(user_id, model_id)
        if success:
            # 删除成功后失效当前用户的模型缓存
            invalidate_user_models(user_id)
            return jsonify({'success': True})
        else:
            return jsonify({'error': '删除失败或无权限'}), 400
    except Exception as e:
        logger.error(f"删除模型失败: {str(e)}")
        return jsonify({'error': '删除模型失败'}), 500

@models_bp.route('/api/models/available', methods=['POST'])
def get_available_models():
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    try:
        data = request.get_json() or {}
        model_url = data.get('model_url')
        api_key = data.get('api_key')
        if not model_url or not api_key:
            return jsonify({'error': '模型地址和API Key为必填项'}), 400
        try:
            client = OpenAI(base_url=model_url, api_key=api_key)
            resp = client.models.list()
        except Exception as e:
            logger.error(f"调用模型列表失败: {str(e)}")
            return jsonify({'error': f'调用模型列表失败: {str(e)}'}), 400
        names = []
        try:
            for m in getattr(resp, 'data', []):
                mid = getattr(m, 'id', None)
                if mid:
                    names.append(mid)
        except Exception:
            pass
        if not names:
            try:
                data_list = resp.get('data', []) if isinstance(resp, dict) else []
                for m in data_list:
                    mid = m.get('id') or m.get('model')
                    if mid:
                        names.append(mid)
            except Exception:
                pass
        return jsonify({'models': names})
    except Exception as e:
        logger.error(f"获取可用模型失败: {str(e)}")
        return jsonify({'error': '获取可用模型失败'}), 500