// 格式化当前计划为易读的HTML字符串
function formatCurrentPlan(plan) {
    if (!plan || plan.length === 0) {
        return '无';
    }
    
    // 如果plan是字符串，尝试解析为JSON
    if (typeof plan === 'string') {
        try {
            plan = JSON.parse(plan);
        } catch (e) {
            return plan; // 如果无法解析，直接返回字符串
        }
    }
    
    // 如果plan是数组，格式化每个计划项
    if (Array.isArray(plan)) {
        let formatted = '<ul class="list-disc pl-6 mt-1">';
        plan.forEach((item, index) => {
            let step = item.step || (index + 1);
            let action = item.action || '未知操作';
            let reason = item.reason || '';
            formatted += `<li>步骤${step}: ${action}${reason ? ' - ' + reason : ''}</li>`;
        });
        formatted += '</ul>';
        return formatted;
    }
    
    // 如果plan是对象，尝试格式化单个计划项
    if (typeof plan === 'object') {
        let step = plan.step || 1;
        let action = plan.action || '未知操作';
        let reason = plan.reason || '';
        return `<div class="ml-4 mt-1">步骤${step}: ${action}${reason ? ' - ' + reason : ''}</div>`;
    }
    
    return String(plan);
}

// 切换模型启用状态
window.toggleModelActive = function(checkbox) {
    const modelId = checkbox.dataset.modelId;
    const isActive = checkbox.checked;
    
    // 显示加载状态
    showLoading('更新模型状态...');
    
    // 发送更新请求
    fetch(`/api/models/${modelId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ is_active: isActive })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('更新模型状态失败');
        }
        return response.json();
    })
    .then(data => {
        hideLoading();
        if (data.success) {
            // 更新成功，可以添加一个提示或不做任何操作
            console.log('模型状态更新成功');
        } else {
            // 更新失败，恢复原来的状态
            checkbox.checked = !isActive;
            showError(data.error || '更新模型状态失败');
        }
    })
    .catch(error => {
        hideLoading();
        // 请求失败，恢复原来的状态
        checkbox.checked = !isActive;
        showError('更新模型状态时发生错误: ' + error.message);
    });
}

// 显示加载状态
showLoading = function(message = '正在处理您的请求...') {
    const loadingMessage = document.getElementById('loadingMessage');
    const loadingModal = document.getElementById('loadingModal');
    loadingMessage.textContent = message;
    loadingModal.classList.remove('hidden');
};

// 隐藏加载状态
hideLoading = function() {
    const loadingModal = document.getElementById('loadingModal');
    loadingModal.classList.add('hidden');
};

// 显示错误消息
showError = function(errorMessage) {
    const chatHistory = document.getElementById('chatHistory');
    const messageElement = document.createElement('div');
    messageElement.className = 'mb-4 p-3 bg-gray-100 rounded-lg';
    messageElement.innerHTML = `
        <div class="flex items-start space-x-2">
            <div class="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white">AI</div>
            <div class="flex-1">
                <p class="text-sm text-gray-700">${errorMessage}</p>
            </div>
        </div>
    `;
    chatHistory.appendChild(messageElement);
    chatHistory.scrollTop = chatHistory.scrollHeight;
};

document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chatForm');
    const userInput = document.getElementById('userInput');
    const chatHistory = document.getElementById('chatHistory');
    const loadingModal = document.getElementById('loadingModal');
    const loadingMessage = document.getElementById('loadingMessage');
    const statusBtn = document.getElementById('statusBtn');
    const memoryBtn = document.getElementById('memoryBtn');
    const historyBtn = document.getElementById('historyBtn');
    const clearBtn = document.getElementById('clearBtn');
    const memoryStatus = document.getElementById('memoryStatus');

    // 处理表单提交
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const message = userInput.value.trim();
        
        if (message) {
            // 添加用户消息到聊天历史
            addUserMessage(message);
            
            // 清空输入框
            userInput.value = '';
            
            // 发送消息到后端
            sendMessage(message);
        }
    });

    // 处理特殊按钮点击
    if (statusBtn) {
        statusBtn.addEventListener('click', function() {
            showLoading('获取Agent状态...');
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    hideLoading();
                    if (data.error) {
                        addBotMessage(`获取状态失败: ${data.error}`);
                    } else {
                    // 构建状态信息HTML
                    let statusHtml = data.response;
                    if (data.detail) {
                            // <li>短期记忆条数: ${data.detail.short_term_memory}</li>
                            // <li>长期记忆条数: ${data.detail.long_term_memory}</li>
                            // <li>执行次数: ${data.detail.execution_count}</li>
                        statusHtml += `<ul class="list-disc pl-6 space-y-1">
                            <li>可用工具数量: ${data.detail.tool_count}</li>
                            <li>当前问题执行计划: ${formatCurrentPlan(data.detail.current_plan)}</li>
                        </ul>`;
                    }
                    addBotMessage(statusHtml, true);
                }
            })
            .catch(error => {
                hideLoading();
                addBotMessage(`获取状态时出错: ${error.message}`);
            });
        });
    }

    if (memoryBtn) {
        memoryBtn.addEventListener('click', function() {
            showLoading('获取记忆摘要...');
            fetch('/api/chat_history')
                .then(response => response.json())
                .then(data => {
                    hideLoading();
                    if (data.error) {
                        addBotMessage(`获取记忆失败: ${data.error}`);
                    } else {
                    addBotMessage(data.response, false, true);
                }
            })
            .catch(error => {
                hideLoading();
                addBotMessage(`获取记忆时出错: ${error.message}`);
            });
        });
    }

    if (clearBtn) {
        // 创建清除选项对话框
        let dialog = document.getElementById('clearOptionsDialog');
        if (!dialog) {
            dialog = document.createElement('div');
            dialog.id = 'clearOptionsDialog';
            dialog.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 hidden'; // 默认隐藏
            dialog.innerHTML = `
                <div class="bg-white rounded-lg p-6 max-w-md w-full">
                    <h3 class="text-xl font-bold mb-4">选择要清除的内容</h3>
                    <div class="space-y-4 mb-6">
                        <label class="flex items-center p-3 border rounded-md cursor-pointer hover:bg-gray-50">
                            <input type="radio" name="clearType" value="short" class="mr-3" checked>
                            <span>🗨️ 清除对话记录</span>
                        </label>
                        <label class="flex items-center p-3 border rounded-md cursor-pointer hover:bg-gray-50">
                            <input type="radio" name="clearType" value="execution" class="mr-3">
                            <span>🔧 清除工具执行历史</span>
                        </label>
                        <label class="flex items-center p-3 border rounded-md cursor-pointer hover:bg-gray-50">
                            <input type="radio" name="clearType" value="all" class="mr-3">
                            <span>🗑️ 清除所有内容</span>
                        </label>
                    </div>
                    <div class="flex justify-end space-x-3">
                        <button id="cancelClearBtn" class="px-4 py-2 border rounded-md hover:bg-gray-100">取消</button>
                        <button id="confirmClearBtn" class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">确认清除</button>
                    </div>
                </div>
            `;
            document.body.appendChild(dialog);
            
            // 取消按钮事件 - 只绑定一次
            document.getElementById('cancelClearBtn').addEventListener('click', function() {
                dialog.classList.add('hidden');
            });
            
            // 确认清除按钮事件 - 只绑定一次
            document.getElementById('confirmClearBtn').addEventListener('click', function() {
                const selectedType = document.querySelector('input[name="clearType"]:checked').value;
                dialog.classList.add('hidden');
                
                // 显示加载状态
                showLoading('正在清除...');
                
                // 发送清除请求
                fetch('/api/clear_memory', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content || ''
                    },
                    body: JSON.stringify({ type: selectedType })
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('清除失败');
                    }
                    return response.json();
                })
                .then(data => {
                    hideLoading();
                    if (data.error) {
                        addBotMessage(`清除失败: ${data.error}`);
                    } else {
                        addBotMessage(data.response);
                        
                        // 更新记忆状态显示（如果清除了对话记录）
                        if (selectedType === 'short' || selectedType === 'all') {
                            const memoryStatus = document.getElementById('memoryStatus');
                            if (memoryStatus) {
                                memoryStatus.textContent = '短期记忆: 0';
                            }
                        }
                    }
                })
                .catch(error => {
                    hideLoading();
                    addBotMessage(`清除时发生错误: ${error.message}`);
                });
            });
        }
        
        // clearBtn点击事件 - 只负责显示对话框
        clearBtn.addEventListener('click', function() {
            dialog.classList.remove('hidden');
        });
    }
    
    // 将执行历史列表转换为文本格式，每行一条记录，元素之间用 " | " 分隔
    function formatExecutionHistory(historyList) {
        console.log('formatExecutionHistory收到的参数类型:', typeof historyList);
        console.log('formatExecutionHistory收到的参数内容:', historyList);
        
        // 检查是否有执行历史
        if (!historyList || (Array.isArray(historyList) && historyList.length === 0)) {
            return '<div class="execution-history"><h3>工具执行历史</h3><p>暂无执行历史</p></div>';
        }
        
        // 创建文本格式的历史记录
        let textContent = '<div class="execution-history"><h3>工具执行历史</h3><pre class="execution-text">序号 | 问题 | 工具名称 | 工具参数 | 执行开始时间 | 执行结束时间 | 执行结果\n';
        
        // 处理不同类型的输入
        let records = [];
        
        // 处理可能的字符串形式的数组
        if (typeof historyList === 'string') {
            try {
                // 尝试解析字符串为JSON
                const parsed = JSON.parse(historyList);
                if (Array.isArray(parsed)) {
                    records = parsed;
                } else {
                    records = [parsed];
                }
            } catch (e) {
                console.error('解析执行历史字符串失败:', e);
                // 如果解析失败，尝试手动分割字符串
                if (historyList.includes('[object Object]')) {
                    // 这可能是对象数组的字符串表示，我们将其视为空数据
                    records = [];
                } else {
                    records = [historyList];
                }
            }
        } else if (Array.isArray(historyList)) {
            records = historyList;
        } else {
            records = [historyList];
        }
        
        // console.log('处理后的记录列表:', records);
        
        // 添加每条记录为一行文本
        records.forEach((record, index) => {
            // console.log('处理单条记录:', record, typeof record);
            
            // 安全获取字段值，处理各种可能的数据格式
            let recordIndex = index + 1;
            let question = '未知';
            let toolName = '未知';
            let params = '未知';
            let result = '未知';
            
            // 初始化时间变量，确保作用域正确
            let startTime = '未知';
            let endTime = '未知';
            
            // 处理对象类型的记录
            if (record && typeof record === 'object' && record !== null) {
                // 防止循环引用导致的JSON序列化问题
                try {
                    // 尝试序列化以检查是否有循环引用
                    JSON.stringify(record);
                    
                    // 安全获取字段
                    recordIndex = record.index !== undefined ? String(record.index) : String(index + 1);
                    question = record.question !== undefined ? String(record.question) : '未知';
                    toolName = record.tool_name !== undefined ? String(record.tool_name) : '未知';
                    
                    // 特殊处理params和result，它们可能是对象
                    if (record.params !== undefined) {
                        params = typeof record.params === 'object' ? JSON.stringify(record.params) : String(record.params);
                    }
                    // 获取开始时间和结束时间
                    if (record.start_time !== undefined) {
                        startTime = String(record.start_time);
                    }
                    if (record.end_time !== undefined) {
                        endTime = String(record.end_time);
                    }
                    if (record.result !== undefined) {
                        result = typeof record.result === 'object' ? JSON.stringify(record.result) : String(record.result);
                    }
                } catch (e) {
                    console.error('处理记录对象时出错:', e);
                    // 如果对象无法序列化，将整个对象转换为字符串
                    question = String(record);
                }
            } else if (typeof record === 'string') {
                // 处理字符串类型的记录
                question = record;
            } else {
                // 处理其他类型的记录
                question = String(record);
            }
            
            // 限制显示长度
            const questionText = question.length > 30 ? question.substring(0, 30) + '...' : question;
            const paramsText = params.length > 50 ? params.substring(0, 50) + '...' : params;
            
            // 安全转义HTML
            const safeQuestionText = escapeHTML(questionText);
            const safeToolName = escapeHTML(toolName);
            const safeParamsText = escapeHTML(paramsText);
            const safeStartTime = escapeHTML(startTime);
            const safeEndTime = escapeHTML(endTime);
            const safeResult = escapeHTML(result);
            
            // 添加一条记录为一行文本，使用 " | " 分隔各元素
            textContent += `${recordIndex} | ${safeQuestionText} | ${safeToolName} | ${safeParamsText} | ${safeStartTime} | ${safeEndTime} | ${safeResult}\n`;
        });
        
        // 结束文本内容
        textContent += '</pre></div>';
        
        console.log('生成的文本内容:', textContent);
        return textContent;
    }

    // 处理执行历史按钮点击
    historyBtn.addEventListener('click', function() {
        showLoading('获取执行历史...');
        fetch('/api/execution_history')
            .then(response => response.json())
            .then(data => {
                hideLoading();
                if (data.error) {
                    addBotMessage(`获取执行历史失败: ${data.error}`);
                } else {
                    // console.log('执行历史数据类型:', typeof data.response);
                    console.log('执行历史数据:', data.response);
                    
                    // 确保data.response是数组
                    let historyList = data.response;
                    if (!Array.isArray(historyList)) {
                        // 尝试将字符串解析为JSON数组
                        try {
                            if (typeof historyList === 'string') {
                                historyList = JSON.parse(historyList);
                            } else {
                                // 如果不是数组也不是可解析的字符串，则转换为空数组
                                historyList = [];
                            }
                        } catch (e) {
                            console.error('解析执行历史数据失败:', e);
                            historyList = [];
                        }
                    }
                    
                    console.log('处理后的执行历史数据:', historyList);
                    // 将执行历史列表转换为HTML表格并显示
                    const historyHtml = formatExecutionHistory(historyList);
                    addBotMessage(historyHtml, true);
                }
            })
            .catch(error => {
                hideLoading();
                addBotMessage(`获取执行历史时出错: ${error.message}`);
                console.error('获取执行历史错误:', error);
            });
    });

    // 添加用户消息到聊天历史
    function addUserMessage(message) {
        const messageElement = document.createElement('div');
        messageElement.className = 'user-message p-3 rounded-lg bg-blue-600 text-white max-w-3xl';
        messageElement.innerHTML = `
            <div class="flex items-start justify-end">
                <div>
                    <p>${escapeHTML(message)}</p>
                </div>
                <div class="bg-white text-blue-600 rounded-full p-2 ml-3">
                    👤
                </div>
            </div>
        `;
        chatHistory.appendChild(messageElement);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    // 添加机器人消息到聊天历史
    function addBotMessage(message, isStatus = false, isMemory = false) {
        const messageElement = document.createElement('div');
        let messageClass = 'bot-message p-3 rounded-lg bg-gray-100 max-w-3xl';
        
        if (isStatus) {
            messageClass += ' status-message';
        } else if (isMemory) {
            messageClass += ' memory-message';
        }
        
        messageElement.className = messageClass;
        
        // 对于状态消息，直接使用HTML内容而不进行转义
        if (isStatus) {
            messageElement.innerHTML = `
                <div class="flex items-start">
                    <div class="bg-blue-600 text-white rounded-full p-2 mr-3">
                            🤖
                        </div>
                    <div>
                        ${message}
                    </div>
                </div>
            `;
        } else {
            // 对于普通消息，进行格式化处理
            messageElement.innerHTML = `
                <div class="flex items-start">
                    <div class="bg-blue-600 text-white rounded-full p-2 mr-3">
                        <i class="fa fa-robot" aria-hidden="true"></i>
                    </div>
                    <div>
                        <p>${formatMessage(message)}</p>
                    </div>
                </div>
            `;
        }
        
        chatHistory.appendChild(messageElement);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    // 显示加载状态
    function showLoading(message = '正在处理您的请求...') {
        loadingMessage.textContent = message;
        loadingModal.classList.remove('hidden');
    }

    // 隐藏加载状态
    function hideLoading() {
        loadingModal.classList.add('hidden');
    }

    // 显示错误消息
    function showError(errorMessage) {
        addBotMessage(`❌ 发生错误: ${errorMessage}`);
    }

    // 发送消息到后端API
    function sendMessage(message) {
        showLoading();
        
        // 获取选中的模型ID
        const modelSelect = document.getElementById('modelSelect');
        const selectedModelId = modelSelect ? modelSelect.value : null;
        
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content || ''
            },
            body: JSON.stringify({ 
                message: message,
                model_id: selectedModelId
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('网络响应错误，模型不可用或请求失败');
            }
            return response.json();
        })
        .then(data => {
            hideLoading();
            
            if (data.error) {
                showError(data.error);
            } else {
                // 处理不同类型的响应
                if (message.toLowerCase() === 'status' && data.detail) {
                    // 美化后的状态信息
                const statusHtml = `
                    <div class="bg-blue-50 rounded-xl p-4 border border-blue-100">
                        <h4 class="font-bold text-blue-700 mb-3 flex items-center">
                            <span class="mr-2">📊</span>
                            Agent状态详情
                        </h4>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div class="bg-white rounded-lg p-3 shadow-sm">
                                <div class="text-xs text-gray-500 uppercase mb-1">短期记忆</div>
                                <div class="flex items-center">
                                    <div class="text-2xl font-bold text-blue-600">${data.detail.short_term_memory}</div>
                                    <div class="ml-2 text-sm text-gray-500">条</div>
                                </div>
                                <div class="mt-2 h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
                                    <div class="bg-blue-500 h-full rounded-full" style="width: ${Math.min(100, data.detail.short_term_memory * 5)}%"></div>
                                </div>
                            </div>
                            
                            <div class="bg-white rounded-lg p-3 shadow-sm">
                                <div class="text-xs text-gray-500 uppercase mb-1">长期记忆</div>
                                <div class="flex items-center">
                                    <div class="text-2xl font-bold text-purple-600">${data.detail.long_term_memory}</div>
                                    <div class="ml-2 text-sm text-gray-500">条</div>
                                </div>
                                <div class="mt-2 h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
                                    <div class="bg-purple-500 h-full rounded-full" style="width: ${Math.min(100, data.detail.long_term_memory * 10)}%" ></div>
                                </div>
                            </div>
                            
                            <div class="bg-white rounded-lg p-3 shadow-sm">
                                <div class="text-xs text-gray-500 uppercase mb-1">可用工具</div>
                                <div class="flex items-center">
                                    <div class="text-2xl font-bold text-green-600">${data.detail.tool_count}</div>
                                    <div class="ml-2 text-sm text-gray-500">个</div>
                                </div>
                                <div class="mt-2 h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
                                    <div class="bg-green-500 h-full rounded-full" style="width: ${Math.min(100, data.detail.tool_count * 10)}%" ></div>
                                </div>
                            </div>
                            
                            <div class="bg-white rounded-lg p-3 shadow-sm">
                                <div class="text-xs text-gray-500 uppercase mb-1">执行记录</div>
                                <div class="flex items-center">
                                    <div class="text-2xl font-bold text-amber-600">${data.detail.execution_count}</div>
                                    <div class="ml-2 text-sm text-gray-500">条</div>
                                </div>
                                <div class="mt-2 h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
                                    <div class="bg-amber-500 h-full rounded-full" style="width: ${Math.min(100, data.detail.execution_count * 5)}%" ></div>
                                </div>
                            </div>
                        </div>
                        
                        ${data.detail.current_plan && data.detail.current_plan.length > 0 ? 
                            `<div class="mt-4 bg-white rounded-lg p-3 shadow-sm">
                                <div class="text-sm font-medium text-gray-700 mb-2 flex items-center">
                                    <span class="mr-2">📋</span>
                                    当前计划
                                </div>
                                <div class="bg-gray-50 p-3 rounded-md text-xs text-gray-700 font-mono overflow-x-auto">
                                    ${JSON.stringify(data.detail.current_plan, null, 2).replace(/\n/g, '<br>').replace(/\s/g, '&nbsp;')}
                                </div>
                            </div>` : 
                            '<div class="mt-4 text-center text-sm text-gray-500 italic">暂无当前计划</div>'
                        }
                    </div>
                `;
                    addBotMessage(statusHtml, true);
                    
                    // 更新状态栏
                    memoryStatus.textContent = `短期记忆: ${data.detail.short_term_memory}`;
                } else if (message.toLowerCase() === 'memory') {
                    addBotMessage(data.response, false, true);
                } else {
                    addBotMessage(data.response);
                    
                    // 如果是clear命令，更新状态栏
                    if (message.toLowerCase() === 'clear') {
                        memoryStatus.textContent = '短期记忆: 0';
                    }
                }
            }
        })
        .catch(error => {
            hideLoading();
            showError(error.message);
        });
    }

    // 转义HTML特殊字符
    function escapeHTML(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // 格式化消息内容（处理换行、代码、Markdown格式等）
    function formatMessage(message) {
        if (!message) return '';
        
        // 替换换行符为<br>
        let formatted = escapeHTML(message).replace(/\n/g, '<br>');
        
        // 处理代码块
        formatted = formatted.replace(/```([\s\S]*?)```/g, '<pre>$1</pre>');
        
        // 处理Markdown粗体（**文本**）- 更严格边界，避免乘号误匹配
        formatted = formatted.replace(/(^|[^\w])\*\*([^*]+)\*\*(?=[^\w]|$)/g, '$1<strong>$2</strong>');
        
        // 处理Markdown斜体（*文本*）- 更严格边界，避免乘号误匹配
        formatted = formatted.replace(/(^|[^\w])\*([^*]+)\*(?=[^\w]|$)/g, '$1<em>$2</em>');
        
        // 处理Markdown无序列表（- 项目）
        formatted = formatted.replace(/<br>- (.*?)(?=<br>|$)/g, '<br><ul><li>$1</li></ul>');
        
        // 处理数字列表（1. 项目）
        formatted = formatted.replace(/<br>(\d+)\. (.*?)(?=<br>|$)/g, '<br><ol><li>$2</li></ol>');
        
        return formatted;
    }

    // 按Enter发送消息，Shift+Enter换行
    userInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });

    // 初始化时获取工具列表（可选，这里主要是为了验证API连接）
    fetch('/api/tools')
        .then(response => response.json())
        .then(tools => {
            // 工具列表已经在模板中渲染，这里可以做一些额外的处理
            console.log('已加载工具列表:', tools);
        })
        .catch(error => {
            console.error('加载工具列表失败:', error);
        });

    // 将API Key的中间部分替换为星号
    function maskApiKey(apiKey) {
        if (!apiKey || apiKey.length <= 8) {
            return apiKey; // 如果API Key太短，不进行隐藏
        }
        
        const prefixLength = 4; // 前4个字符保持可见
        const suffixLength = 4; // 后4个字符保持可见
        
        // 计算需要隐藏的字符数量
        const maskedLength = apiKey.length - prefixLength - suffixLength;
        
        // 创建星号字符串
        const maskedPart = '*'.repeat(Math.max(4, maskedLength)); // 至少显示4个星号
        
        // 拼接结果
        return apiKey.substring(0, prefixLength) + maskedPart + apiKey.substring(apiKey.length - suffixLength);
    }
    
    // API Key隐藏功能实现
    const apiKeyInput = document.getElementById('apiKey');
    if (apiKeyInput) {
        const originalKey = apiKeyInput.value;
        
        // 存储原始API Key值
        if (originalKey) {
            apiKeyInput.dataset.originalKey = originalKey;
            apiKeyInput.value = maskApiKey(originalKey);
        }
        
        // 当输入框获得焦点时，显示完整的API Key
        apiKeyInput.addEventListener('focus', function() {
            if (this.dataset.originalKey) {
                this.value = this.dataset.originalKey;
            }
        });
        
        // 当输入框失去焦点时，重新隐藏API Key的中间部分
        apiKeyInput.addEventListener('blur', function() {
            if (this.value) {
                this.dataset.originalKey = this.value;
                this.value = maskApiKey(this.value);
            }
        });
    }
    
    // 额外的确保措施 - 直接在文件末尾执行一次
    // 查找API Key输入框并应用隐藏
    (function() {
        setTimeout(function() {
            const apiKeyInput = document.getElementById('apiKey');
            if (apiKeyInput && apiKeyInput.value && !apiKeyInput.dataset.originalKey) {
                console.log('额外确保措施：应用API Key隐藏');
                apiKeyInput.dataset.originalKey = apiKeyInput.value;
                apiKeyInput.value = maskApiKey(apiKeyInput.value);
            }
        }, 500);
    })();


    // 用户下拉菜单交互
    const userMenuBtn = document.getElementById('userMenuBtn');
    const userDropdownMenu = document.getElementById('userDropdownMenu');
    
    if (userMenuBtn && userDropdownMenu) {
        // 点击用户菜单按钮显示/隐藏下拉菜单
        userMenuBtn.addEventListener('click', function() {
            userDropdownMenu.classList.toggle('opacity-0');
            userDropdownMenu.classList.toggle('invisible');
            userDropdownMenu.classList.toggle('translate-y-2');
            userDropdownMenu.classList.toggle('translate-y-0');
        });
        
        // 点击文档其他地方关闭下拉菜单
        document.addEventListener('click', function(event) {
            if (!userMenuBtn.contains(event.target) && !userDropdownMenu.contains(event.target)) {
                userDropdownMenu.classList.add('opacity-0', 'invisible', 'translate-y-2');
                userDropdownMenu.classList.remove('translate-y-0');
            }
        });
    }
    
    // 个人资料显示功能
    window.showProfile = function() {
        showLoading('获取个人资料...');
        fetch('/api/user_profile')
            .then(response => response.json())
            .then(data => {
                hideLoading();
                if (data.error) {
                    addBotMessage(`获取个人资料失败: ${data.error}`, true);
                } else {
                    addBotMessage('📋 <strong>个人资料</strong><br>' +
                                 '用户名: 👤 ' + (data.username || '未知用户') + '<br>' +
                                 '角色: ' + (data.role || '普通用户') + '<br>' +
                                 '注册时间: ' + (data.registration_date || '未知') + '<br>' +
                                 '最后登录: ' + (data.last_login || '未知'), true);
                }
            })
            .catch(error => {
                hideLoading();
                addBotMessage(`获取个人资料时出错: ${error.message}`, true);
            });
    };
    
    // 修改密码功能
    window.showChangePassword = function() {
        // 创建修改密码表单
        const passwordFormHtml = `
            <div id="passwordForm" class="w-full max-w-sm">
                <div class="mb-3">
                    <label for="currentPassword" class="block text-sm font-medium text-gray-700 mb-1">当前密码</label>
                    <input type="password" id="currentPassword" class="w-full px-3 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" placeholder="请输入当前密码">
                </div>
                <div class="mb-3">
                    <label for="newPassword" class="block text-sm font-medium text-gray-700 mb-1">新密码</label>
                    <input type="password" id="newPassword" class="w-full px-3 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" placeholder="请输入新密码">
                </div>
                <div class="mb-4">
                    <label for="confirmPassword" class="block text-sm font-medium text-gray-700 mb-1">确认新密码</label>
                    <input type="password" id="confirmPassword" class="w-full px-3 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" placeholder="请再次输入新密码">
                </div>
                <div class="flex gap-2">
                    <button id="submitPasswordBtn" class="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors w-1/2">确认修改</button>
                    <button id="cancelPasswordBtn" class="bg-gray-300 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-colors w-1/2">取消</button>
                </div>
            </div>
        `;
        
        // 显示密码修改对话框
        addBotMessage('🔒 <strong>修改密码</strong><br>' + passwordFormHtml, true);
        
        // 添加确认按钮事件处理
        setTimeout(() => {
            const submitBtn = document.getElementById('submitPasswordBtn');
            const cancelBtn = document.getElementById('cancelPasswordBtn');
            
            if (submitBtn) {
                submitBtn.addEventListener('click', function() {
                    const currentPassword = document.getElementById('currentPassword').value;
                    const newPassword = document.getElementById('newPassword').value;
                    const confirmPassword = document.getElementById('confirmPassword').value;
                    
                    // 验证密码
                    if (!currentPassword) {
                        alert('请输入当前密码');
                        return;
                    }
                    
                    if (!newPassword) {
                        alert('请输入新密码');
                        return;
                    }
                    
                    if (newPassword !== confirmPassword) {
                        alert('两次输入的新密码不一致');
                        return;
                    }
                    
                    // 提交修改密码请求
                    showLoading('正在修改密码...');
                    fetch('/api/change_password', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content || ''
                        },
                        body: JSON.stringify({
                            current_password: currentPassword,
                            new_password: newPassword
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        hideLoading();
                        if (data.success) {
                            addBotMessage('✅ 密码修改成功！', true);
                        } else {
                            addBotMessage(`❌ 密码修改失败: ${data.error || '未知错误'}`, true);
                        }
                    })
                    .catch(error => {
                        hideLoading();
                        addBotMessage(`❌ 密码修改时出错: ${error.message}`, true);
                    });
                });
            }
            
            if (cancelBtn) {
                cancelBtn.addEventListener('click', function() {
                    // 可以添加关闭对话框的逻辑
                    addBotMessage('已取消密码修改操作', true);
                });
            }
        }, 100);
    };
    
    // 设置功能
    window.showSettings = function() {
        // 这里可以实现显示设置的逻辑
        addBotMessage('⚙️ <strong>设置选项</strong><br>' +
                     '目前系统暂不支持个人设置功能<br>' +
                     '如有特殊需求，请联系管理员', true);
    };
});