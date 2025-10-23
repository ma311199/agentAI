# React增强型智能Agent项目介绍

## 1. 项目概述

React增强型智能Agent是一个基于LLM（大语言模型）的智能代理系统，采用React（思考-行动-观察-响应）模式，具备记忆管理、执行规划、工具使用、日志与安全审查等能力。当前版本以Web应用形式提供：后端使用Flask提供API与页面，前端使用模板与原生JS实现交互式体验。

### 核心特性：
- 🧠 记忆增强：支持对话历史与工具执行历史的记录与清理
- 📋 执行规划：为复杂任务生成多步骤计划并逐步执行
- 🔧 工具集成：支持函数型工具的注册、执行与历史查询
- 🔒 安全审查：对字符串代码型工具做安全审查（可拦截不安全代码）
- 📜 日志记录：统一记录API调用与数据库操作，便于审计与排错

## 2. 系统架构

系统采用模块化设计，核心组件如下：

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│                 │      │                 │      │                 │
│   app.py        │──────▶   agent.py      │──────▶   prompt.py     │
│  Flask服务与路由 │      │ ReactAgent核心  │      │ 提示词生成模块   │
│                 │      │                 │      │                 │
└────────┬────────┘      └────────┬────────┘      └─────────────────┘
         │                        │
         │                        ▼
         │                  ┌─────────────────┐
         │                  │                 │
         │                  │   tools.py      │
         │                  │ 工具基类定义     │
         │                  │                 │
         │                  └────────┬────────┘
         │                           │
         └───────────────────┬───────┘
                             │
                             ▼
                     ┌─────────────────┐      ┌──────────────────────┐
                     │                 │      │                      │
                     │ tool_process.py │◀─────┤ internal_tools.py    │
                     │ 动态注册工具     │      │ 内置函数工具清单      │
                     │（DB→内存加载）   │      │（add/multiply等）     │
                     └─────────────────┘      └──────────────────────┘

前端：
- `templates/`：`index.html`、`login.html` 页面模板
- `static/js/`：`main.js`（聊天与展示）、`tool-management.js`（工具管理）、`model-management.js`（模型管理）
- `static/css/`：`style.css` 与 Tailwind CSS
```

### 数据流（Web）：
1. 用户在页面输入请求 → 提交到 `/api/chat`
2. `app.py` 根据会话与模型选择创建 `ReactAgent`
3. `tool_process.Toolregister` 从数据库加载用户可用工具到内存（`Tool`对象）
4. `ReactAgent` 按React模式规划→执行工具→汇总结果
5. 返回计划与最终回复；前端渲染显示，并提供执行历史与记忆查看

## 3. 文件功能介绍

### 3.1 app.py

- 功能：Flask应用入口与路由。负责会话与CSRF、初始化LLM、初始化内置工具（写入DB）、工具与模型的CRUD、聊天请求处理与日志记录。
- 关键职责：
  - 页面：`/`（首页）、`/login`、`/register`、`/logout`
  - 聊天：`POST /api/chat`（计划与回复）
  - 工具：`GET/POST /api/tools`、`DELETE /api/tools/<id>`
  - 历史：`GET /api/execution_history`、`GET /api/chat_history`、`GET /api/sessions`
  - 模型：`GET/POST/PUT/DELETE /api/models`、`GET /api/models/<id>`
  - 用户：`GET /api/user_profile`、`POST /api/change_password`、`POST /api/clear_memory`
- 启动示例：
```python
if __name__ == '__main__':
    initialize_add_tool_and_admin()  # 注册admin与内置工具到DB
    initialize_llm()                 # 创建默认LLMClient
    app.run(debug=True, host='0.0.0.0', port=5000)
