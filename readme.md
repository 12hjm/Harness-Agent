# RAG Agent Customer Service

基于 LangGraph + FastAPI 的中文客服 RAG-Agent。它从本地 `data/kb/` 同步知识库文档，使用向量检索生成客服答案，并提供企业微信、飞书 webhook 入口。

## Quick Start

1. 复制配置：

```powershell
Copy-Item .env.example .env
```

2. 本地开发默认可用 mock/hash 模型启动：

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\uvicorn app.main:app --reload
```

3. 触发知识库索引：

```powershell
$env:ADMIN_TOKEN="dev-admin-token"
.\scripts\reindex_kb.ps1 -AdminToken "dev-admin-token"
```

4. 测试问答：

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/chat" -ContentType "application/json" -Body '{"message":"退款多久到账？"}'
```

## Docker 部署

生产建议使用 `.env.example` 中的 Postgres/Qdrant/Redis 配置：

```powershell
Copy-Item .env.example .env
docker compose up -d --build
```

配置公网 HTTPS 后，将平台回调地址设置为：

- 企业微信：`https://your-domain.example.com/webhooks/wecom`
- 飞书：`https://your-domain.example.com/webhooks/feishu`

## 模块

- `app/agent`：LangGraph 客服 Agent 流程。
- `app/rag`：文档加载、chunk、embedding、检索和索引。
- `app/api`：FastAPI 路由、admin API、平台 webhook。
- `app/integrations`：模型、企业微信、飞书适配。
- `app/storage`：会话、幂等、索引任务存储。
