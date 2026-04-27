# Agent Service

IHRS 的独立 AI 导诊服务，基于 FastAPI，负责 RAG 检索、LangChain 大模型编排、多轮问诊上下文、医生推荐编排，以及通过 MCP Server 调用后端医院 / 诊室 / 医生 / 号源能力。

## 功能概览

- 健康检查：`GET /health`
- 普通问诊：`POST /consult`
- 流式问诊：`POST /consult/stream`
- 会话恢复：`GET /consult/session`
- 会话删除：`DELETE /consult/conversations/{conversationId}`
- RAG 调试：
  - `GET /rag/stats`
  - `GET /rag/documents`
  - `POST /rag/search`

当前问诊能力包括：

- 使用 Chroma + FastEmbed 从本地知识库检索导诊片段
- 使用 LangChain 将系统提示词、历史对话、RAG 知识片段和结构化输出解析串成调用链
- 使用 `TriageGeneration` Pydantic schema 校验模型输出字段
- 支持 OpenAI-compatible 模型服务，例如 OpenAI、通义千问兼容接口、DeepSeek 兼容接口
- 未配置 LLM 或模型返回异常时，自动回退到本地规则 + RAG 兜底
- 支持 Redis 保存 `conversationId` 多轮上下文，刷新页面后可恢复当前会话
- 支持通过 MCP Server 查询真实医院、诊室、医生和号源数据
- 支持地域偏好，例如“广东的医院”会约束到广州 / 深圳候选，而不是继续推荐上海
- 支持医生推荐按钮按需展开，避免问诊阶段加载全量医生目录

## 实现链路

```text
前端症状输入
  -> agent-service /consult 或 /consult/stream
  -> Redis 读取当前 conversationId 历史消息
  -> Chroma 检索 knowledge/*.json 导诊 chunk
  -> 规则兜底先生成基础科室和风险判断
  -> LangChain 调用 OpenAI-compatible LLM 并用 PydanticOutputParser 解析
  -> 结合 MCP Server 查询医院 / 诊室 / 医生 / 号源
  -> 返回结构化问诊结果、知识引用和可选医生推荐
```

LangChain 在这里主要负责：

- `ChatPromptTemplate`：组织系统提示词、用户问题、历史上下文和 RAG 知识片段
- `ChatOpenAI`：调用 OpenAI-compatible 模型服务
- `PydanticOutputParser`：要求模型输出符合 `TriageGeneration` 结构
- `prompt | model | parser`：形成稳定的结构化生成链路

RAG 在这里主要负责：

- 启动时读取 `knowledge/` 下的 JSON chunk
- 使用 `fastembed-BAAI/bge-small-zh-v1.5` 生成向量
- 持久化到 `chroma_db/`
- 问诊时按症状和诉求检索 top-k 知识片段
- 将命中的知识片段写入 prompt，并在响应中返回 `knowledgeReferences`

## 目录结构

```text
agent-service/
├── app/
│   ├── main.py                    # FastAPI 路由、问诊主链路、SSE 流式输出
│   ├── llm.py                     # LangChain LLM 客户端与结构化输出解析
│   ├── rag.py                     # Chroma / FastEmbed 知识库加载与检索
│   ├── conversation_store.py      # Redis 多轮问诊会话存储
│   ├── doctor_recommendation.py   # 服务端医生推荐和地域约束
│   └── mcp_client.py              # MCP JSON-RPC 客户端
├── knowledge/                     # 导诊知识库 JSON chunk
├── mcp_server/                    # 独立 MCP Server
├── chroma_db/                     # Chroma 持久化目录
├── Dockerfile
├── Dockerfile.mcp
└── requirements.txt
```

## 技术栈

- FastAPI
- Uvicorn
- Pydantic
- httpx
- Redis
- ChromaDB
- FastEmbed
- LangChain
- LangChain OpenAI
- JSON-RPC over HTTP MCP Server

## 启动方式

### Docker Compose

推荐从仓库根目录启动完整环境：

```bash
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up --build -d
```

默认地址：

- Agent Service：`http://127.0.0.1:8000`
- MCP Server：`http://127.0.0.1:8100`

### 本地启动 Agent Service

```bash
cd agent-service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 本地启动 MCP Server

```bash
cd agent-service
pip install -r requirements.txt
uvicorn mcp_server.http_server:app --host 0.0.0.0 --port 8100
```

## 环境变量

### LLM

- `LLM_BASE_URL`：OpenAI-compatible 接口基地址，例如 `https://api.openai.com/v1`
- `LLM_API_KEY`：模型服务密钥；本地兼容服务可留空
- `LLM_MODEL`：模型名称，例如 `gpt-4o-mini`、`deepseek-chat`、`qwen-plus`
- `LLM_TIMEOUT_SECONDS`：模型调用超时时间，默认 `90`
- `LLM_TEMPERATURE`：模型温度，默认 `0.2`

说明：

- 配置 `LLM_BASE_URL` 和 `LLM_MODEL` 后，`/consult` 会走 `answerMode=langchain`
- 未配置时不会报错，会自动使用 `answerMode=fallback`
- 如果模型输出不符合 `TriageGeneration` schema，也会被捕获并回退到本地导诊

### RAG

- `RAG_EMBEDDING_MODEL_NAME`：向量模型名称，默认 `BAAI/bge-small-zh-v1.5`
- `RAG_EMBEDDING_DEVICE`：运行设备，默认 `cpu`
- `RAG_EMBEDDING_CACHE_DIR`：FastEmbed 模型缓存目录，可选

