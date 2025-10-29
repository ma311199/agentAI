# React增强型智能Agent（Flask + 原生前端）

一个可扩展的 Web 版 React Agent，支持“思考 → 规划 → 行动（工具） → 观察 → 响应”全流程，内置工具动态注册、模型管理、记忆与执行历史可视化、CSRF 保护与日志审计，适合学习、演示与二次开发。

## 特性概览
- React 推理模式：生成可视化的执行计划与最终回复。
- 动态函数工具：工具以代码字符串存库，运行时安全审查与合规校验后注册为可执行函数。
- 模型管理与缓存：OpenAI 兼容接口，支持私有/共享模型与 TTL 缓存。
- 记忆管理：对话历史与工具执行历史查询、清理。
- 安全与会话：CSRF 保护、登录/注册、会话滑动过期、Cookie 安全参数。
- 日志体系：文件轮转、保留清理、统一 API/DB 操作日志。

## 快速开始
1) 环境要求：`Python 3.10+`
2) 安装依赖：
   - `pip install -r requirements.txt`
3) 配置模型 API Key（可选但推荐）：
   - Windows PowerShell：`$env:API_KEY = "your-api-key"`
   - 或运行时在“模型管理”中填写 `model_url` 与 `api_key`
4) 启动：`python app.py`，访问 `http://127.0.0.1:5000/`
5) 默认账户：`admin / 123456`（启动时自动注册，见 `startup.initialize_add_tool_and_admin`）。
6) 默认内置工具：在internal_tools.py中添加，启动时自动注册，可根据自己添加、删除、编辑内置工具。

## 架构与数据流
- 后端入口：`app.py`（创建 Flask 应用、注册蓝图、初始化内置工具与 CSRF）。
- 路由蓝图：
  - 页面：`routes/main.py`（`/` 首页）
  - 认证：`routes/auth.py`（`/login`、`/register`、`/logout`）
  - 聊天：`routes/chat.py`（`POST /api/chat`、历史/执行记录等）
  - 模型：`routes/models.py`（模型 CRUD 与可用模型查询）
  - 工具：`routes/tools.py`（工具 CRUD 与代码合规/安全审查）
- Agent 核心：`agent.py`（计划生成、工具执行、记忆/响应拼装）。
- LLM 客户端：`llmclient.py`（OpenAI 兼容，读取 `API_KEY`，支持自定义 `url/model/timeout`）。
- 工具注册：`tool_process.py`（DB→内存，字符串代码转函数）；`tools.py`（`Tool` 基类）。
- 内置工具：`internal_tools.py`（add/subtract/multiply/divide/search/search_hana）。
- 缓存：`tools_cache.py`、`models_cache.py`（按用户缓存，TTL 从 `Config` 读取）。
- 前端：`templates/` + `static/js|css`（原生 JS + Tailwind + Jinja2）。

数据流（Web）：前端提交 → `/api/chat` → 加载用户工具与模型 → `ReactAgent` 规划并执行 → 返回“计划+最终回复”并记录历史。

## Agent执行流程（详细）

### 组件架构图（ASCII）
```
┌──────────────┐      ┌──────────────┐      ┌───────────────────┐      ┌───────────────┐
│  前端页面    │──POST▶ /api/chat    │────▶│  缓存层（按用户）   │────▶│  LLMClient     │
│ (index.html) │     │ (routes/chat) │     │ tools_cache/models │     │ (OpenAI兼容)   │
└─────┬────────┘     └───────┬──────┘     └───────────┬───────┘      └───────┬───────┘
      │                      │                          │                     │
      │ GET 视图/列表        │ 调用 get_tools_for_user   │ 构建/命中模型缓存     │ chat()/stream_chat()
      │ / /login /register   │ 调用 get_model_for_user   │ TTL 控制（Config）    │
      ▼                      ▼                          ▼                     ▼
┌──────────────┐      ┌──────────────────────┐      ┌──────────────────────┐      ┌─────────────────┐
│ routes/main  │      │ ReactAgent           │      │ Toolregister          │      │ Tool.execute     │
│ 页面渲染与CSRF│      │ 规划+执行+记忆摘要    │      │ DB→函数对象→内存注册   │      │ 执行函数工具     │
└─────┬────────┘      └─────────┬────────────┘      └──────────┬───────────┘      └────────┬────────┘
      │                           │                              │                           │
      │                           │                              │                           │
      ▼                           ▼                              ▼                           ▼
┌──────────────┐      ┌──────────────────────┐      ┌──────────────────────┐      ┌────────────────────┐
│ database/db  │◀────▶│  chat_history        │◀────▶│ tool_execution_history│◀────▶│ 日志 log.py/文件轮转 │
│ SQLite/Managers│     │ 记录计划与回复       │      │ 记录工具执行摘要       │      │ API/DB操作日志       │
└──────────────┘      └──────────────────────┘      └──────────────────────┘      └────────────────────┘
```

