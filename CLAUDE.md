# CLAUDE.md

## 项目目标
构建一个基于 RAG 的文档问答聊天机器人，支持：
- 中文 PDF 上传
- 基于文档内容问答（禁止使用外部知识）
- 必须提供页码引用（可附原文片段）
- 文档持久化（重启后仍可用）
- 支持 `docker compose up` 一键启动

目标是完成一个 **小而完整、可信、可解释** 的系统，而不是功能堆砌。

---

## 技术栈（已确定，不要改）
- 后端：Python 3.11 + FastAPI
- 前端：React
- 向量库：Chroma（本地持久化）
- Embedding：OpenAI text-embedding-3-small
- LLM：gpt-4o-mini
- PDF 解析：PyMuPDF（fitz）
- 元数据：SQLite
- 测试:pytest + httpx（API 集成测试）
- 编排:docker compose

不要引入 LangChain / LlamaIndex，优先自己实现轻量 RAG pipeline。

明确不做 reranker。我会先跑通主链路,用腾讯年报的示例问题
做 baseline 评测,再决定是否加 reranker。请你在生成实现计划时,
把检索模块设计成可以后续平滑插入 reranker 的接口形态
(例如 Retriever 类有一个 _rerank 钩子,v1 是 identity
函数,v2 可以替换为真实 reranker),但 v1 不实现它。

---

## 核心设计原则（非常重要）

### 1. 严格基于文档（防 hallucination）
- LLM **只能使用检索到的 chunks**
- 如果检索结果不包含答案，必须明确返回：
  > 未在当前文档中找到相关信息
- 禁止编造数据、数字、结论

### 2. 所有答案必须可追溯
- 每个回答必须包含：
  - 页码（必选）
  - 原文引用（推荐）
- chunk 必须保存 page_number metadata

### 3. 检索范围必须受控
- 只能在当前上传/选中的文档中检索
- 不允许跨文档污染答案

### 4. 数据流必须清晰（RAG pipeline）
标准流程：

PDF → 文本 → chunk → embedding → vector store  
用户问题 → embedding → retrieval → LLM → answer + citations

不要跳步骤，不要让 LLM 直接看整篇 PDF。

---

## 代码规范

- 所有函数必须有类型注解
- 核心模块必须写 docstring（解释输入/输出/设计）
- 中文注释 OK，但变量命名用英文
- 模块职责清晰（API / service / db 分层）

### 可测试性（非常重要）
- retrieval / answer generation 必须可单独测试
- 使用依赖注入（不要写死 OpenAI client）
- LLM 调用必须可以 mock

---

## 实现策略约束（防止过度设计）

- 不要实现多用户系统
- 不要实现流式输出（streaming）
- 不要做复杂权限控制
- 不要过度抽象（如过多 repository / abstraction layers）

优先保证：
1. 主链路跑通
2. 答案可信
3. 引用正确
4. 可持久化

---

## 交付物要求（评委关注点）

评委主要考察：

1. Scope 控制（是否没有乱加功能）
2. 架构设计是否清晰
3. 是否能稳定跑通 end-to-end
4. 是否能解释设计取舍

重点不是 feature 数量，而是：
👉 是否“像一个真实可用的小系统”

---

## 测试要求（必须覆盖）

必须至少覆盖：

- PDF 上传 → 文本提取成功
- 中文文本不乱码
- chunk 保留正确页码
- retrieval 只在当前文档范围内
- 回答必须带 citation
- 无答案时拒答（不 hallucinate）
- 服务重启后仍可检索

---

## 我的约束（协作方式）

- 时间有限：优先完成基础闭环
- 每完成一个模块，你必须停下来让我 review
- 不要一次性生成整个项目代码
- 每次只实现一个模块（例如：pdf parsing / chunking / retrieval）

---

## 与 AI 协作规则（非常重要）

你在回答时必须遵守：

1. **只做当前模块，不扩展其他模块**
2. **如果有设计假设，必须明确写出来**
3. **优先给清晰、可维护的代码，而不是复杂设计**
4. **避免过度工程化**
5. **如果有更简单方案，必须指出**

---

## 系统架构（已经评审通过的 plan）

### Upload 链路
```
Browser [PDF] 
  → POST /documents/upload 
  → FastAPI 
  → pdf_processor.py (PyMuPDF get_text("blocks") + 多栏坐标排序 + 段落切分)
  → Chunk[] {text, page_num, chunk_index}
  → embedding_service (OpenAI text-embedding-3-small → float[1536])
  → ChromaDB (vectors + metadata {doc_id, page_num}) 
  → SQLite documents 表 (id, name, path, page_count, created_at)
```

### Query 链路
```
Browser [Question] 
  → POST /chat/completions 
  → retrieval_service (embed query → Chroma top-5 → distance 阈值过滤 0.45)
  → RetrievedChunk[] {text, page, score}
  → chat_service (RAG prompt + 双语拒答指令 → gpt-4o-mini temperature=0)
  → {answer, sources:[{page, snippet}]}
  → Browser (气泡 + 引用卡片)
```

---

## 模块文件清单

