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
                        <label class="block text-sm font-medium text-gray-700 mb-1">工具代码/URL *</label>
                        <textarea id="newToolCode" rows="4" placeholder='函数代码（Python）,代码中函数工具名与上面的工具名称一致，或者函数工具名定义在代码中的第一个函数\n例如：\ndef add(a, b):\n    return a + b' class="w-full px-3 py-2 rounded-md border border-gray-300 text-sm" required></textarea>
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
            
            const nameVal = (toolName || '').trim();
            if (!nameVal) {
                alert('请填写工具名称');
                return;
            }
            // 名称规则：只能包含英文字符和下划线，不能以下划线开头，且必须包含至少一个英文字符
            const namePattern = /^(?!_)[A-Za-z_]+$/;
            if (!namePattern.test(nameVal) || !/[A-Za-z]/.test(nameVal)) {
                alert('工具名称不合法：只能包含英文字符和下划线，不能以下划线开头，且必须包含至少一个英文字符');
                return;
            }
            // 新增必填校验：工具代码或URL
            if (!toolCode || !toolCode.trim()) {
                alert('请填写工具代码或URL');
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
                        tool_name: nameVal,
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
                    await refreshToolList();
                    document.body.removeChild(modal);
                } else {
                    try {
                        const data = await response.json();
                        alert('添加失败: ' + (data.error || JSON.stringify(data)));
                    } catch (_) {
                        const text = await response.text();
                        alert('添加失败: ' + text);
                    }
                }
            } catch (error) {
                alert('错误: ' + error.message);
            }
        };
    }

    // 局部刷新：渲染工具列表
    async function refreshToolList() {
        try {
            const res = await fetch('/api/tools');
            if (!res.ok) throw new Error('获取工具列表失败');
            const tools = await res.json();
            renderToolItems(tools);
        } catch (e) {
            console.error('刷新工具列表失败:', e);
        }
    }

    function renderToolItems(tools) {
        const container = document.getElementById('toolsContainer');
        if (!container) return;
        container.innerHTML = '';
        if (!Array.isArray(tools) || tools.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'text-sm text-gray-500';
            empty.textContent = '暂无工具';
            container.appendChild(empty);
            return;
        }
        tools.forEach(tool => {
            const item = document.createElement('div');
            item.className = 'tool-item mb-4 p-3 bg-blue-50 rounded border-l-4 border-blue-500';
            item.dataset.toolId = tool.tool_id;

            const header = document.createElement('div');
            header.className = 'font-medium text-blue-700 flex items-center justify-between';

            const nameWrap = document.createElement('div');
            const iconSpan = document.createElement('span'); iconSpan.className = 'mr-1'; iconSpan.textContent = '📦';
            const nameText = document.createTextNode(tool.tool_name || '');
            nameWrap.appendChild(iconSpan);
            nameWrap.appendChild(nameText);

            const actions = document.createElement('div');
            actions.className = 'text-sm font-medium';
            const editBtn = document.createElement('button');
            editBtn.className = 'text-blue-600 hover:text-blue-900 mr-2';
            editBtn.textContent = '编辑';
            editBtn.onclick = () => window.editTool(String(tool.tool_id));
            const delBtn = document.createElement('button');
            delBtn.className = 'delete-tool-btn text-red-600 hover:text-red-900';
            delBtn.textContent = '删除';
            delBtn.onclick = () => window.deleteTool(String(tool.tool_id), String(tool.tool_name || '工具'));
            actions.appendChild(editBtn);
            actions.appendChild(delBtn);

            header.appendChild(nameWrap);
            header.appendChild(actions);
            item.appendChild(header);

            if (tool.description) {
                const desc = document.createElement('div');
                desc.className = 'text-sm text-gray-600 mt-1';
                desc.textContent = tool.description;
                item.appendChild(desc);
            }

            if (tool.parameters && Array.isArray(tool.parameters) && tool.parameters.length > 0) {
                const paramsWrap = document.createElement('div');
                paramsWrap.className = 'mt-2 text-xs text-gray-500';
                const strong = document.createElement('strong'); strong.textContent = '参数:';
                const ul = document.createElement('ul'); ul.className = 'list-disc list-inside';
                tool.parameters.forEach(p => {
                    const li = document.createElement('li');
                    const name = String(p.name || p.param || '参数');
                    const required = !!p.required;
                    const desc = p.description ? ` - ${p.description}` : '';
                    li.textContent = name + (required ? ' *' : '') + desc;
                    ul.appendChild(li);
                });
                paramsWrap.appendChild(strong);
                paramsWrap.appendChild(ul);
                item.appendChild(paramsWrap);
            }

            if (tool.code_content) {
                const codeWrap = document.createElement('div');
                codeWrap.className = 'mt-2 text-xs text-gray-500';
                const strong = document.createElement('strong'); strong.textContent = '工具代码:';
                const pre = document.createElement('pre');
                pre.className = 'bg-gray-100 p-2 rounded mt-1 text-xs overflow-x-auto';
                pre.textContent = tool.code_content;
                codeWrap.appendChild(strong);
                codeWrap.appendChild(pre);
                item.appendChild(codeWrap);
            }

            container.appendChild(item);
        });
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
    
    // 添加工具按钮事件
    if (document.getElementById('addToolBtn')) {
        document.getElementById('addToolBtn').onclick = showAddToolModal;
    }
    
    // 删除工具函数
    async function deleteTool(toolId, toolName) {
        const ok = await showConfirmDialog(`确定要删除工具"${toolName}"吗？此操作不可撤销。`);
        if (!ok) return;
        
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
                refreshToolList();
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
                            <label class="block text-sm font-medium text-gray-700 mb-1">工具名称</label>
                            <input type="text" id="editToolName" value="${tool.tool_name || ''}" class="w-full px-3 py-2 rounded-md border border-gray-300">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">描述</label>
                            <textarea id="editToolDescription" rows="3" class="w-full px-3 py-2 rounded-md border border-gray-300 text-sm">${tool.description || ''}</textarea>
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">参数描述 (JSON格式)</label>
                            <textarea id="editToolParameters" rows="3" class="w-full px-3 py-2 rounded-md border border-gray-300 text-sm">${JSON.stringify(tool.parameters || [])}</textarea>
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">工具代码/URL *</label>
                            <textarea id="editToolCode" rows="6" class="w-full px-3 py-2 rounded-md border border-gray-300 text-sm" required>${tool.code_content || ''}</textarea>
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">工具标签</label>
                            <input type="text" id="editToolLabel" value="${tool.label || ''}" class="w-full px-3 py-2 rounded-md border border-gray-300 text-sm">
                        </div>
                        <div class="pt-2">
                            <label class="inline-flex items-center">
                                <input type="checkbox" id="editToolPrivate" ${tool.tool_flag === 1 ? 'checked' : ''} class="form-checkbox h-4 w-4 text-blue-600">
                                <span class="ml-2 text-sm text-gray-700">私有工具</span>
                            </label>
                        </div>
                        <div class="flex justify-end space-x-3 pt-2">
                            <button id="cancelEditTool" class="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50">取消</button>
                            <button id="confirmEditTool" class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">确认更新</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);

            document.getElementById('cancelEditTool').onclick = () => document.body.removeChild(modal);
            
            document.getElementById('confirmEditTool').onclick = async () => {
                const toolName = document.getElementById('editToolName').value;
                const description = document.getElementById('editToolDescription').value;
                const parametersText = document.getElementById('editToolParameters').value;
                const codeContent = document.getElementById('editToolCode').value;
                const label = document.getElementById('editToolLabel').value.trim();
                const isPrivate = document.getElementById('editToolPrivate').checked;
                
                const nameVal = (toolName || '').trim();
                if (!nameVal) {
                    alert('工具名称不能为空');
                    return;
                }
                // 名称规则：只能包含英文字符和下划线，不能以下划线开头，且必须包含至少一个英文字符
                const namePattern = /^(?!_)[A-Za-z_]+$/;
                if (!namePattern.test(nameVal) || !/[A-Za-z]/.test(nameVal)) {
                    alert('工具名称不合法：只能包含英文字符和下划线，不能以下划线开头，且必须包含至少一个英文字符');
                    return;
                }

                // 新增必填校验：工具代码或URL
                if (!codeContent || !codeContent.trim()) {
                    alert('工具代码或URL不能为空');
                    return;
                }

                let parameters = [];
                try {
                    parameters = JSON.parse(parametersText || '[]');
                    if (!Array.isArray(parameters)) {
                        alert('参数描述必须是JSON数组格式');
                        return;
                    }
                } catch (e) {
                    alert('参数描述不是有效的JSON格式');
                    return;
                }

                try {
                    const response = await fetch(`/api/tools/${toolId}`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content || ''
                        },
                        body: JSON.stringify({
                            tool_name: nameVal,
                            description: description,
                            parameters: parameters,
                            is_active: true,
                            code_or_url: codeContent,
                            tool_flag: isPrivate ? 1 : 0,
                            label: label || undefined
                        })
                    });
                    if (response.ok) {
                        alert('工具更新成功');
                        await refreshToolList();
                        document.body.removeChild(modal);
                    } else {
                        try {
                            const data = await response.json();
                            alert('更新失败: ' + (data.error || JSON.stringify(data)));
                        } catch (_) {
                            const text = await response.text();
                            alert('更新失败: ' + text);
                        }
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
    window.refreshToolList = refreshToolList;
});