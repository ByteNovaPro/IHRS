# IHRS

智能医院挂号系统（Intelligent Hospital Registration System）。

IHRS 是一个面向患者与医院管理人员的全栈示例项目，覆盖 AI 导诊、挂号预约、用户登录、后台管理和 Docker 一键部署等完整链路。当前仓库已经包含前端、业务后端、独立 AI 服务、独立 MCP Server 以及 MySQL / Redis / RabbitMQ 的容器化运行方案，适合课程设计、毕设展示、全栈练手和二次开发。

## 项目亮点

- 面向普通用户与管理员的双角色系统
- 支持手机号注册、登录、会话鉴权与权限隔离
- 支持 AI 导诊并将推荐结果带入预约流程
- 支持多轮导诊会话、流式问答与 RAG 知识库调试
- 支持独立 `mcp-server` 作为后端能力工具层，供 AI 服务通过 MCP 调用医院 / 诊室 / 医生 / 号源接口
- 支持服务端真实医生推荐，不再仅依赖前端本地拼接推荐结果
- 支持医院、诊室、医生、预约四大后台管理模块
- 后台管理支持医院、诊室、医生分页查询与服务端筛选
- 支持医生排班、时段限额、重复预约校验
- 支持首页查看“我的预约”并直接取消预约
- 内置大规模演示数据，当前已生成 `1000` 家医院、`3996` 个诊室、`11988` 位医生
- 支持未来 15 天号源展示与预约容量查询
- RAG 已切换为 `fastembed + BAAI/bge-small-zh-v1.5` 轻量中文向量模型
- 当前知识库已按统一模板拆分为 `54` 个导诊 chunk，覆盖症状匹配、追问、红旗症状、边界分流、推荐诉求与特殊人群
- 支持 Docker Compose 一键启动完整环境

## 功能概览

### 1. 用户与权限

- 普通用户可注册并登录系统
- 管理员可通过内置账号登录后台
- Redis 用于存储登录会话
- 普通用户只能使用：
  - 首页
  - AI 问诊
  - 挂号预约
- 管理员额外可访问：
  - 医院管理
  - 诊室管理
  - 医生管理
  - 预约管理

### 2. AI 问诊

- 前端提供独立 AI 问诊入口
- 用户输入症状后，可得到推荐科室、风险提示、补充追问和可选医生推荐
- `agent-service` 已支持 LangChain 编排的 RAG 检索增强生成式导诊回答
- 支持 `conversationId` 多轮上下文会话和 `POST /consult/stream` 流式输出
- 支持服务端保存用户当前导诊会话，刷新页面或重新登录后可恢复当前会话
- 可通过 OpenAI-compatible 接口接入 OpenAI、通义、DeepSeek 等模型
- 未配置 LLM 或模型超时时会自动回退到本地知识库 + 规则导诊
- 第一轮导诊结果会按“情况总结 / 初步推荐 / 建议继续补充”三段式组织
- 当症状和诉求足够明确时，AI 服务会在服务端生成 `doctorRecommendation`，并由前端按需展开“推荐医生”
- 已对“你好”“无关提问”“明确要求推荐医生”等不同输入意图做区分处理
- 已支持地域偏好约束，例如用户要求“广东的医院”时会优先推荐广州 / 深圳候选，避免继续推荐上海医院

说明：

- 当前结果仅用于导诊演示，不构成医疗诊断建议
- 只有当用户明确提出“帮我推荐医生 / 挂哪个医生”等诉求时，前端才会展示下方 `1-5` 位医生推荐卡片

### 2.1 AI 导诊链路

当前 AI 问诊采用“规则 + RAG + LangChain + LLM + MCP 工具编排”的混合模式：

1. 前端将用户症状发送到 `agent-service`
2. `agent-service` 从 Redis 读取 `conversationId` 对应的历史上下文
3. 使用 Chroma 检索本地导诊知识库
4. 若已配置大模型，则通过 LangChain 将知识片段、历史对话和结构化输出解析串联起来生成导诊结果；否则回退到规则兜底
5. 分诊得到目标科室后，`agent-service` 通过 `BackendMcpClient` 调用独立 `mcp-server`
6. `mcp-server` 再转调 Spring Boot 公开目录和号源接口，返回真实医院 / 诊室 / 医生 / 余号数据
7. `agent-service` 将最终 `doctorRecommendation` 写回导诊结果，前端再决定是否展示“推荐医生”按钮与预约入口

### 3. 挂号预约