```

### 3.2 agent.py

- 功能：`ReactAgent` 核心实现，包含记忆、规划、工具调用与响应生成。
- 方法要点：`process_query(user_id, user_input)` 内部生成计划、执行工具、更新记忆并返回（本项目会返回“计划文本 + 最终回复”用于前端展示）。

### 3.3 prompt.py

- 功能：生成工具选择与参数抽取、执行规划、记忆摘要等提示词模板。

### 3.4 tools.py

- 功能：`Tool` 基类，封装工具的名称、描述、参数与执行函数；`execute(**kwargs)` 调用真实函数。

### 3.5 tool_process.py（工具动态注册）

- 功能：`Toolregister` 负责把数据库中的函数工具加载为内存中的 `Tool` 对象；当工具以“代码字符串”存储时，使用 `_convert_string_to_function(code_content, tool_name)` 提取函数对象。
- 关键逻辑：
  - 优先按 `tool_name` 在 `exec` 命名空间中寻找可调用函数（不以内划线开头、非内建、`callable=True`）
  - 未命中时回退到首个符合条件的函数
  - 注册后存入 `self.tools` 字典（进程内存储，重启不持久化）

### 3.6 internal_tools.py（内置工具清单）

- 功能：提供 `in_tools` 数组（add/subtract/multiply/divide/search/search_hana等），在应用启动时自动写入数据库，供所有用户使用或作为示例。

## 4. 核心功能详解

### 4.1 React模式实现
- 思考 → 规划 → 行动（工具） → 观察（结果） → 响应（总结）。

### 4.2 记忆管理
- 对话记忆：`GET /api/chat_history` 展示最近N条记录；`POST /api/clear_memory` 清理（短期/执行历史/全部）。
- 执行历史：`GET /api/execution_history` 返回最近工具执行的摘要列表。

### 4.3 执行规划
- 由LLM生成步骤化计划，包含动作类型、理由、工具名称与置信度；前端展示计划文本与最终回复。

### 4.4 工具使用机制
- 后端从DB加载工具定义（名称/描述/参数/代码）；执行时由 `Tool.execute(**kwargs)` 调用真实函数，并记录到执行历史。

## 5. 使用方法

### 5.1 启动与访问
```bash
pip install -r requirements.txt
set FLASK_SECRET_KEY=your-secret  # Windows示例（PowerShell可用 $env:FLASK_SECRET_KEY）
set API_KEY=your-api-key          # 可选，LLMClient也支持通过代码传参
python app.py
```
- 打开浏览器访问 `http://127.0.0.1:5000/`
- 默认会自动注册 `admin/123456` 管理员账户（见 `initialize_add_tool_and_admin`）

### 5.2 基本使用（Web）
- 登录后在输入框提交请求，后台返回“计划+最终回复”；底部状态栏展示“短期记忆”与“可用工具”数量。
- 查看历史：在界面中点击“工具执行历史”，或前端触发请求到 `GET /api/execution_history`。
- 清理记忆：通过“清除记忆”按钮或 `POST /api/clear_memory`（支持 short/execution/all）。

### 5.3 添加与管理工具
- 通过页面“添加工具”弹窗或 `POST /api/tools` 提交：
  - `tool_name`、`description`、`parameters`（JSON数组）、`code_or_url`（函数型工具以代码字符串提交）
- 安全审查：字符串代码会经过 `security_review.review_tool_code`，不安全将被拒绝。
- 执行参数：严格使用标准JSON（双引号、`true/false/null`），否则会解析失败。

## 6. API 路由速览
- `/` 首页（登录后可访问）
- `/login`（GET/POST）、`/register`（GET/POST）、`/logout`
- `POST /api/chat` 聊天与执行规划
- `GET/POST /api/tools`，`DELETE /api/tools/<id>` 工具管理
- `GET /api/execution_history` 工具执行历史
- `GET /api/chat_history` 对话历史摘要
- `GET /api/sessions` 会话列表
- `GET /api/models`、`POST /api/models`、`PUT /api/models/<id>`、`DELETE /api/models/<id>` 模型管理
- `GET /api/user_profile` 用户信息；`POST /api/change_password` 修改密码
- `POST /api/clear_memory` 清除记忆

## 7. 技术栈
- 后端：Python 3.10+、Flask、SQLite（见 `db/` 与 `database.py`）
- LLM：`LLMClient`（OpenAI兼容接口；示例使用 DashScope `qwen-flash`）
- 前端：原生JS、Tailwind CSS、Jinja2模板
- 日志：统一API与DB日志（`log.py`），生成 `logs/agent_ai_*.log`

## 8. 扩展与定制

### 8.1 添加新函数工具（字符串代码形式）
```python
code_str = """
import math

def circle_area(radius: float) -> float:
    return math.pi * radius * radius
"""
# 通过API或前端提交：tool_name 与函数名一致可优先匹配
# 后端将执行 `_convert_string_to_function(code_str, tool_name)` 并注册为可执行工具
```
- 命名规范：函数名不以下划线开头；建议与 `tool_name` 一致以确保优先匹配。
- 安全建议：确保代码来源可信；若被审查拒绝，请根据返回的 issues 调整代码。

### 8.2 调整LLM配置
- 方法一：设置环境变量 `API_KEY`，在 `llmclient.py` 默认读取。
- 方法二：修改 `app.py` 的 `initialize_llm()`，传入自定义 `url/model/api_key/timeout`。

## 9. 总结
本项目提供一个可扩展的Web版React智能Agent：支持工具动态注册与执行、计划与记忆可视化、API与前端联动。通过安全审查与日志审计，兼顾易用性与稳定性；适用于学习、演示与二次开发。