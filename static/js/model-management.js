// 确保DOM加载完成后再执行代码
document.addEventListener('DOMContentLoaded', function() {
    // 添加模型模态框
    function showAddModelModal() {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white rounded-lg p-6 max-w-xl w-full overflow-y-auto" style="height: 66vh;">
                <h2 class="text-xl font-semibold mb-4">添加模型</h2>
                <div class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700">模型地址 (URL)</label>
                        <input type="text" id="newModelUrl" class="w-full px-3 py-2 rounded-md border border-gray-300" placeholder="例如：https://api.openai.com/v1">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">API Key</label>
                        <input type="text" id="newModelApiKey" class="w-full px-3 py-2 rounded-md border border-gray-300" placeholder="填写对应提供商的Key">
                        <p class="text-xs text-gray-500 mt-1">根据地址和API Key获取可用模型</p>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">模型名称</label>
                        <div class="flex space-x-2">
                            <input type="text" id="newModelName" list="availableModelDatalist" class="flex-1 w-full px-3 py-2 rounded-md border border-gray-300" placeholder="例如：gpt-4o-mini">
                            <button id="fetchModelsBtn" class="px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">获取模型</button>
                        </div>
                        <datalist id="availableModelDatalist"></datalist>
                        <p class="text-xs text-gray-500 mt-1">点击“获取模型”后，可在上方输入框下拉选择</p>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">Temperature</label>
                        <input type="number" id="newModelTemperature" class="w-full px-3 py-2 rounded-md border border-gray-300" value="0.7" step="0.1" min="0" max="2">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">Max Tokens</label>
                        <input type="number" id="newModelMaxTokens" class="w-full px-3 py-2 rounded-md border border-gray-300" value="4096" min="1024" max="32768">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">描述</label>
                        <input type="text" id="newModelDesc" class="w-full px-3 py-2 rounded-md border border-gray-300" placeholder="可选描述">
                    </div>
                    <div class="pt-1">
                        <label class="inline-flex items-center">
                            <input type="checkbox" id="newModelShared" class="form-checkbox h-4 w-4 text-blue-600">
                            <span class="ml-2 text-sm text-gray-700">共享模型（勾选则其他用户可见）</span>
                        </label>
                    </div>
                    <div class="flex justify-end space-x-3 pt-2">
                        <button id="cancelAddModel" class="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50">取消</button>
                        <button id="confirmAddModel" class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">添加</button>
                    </div>
                </div>
            </div>`;
        document.body.appendChild(modal);
        
        document.getElementById('cancelAddModel').addEventListener('click', () => {
            document.body.removeChild(modal);
        });
        
        document.getElementById('confirmAddModel').addEventListener('click', async () => {
            const modelUrl = document.getElementById('newModelUrl').value;
            const apiKey = document.getElementById('newModelApiKey').value;
            const modelName = document.getElementById('newModelName').value;
            const temperature = parseFloat(document.getElementById('newModelTemperature').value) || 0.7;
            const maxTokens = parseInt(document.getElementById('newModelMaxTokens').value) || 4096;
            const desc = document.getElementById('newModelDesc').value || '暂无';
        
            try {
                const response = await fetch('/api/models', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content || ''
                    },
                    body: JSON.stringify({ model_url: modelUrl, api_key: apiKey, model_name: modelName, temperature, max_tokens: maxTokens, desc, model_flag: (document.getElementById('newModelShared')?.checked ? 0 : 1) })
                });
        
                if (response.ok) {
                    alert('模型添加成功');
                    document.body.removeChild(modal);
                    // 局部刷新模型管理表 + 同步聊天下拉
                    refreshModelList();
                    if (window.loadModels) window.loadModels();
                } else {
                    const errorData = await response.json();
                    alert('添加模型失败: ' + (errorData.error || '未知错误'));
                }
            } catch (error) {
                alert('请求失败: ' + error.message);
            }
        });
        
        const fetchBtn = document.getElementById('fetchModelsBtn');
        const modelDatalist = document.getElementById('availableModelDatalist');
        if (fetchBtn) {
            fetchBtn.onclick = async () => {
                const modelUrl = document.getElementById('newModelUrl').value.trim();
                const apiKey = document.getElementById('newModelApiKey').value.trim();
                if (!modelUrl || !apiKey) {
                    alert('请先填写模型地址和API Key');
                    return;
                }
                try {
                    const resp = await fetch('/api/models/available', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content || ''
                        },
                        body: JSON.stringify({ model_url: modelUrl, api_key: apiKey })
                    });
                    if (!resp.ok) {
                        const text = await resp.text();
                        alert('获取失败: ' + text);
                        return;
                    }
                    const data = await resp.json();
                    const names = data.models || [];
                    modelDatalist.innerHTML = '';
                    if (names.length === 0) {
                        alert('未获取到可用模型');
                        return;
                    }
                    names.forEach(name => {
                        const opt = document.createElement('option');
                        opt.value = name;
                        modelDatalist.appendChild(opt);
                    });
                    // 使用 datalist 提供下拉建议，用户可在输入框中选择或输入
                } catch (error) {
                    alert('错误: ' + error.message);
                }
            };
        }
    }
    
    // 局部刷新模型管理表（侧边面板的表格）
    async function refreshModelList() {
        try {
            const resp = await fetch('/api/models');
            if (!resp.ok) {
                throw new Error('获取模型列表失败');
            }
            const data = await resp.json();
            renderModelRows(Array.isArray(data.models) ? data.models : []);
        } catch (e) {
            console.error('刷新模型列表失败:', e);
        }
    }

    function renderModelRows(models) {
        const tbody = document.querySelector('#modelsSubContent table tbody');
        if (!tbody) return;
        if (!models || models.length === 0) {
            tbody.innerHTML = `<tr><td colspan="9" class="px-3 py-4 text-center text-sm text-gray-500">暂无模型信息</td></tr>`;
            return;
        }
        const rows = models.map(model => `
            <tr>
                <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-900">${model.model_id}</td>
                <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-900">${model.model_name}</td>
                <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-500">${model.temperature ?? 0.7}</td>
                <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-500">${model.max_tokens ?? 4096}</td>
                <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-500">${model.add_time || ''}</td>
                <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-500">
                    <label class="inline-flex items-center cursor-pointer">
                        <input 
                            type="checkbox" 
                            class="form-checkbox h-5 w-5 text-blue-600" 
                            data-model-id="${model.model_id}" 
                            ${model.is_active ? 'checked' : ''} 
                            onchange="toggleModelActive(this)"
                        >
                        <span class="ml-2">${model.is_active ? '已启用' : '已禁用'}</span>
                    </label>
                </td>
                <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-900">${model.desc ?? ''}</td>
                <td class="px-3 py-2 whitespace-nowrap text-sm font-medium">
                    <button onclick="editModel('${model.model_id}')" class="text-blue-600 hover:text-blue-900 mr-2">编辑</button>
                    <button onclick="deleteModel('${model.model_id}')" class="text-red-600 hover:text-red-900">删除</button>
                </td>
            </tr>
        `).join('');
        tbody.innerHTML = rows;
    }

    // 编辑模型
    async function editModel(modelId) {
        try {
            const modelResponse = await fetch(`/api/models/${modelId}`);
            if (!modelResponse.ok) {
                alert('获取模型信息失败，无权限处理');
                return;
            }
            
            const model = await modelResponse.json();
            
            const modal = document.createElement('div');
            modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-start justify-center z-50 overflow-y-auto py-6';
            modal.innerHTML = `
                <div class="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto">
                    <h3 class="text-lg font-semibold mb-4">编辑模型</h3>
                    <div class="space-y-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">模型名称</label>
                            <input type="text" id="editModelName" value="${model.model_name}" class="w-full px-3 py-2 rounded-md border border-gray-300">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">模型地址</label>
                            <input type="text" id="editModelUrl" value="${model.model_url}" class="w-full px-3 py-2 rounded-md border border-gray-300">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                            <input type="password" id="editModelApiKey" value="${model.api_key}" class="w-full px-3 py-2 rounded-md border border-gray-300">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Temperature</label>
                            <input type="number" id="editModelTemperature" step="0.1" min="0" max="2" value="${model.temperature || 0.7}" class="w-full px-3 py-2 rounded-md border border-gray-300">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Max Tokens</label>
                            <input type="number" id="editModelMaxTokens" min="1024" max="32768" value="${model.max_tokens || 2048}" class="w-full px-3 py-2 rounded-md border border-gray-300">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">描述</label>
                            <input type="text" id="editModelDesc" value="${model.desc}" class="w-full px-3 py-2 rounded-md border border-gray-300">
                        </div>
                        <div class="pt-1">
                            <label class="inline-flex items-center">
                                <input type="checkbox" id="editModelShared" class="form-checkbox h-4 w-4 text-blue-600" ${model.model_flag === 0 ? 'checked' : ''}>
                                <span class="ml-2 text-sm text-gray-700">共享模型（勾选则其他用户可见）</span>
                            </label>
                        </div>
                        <div class="flex justify-end space-x-3 pt-2">
                            <button id="cancelEditModel" class="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50">取消</button>
                            <button id="confirmEditModel" class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">确认更新</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            
            document.getElementById('cancelEditModel').onclick = () => document.body.removeChild(modal);
            
            document.getElementById('confirmEditModel').onclick = async () => {
                const modelName = document.getElementById('editModelName').value;
                const modelUrl = document.getElementById('editModelUrl').value;
                const apiKey = document.getElementById('editModelApiKey').value;
                const temperature = document.getElementById('editModelTemperature').value;
                const maxTokens = document.getElementById('editModelMaxTokens').value;
                const modelDesc = document.getElementById('editModelDesc').value;
                
                if (!modelName || !modelUrl || !apiKey) {
                    alert('请填写必填字段');
                    return;
                }
                
                try {
                    const response = await fetch(`/api/models/${modelId}`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content || ''
                        },
                        body: JSON.stringify({
                            model_name: modelName,
                            model_url: modelUrl,
                            api_key: apiKey,
                            temperature: parseFloat(temperature),
                            max_tokens: parseInt(maxTokens),
                            desc: modelDesc,
                            model_flag: (document.getElementById('editModelShared')?.checked ? 0 : 1)
                        })
                    });
                    
                    if (response.ok) {
                        alert('模型更新成功');
                        // 局部刷新模型管理表 + 同步聊天下拉
                        document.body.removeChild(modal);
                        refreshModelList();
                        if (window.loadModels) window.loadModels();
                    } else {
                        alert('更新失败: ' + await response.text());
                    }
                } catch (error) {
                    alert('错误: ' + error.message);
                }
            };
        } catch (error) {
            alert('错误: ' + error.message);
        }
    }
    
    // 简易确认弹窗（替换原生confirm，避免浏览器兼容问题）
    function showConfirmDialog(message) {
        return new Promise(resolve => {
            const modal = document.createElement('div');
            modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
            modal.innerHTML = `
                <div class="bg-white rounded-lg p-6 max-w-sm w-full">
                    <h3 class="text-lg font-semibold mb-3">确认操作</h3>
                    <p class="text-sm text-gray-700 mb-4">${message}</p>
                    <div class="flex justify-end space-x-3">
                        <button id="confirmCancel" class="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50">取消</button>
                        <button id="confirmOk" class="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700">确定</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            const cleanup = () => { try { document.body.removeChild(modal); } catch(_){} };
            modal.querySelector('#confirmCancel').onclick = () => { cleanup(); resolve(false); };
            modal.querySelector('#confirmOk').onclick = () => { cleanup(); resolve(true); };
        });
    }

    // 删除模型
    async function deleteModel(modelId) {
        const ok = await showConfirmDialog('确定要删除这个模型吗？');
        if (!ok) return;
        
        fetch(`/api/models/${modelId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content || ''
            }
        })
        .then(response => {
            if (response.ok) {
                alert('模型删除成功');
                // 局部刷新模型管理表 + 同步聊天下拉
                refreshModelList();
                if (window.loadModels) window.loadModels();
            } else {
                // 优先解析JSON错误，回退到纯文本
                return response.json()
                    .then(data => {
                        alert('删除失败: ' + (data.error || JSON.stringify(data)));
                    })
                    .catch(() => {
                        return response.text().then(text => {
                            alert('删除失败: ' + text);
                        });
                    });
            }
        })
        .catch(error => {
            alert('错误: ' + error.message);
        });
    }
    
    // 添加模型按钮事件
    if (document.getElementById('addModelBtn')) {
        document.getElementById('addModelBtn').onclick = showAddModelModal;
    }
    
    // 为模型信息表面板添加折叠功能
    if (document.getElementById('modelsSubHeader')) {
        document.getElementById('modelsSubHeader').addEventListener('click', function(e) {
            // 只有点击折叠图标或标题时才触发折叠
            if (e.target.closest('#addModelBtn')) {
                return; // 点击添加按钮不触发折叠
            }
            
            const content = document.getElementById('modelsSubContent');
            const icon = document.getElementById('modelsSubCollapseIcon');
            
            if (content.style.display === 'none') {
                content.style.display = 'block';
                icon.textContent = '▼';
            } else {
                content.style.display = 'none';
                icon.textContent = '▶';
            }
        });
    }
    
    // 将函数暴露到全局，以便内联onclick可以访问
    window.editModel = editModel;
    window.deleteModel = deleteModel;
    window.showAddModelModal = showAddModelModal;
    window.refreshModelList = refreshModelList;
});