- 用户按“医院 -> 诊室 -> 日期 -> 医生 -> 填信息”的流程完成预约
- 日期选择展示未来 15 天预约情况
- 支持查看日期维度剩余号源和可约医生数
- 支持查询医生指定日期 / 时段余号
- 支持取消预约
- 首页“我的预约”仅展示状态为“已预约”的有效记录

### 4. 后台管理

当前后台已支持以下数据模块：

- 医院管理
- 诊室管理
- 医生管理
- 预约管理

每个模块具备的核心能力：

- 列表展示
- 分页查询
- 搜索与筛选
- 查看详情
- 新增
- 编辑
- 删除
- 批量删除

说明：

- 医院、诊室、医生列表当前使用后端真分页
- 医院、诊室、医生筛选条件已接入服务端查询
- 预约管理仍以全量列表为主

### 5. 关键业务规则

- 普通用户必须登录后才能创建预约
- 同一医生同一天同一时段最多预约 `10` 人
- 同一普通用户不能重复预约同一医生的同一天同一时段
- 已取消预约不计入时段容量
- 同一诊室同一时段不能安排两位医生同时出诊
- 用户只能预约医生实际排班时段

## 技术架构

### 前端

- Vue 3
- Vite
- Element Plus

### 后端

- Spring Boot 3
- Spring Web
- Spring Data JPA
- Spring Validation
- MySQL
- Redis
- RabbitMQ

### AI 服务

- FastAPI
- Uvicorn
- Pydantic
- Chroma
- FastEmbed
- LangChain
- LangChain OpenAI

### MCP 工具层

- FastAPI
- JSON-RPC over HTTP
- 独立 `mcp-server`
- 面向 `agent-service` 提供医院 / 诊室 / 医生 / 号源工具调用

### 部署

- Docker
- Docker Compose
- Nginx

## 项目结构

```text
.
├── frontend/                  # Vue 3 前端应用
├── backend/                   # Spring Boot 后端服务
├── agent-service/             # FastAPI AI 导诊服务
│   ├── app/                   # 导诊主逻辑、RAG、LLM、MCP client、医生推荐编排
│   ├── knowledge/             # 本地导诊知识库 JSON chunk
│   ├── mcp_server/            # 独立 MCP Server 实现
│   └── chroma_db/             # Chroma 持久化目录
├── deploy/                    # Docker Compose 与环境配置
├── README.md
└── ...
```

## 运行环境

推荐直接使用 Docker 方式启动。

### Docker 运行所需

- Docker
- Docker Compose

### 本地分服务开发所需

- Node.js 20+
- Java 17
- Maven 3.9+
- Python 3.11+
- MySQL 8+
- Redis 7+
- RabbitMQ 3.13+

## 快速开始

### 方式一：Docker Compose 一键启动

这是当前最推荐的方式。

```bash
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up --build -d
```

查看服务状态：

```bash
docker compose -f deploy/docker-compose.yml ps
```

停止服务：

```bash
docker compose -f deploy/docker-compose.yml down
```

默认访问地址：

- 前端：`http://127.0.0.1:5173`
- 后端：`http://127.0.0.1:8080`
- AI 服务：`http://127.0.0.1:8000`
- MCP Server：`http://127.0.0.1:8100`
- RabbitMQ 管理台：`http://127.0.0.1:15672`

### 方式二：本地分服务启动

#### 1. 启动前端

```bash
cd frontend
npm install
npm run dev
```

默认地址：

```text
http://127.0.0.1:5173
```

#### 2. 启动后端

启动前请确保 MySQL、Redis、RabbitMQ 已可用。

```bash
cd backend
mvn spring-boot:run
```

默认地址：

```text
http://127.0.0.1:8080
```

#### 3. 启动 AI 服务