### 时序图（步骤说明）
```
1. 前端提交消息：
   - 用户在首页输入问题，选择启用模型（左侧模型管理）。
   - 发送到 `POST /api/chat`，附带 `message`、`model_id`、`session_id`。

2. 路由处理：
   - `routes/chat.py` 校验登录与参数；记录 API 调用耗时。
   - 按用户加载工具缓存 `get_tools_for_user(user_id)`。
   - 按用户与模型ID加载模型缓存 `get_model_for_user(user_id, model_id)`；仅缓存启用模型。

3. 初始化 Agent 与 LLM：
   - 构建 `LLMClient(url=model_url, model=model_name, api_key, timeout)`。
   - 构建 `ReactAgent(llm=LLMClient, tools=tools_dict)`。

4. 创建执行计划：
   - `ReactAgent.create_plan()`：
     - 生成规划提示词 `create_planning_prompt(user_input, tools_schema, conversation_summary)`。
     - LLM 生成计划（JSON 数组或回退“直接回答”）。
     - 从响应中提取计划 `_extract_plan_from_response()`。

5. 逐步执行计划：
   - 遍历计划步骤，若需要调用工具：
     - 参数与工具校验 `_validate_parsed_result()`。
     - 执行 `Tool.execute(**kwargs)`。
     - 记录工具执行摘要到 DB（开始/结束时间、参数、结果截断）。
   - 若“直接回答”，走 `_generate_direct_answer()`。

6. 整理结果与记忆：
   - 拼装“计划文本 + 最终回复”。
   - 写入 `chat_history`（模型名、计划、用户消息、最终回复、时间戳）。

7. 返回响应：
   - 将“计划+最终回复”返回给前端并呈现。
   - 侧栏或弹窗可查询“工具执行历史”“对话记忆摘要”。

8. 保护与审计：
   - CSRF：`routes/common.py` 的 `init_csrf` 挂载 `before_request` 校验。
   - 日志：`log_api_call`/`log_db_operation`、文件轮转与保留清理（`log.py`）。
```

### 关键模块职责
- `agent.py`：对话摘要、规划提示词、计划解析与工具执行、最终回复拼装。
- `llmclient.py`：与 OpenAI 兼容接口交互，支持 `timeout`、普通与流式输出。
- `tools.py`：`Tool` 基类，封装元信息与执行入口。
- `tool_process.py`：从 DB 的字符串代码提取函数对象并注册，维护进程内 `self.tools`。
- `tools_cache.py`/`models_cache.py`：按用户维度缓存并 TTL 控制；支持失效与刷新。
- `routes/*`：REST API 与页面模板渲染；登录、注册、模型/工具 CRUD、聊天与历史。
- `security_review.py`：工具字符串代码的安全审查（提交/更新时执行）。
- `log.py`：统一日志，轮转与保留清理；封装 API 与 DB 操作日志。

## 使用说明
- 登录后在首页输入问题；需先在左侧启用并选择模型，否则 `/api/chat` 会提示“未选择模型”。
- 页面可查看“对话记忆”（`GET /api/chat_history`）与“工具执行历史”（`GET /api/execution_history`）。
- 清理记忆：`POST /api/clear_memory`，`type` 支持 `short`、`execution`、`all`。

## 模型管理
- 路由：`GET/POST/PUT/DELETE /api/models`、`GET /api/models/<id>`。
- 查询可用模型：`POST /api/models/available`，传入 `model_url` 与 `api_key`。
- 缓存：仅缓存启用模型（`is_active=1`），按用户 TTL 过期，接口在 `models_cache.py`。

## 工具管理
- 路由：`GET/POST /api/tools`、`GET/PUT/DELETE /api/tools/<id>`。
- 提交字段：`tool_name`、`description`、`parameters`（JSON 数组）、`code_or_url`（函数型工具传代码字符串）、`tool_flag`（0共享/1私有）、`label`。
- 合规校验：`validate_python_tool` 检查语法/函数同名/参数匹配/依赖模块；未通过直接拒绝。
- 安全审查：`security_review.review_tool_code`；不安全代码会返回 `issues` 与 `summary` 并拒绝入库。
- 执行机制：DB 存储 → 运行时转换为函数对象 → 注册至内存字典 → `Tool.execute(**kwargs)` 执行。

示例（字符串代码工具）：
```python
code_str = """
import math

def circle_area(radius: float) -> float:
    return math.pi * radius * radius
"""
# 前端或 API 提交：保证 tool_name 与函数名一致可优先匹配
```

## 安全与配置（`config.py`）
- 会话安全：`SECRET_KEY`、`SESSION_COOKIE_HTTPONLY/SAMESITE/SECURE`、滑动过期 `PERMANENT_SESSION_LIFETIME`。
- CSRF：开启 `CSRF_ENABLED`；JSON 请求需在请求头携带 `X-CSRF-Token` 或 body 字段；`login/register` 默认豁免。
- 缓存 TTL：`TOOLS_CACHE_TTL_SECONDS`、`MODELS_CACHE_TTL_SECONDS`（默认 300s）。
- 数据库：`DB_PATH=./db/db.sqlite3`，跨线程访问关闭同线程限制。
- 日志：`logs/agent_ai_YYYY-MM-DD.log`，轮转、保留天数、级别与格式均可在 `Config` 中调整。

## API 速览
- 页面：`/`、`/login`、`/register`、`/logout`
- 聊天：`POST /api/chat`、`GET /api/chat_history`、`GET /api/execution_history`、`GET /api/sessions`、`POST /api/clear_memory`
- 工具：`GET/POST /api/tools`、`GET/PUT/DELETE /api/tools/<id>`
- 模型：`GET/POST/PUT/DELETE /api/models`、`GET /api/models/<id>`、`POST /api/models/available`

## 目录结构（节选）
```
agent.py        # ReactAgent 核心
app.py          # Flask 入口与蓝图注册
routes/         # 页面/认证/聊天/模型/工具 路由
tools.py        # Tool 基类
tool_process.py # DB→内存工具注册，字符串代码转函数
internal_tools.py# 内置工具清单
models_cache.py # 模型缓存（按用户/TTL）
tools_cache.py  # 工具缓存（按用户/TTL）
config.py       # 安全、会话、日志、缓存 等配置
log.py          # 日志轮转与清理
templates/      # Jinja2 模板（index/login/register）
static/js|css   # 前端交互与样式
```

## 备注
- 生产环境请修改 `config.py` 的 `SECRET_KEY` 与 Cookie 安全参数，并根据需求调整 CSRF、日志与缓存策略。
- 若提交工具代码失败，请根据返回的合规/安全提示修正后重试。