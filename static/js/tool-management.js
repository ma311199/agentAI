// 确保DOM加载完成后再执行代码
document.addEventListener('DOMContentLoaded', function() {
    // 添加工具模态框
    function showAddToolModal() {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white rounded-lg p-6 max-w-xl w-full overflow-y-auto" style="height: 75vh;">
                <h3 class="text-lg font-semibold mb-4">添加工具</h3>
                <div class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">工具名称 *</label>
                        <input type="text" id="newToolName" placeholder='例如：add（不要命令为下划线开头的函数工具名称）' class="w-full px-3 py-2 rounded-md border border-gray-300">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">描述</label>
                        <textarea id="newToolDescription" rows="3" placeholder='例如：计算两个数的和' class="w-full px-3 py-2 rounded-md border border-gray-300 text-sm"></textarea>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">工具类型</label>
                        <select id="newToolType" class="w-full px-3 py-2 rounded-md border border-gray-300">
                            <option value="function">函数工具</option>
                            <option value="api">API调用工具</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">参数描述 (JSON格式)</label>
                        <textarea id="newToolParameters" rows="3" placeholder='示例: [{"name":"a","description":"加数1","type":"string","required":true},{"name":"b","description":"加数2","type":"string","required":true}]' class="w-full px-3 py-2 rounded-md border border-gray-300 text-sm"></textarea>
                        <p class="text-xs text-gray-500 mt-1">请以JSON数组格式输入参数信息</p>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">工具代码/URL</label>
                        <textarea id="newToolCode" rows="4" placeholder='函数代码（Python）,代码中函数工具名与上面的工具名称一致，或者函数工具名定义在代码中的第一个函数\n例如：\ndef add(a, b):\n    return a + b' class="w-full px-3 py-2 rounded-md border border-gray-300 text-sm"></textarea>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">工具标签</label>
                        <input type="text" id="newToolLabel" placeholder="例如：通用、计算、搜索、数据库" class="w-full px-3 py-2 rounded-md border border-gray-300 text-sm">
                        <p class="text-xs text-gray-500 mt-1">可添加多个标签，用分号分割</p>
                    </div>
                    <div class="pt-2">
                        <label class="inline-flex items-center">
                            <input type="checkbox" id="newToolPrivate" class="form-checkbox h-4 w-4 text-blue-600">
                            <span class="ml-2 text-sm text-gray-700">私有工具</span>
                        </label>
                    </div>
                    <div class="flex justify-end space-x-3 pt-2">
                        <button id="cancelAddTool" class="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50">取消</button>
                        <button id="confirmAddTool" class="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700">确认添加</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        document.getElementById('cancelAddTool').onclick = () => document.body.removeChild(modal);
        
        document.getElementById('confirmAddTool').onclick = async () => {
            const toolName = document.getElementById('newToolName').value;
            const toolDescription = document.getElementById('newToolDescription').value;
            const toolType = document.getElementById('newToolType').value;
            const toolCode = document.getElementById('newToolCode').value;
            const toolParameters = document.getElementById('newToolParameters').value;
            const isPrivate = document.getElementById('newToolPrivate').checked;
            const label = document.getElementById('newToolLabel').value.trim();
            
            if (!toolName) {
                alert('请填写工具名称');
                return;
            }
            
            // 验证参数描述是否为有效的JSON（如果有输入）
            let parameters = null;
            if (toolParameters.trim()) {
                try {
                    parameters = JSON.parse(toolParameters);
                    if (!Array.isArray(parameters)) {
                        alert('参数描述必须是JSON数组格式');
                        return;
                    }
                } catch (e) {
                    alert('参数描述不是有效的JSON格式');
                    return;
                }
            }
            
            try {
                const response = await fetch('/api/tools', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content || ''
                    },
                    body: JSON.stringify({
                        tool_name: toolName,
                        description: toolDescription,
                        tool_type: toolType,
                        code_or_url: toolCode,
                        parameters: parameters,
                        tool_flag: isPrivate ? 1 : 0,
                        label: label || undefined
                    })
                });
                
                if (response.ok) {
                    alert('工具添加成功');
                    location.reload();
                } else {
                    alert('添加失败: ' + await response.text());
                }
            } catch (error) {
                alert('错误: ' + error.message);
            }
        };
    }
    
    // 添加工具按钮事件
    if (document.getElementById('addToolBtn')) {
        document.getElementById('addToolBtn').onclick = showAddToolModal;
    }
    
    // 删除工具函数
    function deleteTool(toolId, toolName) {
        if (!confirm(`确定要删除工具"${toolName}"吗？此操作不可撤销。`)) {
            return;
        }
        
        fetch(`/api/tools/${toolId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content || ''
            }
        })
        .then(response => {
            if (response.ok) {
                alert('工具删除成功');
                location.reload();
            } else {
                return response.json().then(data => {
                    throw new Error(data.error || '删除失败');
                });
            }
        })
        .catch(error => {
            alert('错误: ' + error.message);
        });
    }

    // 编辑工具
    async function editTool(toolId) {
        try {
            const res = await fetch(`/api/tools/${toolId}`);
            if (!res.ok) {
                alert('编辑工具失败，无权限，需要创建者进行编辑');
                return;
            }
            const tool = await res.json();

            const modal = document.createElement('div');
            modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-start justify-center z-50 overflow-y-auto py-6';
            modal.innerHTML = `
                <div class="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto">
                    <h3 class="text-lg font-semibold mb-4">编辑工具</h3>
                    <div class="space-y-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">工具名称 *</label>
                            <input type="text" id="editToolName" value="${tool.tool_name || ''}" class="w-full px-3 py-2 rounded-md border border-gray-300">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">描述</label>
                            <textarea id="editToolDescription" rows="3" class="w-full px-3 py-2 rounded-md border border-gray-300 text-sm">${tool.description || ''}</textarea>
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">参数描述 (JSON格式)</label>
                            <textarea id="editToolParameters" rows="3" class="w-full px-3 py-2 rounded-md border border-gray-300 text-sm">${tool.parameters ? JSON.stringify(tool.parameters) : ''}</textarea>
                            <p class="text-xs text-gray-500 mt-1">请以JSON数组格式输入参数信息</p>
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">工具代码/URL</label>
                            <textarea id="editToolCode" rows="4" class="w-full px-3 py-2 rounded-md border border-gray-300 text-sm">${tool.code_content || ''}</textarea>
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">工具标签</label>
                            <input type="text" id="editToolLabel" value="${tool.label || '通用'}" placeholder="例如：通用、计算、搜索、数据库" class="w-full px-3 py-2 rounded-md border border-gray-300 text-sm">
                            <p class="text-xs text-gray-500 mt-1">可添加多个标签，用分号分割</p>
                        </div>
                        <div class="flex items-center justify-between pt-2">
                            <div class="flex items-center space-x-4">
                                <label class="inline-flex items-center">
                                    <input type="checkbox" id="editToolActive" class="form-checkbox h-4 w-4 text-blue-600" ${tool.is_active ? 'checked' : ''}>
                                    <span class="ml-2 text-sm text-gray-700">启用</span>
                                </label>
                                <label class="inline-flex items-center">
                                    <input type="checkbox" id="editToolPrivate" class="form-checkbox h-4 w-4 text-blue-600" ${tool.tool_flag === 1 ? 'checked' : ''}>
                                    <span class="ml-2 text-sm text-gray-700">私有工具</span>
                                </label>
                            </div>
                            <div class="space-x-3">
                                <button id="cancelEditTool" class="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50">取消</button>
                                <button id="confirmEditTool" class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">确认更新</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);

            document.getElementById('cancelEditTool').onclick = () => document.body.removeChild(modal);

            document.getElementById('confirmEditTool').onclick = async () => {
                const toolName = document.getElementById('editToolName').value.trim();
                const description = document.getElementById('editToolDescription').value;
                const paramsText = document.getElementById('editToolParameters').value.trim();
                const codeContent = document.getElementById('editToolCode').value;
                const isActive = document.getElementById('editToolActive').checked;
                const isPrivate = document.getElementById('editToolPrivate').checked;
                const label = document.getElementById('editToolLabel').value.trim();

                if (!toolName) {
                    alert('工具名称为必填项');
                    return;
                }

                let parameters = null;
                if (paramsText) {
                    try {
                        parameters = JSON.parse(paramsText);
                        if (!Array.isArray(parameters)) {
                            alert('参数描述必须是JSON数组格式');
                            return;
                        }
                    } catch (e) {
                        alert('参数描述不是有效的JSON格式');
                        return;
                    }
                }

                try {
                    const response = await fetch(`/api/tools/${toolId}`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content || ''
                        },
                        body: JSON.stringify({
                            tool_name: toolName,
                            description: description,
                            parameters: parameters,
                            is_active: isActive,
                            code_or_url: codeContent,
                            tool_flag: isPrivate ? 1 : 0,
                            label: label || undefined
                        })
                    });
                    if (response.ok) {
                        alert('工具更新成功');
                        location.reload();
                    } else {
                        const text = await response.text();
                        alert('更新失败: ' + text);
                    }
                } catch (error) {
                    alert('错误: ' + error.message);
                }
            };
        } catch (error) {
            alert('错误: ' + error.message);
        }
    }

    // 为工具列表中的每个工具添加删除按钮（保留，兼容旧结构）
    function addDeleteButtonsToTools() {
        const toolElements = document.querySelectorAll('#toolsContainer .tool-item');
        toolElements.forEach(element => {
            const header = element.querySelector('.font-medium.text-blue-700');
            const existingDeleteBtn = element.querySelector('.delete-tool-btn');
            if (header && !existingDeleteBtn) {
                const toolId = element.dataset.toolId;
                const nameEl = header.querySelector('div');
                const toolName = nameEl ? nameEl.textContent.trim() : '工具';
                const deleteButton = document.createElement('button');
                deleteButton.className = 'delete-tool-btn ml-2 px-2 py-1 text-xs bg-red-500 text-white rounded hover:bg-red-600';
                deleteButton.textContent = '删除';
                deleteButton.onclick = function(e) {
                    e.stopPropagation();
                    deleteTool(toolId, toolName);
                };
                header.appendChild(deleteButton);
            }
        });
    }

    // 折叠事件
    if (document.getElementById('toolsSubHeader')) {
        document.getElementById('toolsSubHeader').addEventListener('click', function(e) {
            if (e.target.closest('#addToolBtn')) {
                return;
            }
            const content = document.getElementById('toolsSubContent');
            const icon = document.getElementById('toolsSubCollapseIcon');
            if (content.style.display === 'none') {
                content.style.display = 'block';
                icon.textContent = '▼';
                // 删除重复按钮注入：不再调用 addDeleteButtonsToTools
            } else {
                content.style.display = 'none';
                icon.textContent = '▶';
            }
        });
    }
    
    // 初始展开时不再注入删除按钮，避免重复
    // if (document.getElementById('toolsSubContent') && document.getElementById('toolsSubContent').style.display !== 'none') {
    //     setTimeout(addDeleteButtonsToTools, 100);
    // }
    
    // 暴露到全局
    window.showAddToolModal = showAddToolModal;
    window.deleteTool = deleteTool;
    window.editTool = editTool;
});