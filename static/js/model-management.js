// 确保DOM加载完成后再执行代码
document.addEventListener('DOMContentLoaded', function() {
    // 添加模型模态框
    function showAddModelModal() {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white rounded-lg p-6 max-w-md w-full">
                <h3 class="text-lg font-semibold mb-4">添加模型</h3>
                <div class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">模型名称</label>
                        <input type="text" id="newModelName" class="w-full px-3 py-2 rounded-md border border-gray-300">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">模型地址</label>
                        <input type="text" id="newModelUrl" class="w-full px-3 py-2 rounded-md border border-gray-300">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                        <input type="text" id="newModelApiKey" class="w-full px-3 py-2 rounded-md border border-gray-300">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Temperature</label>
                        <input type="number" id="newModelTemperature" step="0.1" min="0" max="2" value="0.7" class="w-full px-3 py-2 rounded-md border border-gray-300">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Max Tokens</label>
                        <input type="number" id="newModelMaxTokens" min="1024" max="32768" value="2048" class="w-full px-3 py-2 rounded-md border border-gray-300">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">描述</label>
                        <input type="text" id="newModelDesc" class="w-full px-3 py-2 rounded-md border border-gray-300">
                    </div>
                    <div class="flex justify-end space-x-3 pt-2">
                        <button id="cancelAddModel" class="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50">取消</button>
                        <button id="confirmAddModel" class="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700">确认添加</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        document.getElementById('cancelAddModel').onclick = () => document.body.removeChild(modal);
        
        document.getElementById('confirmAddModel').onclick = async () => {
            const modelName = document.getElementById('newModelName').value;
            const modelUrl = document.getElementById('newModelUrl').value;
            const apiKey = document.getElementById('newModelApiKey').value;
            const temperature = document.getElementById('newModelTemperature').value;
            const maxTokens = document.getElementById('newModelMaxTokens').value;
            const modelDesc = document.getElementById('newModelDesc').value;
            
            if (!modelName || !modelUrl || !apiKey) {
                alert('请填写必填字段');
                return;
            }
            
            try {
                const response = await fetch('/api/models', {
                    method: 'POST',
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
                        desc: modelDesc
                    })
                });
                
                if (response.ok) {
                    alert('模型添加成功');
                    location.reload();
                } else {
                    alert('添加失败: ' + await response.text());
                }
            } catch (error) {
                alert('错误: ' + error.message);
            }
        };
    }
    
    // 编辑模型
    async function editModel(modelId) {
        try {
            const modelResponse = await fetch(`/api/models/${modelId}`);
            if (!modelResponse.ok) {
                alert('获取模型信息失败');
                return;
            }
            
            const model = await modelResponse.json();
            
            const modal = document.createElement('div');
            modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
            modal.innerHTML = `
                <div class="bg-white rounded-lg p-6 max-w-md w-full">
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
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            model_name: modelName,
                            model_url: modelUrl,
                            api_key: apiKey,
                            temperature: parseFloat(temperature),
                            max_tokens: parseInt(maxTokens),
                            desc: modelDesc
                        })
                    });
                    
                    if (response.ok) {
                        alert('模型更新成功');
                        location.reload();
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
    
    // 删除模型
    function deleteModel(modelId) {
        if (confirm('确定要删除这个模型吗？')) {
            fetch(`/api/models/${modelId}`, {
                method: 'DELETE'
            })
            .then(response => {
                if (response.ok) {
                    alert('模型删除成功');
                    location.reload();
                } else {
                    return response.text().then(text => {
                        alert('删除失败: ' + text);
                    });
                }
            })
            .catch(error => {
                alert('错误: ' + error.message);
            });
        }
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
});