### Backend
| 文件 | 职责 |
|------|------|
| `app/main.py` | FastAPI 实例,lifespan 调用 init_db() |
| `app/config.py` | Pydantic Settings 读环境变量 |
| `app/api/deps.py` | 依赖注入:get_db / get_chroma / get_embedding_service |
| `app/api/v1/documents.py` | POST /upload, GET / |
| `app/api/v1/chat.py` | POST /completions |
| `app/services/pdf_processor.py` | PyMuPDF 提取 + 多栏排序 + 分块 |
| `app/services/embedding_service.py` | OpenAI Embedding 批量封装 |
| `app/services/retrieval_service.py` | query embed + Chroma top-k + 距离阈值 + (预留 _rerank 钩子) |
| `app/services/chat_service.py` | RAG prompt + gpt-4o-mini + JSON structured output |
| `app/db/database.py` | SQLAlchemy engine + SessionLocal + init_db (create_all) |
| `app/db/models.py` | 只有 Document 模型,不建 Chunk 表 |
| `app/db/vector_store.py` | 封装 Chroma PersistentClient |
| `app/schemas/document.py` | DocumentInfo, DocumentUploadResponse |
| `app/schemas/chat.py` | ChatRequest, SourceCitation, ChatResponse |

### Frontend(Vite + React + TS)
| 文件 | 职责 |
|------|------|
| `src/App.tsx` | 主页面:左侧文档面板 + 右侧聊天 |
| `src/components/ChatWindow.tsx` | 消息列表 + 自动滚底 |
| `src/components/MessageBubble.tsx` | 单条消息 + 可折叠引用 |
| `src/components/SourceCitation.tsx` | 页码 badge + 原文片段 |
| `src/components/DocumentUpload.tsx` | 拖拽/点击上传 + 进度 |
| `src/components/DocumentList.tsx` | 文档列表 + 多选(限定回答范围) |
| `src/hooks/useChat.ts` | 消息历史 + loading + POST /chat |
| `src/hooks/useDocuments.ts` | GET /documents + 上传触发刷新 |
| `src/lib/api.ts` | fetch 封装,baseURL 从 VITE_API_URL 读 |

---

## 分块策略(已定)
- chunk size: 500 中文字符(约 300 tokens)
- overlap: 80 字符
- 切分优先级:双换行段落边界 > 句末标点(。!?;\n) > 强制切
- 多栏 PDF:`page.get_text("blocks")` → 按 x_bin(左列/右列) + y 排序 → 左列先读完

---

## 三大翻车点(已规避)

### 翻车点 1:多栏 PDF 中文乱序
- 症状:默认 `get_text()` 流式读取,双栏年报左右列交替混入
- 规避:用 `get_text("blocks")`,按 (x_bin, y) 排序,左列读完再读右列
- 验证:上传后打印前 3 页,人工确认

### 翻车点 2:ChromaDB 持久化静默失效
- 症状:路径错或 volume 没挂,Chroma 降级内存模式,重启全丢
- 规避:
  - `os.makedirs(chroma_path, exist_ok=True)`
  - `assert os.access(chroma_path, os.W_OK)`
  - lifespan 中打印 `collection.count()` 到日志
  - docker-compose 显式挂 `./data/chroma:/data/chroma`

### 翻车点 3:LLM 用先验知识答(腾讯是公开信息)
- 症状:sources 为空但 answer 言之凿凿
- 规避:
  - 双语 system prompt(中英各一份)
  - `temperature=0`
  - 检索结果全部低于阈值时 → **chat_service 层直接短路返回固定拒答文本,不调用 LLM**
  - JSON structured output:`{answer, citations:[{page, quote}]}`
  - 集成测试:问文档外问题,断言 sources=[] 且 answer 含"未找到"

---

## 环境变量(.env.example)
```
OPENAI_API_KEY=sk-...
CHROMA_PATH=/data/chroma
SQLITE_PATH=/data/sqlite/app.db
UPLOADS_PATH=/data/uploads
VITE_API_URL=http://localhost:8000
```

---

## Step 验收标准

### Step 1:项目骨架 + Docker Compose
`docker compose up` 无报错,`/health` 返 `{"status":"ok"}`,前端 3000 端口可访问

### Step 2:PDF 上传 + 文本提取
上传腾讯年报,打印前 3 页,中文不乱码,页码准确,SQLite 记录重启后还在

### Step 3:向量化 + Chroma
上传后日志打印 chunk 数(年报约 500-800),`docker compose restart` 后 count 不变

### Step 4:检索
`retrieve("腾讯2025总收入")` 返 top-5 全含财务数据;`retrieve("火星探测")` 返空列表

### Step 5:LLM + 引用
问"腾讯总收入"返 `{answer, sources:[{page, snippet}]}`;文档外问题返 sources=[] 且 answer 含"未找到";空召回短路不调 LLM

### Step 6:前端
上传(进度条)/ 提问 / 气泡答案 / 可折叠引用卡 / 文档列表实时刷新

### Step 7:测试
pytest 全绿,覆盖:中文提取、页码正确、拒答、持久化、端到端上传、短路
---

## 优先开发顺序（必须遵守）

1. PDF 上传 + 文本提取
2. chunking（带页码）
3. embedding + vector store
4. retrieval（top-k + 阈值）
5. answer generation（带 citation + refusal）
6. 持久化（SQLite + Chroma）
7. 测试
8. 前端 UI

不要跳步骤。

---