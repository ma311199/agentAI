document.addEventListener('DOMContentLoaded', function() {
    // 为左侧配置面板添加折叠功能
    const mainPanel = document.querySelector('#mainPanel');
    const mainHeader = document.querySelector('#mainHeader');
    
    if (mainHeader && mainPanel) {
        mainHeader.addEventListener('click', function() {
            mainPanel.classList.toggle('collapsed');
            // 存储折叠状态
            localStorage.setItem('mainPanelCollapsed', mainPanel.classList.contains('collapsed'));
            
            // 重新计算布局
            adjustLayout();
        });
        
        // 从localStorage恢复折叠状态
        const mainCollapsed = localStorage.getItem('mainPanelCollapsed') === 'true';
        if (mainCollapsed) {
            mainPanel.classList.add('collapsed');
        }
    }
    
    // 为可用工具子面板添加折叠功能
    const toolsSubHeader = document.querySelector('#toolsSubHeader');
    const toolsSubContent = document.querySelector('#toolsSubContent');
    const toolsSubCollapseIcon = document.querySelector('#toolsSubCollapseIcon');
    
    if (toolsSubHeader && toolsSubContent && toolsSubCollapseIcon) {
        toolsSubHeader.addEventListener('click', function() {
            toolsSubContent.classList.toggle('hidden');
            toolsSubCollapseIcon.textContent = toolsSubContent.classList.contains('hidden') ? '▶' : '▼';
            
            // 存储折叠状态
            localStorage.setItem('toolsSubPanelCollapsed', toolsSubContent.classList.contains('hidden'));
        });
        
        // 从localStorage恢复折叠状态
        const toolsSubCollapsed = localStorage.getItem('toolsSubPanelCollapsed') === 'true';
        if (toolsSubCollapsed) {
            toolsSubContent.classList.add('hidden');
            toolsSubCollapseIcon.textContent = '▶';
        }
    }
    
    // 为模型配置子面板添加折叠功能
    const modelSubHeader = document.querySelector('#modelSubHeader');
    const modelSubContent = document.querySelector('#modelSubContent');
    const modelSubCollapseIcon = document.querySelector('#modelSubCollapseIcon');
    
    if (modelSubHeader && modelSubContent && modelSubCollapseIcon) {
        modelSubHeader.addEventListener('click', function() {
            modelSubContent.classList.toggle('hidden');
            modelSubCollapseIcon.textContent = modelSubContent.classList.contains('hidden') ? '▶' : '▼';
            
            // 存储折叠状态
            localStorage.setItem('modelSubPanelCollapsed', modelSubContent.classList.contains('hidden'));
        });
        
        // 从localStorage恢复折叠状态
        const modelSubCollapsed = localStorage.getItem('modelSubPanelCollapsed') === 'true';
        if (modelSubCollapsed) {
            modelSubContent.classList.add('hidden');
            modelSubCollapseIcon.textContent = '▶';
        }
    }
    
    // 调整布局函数
    function adjustLayout() {
        const chatSection = document.querySelector('#chatSection');
        const mainPanel = document.querySelector('#mainPanel');
        
        if (!chatSection || !mainPanel) return;
        
        // 在大屏幕上调整布局
        if (window.innerWidth >= 1024) {
            // 面板折叠时保留80px宽度，确保标题栏可见
            let isMainCollapsed = mainPanel.classList.contains('collapsed');
            
            // 应用宽度
            mainPanel.style.width = isMainCollapsed ? '80px' : '25%';
            
            // 计算聊天区域宽度
            chatSection.style.width = isMainCollapsed ? 'calc(100% - 80px)' : '75%';
        } else {
            // 小屏幕上不做特殊调整
            mainPanel.style.width = '';
            chatSection.style.width = '';
        }
    }
    
    // 监听窗口大小变化，调整布局
    window.addEventListener('resize', adjustLayout);
    
    // 初始化布局
    adjustLayout();
    
    // 为模型配置保存按钮添加功能
    const saveBtn = document.querySelector('#saveModelConfig');
    if (saveBtn) {
        saveBtn.addEventListener('click', function() {
            const modelUrl = document.querySelector('#modelUrl').value;
            const modelName = document.querySelector('#modelName').value;
            const apiKey = document.querySelector('#apiKey').value;
            
            // 保存到localStorage
            localStorage.setItem('modelConfig', JSON.stringify({
                url: modelUrl,
                name: modelName,
                apiKey: apiKey
            }));
            
            // 显示保存成功提示
            const originalText = saveBtn.textContent;
            saveBtn.textContent = '✅ 已保存';
            setTimeout(() => {
                saveBtn.textContent = originalText;
            }, 2000);
        });
    }
    
    // 从localStorage加载模型配置
    const savedConfig = localStorage.getItem('modelConfig');
    if (savedConfig) {
        try {
            const config = JSON.parse(savedConfig);
            if (config.url) document.querySelector('#modelUrl').value = config.url;
            if (config.name) document.querySelector('#modelName').value = config.name;
            if (config.apiKey) document.querySelector('#apiKey').value = config.apiKey;
        } catch (e) {
            console.error('Failed to load model config:', e);
        }
    }
});