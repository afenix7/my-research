# LangGraph 完整教程：从入门到实战

> 来源：3 小时完整教程视频字幕（基础 & 进阶）
> 讲师：Viva（机器人与 AI 专业学生）
> 本笔记覆盖教程前半部分（基础图结构 + 首个 AI 智能体）

---

## 概述

LangGraph 是一个基于**图（Graph）**结构的 Python 库，专门用于构建高级对话式 AI 工作流。它建立在 LangChain 之上，通过可视化的节点（Node）和边（Edge）来设计、实现和管理复杂的对话系统。

**核心价值：**
- 以图的方式描述 AI 工作流，逻辑清晰
- 支持顺序执行、条件分支、循环、并发等流程
- 便于管理多节点之间的状态共享
- 可构建生产级的、可扩展的对话 Agent

---

## 目录

1. [Python 类型注解基础](#一python-类型注解基础)
2. [LangGraph 核心概念](#二langgraph-核心概念)
3. [图一：Hello World 单节点图](#三图一hello-world-单节点图)
4. [图二：多输入图（处理列表数据）](#四图二多输入图处理列表数据)
5. [图三：顺序多节点图（使用边连接）](#五图三顺序多节点图使用边连接)
6. [图四：条件路由图（Conditional Edge）](#六图四条件路由图conditional-edge)
7. [图五：循环图（Loop）](#七图五循环图loop)
8. [第一个 AI 智能体（集成 LLM）](#八第一个-ai-智能体集成-llm)
9. [关键 API 速查表](#九关键-api-速查表)
10. [总结](#十总结)

---

## 一、Python 类型注解基础

> 教程在正式写代码之前，专门讲解了 LangGraph 中频繁使用的 Python 类型注解，因为它们在定义状态时无处不在。

### 1.1 普通字典 vs TypedDict

**问题：** 普通 Python 字典不做类型检查，容易引入逻辑错误。

```python
# 普通字典 - 无类型约束，键值随意
movie = {
    "name": "复仇者联盟：终局之战",
    "year": 2019
}
```

**解决方案：`TypedDict`** — 通过类定义字典结构，明确每个键的数据类型。

```python
from typing import TypedDict

class Movie(TypedDict):
    name: str   # 明确 name 必须是字符串
    year: int   # 明确 year 必须是整数

movie: Movie = {
    "name": "复仇者联盟：终局之战",
    "year": 2019
}
```

**TypedDict 的两大好处：**
- **类型安全**：明确指定数据结构，减少运行时错误
- **可读性提升**：代码意图更清晰，调试更容易

> 在 LangGraph 中，`TypedDict` 被广泛用来定义**状态（State）**。

---

### 1.2 Union 联合类型

表示一个值可以是多种类型之一，使用 `Union[类型A, 类型B]` 或 Python 3.10+ 的 `类型A | 类型B`。

```python
from typing import Union

def square(x: Union[int, float]) -> Union[int, float]:
    """计算 x 的平方，x 可以是整数或浮点数"""
    return x * x

square(5)     # 合法
square(1.234) # 合法
square("hi")  # 类型错误：字符串不被允许
```

---

### 1.3 Optional 可选类型

`Optional[X]` 等价于 `Union[X, None]`，表示值可以是某种类型或者 `None`。

```python
from typing import Optional

def nice_message(name: Optional[str] = None) -> str:
    """生成友好消息，name 可以是字符串或 None"""
    if name is None:
        return "嘿，随机的人！"
    return f"Hi {name}!"

nice_message("Bob")  # → "Hi Bob!"
nice_message()       # → "嘿，随机的人！"
```

---

### 1.4 Any 任意类型

`Any` 表示该值可以是任何数据类型，不作类型约束。

```python
from typing import Any

def print_value(value: Any) -> None:
    print(value)

print_value("字符串")   # 合法
print_value(123)        # 合法
print_value([1, 2, 3])  # 合法
```

---

### 1.5 Lambda 函数

Lambda 是编写小型匿名函数的快捷方式，在数据处理中非常高效。

```python
# 普通函数写法
def square(x):
    return x * x

# Lambda 等价写法
square = lambda x: x * x
print(square(10))  # → 100

# 配合 map 使用（更常见的实战用法）
numbers = [1, 2, 3, 4]
squared = list(map(lambda x: x * x, numbers))
print(squared)  # → [1, 4, 9, 16]
```

---

## 二、LangGraph 核心概念

### 2.1 State（状态）

**定义：** 一个共享的数据结构，存储整个应用程序的当前信息或上下文。

**类比：** 会议室里的白板 — 所有参与者（节点）都可以读取和更新白板上的信息。

- 状态展示了应用程序的最新内容
- 所有节点都可以访问和修改状态
- 在 LangGraph 中，状态通过 `TypedDict` 子类来定义

---

### 2.2 Node（节点）

**定义：** 图中执行特定任务的独立函数或操作单元。

**特征：**
- 接受当前**状态**作为输入
- 对状态进行处理
- 返回**更新后的状态**

**类比：** 流水线上的工作站 — 每个站点负责一项特定任务（安装零件、涂漆、质检等）。

---

### 2.3 Graph（图）

**定义：** 描述所有节点如何连接和执行的总体结构，以可视化方式呈现工作流程。

**类比：** 路线图 — 显示城市（节点）之间的路线和交叉路口（边），提供行进方向。

---

### 2.4 Edge（边）

**定义：** 节点之间的连接，决定执行流程的方向。

**作用：** 告诉应用程序，在当前节点完成任务后，接下来应执行哪个节点。

**类比：** 火车轨道 — 连接两个站点（节点），状态就像火车在轨道上行进，逐站更新。

---

### 2.5 Conditional Edge（条件边）

**定义：** 根据当前状态中的特定条件或逻辑，决定下一个执行节点的特殊边。

**类比：** 交通灯 — 绿灯通行、红灯停止、黄灯减速，颜色（条件）决定下一步动作。

本质上等同于 `if-else` 语句，但以图的方式呈现。

---

### 2.6 Start / End（起点与终点）

- **起点（Start）**：图执行的虚拟入口，标志工作流从哪里开始。不执行任何操作，类比比赛的起跑线。
- **终点（End）**：表示工作流结束。当应用程序到达此节点时，图的执行完全停止，类比终点线。

---

### 2.7 Tools（工具）与 Tool Node（工具节点）

- **工具（Tools）**：专门的函数或实用程序，例如从 API 获取数据、执行搜索等。工具是节点内部使用的功能。
- **工具节点（Tool Node）**：一种特殊节点，其主要任务是运行工具，并将工具输出连接回状态供其他节点使用。

> 区别：节点是图结构的一部分；工具是节点内部使用的功能。

---

### 2.8 StateGraph（状态图）

**定义：** LangGraph 中用于构建和编译图结构的核心类，管理节点、边和整体状态。

**类比：** 建筑的蓝图 — 勾勒出建筑物的设计和连接方式，定义应用程序的结构和流程。

```python
from langgraph.graph import StateGraph

graph = StateGraph(AgentState)  # 传入状态模式
```

---

### 2.9 Runnable（可运行组件）

**定义：** 标准化的可执行组件，用于在 AI 工作流中完成特定任务，是模块化系统的基础构建块。

**类比：** 乐高积木 — 可以拼接组合，构建复杂的 AI 工作流。

> 区别：Runnable 可以代表各种操作；LangGraph 中的节点通常专指接收状态、执行操作、更新状态的函数。

---

### 2.10 消息类型（Message Types）

LangGraph 中最常见的 5 种消息类型：

| 消息类型 | 说明 |
|---|---|
| `HumanMessage` | 用户的输入，表示人类提供给 AI 的消息 |
| `AIMessage` | 由大语言模型（LLM）生成的响应 |
| `SystemMessage` | 为模型提供指令或上下文背景 |
| `ToolMessage` | 专门用于工具调用结果的消息 |
| `FunctionMessage` | 函数调用的结果（类似 ToolMessage） |

---

## 三、图一：Hello World 单节点图

> 目标：理解状态定义、节点函数、图的构建与调用，数据如何通过单个节点流动。

**图结构：** `START → greeter → END`

### 完整代码

```python
from typing import TypedDict
from langgraph.graph import StateGraph

# 第一步：定义状态模式（Agent State）
# 状态是共享的数据结构，跟踪应用程序运行时的所有信息
class AgentState(TypedDict):
    message: str  # 只有一个属性：消息字符串

# 第二步：定义节点函数
# 节点是图中执行特定任务的独立函数
# 输入类型必须是 AgentState，输出类型也必须是 AgentState
def greeting_node(state: AgentState) -> AgentState:
    """一个向状态添加问候消息的简单节点"""
    # 读取状态中的消息，并更新它
    state["message"] = "嘿 " + state["message"] + "，今天过得怎么样？"
    return state

# 第三步：构建图
graph = StateGraph(AgentState)  # 传入状态模式

# 第四步：添加节点（节点名称, 对应的函数）
graph.add_node("greeter", greeting_node)

# 第五步：设置起点和终点
graph.set_entry_point("greeter")   # 起点连接到 greeter 节点
graph.set_finish_point("greeter")  # 终点连接自 greeter 节点

# 第六步：编译图（注意：编译成功 ≠ 逻辑正确）
app = graph.compile()

# 第七步：调用图（invoke 方法）
result = app.invoke({"message": "Bob"})
print(result["message"])
# 输出：嘿 Bob，今天过得怎么样？
```

### 关键要点

- **状态（State）** 通过 `TypedDict` 子类定义，本例只有一个 `message: str` 属性
- **节点函数** 的输入和输出类型都是 `AgentState`（状态）
- **文档字符串（docstring）** 非常重要，当构建真正的 AI 智能体时，LLM 会通过 docstring 了解节点的功能
- `graph.compile()` 返回可调用的 `app` 对象
- `app.invoke()` 传入初始状态字典，返回最终状态字典

---

## 四、图二：多输入图（处理列表数据）

> 目标：理解如何处理多个输入属性，以及如何在状态中处理不同数据类型（不仅仅是字符串）。

### 完整代码

```python
from typing import TypedDict, List
from langgraph.graph import StateGraph

# 状态中包含多个属性，包括列表类型
class AgentState(TypedDict):
    values: List[int]   # 整数列表
    result: int         # 处理结果

def process_node(state: AgentState) -> AgentState:
    """处理数值列表，计算总和并存入 result"""
    state["result"] = sum(state["values"])
    return state

graph = StateGraph(AgentState)
graph.add_node("processor", process_node)
graph.set_entry_point("processor")
graph.set_finish_point("processor")
app = graph.compile()

# 调用时传入多个属性
result = app.invoke({"values": [1, 2, 3, 4, 5], "result": 0})
print(result["result"])  # → 15
```

### 关键要点

- 状态可以包含**多个属性**，类型可以是任意 Python 类型（`str`、`int`、`List`、`Dict` 等）
- 调用 `invoke` 时，需要提供所有状态属性的初始值
- 节点可以读取状态中的任意属性，并更新任意属性

---

## 五、图三：顺序多节点图（使用边连接）

> 目标：学习如何通过边（Edge）将多个节点顺序连接。理解状态如何在节点间传递和累积。

**图结构：** `START → first_node → second_node → END`

### 完整代码

```python
from typing import TypedDict
from langgraph.graph import StateGraph

class AgentState(TypedDict):
    name: str    # 输入：姓名
    age: str     # 输入：年龄
    final: str   # 输出：最终消息（由两个节点共同构建）

def first_node(state: AgentState) -> AgentState:
    """序列中的第一个节点：生成问候语"""
    state["final"] = f"嗨 {state['name']}！"
    return state

def second_node(state: AgentState) -> AgentState:
    """序列中的第二个节点：追加年龄信息"""
    # 注意：必须追加（+=），而不是替换，否则会丢失第一个节点的结果
    state["final"] += f" 你今年 {state['age']} 岁了！"
    return state

# 构建图
graph = StateGraph(AgentState)

# 添加两个节点
graph.add_node("first_node", first_node)
graph.add_node("second_node", second_node)

# 设置起点 → 第一个节点
graph.set_entry_point("first_node")

# 关键：用 add_edge 连接两个节点（有向边）
graph.add_edge("first_node", "second_node")

# 设置终点 → 第二个节点
graph.set_finish_point("second_node")

app = graph.compile()

result = app.invoke({"name": "Charlie", "age": "20", "final": ""})
print(result["final"])
# 输出：嗨 Charlie！ 你今年 20 岁了！
```

### 关键要点

- **`graph.add_edge(from_node, to_node)`** 用于在两个节点间创建有向边
- 边是**有向的**，数据从 `first_node` 流向 `second_node`
- **常见陷阱**：在第二个节点中用赋值（`=`）替代追加（`+=`），会导致第一个节点的结果丢失
- 正确做法是使用字符串拼接或列表追加来**保留**之前节点的输出

---

## 六、图四：条件路由图（Conditional Edge）

> 目标：学习如何根据状态中的条件，动态决定下一步执行哪个节点。

**图结构：** `START → router → (加法节点 or 减法节点) → END`

### 完整代码

```python
from typing import TypedDict
from langgraph.graph import StateGraph, END

class AgentState(TypedDict):
    number1: int
    number2: int
    operation: str    # "+" 或 "-"
    final_number: int

# 节点 1：加法
def addition_node(state: AgentState) -> AgentState:
    """执行加法运算"""
    state["final_number"] = state["number1"] + state["number2"]
    return state

# 节点 2：减法
def subtraction_node(state: AgentState) -> AgentState:
    """执行减法运算"""
    state["final_number"] = state["number1"] - state["number2"]
    return state

# 节点 3：路由器（决定走哪条边）
def router(state: AgentState) -> AgentState:
    """路由节点：接收输入，不做实际计算，交给条件边决定流向"""
    return state

# 路由函数：返回边的名称（字符串），决定下一步走哪条路
def decide_next_node(state: AgentState) -> str:
    """根据操作符返回对应的边名称"""
    if state["operation"] == "+":
        return "addition_operation"    # 边的名称
    else:
        return "subtraction_operation" # 边的名称

# 构建图
graph = StateGraph(AgentState)

graph.add_node("router", router)
graph.add_node("addition_node", addition_node)
graph.add_node("subtraction_node", subtraction_node)

# 起点 → 路由器
graph.set_entry_point("router")

# 关键：添加条件边
# 参数1：源节点（router）
# 参数2：路由函数（decide_next_node）
# 参数3：路径映射字典 {"边名称": "目标节点名称"}
graph.add_conditional_edges(
    "router",          # 源节点
    decide_next_node,  # 路由函数
    {
        "addition_operation":    "addition_node",     # 边名 → 目标节点
        "subtraction_operation": "subtraction_node",  # 边名 → 目标节点
    }
)

# 两个分支都需要连接到终点
graph.add_edge("addition_node", END)
graph.add_edge("subtraction_node", END)

app = graph.compile()

# 测试减法
result = app.invoke({
    "number1": 10,
    "operation": "-",
    "number2": 5,
    "final_number": 0
})
print(result)
# number1=10, operation="-", number2=5, final_number=5
```

### 关键要点

- **`graph.add_conditional_edges(source, path_fn, path_map)`** 是条件路由的核心 API
  - `source`：条件边的起始节点名称
  - `path_fn`：路由函数，接收 `state`，返回一个字符串（边的名称）
  - `path_map`：字典，将边名称映射到目标节点名称
- 路由函数的返回值必须是 `path_map` 中的某个键
- 多个分支都需要单独用 `add_edge` 连接到 `END`
- 从 `langgraph.graph` 导入 `END` 常量表示终点

---

## 七、图五：循环图（Loop）

> 目标：实现包含循环的图逻辑 — 数据可以流回之前的节点，直到满足退出条件。

### 核心思路

循环图的实现方式：用**条件边**来决定是"继续循环"还是"退出到 END"。

```
START → guess_node → check_node → (继续循环 → guess_node) 或 (退出 → END)
```

### 代码示例（更高或更低猜数游戏）

```python
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
import random

class AgentState(TypedDict):
    player_name: str
    guesses: List[int]       # 历史猜测记录
    attempts: int            # 当前尝试次数
    lower_bound: int         # 猜测下界
    upper_bound: int         # 猜测上界
    target: int              # 目标数字
    hint: str                # 提示：更高/更低/正确

MAX_ATTEMPTS = 7

def guess_node(state: AgentState) -> AgentState:
    """在当前范围内猜一个数（取中间值）"""
    guess = (state["lower_bound"] + state["upper_bound"]) // 2
    state["guesses"].append(guess)
    state["attempts"] += 1
    return state

def hint_node(state: AgentState) -> AgentState:
    """根据猜测值与目标的关系，给出提示"""
    current_guess = state["guesses"][-1]
    if current_guess == state["target"]:
        state["hint"] = "correct"
    elif current_guess < state["target"]:
        state["hint"] = "higher"
        state["lower_bound"] = current_guess + 1
    else:
        state["hint"] = "lower"
        state["upper_bound"] = current_guess - 1
    return state

def should_continue(state: AgentState) -> str:
    """路由函数：判断是否继续循环"""
    if state["hint"] == "correct" or state["attempts"] >= MAX_ATTEMPTS:
        return "end"
    return "continue"

# 构建图
graph = StateGraph(AgentState)
graph.add_node("guess", guess_node)
graph.add_node("hint", hint_node)

graph.set_entry_point("guess")
graph.add_edge("guess", "hint")

# 条件边：从 hint 节点出发，根据条件决定循环或退出
graph.add_conditional_edges(
    "hint",
    should_continue,
    {
        "continue": "guess",  # 循环回到 guess 节点
        "end":      END       # 退出图
    }
)

app = graph.compile()

result = app.invoke({
    "player_name": "Auto",
    "guesses": [],
    "attempts": 0,
    "lower_bound": 1,
    "upper_bound": 20,
    "target": 13,
    "hint": ""
})
print(f"猜测历史：{result['guesses']}")
print(f"尝试次数：{result['attempts']}")
```

### 关键要点

- **循环**通过条件边指向之前的节点实现
- 必须设置**退出条件**，否则会无限循环
- 路由函数的返回值既可以是普通节点名，也可以是 `END` 常量
- `path_map` 的值可以直接是 `END`（无需加引号的字符串）

---

## 八、第一个 AI 智能体（集成 LLM）

> 目标：将大语言模型（LLM）集成到 LangGraph 图中，构建最简单的 AI 聊天机器人。

**核心思路：** LangGraph 建立在 LangChain 之上，可以直接使用 LangChain 提供的 LLM 封装库。

**图结构：** `START → chatbot_node → END`

### 环境准备

```bash
pip install langgraph langchain langchain-openai python-dotenv
```

创建 `.env` 文件（不要提交到 Git）：

```
OPENAI_API_KEY=your_api_key_here
```

### 完整代码

```python
from typing import TypedDict, List
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

# 加载环境变量（API 密钥）
load_dotenv()

# 第一步：定义状态
# messages 是 HumanMessage 对象的列表，因为 LLM 需要知道消息来自人类
class AgentState(TypedDict):
    messages: List[HumanMessage]

# 第二步：初始化大语言模型
llm = ChatOpenAI(model="gpt-4o")

# 第三步：定义节点函数（集成 LLM）
def chatbot_node(state: AgentState) -> AgentState:
    """简单的聊天机器人节点：将消息传给 LLM 并获取响应"""
    # llm.invoke() 接受消息列表，返回 AIMessage
    response = llm.invoke(state["messages"])
    # 将 LLM 响应追加到消息列表
    state["messages"].append(response)
    return state

# 第四步：构建图
graph = StateGraph(AgentState)
graph.add_node("chatbot", chatbot_node)
graph.set_entry_point("chatbot")
graph.set_finish_point("chatbot")
app = graph.compile()

# 第五步：调用图
result = app.invoke({
    "messages": [HumanMessage(content="你好，请介绍一下 LangGraph")]
})

# 获取 LLM 的最后一条回复
print(result["messages"][-1].content)
```

### 关键要点

- **LangGraph 建立在 LangChain 之上**，可以直接使用 `langchain_core`、`langchain_openai` 等库，这不是"混用"，而是设计如此
- 使用 `HumanMessage` 对象包装用户输入，让 LLM 知道消息来自人类
- `ChatOpenAI(model="gpt-4o")` 初始化 OpenAI 的 GPT-4o 模型
- `llm.invoke(messages)` 返回 `AIMessage` 对象
- API 密钥通过 `.env` 文件管理，通过 `load_dotenv()` 加载，永远不要硬编码
- 如果使用本地模型（如 Ollama），不需要 API 密钥，直接使用 Ollama 的集成库

---

## 九、关键 API 速查表

### 图的构建 API

| API | 说明 | 示例 |
|-----|------|------|
| `StateGraph(State)` | 创建状态图，传入状态模式 | `graph = StateGraph(AgentState)` |
| `graph.add_node(name, fn)` | 添加节点，指定名称和执行函数 | `graph.add_node("greeter", greet_fn)` |
| `graph.set_entry_point(node)` | 设置起点，连接到指定节点 | `graph.set_entry_point("first")` |
| `graph.set_finish_point(node)` | 设置终点，从指定节点结束 | `graph.set_finish_point("last")` |
| `graph.add_edge(from, to)` | 添加有向边，连接两个节点 | `graph.add_edge("node1", "node2")` |
| `graph.add_conditional_edges(src, fn, map)` | 添加条件边 | 见下方详解 |
| `graph.compile()` | 编译图，返回可执行的 `app` | `app = graph.compile()` |

### 条件边详解

```python
graph.add_conditional_edges(
    source_node,      # 条件边的起始节点名称（字符串）
    routing_function, # 路由函数：(state) -> str，返回边的名称
    {                 # 路径映射：边名称 → 目标节点（字符串或 END）
        "edge_a": "node_a",
        "edge_b": "node_b",
        "exit":   END,
    }
)
```

### 图的调用 API

| API | 说明 | 示例 |
|-----|------|------|
| `app.invoke(state)` | 同步调用，传入初始状态，返回最终状态 | `result = app.invoke({"key": "val"})` |
| `app.stream(state)` | 流式调用，逐步返回每个节点的输出 | `for chunk in app.stream(state): ...` |

### 特殊常量

```python
from langgraph.graph import StateGraph, END, START
```

| 常量 | 说明 |
|------|------|
| `START` | 起点节点的常量表示 |
| `END` | 终点节点的常量表示，用于条件边的 path_map |

### 常用消息类型

```python
from langchain_core.messages import (
    HumanMessage,   # 人类消息（用户输入）
    AIMessage,      # AI 消息（LLM 输出）
    SystemMessage,  # 系统消息（指令/上下文）
    ToolMessage,    # 工具调用结果
)
```

### 状态定义模板

```python
from typing import TypedDict, List, Optional, Any

class AgentState(TypedDict):
    # 基础类型
    name: str
    count: int

    # 列表类型
    messages: List[str]

    # 可选类型（可以为 None）
    result: Optional[str]

    # 任意类型
    metadata: Any
```

---

## 十、总结

### 教程前半部分学习路径

```
Python 类型注解基础
    ↓
LangGraph 核心概念（State、Node、Edge、Graph）
    ↓
图一：单节点（Hello World）
    ↓
图二：多输入/多类型状态
    ↓
图三：多节点顺序执行（add_edge）
    ↓
图四：条件路由（add_conditional_edges）
    ↓
图五：循环图（条件边指向前驱节点）
    ↓
第一个 AI 智能体（集成 ChatOpenAI + HumanMessage）
```

### 核心编程模式

1. **定义状态模式**：用 `TypedDict` 子类定义图的共享数据结构
2. **实现节点函数**：纯函数，接受 `AgentState` 返回 `AgentState`
3. **构建图结构**：`StateGraph` + `add_node` + `add_edge` / `add_conditional_edges`
4. **编译并调用**：`compile()` + `invoke()`

### 重要编程习惯

- 每个节点函数都要写 **docstring**，这在构建 AI 智能体时会被 LLM 读取，用于理解节点功能
- 图编译成功不代表逻辑正确，务必测试实际输出
- 在多节点顺序图中，修改状态属性时注意是**追加**还是**替换**，避免丢失前节点的结果
- API 密钥通过 `.env` 文件管理，不要硬编码
