# RAG 多智能体笔记本客服系统

> 调度-专家模式（Dispatcher-Specialist）多智能体 + RAG 混合检索 + MCP 外部工具的智能客服系统

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Vue3](https://img.shields.io/badge/Vue-3.5-4FC08D?logo=vue.js&logoColor=white)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Milvus](https://img.shields.io/badge/Milvus-2.4-00A1EA)](https://milvus.io/)

---

## 项目简介

面向笔记本电脑售后场景的智能客服系统。针对单一 Agent 在复杂业务下**上下文膨胀**和**工具调用混乱**的问题，采用调度-专家架构：由调度智能体统一做意图识别与分发，各垂直领域专家智能体各司其职。

**核心设计**：纯向量召回在型号编号、专业术语类问题上容易漏召，叠加 BM25 关键词路补齐这部分盲区；两路候选再由 Cross-Encoder 统一精排，而非直接加权融合（两路分数不在同一量纲）。详见下方「RAG 混合检索链路」。

### 架构模式

```
用户问题
   │
   ▼
┌─────────────────────────────────────────┐
│         Triage Agent（调度智能体）        │
│    意图分类 · 无工具 · 仅通过 handoff 委派 │
└──┬──────────┬──────────┬────────────────┘
   │ handoff  │ handoff  │ handoff
   ▼          ▼          ▼
┌────────┐ ┌─────────┐ ┌──────────┐
│Tech    │ │Nav      │ │General   │
│Expert  │ │Expert   │ │Agent     │
│技术专家 │ │导航专家  │ │通用闲聊   │
│        │ │         │ │          │
│rag_    │ │map_     │ │无工具     │
│search  │ │locate   │ │          │
│        │ │map_     │ │          │
│        │ │search   │ │          │
│        │ │map_dist │ │          │
└────────┘ └─────────┘ └──────────┘
```

**为什么这样拆分？**

- **单 Agent 的问题**：所有工具（知识检索 + 地图导航）塞进同一个上下文，工具描述互相干扰，模型容易选错工具；长对话累积后上下文迅速膨胀，成本和延迟同步上升。
- **拆分后的收益**：每个专家只持有自己领域的工具与提示词，工具选择准确率提升；调度层只做分类，逻辑清晰、便于单独调试和扩展新领域。

---

## 技术栈

| 层次 | 技术选型 |
|---|---|
| **多智能体** | OpenAI Agents SDK · 调度-专家模式 · handoff 委派 |
| **检索增强** | LangChain 文本切分 · Qwen3-Embedding · Milvus · jieba + BM25 · BAAI/bge-reranker-v2-m3（Cross-Encoder） |
| **外部工具** | MCP 协议 · 百度地图服务（定位 / 站点查询 / 距离计算） |
| **后端** | FastAPI · Pydantic · SSE 流式输出 · Python asyncio |
| **存储** | Milvus（向量库）· MySQL（会话与文档元数据） |
| **前端** | Vue 3 · TypeScript · Vite · vue-router · marked · highlight.js |

---

## RAG 混合检索链路

纯向量召回在专业术语、型号编号等场景下容易漏召，因此引入关键词路补齐：

```
用户问题
   │
   ├──────────────► 路 1：向量语义召回
   │                  Qwen3-Embedding → Milvus
   │                  Top-K = 10
   │
   └──────────────► 路 2：BM25 关键词召回
                      jieba 分词 → BM25（k1=1.5, b=0.75）
                      Top-K = 10
                              │
                              ▼
                    ┌─────────────────────┐
                    │  Cross-Encoder 重排序 │
                    │  bge-reranker-v2-m3  │
                    │  两路候选统一打分       │
                    └──────────┬──────────┘
                               ▼
                          精排后 Top-N
                               │
                               ▼
                        注入专家 Agent 上下文
```

**关键设计**：

- **BM25 双路并行**：vocabulary 由 jieba 分词构建，参数 `k1=1.5` / `b=0.75`，与向量路结果并行产出，避免单一召回策略的盲区
- **Cross-Encoder 统一精排**：两路候选合并后由 `bge-reranker-v2-m3` 统一打分，而非简单加权融合——因为两路分数不在同一量纲，直接加权不可靠
- **重排序器懒加载 + 降级**：`CrossEncoder` 惰性初始化，不可用时自动跳过重排继续走召回结果，不让可选组件阻塞主链路

---

## 目录结构

```
├── backend/
│   ├── app/
│   │   ├── agents/              # 多智能体层
│   │   │   ├── triage.py        #   调度智能体（意图分类 + handoff）
│   │   │   ├── tech_expert.py   #   技术专家（持有 rag_search 工具）
│   │   │   ├── nav_expert.py    #   导航专家（持有 3 个地图工具）
│   │   │   └── general.py       #   通用闲聊兜底
│   │   ├── rag/                 # 检索增强层
│   │   │   ├── document.py      #   文档解析与切分
│   │   │   ├── embedding.py     #   向量化
│   │   │   └── retrieval.py     #   混合检索（BM25 + 向量 + 重排序）
│   │   ├── mcp/                 # MCP 工具服务
│   │   │   └── baidu_map_server.py
│   │   ├── db/                  # Milvus / MySQL 连接与模型
│   │   ├── api/                 # 路由层
│   │   │   ├── chat.py          #   对话接口（SSE 流式）
│   │   │   ├── documents.py     #   知识库文档管理
│   │   │   └── stations.py      #   服务站点
│   │   ├── models/              # 数据模型
│   │   ├── config.py            # 配置管理
│   │   └── main.py              # 应用入口
│   ├── tests/                   # 测试（含召回率测试、性能测试）
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/                    # Vue3 前端
│   ├── src/
│   │   ├── views/ChatView.vue
│   │   ├── components/          #   ChatWindow / ChatMessage / SourceCard
│   │   └── composables/useChat.ts
│   └── package.json
└── 系统架构文档.md               # 完整架构设计说明
```

---

## API 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/chat` | 对话接口（**SSE 流式**返回） |
| `GET` | `/api/chat/conversations` | 会话列表 |
| `GET` | `/api/chat/conversations/{session_id}` | 会话详情 |
| `GET` | `/api/chat/bm25-debug` | BM25 召回调试接口 |
| `POST` | `/api/documents` | 上传知识库文档 |
| `GET` | `/api/documents` | 文档列表 |
| `DELETE` | `/api/documents/{doc_id}` | 删除文档 |
| `GET` | `/api/stations` | 服务站点查询 |

---

## 快速开始

### 前置依赖

- Python 3.11+
- Node.js 18+
- Milvus 2.4+（向量库）
- MySQL 8.0+（关系型存储）

> Milvus 和 MySQL 可以用 Docker 一键拉起（见下），无需手动安装。

### 一键启动依赖（Docker）

```bash
docker compose up -d
```

会在本地启动 MySQL 8.0（自动创建 `customer_service` 库）和 Milvus 2.4 standalone。`.env` 中对应填：

```
MYSQL_HOST=localhost  MYSQL_PORT=3306  MYSQL_USER=root  MYSQL_PASSWORD=your_password  MYSQL_DATABASE=customer_service
MILVUS_HOST=localhost  MILVUS_PORT=19530
```

Milvus collection 和 MySQL 表由后端应用启动时自动创建，无需手动初始化。

### 后端

```bash
cd backend

# 1. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，填入以下必需项：
#   DASHSCOPE_API_KEY   —— 向量化与 LLM 调用
#   OPENAI_API_KEY      —— LLM 服务
#   MILVUS_HOST / PORT  —— 向量库地址
#   MYSQL_HOST / USER / PASSWORD / DATABASE

# 4. 启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

---

## 环境变量

| 变量 | 说明 |
|---|---|
| `DASHSCOPE_API_KEY` | **必填**，阿里云百炼 API Key（Embedding） |
| `OPENAI_API_KEY` | **必填**，LLM API Key |
| `OPENAI_BASE_URL` | LLM 服务地址 |
| `LLM_MODEL` | LLM 模型名 |
| `MILVUS_HOST` / `MILVUS_PORT` | 向量库连接信息 |
| `MILVUS_COLLECTION` | 向量集合名 |
| `MYSQL_HOST` / `MYSQL_PORT` | 数据库连接信息 |
| `MYSQL_USER` / `MYSQL_PASSWORD` / `MYSQL_DATABASE` | 数据库凭据 |
| `BAIDU_MAP_AK` | 百度地图开放平台 AK（导航工具） |

> 完整字段见 `backend/.env.example`

---

## 工程设计要点

**1. 调度-专家模式的取舍**

拆成多 Agent 的代价是 handoff 有一次额外的 LLM 调用（延迟 +1 次）。收益是每个专家的提示词和工具集都极小，工具选择准确率显著提升。在"工具少但调用频繁"的售后场景下，这个取舍是划算的。

**2. 为什么用 Cross-Encoder 而不是加权融合**

BM25 分数（无上界）和向量相似度（0-1）**量纲不同**，直接加权融合需要反复调参且不稳定。Cross-Encoder 让两路候选进入同一个模型统一打分，把"融合"问题变成"精排"问题，效果更可控。

**3. 重排序器的降级设计**

`bge-reranker-v2-m3` 需要下载模型、占用内存，且非核心链路必需。因此设计为懒加载 + 不可用时自动跳过——保证检索功能在任何环境下都有降级路径，不会因为一个可选组件导致整个服务起不来。

**4. 启动依赖的顺序编排**

通过 FastAPI `lifespan` 统一编排 MySQL → Milvus → BM25 索引的初始化顺序，避免连接就绪前收到请求导致的竞态问题。

---

## License

MIT
