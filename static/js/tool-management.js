// 确保DOM加载完成后再执行代码
document.addEventListener('DOMContentLoaded', function() {
    // 添加工具模态框
    function showAddToolModal() {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white rounded-lg p-6 max-w-md w-full">
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
                        <textarea id="newToolCode" rows="4" placeholder='函数代码（Python）,代码中函数工具名与上面的工具名称一致，或者函数工具名定义在代码中的第一个函数
例如：
def add(a, b):
    return a + b' class="w-full px-3 py-2 rounded-md border border-gray-300 text-sm"></textarea>
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
                        parameters: parameters
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
                'Content-Type': 'application/json'
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
    
    // 为工具列表中的每个工具添加删除按钮
    function addDeleteButtonsToTools() {
        const toolElements = document.querySelectorAll('#toolsSubContent > div');
        toolElements.forEach(element => {
            // 查找工具名称和ID
            const toolNameElement = element.querySelector('h4');
            if (toolNameElement) {
                // 尝试从元素ID或其他属性获取工具ID
                // 假设工具元素有一个data-tool-id属性
                const toolId = element.dataset.toolId;
                const toolName = toolNameElement.textContent.trim();
                
                if (toolId && !element.querySelector('.delete-tool-btn')) {
                    const deleteButton = document.createElement('button');
                    deleteButton.className = 'delete-tool-btn ml-2 px-2 py-1 text-xs bg-red-500 text-white rounded hover:bg-red-600';
                    deleteButton.textContent = '删除';
                    deleteButton.onclick = function(e) {
                        e.stopPropagation();
                        deleteTool(toolId, toolName);
                    };
                    
                    // 将删除按钮添加到工具名称旁边
                    toolNameElement.parentNode.appendChild(deleteButton);
                }
            }
        });
    }
    
    // 为内部工具面板添加折叠功能
    if (document.getElementById('toolsSubHeader')) {
        document.getElementById('toolsSubHeader').addEventListener('click', function(e) {
            // 只有点击折叠图标或标题时才触发折叠
            if (e.target.closest('#addToolBtn')) {
                return; // 点击添加按钮不触发折叠
            }
            
            const content = document.getElementById('toolsSubContent');
            const icon = document.getElementById('toolsSubCollapseIcon');
            
            if (content.style.display === 'none') {
                content.style.display = 'block';
                icon.textContent = '▼';
                // 内容显示后添加删除按钮
                setTimeout(addDeleteButtonsToTools, 100);
            } else {
                content.style.display = 'none';
                icon.textContent = '▶';
            }
        });
    }
    
    // 初始添加删除按钮（如果面板默认是展开的）
    if (document.getElementById('toolsSubContent') && document.getElementById('toolsSubContent').style.display !== 'none') {
        setTimeout(addDeleteButtonsToTools, 100);
    }
    
    // 将函数暴露到全局，以便内联onclick可以访问
    window.showAddToolModal = showAddToolModal;
    window.deleteTool = deleteTool;
});