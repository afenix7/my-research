# Agentic RAG 原理详解与 ChatBox 实现分析

> 来源：视频字幕《Agentic RAG才是未来！吊打传统 RAG！30分钟详解chatbox 的 Agentic 主动决策机制，手把手带你掌握下一代RAG核心原理！》
> 讲师：海文
> 覆盖内容：传统 RAG 原理 → Agentic RAG 概念 → ChatBox 开源实现拆解 → LangGraph 代码实现

---

## 概述

传统 RAG 是"一条直线走到底"的固定流程：检索一次、生成一次、结束。**Agentic RAG** 是对这套流程的根本性升级——它把检索、文件读取等能力封装成可调用的**工具（Tools）**，赋予大模型自主决策权，通过 ReAct 循环（思考→行动→观察→再思考）动态迭代，直到获取足够信息后再生成最终答案。

**核心对比：**
- 传统 RAG：固定流程，检索一次生成一次，缺乏灵活性
- Agentic RAG：智能体行为，可以规划、调用工具、反思、迭代

---

## 目录

1. [传统 RAG 的两条链路](#一传统-rag-的两条链路)
2. [传统 RAG 的局限性](#二传统-rag-的局限性)
3. [Agentic RAG 的核心概念](#三agentic-rag-的核心概念)
4. [模型需要具备的三类核心能力](#四模型需要具备的三类核心能力)
5. [传统 RAG 代码实现](#五传统-rag-代码实现)
6. [ChatBox 的 Agentic RAG 实现](#六chatbox-的-agentic-rag-实现)
7. [ChatBox 的四个核心工具](#七chatbox-的四个核心工具)
8. [Agentic RAG 代码实现（LangGraph）](#八agentic-rag-代码实现langgraph)
9. [多轮搜索案例对比](#九多轮搜索案例对比)
10. [总结](#十总结)

---

## 一、传统 RAG 的两条链路

传统 RAG 由**离线链路**和**在线链路**两部分构成。

### 1.1 离线链路：文档入库

```
原始文档（PDF/Word/TXT）
    ↓ 切片（chunk_size=256，有重叠）
文本段落列表
    ↓ Embedding 模型向量化
固定维度的向量
    ↓ 存储
向量数据库（如 ChromaDB）
```

- **切片参数**：`chunk_size`（每块字符数）+ `chunk_overlap`（相邻块重叠部分）
- **向量化**：用 Embedding 模型（如千问3-embedding-0.6B）将文本转为高维向量
- **存储**：向量和原始文本一起存入向量数据库
- 这一步与用户无关，是**预处理阶段**

### 1.2 在线链路：检索与生成

```
用户问题（User Query）
    ↓ Embedding 模型向量化
查询向量
    ↓ 向量相似度计算（点积/余弦）
Top-K 最相关片段（如 K=3）
    ↓ 拼接进 Prompt 模板
    "你是专业助手，请根据以下文档回答：
     [Context: 片段1, 片段2, 片段3]
     [Question: 用户问题]"
    ↓ 大模型生成
最终答案
```

**Enhanced 版本（传统 RAG 增强）**：
- **Query 改写**：先用 LLM 对用户问题重写，使其更适合检索
- **混合检索**：BM25 关键词检索 + 向量语义检索，两路结果合并
- **重排序（Re-rank）**：合并结果后再做一次排序，取最相关的 Top-K

---

## 二、传统 RAG 的局限性

整个过程是**单向、固定、一次性**的，存在以下问题：

| 问题场景 | 传统 RAG 的表现 |
|---------|--------------|
| 第一轮检索命中率低 | 无法重试，直接返回不相关内容 |
| 用户问"知识库里有哪些文件" | 无法回答，因为它只做语义检索 |
| 信息散落在多个片段中 | 无法主动补全上下文 |
| 需要换一种检索方式 | 无法自适应调整策略 |

**根本原因**：传统 RAG 只在**生成阶段**使用大模型，检索逻辑完全固化，模型没有"决策权"。

---

## 三、Agentic RAG 的核心概念

Agentic RAG 把 RAG 流程中的各个环节（Query 改写、向量检索、关键词搜索、文件读取等）全部封装成**可调用的工具（Tools）**，允许大模型在生成答案前：

1. **自主决策**：判断是否需要调用工具、调用哪个工具
2. **多轮调用**：根据工具返回结果，决定继续调用还是直接回答
3. **动态调整**：观察中间结果，改变检索策略

**ReAct 循环（Agentic 行为的核心）：**

```
用户问题
    ↓
大模型思考（Thinking/Planning）
    ↓
调用工具（Tool Call）
    ↓
观察结果（Observation）
    ↓
再次思考（是否信息足够？）
    ↓ 是       ↓ 否
  生成答案   再次调用工具（换策略/补充信息）
```

这是一个**可以循环的智能体行为闭环**，不再是直线流程。

---

## 四、模型需要具备的三类核心能力

| 能力类型 | 含义 | 体现 |
|---------|------|------|
| **Planning（规划）** | 规划如何完成任务，反思结果质量 | 体现在 long CoT（长链推理）过程中 |
| **Tool Calling（工具调用）** | 多工具协作，或多 Agent 协作 | 体现在工具调用机制里 |
| **Multi-step（多步调用）** | 在回答前能进行多步工具调用 | 体现在 Agent 循环接口里 |

---

## 五、传统 RAG 代码实现

使用 LangChain 实现，技术栈：
- **框架**：LangChain
- **Embedding 模型**：硅基流动 + 千问3-embedding-0.6B（兼容 OpenAI 接口）
- **向量数据库**：ChromaDB

### 5.1 离线链路代码

```python
from langchain.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma

# Step 1: 加载文档
loader = TextLoader("your_document.txt")
documents = loader.load()

# Step 2: 文档切片
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,      # 每块字符数
    chunk_overlap=50     # 相邻块重叠字符数
)
chunks = text_splitter.split_documents(documents)

# Step 3: 向量化并存入 ChromaDB
embedding = OpenAIEmbeddings(
    model="Qwen/Qwen3-Embedding-0.6B",
    openai_api_base="https://api.siliconflow.cn/v1",
    openai_api_key="your_api_key"
)
vectorstore = Chroma.from_documents(
    documents=chunks,   # 切分后的文本块
    embedding=embedding,
    persist_directory="./chroma_db"  # 本地存储路径
)
# 结果：37个文本块存入向量数据库
```

### 5.2 在线链路代码

```python
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

# 加载向量数据库
vectorstore = Chroma(
    persist_directory="./chroma_db",
    embedding_function=embedding
)

# 用户查询
query = "韩立的二哥叫什么名字？"

# 向量相似度检索，返回 Top-3 片段
docs = vectorstore.similarity_search(query, k=3)
context = "\n".join([doc.page_content for doc in docs])

# 构造 Prompt
prompt_template = PromptTemplate.from_template("""
你是一个专业的助手。如果知道就回答，不知道就说不知道，不要胡编乱造。
参考文档：{context}
用户问题：{question}
""")
prompt = prompt_template.format(context=context, question=query)

# 大模型生成答案
llm = ChatOpenAI(model="your_model", api_key="your_key")
answer = llm.invoke(prompt)
```

**实际运行结果说明**：如果检索到的 3 个片段都是关于"大哥"的内容，大模型会如实回答"不知道"，这正暴露了传统 RAG 的局限——context 质量完全依赖单次检索命中率。

---

## 六、ChatBox 的 Agentic RAG 实现

ChatBox 是知名开源 AI 客户端（GitHub 可查源码），它在早期就实现了比其他产品更强的 Agentic RAG 能力。其核心思路是**用时间换取模型智能**。

### 6.1 决策流程图

```
用户发来问题
    ↓
[判断] 模型是否支持工具调用（Function Calling）？
    │
    ├─ 不支持工具调用 ──→ [Prompt 判断] 是否需要检索？
    │                         │
    │                    ├─ 不需要 ──→ 直接回复（跳过检索）
    │                    └─ 需要 ───→ 语义搜索 → 注入 context → 生成回答
    │
    └─ 支持工具调用 ────→ 注册所有工具 → 模型自主决策调用 → 迭代至满足要求 → 生成回答
```

**两种模式的区别：**

| 模式 | 适用场景 | 特点 |
|------|---------|------|
| Prompt 判断模式 | 模型不支持 Function Calling | 用两个 Prompt 分两步决策，效果优于直接塞 context 让模型忽略无关信息 |
| 工具调用模式 | 模型支持 Function Calling | 把所有工具注册给模型，让模型完全自主决策，能力更强 |

### 6.2 关键洞察

> **传统 RAG** 只在**生成阶段**用到大模型。
> **Agentic RAG** 从**用户输入问题那一刻起**就开始用大模型做决策。

---

## 七、ChatBox 的四个核心工具

ChatBox 设计了 4 个特色工具，代表了 Agentic RAG 工具集的最佳实践：

### 工具一：`query_search` — 基础语义检索

最基础的工具，根据 query 在向量数据库中做相似度检索，返回 Top-K 相关片段。这是传统 RAG 唯一的能力，而在 Agentic RAG 中只是工具之一。

### 工具二：`list_files` — 列出知识库文件清单

**解决了传统 RAG 的盲区**：当用户问"你的知识库里有哪些文件"时，传统 RAG 无法回答（它只会检索片段，无法枚举所有文件）。

`list_files` 工具能直接返回当前知识库中所有文件的名称、数量等元信息，作为**兜底工具**使用。

### 工具三：`read_file_chunk` — 按 ID 精确读取片段

**两大核心优势：**

1. **精确读取**：根据 chunk ID 直接读取特定片段，不依赖语义相似度
2. **主动扩展上下文**：当发现某片段信息不完整时，模型可以主动读取**前后相邻 chunk**，补充上下文

```
传统 RAG：
  向量检索 → 命中 chunk_5（信息不完整）→ 强行回答

Agentic RAG with read_file_chunk：
  向量检索 → 命中 chunk_5（信息不完整）
           → 调用 read_file_chunk(chunk_4) 读取前文
           → 调用 read_file_chunk(chunk_6) 读取后文
           → 拼合完整上下文 → 生成准确答案
```

### 工具四：`get_file_metadata` — 读取文件元数据

读取文件级别的原始元数据（文件名、大小、时间戳等），使用频率较低，作为辅助工具。

### 工具能力对比表

| 工具 | 传统 RAG 能做到吗 | 解决的问题 |
|------|----------------|----------|
| `query_search` | ✅ 能（唯一方式） | 基础语义检索 |
| `list_files` | ❌ 不能 | 知识库文件枚举 |
| `read_file_chunk` | ❌ 不能 | 精确定位 + 主动补全上下文 |
| `get_file_metadata` | ❌ 不能 | 文件元信息查询 |

---

## 八、Agentic RAG 代码实现（LangGraph）

使用 LangGraph 的 `create_react_agent` 一键实现 Agentic RAG。

### 8.1 工具定义示例

```python
from langchain.tools import tool

@tool
def query_search(query: str) -> str:
    """在知识库中进行语义检索，返回相关文档片段"""
    docs = vectorstore.similarity_search(query, k=3)
    return "\n".join([doc.page_content for doc in docs])

@tool
def list_files() -> str:
    """列出知识库中所有文件的清单"""
    # 返回文件列表
    return "文件列表：file1.txt, file2.pdf, ..."

@tool
def read_file_chunk(chunk_id: str) -> str:
    """根据 chunk ID 精确读取文档片段，可用于补充上下文"""
    # 按 ID 读取特定 chunk，并可扩展读取相邻 chunk
    return "chunk 内容..."

@tool
def get_file_metadata(file_id: str) -> str:
    """读取文件的元数据信息（文件名、大小等）"""
    return "元数据..."
```

### 8.2 创建 Agentic RAG Agent

```python
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

# 初始化大模型
llm = ChatOpenAI(model="your_model", api_key="your_key")

# 注册工具列表
tools = [query_search, list_files, read_file_chunk, get_file_metadata]

# 系统提示词（引导模型使用工具的关键）
system_prompt = """你是一个 Agentic RAG 助手。
在回答问题前，你应该：
1. 首先判断是否需要检索知识库
2. 如有需要，调用 query_search 进行检索
3. 如果结果不完整，使用 read_file_chunk 补充上下文
4. 如果需要了解知识库内容，使用 list_files
5. 获得足够信息后，生成最终答案

注意：工具调用参数必须严格遵守格式，不要省略引号或括号。
"""

# 三个参数创建 ReAct Agent
agent = create_react_agent(
    model=llm,              # 大模型
    tools=tools,            # 工具列表
    prompt=system_prompt    # 系统提示词
)

# 调用
result = agent.invoke({
    "messages": [{"role": "user", "content": "基于知识库概述其优缺点并给出引用"}]
})
print(result["messages"][-1].content)
```

### 8.3 重要注意事项

> **提示词必须限制输出格式**：不加限制时，模型可能会省略工具调用中的引号或括号，导致工具调用失败。需要在 System Prompt 中明确要求严格的格式。

---

## 九、多轮搜索案例对比

以一个复杂问题为例，展示两种 RAG 的处理差异：

### 传统 RAG
```
用户问题 → 向量检索 → 检索到结果（命中率低）→ 直接生成答案（可能不准确）
```

### Agentic RAG
```
用户问题
    ↓
第一轮 query_search（命中率低）
    ↓ 观察：相关度不高
改写 Query，进行第二轮 query_search
    ↓ 观察：命中部分相关 chunks
第三轮 read_file_chunk 补充相邻上下文
    ↓ 观察：信息已足够
生成最终答案（包含精确引用）
```

**关键差异**：Agentic RAG 在发现"命中率低"时，会主动**改写查询词**再重试，而不是直接放弃。

---

## 十、总结

### 核心思想对比

| 维度 | 传统 RAG | Agentic RAG |
|------|---------|-------------|
| 流程模式 | 固定单向，一次性 | 动态循环，多轮迭代 |
| LLM 介入时机 | 仅在生成阶段 | 从问题分析阶段开始 |
| 检索策略 | 固化，无法调整 | 自主决策，动态调整 |
| 失败处理 | 直接返回不相关内容 | 改写查询/换工具重试 |
| 上下文补全 | 无法主动扩展 | 可读取相邻 chunk 补全 |
| 代码复杂度 | 简单直接 | 借助 LangGraph 同样简洁 |

### Agentic RAG 的实现要素

```
1. 工具化  — 把检索、文件操作封装成 Tools
2. 决策权  — 把工具集交给模型，由模型自主选择
3. 循环    — 用 ReAct Agent（思考→行动→观察）驱动迭代
4. 提示词  — 引导模型正确使用工具（格式必须严格）
```

### ChatBox 的设计亮点

- **双模式兼容**：自动检测模型是否支持 Function Calling，给出不同实现路径
- **`list_files` 工具**：弥补了传统 RAG 无法枚举文件的盲区
- **`read_file_chunk` 工具**：实现精确定位 + 主动上下文补全，突破了纯语义检索的局限
- **核心逻辑极简**：企业级产品背后的关键逻辑就是 `create_react_agent` + 4 个工具，复杂度在边界处理而非核心逻辑

### 技术栈参考

| 组件 | 选择 | 说明 |
|------|------|------|
| Agent 框架 | LangGraph `create_react_agent` | 内置 ReAct 循环，一行创建 Agent |
| RAG 框架 | LangChain | 文档加载、切片、检索全套工具 |
| Embedding 模型 | 硅基流动 + Qwen3-Embedding-0.6B | 国内免费额度，OpenAI 兼容接口 |
| 向量数据库 | ChromaDB | 轻量级，适合本地开发 |
| LLM | GPT / Claude / DeepSeek 等 | 需支持 Function Calling 以获得最佳效果 |