当前默认知识库规模：

- 知识文件：`9` 个
- 知识 chunk：`54` 个
- 覆盖方向：心内、呼吸、消化、儿科、产科、口腔、康复、中医、全科内科
- 覆盖意图：症状匹配、追问、红旗症状、边界分流、推荐诉求、特殊人群

### 多轮会话

- `REDIS_HOST`：Redis 主机
- `REDIS_PORT`：Redis 端口
- `CONSULT_CONTEXT_TTL_SECONDS`：导诊上下文缓存时长，默认 `43200`
- `CONSULT_CONTEXT_MAX_MESSAGES`：单会话保留的最大消息条数，默认 `12`

### MCP

- `MCP_SERVER_URL`：MCP Server 地址，例如 `http://mcp-server:8100/mcp`
- `MCP_SERVER_TIMEOUT_SECONDS`：Agent 调用 MCP 超时时间，默认 `20`
- `MCP_SERVER_COMMAND`：未使用 HTTP MCP 时的 stdio MCP 启动命令，可选
- `BACKEND_BASE_URL`：MCP Server 调用 Spring Boot 后端地址
- `BACKEND_TIMEOUT_SECONDS`：MCP Server 调用后端超时时间，默认 `15`

## 接口说明

### `GET /health`

返回服务健康状态和 LLM 是否启用。

```json
{
  "service": "agent-service",
  "status": "UP",
  "llmStatus": "ENABLED"
}
```

### `POST /consult`

请求示例：

```json
{
  "symptom": "咳嗽发热三天，想找广东的医院",
  "conversationId": "可选，会话 ID"
}
```

返回字段示例：

```json
{
  "conversationId": "b12570d9d3774e67b40970ad9e16d634",
  "symptom": "咳嗽发热三天，想找广东的医院",
  "recommendationQueryText": "咳嗽发热三天，想找广东的医院",
  "patientSummary": "患者咳嗽伴发热已持续三天，并希望选择广东地区医院。",
  "inputCategory": "medical",
  "departmentRecommendation": "呼吸诊室",
  "reason": "咳嗽发热更符合呼吸系统首诊方向。",
  "generatedAnswer": "建议首诊呼吸诊室。咳嗽伴发热多见于呼吸道感染相关问题，呼吸诊室可进一步评估体温、咳嗽持续时间、痰色和是否气促。若出现呼吸困难、持续高热不退或意识异常，请立即急诊。",
  "followUpQuestions": [
    "最高体温是多少，发热是否持续不退？",
    "有没有咳痰、气促、胸闷或咽痛流涕？"
  ],
  "urgency": "soon",
  "showDoctorRecommendationAction": true,
  "doctorRecommendationButtonText": "推荐医生",
  "answerMode": "langchain",
  "knowledgeReferences": [
    {
      "id": "triage-respiratory-symptom-match",
      "department": "呼吸诊室",
      "intentType": "symptom_match",
      "source": "semantic"
    }
  ],
  "doctorRecommendation": []
}
```

字段说明：

- `conversationId`：多轮问诊会话 ID
- `recommendationQueryText`：结合上下文后的推荐检索文本
- `patientSummary`：患者情况摘要
- `inputCategory`：`medical` / `greeting` / `symptom_needed` / `non_medical`
- `departmentRecommendation`：推荐首诊科室
- `reason`：一句话判断依据
- `generatedAnswer`：生成式导诊回复
- `followUpQuestions`：建议继续追问的关键信息
- `urgency`：`normal` / `soon` / `emergency`
- `showDoctorRecommendationAction`：是否展示“推荐医生”按钮
- `doctorRecommendation`：服务端推荐的医生列表，可能为空
- `answerMode`：`langchain` / `fallback`
- `knowledgeReferences`：RAG 命中的知识引用

### `POST /consult/stream`

请求体与 `/consult` 相同，返回 `text/event-stream`。

事件类型：

- `meta`：会话 ID、推荐科室、摘要等元信息
- `delta`：分段生成文本
- `complete`：完整结构化结果

### RAG 调试接口

`GET /rag/stats` 返回集合名称、知识数量、embedding 版本和持久化目录。

`GET /rag/documents?limit=12` 返回已入库文档片段。

`POST /rag/search` 请求示例：

```json
{
  "query": "咳嗽发热三天应该挂什么科",
  "top_k": 3
}
```

### MCP Server

MCP Server 独立运行在 `mcp_server/http_server.py`，对 Agent 暴露 JSON-RPC 入口：

- `GET /health`
- `POST /mcp`

当前工具包括：

- `search_hospitals`
- `list_rooms`
- `list_doctors`
- `get_doctor_quota`
- `get_doctor_quota_calendar`

## 容错策略

- LLM 未配置：直接走本地规则 + RAG 兜底
- LLM 返回格式错误：捕获解析异常并回退
- MCP 医生推荐失败：保留导诊结果，不影响问诊回答
- 号源查询失败：继续返回已匹配医生，不因配额失败丢弃全部候选
- 地域偏好：提取省份 / 城市约束，例如广东映射到广州、深圳

## 注意事项

- AI 导诊结果仅用于辅助分诊演示，不能替代医生诊断
- 若出现剧烈胸痛、明显呼吸困难、意识异常、抽搐、呕血等红旗症状，应优先急诊
- 如果公开仓库，请不要提交真实 `LLM_API_KEY`
- 首次启动 FastEmbed 可能需要下载模型，网络不通时可提前准备缓存目录