```bash
cd agent-service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

默认地址：

```text
http://127.0.0.1:8000
```

#### 4. 启动 MCP Server

如果采用本地分服务运行，并希望 `agent-service` 通过独立 MCP Server 调后端接口，还需要单独启动：

```bash
cd agent-service
pip install -r requirements.txt
uvicorn mcp_server.http_server:app --host 0.0.0.0 --port 8100
```

默认地址：

```text
http://127.0.0.1:8100
```

## 环境变量说明

Docker 启动默认读取 `deploy/.env`。

当前常用变量包括：

- `FRONTEND_PORT`：前端暴露端口
- `BACKEND_PORT`：后端暴露端口
- `AGENT_PORT`：AI 服务端口
- `MYSQL_DATABASE`：MySQL 数据库名
- `MYSQL_ROOT_PASSWORD`：MySQL root 密码
- `MYSQL_USERNAME`：业务数据库用户名
- `MYSQL_PASSWORD`：业务数据库密码
- `REDIS_PORT`：Redis 端口
- `RABBITMQ_PORT`：RabbitMQ 端口
- `RABBITMQ_MANAGEMENT_PORT`：RabbitMQ 管理台端口
- `LLM_BASE_URL`：外部大模型兼容接口地址
- `LLM_API_KEY`：外部大模型密钥
- `LLM_MODEL`：外部大模型名称
- `LLM_TIMEOUT_SECONDS`：外部大模型调用超时时间
- `LLM_TEMPERATURE`：外部大模型生成温度
- `CONSULT_CONTEXT_TTL_SECONDS`：导诊上下文缓存时长
- `CONSULT_CONTEXT_MAX_MESSAGES`：单会话保留的最大消息条数
- `RAG_EMBEDDING_MODEL_NAME`：RAG 向量模型名称，默认 `BAAI/bge-small-zh-v1.5`
- `RAG_EMBEDDING_DEVICE`：RAG 向量模型运行设备，默认 `cpu`
- `RAG_EMBEDDING_CACHE_DIR`：RAG 向量模型缓存目录，可选
- `MCP_PORT`：MCP Server 暴露端口
- `MCP_SERVER_URL`：`agent-service` 调用 MCP Server 的地址
- `MCP_SERVER_TIMEOUT_SECONDS`：MCP 调用超时时间
- `MCP_SERVER_COMMAND`：未使用 HTTP MCP 时的 stdio MCP 启动命令，可选
- `BACKEND_TIMEOUT_SECONDS`：`mcp-server` 调用 Spring Boot 接口超时时间

说明：

- 如果你准备公开仓库，建议立即替换或移除当前环境文件中的真实密钥
- 如果未配置 `LLM_BASE_URL` 和 `LLM_MODEL`，AI 服务会继续使用本地 RAG / 规则兜底
- 生产环境请不要直接使用仓库中的默认密码和默认端口

## 默认账号

### 管理员账号

- 手机号：`13800000000`
- 密码：`040130`

说明：

- 管理员密码可通过后端环境变量 `ADMIN_PASSWORD` 覆盖
- 普通注册入口不会创建管理员账号

## 数据存储说明

### MySQL

核心业务数据存储在 MySQL 中，包括：

- 医院
- 诊室
- 医生
- 预约记录
- 用户账号

当前核心表：

- `hospital`
- `clinic_room`
- `doctor`
- `appointment`
- `user_account`

当前默认演示数据规模：

- `hospital`：`1000`
- `clinic_room`：`3996`
- `doctor`：`11988`
- 同时保留少量用户、预约测试数据用于演示首页与后台流程

后端默认使用：

```yaml
spring.jpa.hibernate.ddl-auto: update
```

应用启动时会自动同步表结构。

### 数据表注释

项目内已加入数据库注释初始化器：

- 启动后会自动为核心表写入表注释
- 同时会为字段写入列注释
- 当前仅在 MySQL 环境下执行

相关代码位于：

- `backend/src/main/java/com/ihrs/backend/config/DatabaseCommentInitializer.java`

### Redis

Redis 当前主要用于登录会话管理与 AI 导诊会话上下文：

- 登录成功后生成 token
- 以 `ihrs:session:<token>` 的形式保存会话
- 后端基于 Redis 校验登录态与角色信息
- AI 导诊会话以 `ihrs:consult:conversation:<conversationId>` 的形式缓存上下文
- 同时以“用户 -> 当前 `conversationId`”的映射保存当前会话，便于刷新页面和重新登录后恢复导诊上下文

前端当前还包含以下体验处理：

- 如果管理员或普通用户本地仍持有 token，但服务端返回 `401`
- 前端会自动清理本地登录态并跳回首页登录区

### RabbitMQ

RabbitMQ 当前已接入部署和基础配置，但暂未承担核心业务链路。后续可以扩展为：

- 预约通知
- 异步任务解耦
- 导诊任务排队处理

## API 概览

### 认证接口

- `POST /api/auth/register`：普通用户注册
- `POST /api/auth/login`：登录
- `POST /api/auth/logout`：退出登录
- `GET /api/auth/me`：获取当前登录用户

### 公开目录接口

- `GET /api/catalog/hospitals`
- `GET /api/catalog/rooms`
- `GET /api/catalog/doctors`

### 预约接口

- `POST /api/appointments`：创建预约
- `GET /api/appointments`：查询当前用户预约
- `PUT /api/appointments/{id}/cancel`：取消当前用户预约
- `GET /api/appointments/quota`：查询指定医生某日某时段余号
- `GET /api/appointments/quota-calendar`：查询日期范围内可预约日历数据

### 后台管理接口

- `GET /api/admin/hospitals`：分页查询医院，支持 `page` / `size` / `keyword`
- `POST /api/admin/hospitals`
- `PUT /api/admin/hospitals/{id}`
- `DELETE /api/admin/hospitals/{id}`

- `GET /api/admin/rooms`：分页查询诊室，支持 `hospitalId` / `page` / `size` / `keyword`
- `POST /api/admin/rooms`
- `PUT /api/admin/rooms/{id}`
- `DELETE /api/admin/rooms/{id}`

- `GET /api/admin/doctors`：分页查询医生，支持 `hospitalId` / `roomId` / `workTimeSlot` / `page` / `size` / `keyword`
- `POST /api/admin/doctors`
- `PUT /api/admin/doctors/{id}`
- `DELETE /api/admin/doctors/{id}`

- `GET /api/admin/appointments`
- `PUT /api/admin/appointments/{id}/cancel`
- `DELETE /api/admin/appointments/{id}`

### 健康检查接口

- 后端：`GET /actuator/health`
- AI 服务：`GET /health`

### AI 服务接口

- `POST /consult`：普通导诊问答
- `POST /consult/stream`：流式导诊问答
- `GET /consult/session`：恢复当前用户已缓存的导诊会话
- `DELETE /consult/conversations/{conversationId}`：删除导诊会话上下文
- `GET /rag/stats`：查看知识库状态
- `GET /rag/documents`：查看知识库文档
- `POST /rag/search`：调试知识库检索结果

### MCP Server 接口

- `GET /health`：MCP Server 健康检查
- `POST /mcp`：JSON-RPC MCP 入口

## Docker 说明

当前 `deploy/docker-compose.yml` 包含以下服务：

- `frontend`
- `backend`
- `agent-service`
- `mcp-server`
- `mysql`
- `redis`
- `rabbitmq`

代理关系如下：

- 前端容器通过 Nginx 对后端和 AI 服务做反向代理
- 前端访问 `/api/*` 时转发到后端
- 前端访问 `/agent/*` 时转发到 AI 服务

服务调用关系如下：

- `frontend -> backend`：登录、后台管理、预约流程
- `frontend -> agent-service`：AI 问诊与 RAG 调试
- `backend -> agent-service`：部分 AI 代理能力
- `agent-service -> mcp-server`：MCP 工具调用
- `mcp-server -> backend`：医院 / 诊室 / 医生 / 号源接口访问

## 当前代码特点

- 前端主页面目前集中在 `frontend/src/App.vue`
- 样式主要集中在 `frontend/src/styles.css`
- 后端当前使用自定义拦截器完成鉴权，而非完整 Spring Security
- AI 服务当前采用“本地规则 + Chroma 检索 + LangChain 编排 OpenAI-compatible LLM + MCP 工具编排”的混合导诊策略
- LangChain 当前用于组织 prompt、调用 OpenAI-compatible 模型，并通过 Pydantic schema 校验 `patientSummary / departmentRecommendation / reason / generatedAnswer / followUpQuestions / urgency`
- 当前 RAG 使用 `fastembed + BAAI/bge-small-zh-v1.5`
- 当前 knowledge 已统一为 `9` 个文件、`54` 个 chunk，每个高频科室包含 `symptom_match / follow_up / red_flag / boundary_cases / recommendation_request / special_population`
- 后台管理的医院、诊室、医生已切到后端分页接口
- AI 医生推荐会识别省份和城市偏好，并在配额查询失败时继续返回已匹配医生，避免因号源接口失败丢弃全部推荐
- Vite 构建时会有 chunk size warning，但不影响当前运行

## 已实现的用户体验改进

- 首页支持快速查看“我的预约”
- 首页可直接取消有效预约
- 已取消预约不会继续出现在首页预约列表中
- 预约页支持未来 15 天日期卡片展示
- 预约页支持日期取消选择和医生延迟展示
- 首页和预约页的文案与信息层级已做过多轮简化

## 后续可继续完善

- 将 `App.vue` 拆分为更清晰的组件结构
- 增加单元测试、接口测试和端到端测试
- 增加短信 / 邮件通知
- 增加管理员统计图表
- 增加预约记录导出能力
- 将后台卡片式分页视图进一步升级为更适合大数据量的表格视图
- 优化 AI 推荐排序，让推荐医生优先落在更高质量的演示医院上

## 注意事项

- AI 导诊结果仅供参考，不构成正式医疗建议
- 当前仓库未单独声明开源许可证
- 如需公开发布，建议补充 `LICENSE` 并清理敏感配置
