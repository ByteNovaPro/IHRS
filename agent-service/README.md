# Agent Service

IHRS 的独立 AI 服务，基于 FastAPI。

## 当前功能

- 健康检查接口：`GET /health`
- 导诊占位接口：`POST /consult`

当前 `consult` 仍为骨架返回，用于后续接入真实 AI 导诊流程。

## 技术栈

- FastAPI
- Uvicorn
- Pydantic
- httpx

## 启动方式

```bash
cd agent-service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

默认地址：

```text
http://localhost:8000
```

## 当前接口

### `GET /health`

返回服务健康状态。

### `POST /consult`

请求示例：

```json
{
  "symptom": "发热咳嗽三天"
}
```

当前返回：
- 推荐科室占位
- 医生推荐占位
- 推荐理由占位

## 后续建议

这个服务更适合继续接入 `LangChain`，用于实现：
- 症状理解
- 科室推荐
- 医生推荐
- RAG 知识检索
- 工具调用与多轮对话
