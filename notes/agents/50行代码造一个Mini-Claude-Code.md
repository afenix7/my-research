# 50 行代码造一个 Mini Claude Code：从零拆解 AI 编程智能体核心原理

## 概述

本视频基于 GitHub 开源项目 [run-claude-code](https://github.com/...) 拆解 Claude Code 的底层原理。作者实现了从 V0 到 V4 的五个渐进版本，揭示 AI 编程智能体的核心——**一个 while-true 死循环 + 模型决策 + 工具执行**，没有任何神秘的黑魔法。

核心结论：**Claude Code 的本质是一个让模型反复调用工具直到任务完成的 REPL 循环。代码只提供工具运行环境，模型才是真正的决策者。**

---

## 核心内容

### 1. 基础概念：从聊天机器人到自主代理的本质差异

| 模式 | 流程 | 特征 |
|------|------|------|
| 传统聊天机器人 | 用户问 → 模型答 → 结束 | 一问一答，无自主性 |
| AI 编程智能体 | 用户问 → 模型思考 → 调用工具 → 看结果 → 再思考 → 再调用 → ... → 返回 | 循环自主执行 |

**关键区别**：智能体系统中，模型不只输出文字，而是输出**工具调用指令**，代码层面执行工具后将结果反馈给模型，形成闭环。

---

### 2. 四大支柱：为什么 AI 编程智能体能如此强大

#### 支柱一：工具（赋予行动力）

普通 LLM 只能输出文字。给它工具后，"会说"变成"会做"：

```
read_file  → 探索代码库，理解代码
write_file → 创建新文件
edit_file  → 修改现有代码
bash       → 执行命令、运行测试
```

#### 支柱二：循环（赋予自主性）

```python
while True:
    response = call_llm(messages)
    if response.type == "tool_use":
        result = execute_tool(response.tool, response.input)
        messages.append(tool_result(result))
    else:
        return response.text  # 任务完成，退出循环
```

模型自己决定：调用什么工具、以什么顺序、什么时候停止。

#### 支柱三：上下文（赋予记忆）

每次工具调用的结果都追加到 `messages` 历史中。模型始终能看到：
- 之前读了哪些文件
- 执行了哪些命令
- 得到了什么结果

**消息历史 = 模型的工作记忆**。

#### 支柱四：提示词（赋予方向）

系统提示词告诉模型：
- 你是谁（角色）
- 你在哪个目录工作
- 你有哪些工具（工具描述）
- 你应该怎么做（工作流程规则）

好的提示词 = 好的岗位说明书。

---

### 3. 五大痛点：理解了原理就理解了局限

| 痛点 | 根本原因 | 说明 |
|------|---------|------|
| 上下文遗忘 | 上下文窗口有限 | 聊了 20 轮后，早期内容被截断/压缩，不是 bug |
| AI 幻觉 | 概率匹配而非真理解 | 模型可能编造不存在的 API、文件路径、逻辑 |
| 任务跑偏 | 无明确任务追踪机制 | 让修一个 bug，结果顺手重构了整个模块 |
| token 消耗惊人 | 每轮都要发完整消息历史 | 读一个 500 行文件，这 500 行永远留在上下文里 |
| 执行速度慢 | 每次工具调用 = 一次完整 API 请求 | 30~40 次工具调用 = 30~40 次网络往返 |
| 安全信任问题 | 把键盘交给了概率模型 | 需要路径检查、危险命令拦截、权限控制 |

---

### 4. V0 实现：50 行代码，一个工具，完整 Agent 能力

#### 核心洞察：UNIX 哲学

> 一切皆文件，一切皆可管道。bash 是 UNIX 世界的入口。

当你拥有了 bash，你就拥有了一切：读文件、写文件、执行程序、甚至调用子代理。

#### V0 完整代码逻辑

```python
import anthropic
import subprocess
import sys

client = anthropic.Anthropic()

# 工具定义：只有一个 bash 工具
TOOLS = [
    {
        "name": "bash",
        "description": (
            "执行 shell 命令。常用模式：\n"
            "- 读文件: cat <path>\n"
            "- 写文件: echo '内容' > <path> 或 cat > <path> << 'EOF'\n"
            "- 创建子代理: python main.py '<任务描述>'\n"
            "常用于探索代码库、读写文件、运行命令。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的 shell 命令"
                }
            },
            "required": ["command"]
        }
    }
]

SYSTEM_PROMPT = """你是一位命令行智能体。
工作规则：
- 优先使用工具，少说多做
- 先行动，再简要说明
- 可使用 bash 读写文件、运行命令
- 对于复杂任务，用 python main.py '<任务>' 创建子代理来隔离上下文
"""

def run_agent(prompt: str, history: list = None):
    """Agent 主循环"""
    if history is None:
        history = []

    # 将用户输入加入历史
    history.append({"role": "user", "content": prompt})

    while True:  # 死循环，模型决定何时停止
        # 调用大模型
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=history
        )

        # 将模型响应加入历史
        history.append({"role": "assistant", "content": response.content})

        # 检查是否有工具调用
        tool_uses = [b for b in response.content if b.type == "tool_use"]

        if not tool_uses:
            # 没有工具调用：任务完成，返回最终文本
            final_text = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            )
            return final_text

        # 执行所有工具调用
        tool_results = []
        for tool_use in tool_uses:
            command = tool_use.input["command"]

            # 执行 bash 命令
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            output = result.stdout + result.stderr

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": output or "(命令执行成功，无输出)"
            })

        # 将工具结果追加到历史，进入下一轮循环
        history.append({"role": "user", "content": tool_results})


# 入口
if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 子代理模式：直接执行传入的任务
        result = run_agent(sys.argv[1])
        print(result)
    else:
        # 交互模式：REPL 循环
        while True:
            user_input = input("\n> ")
            if user_input.lower() in ("exit", "quit"):
                break
            result = run_agent(user_input)
            print(f"\n{result}")
```

#### 子代理的递归实现

V0 中子代理的实现方式极为优雅——**通过 bash 调用自身**：

```bash
# 大模型输出的工具调用：
{
  "name": "bash",
  "input": {
    "command": "python main.py '请总结 src/ 目录下所有文件的功能'"
  }
}
```

- 主代理通过 bash 启动新的 Python 进程
- 新进程拥有**独立的上下文**（进程隔离）
- 子代理完成任务后通过 stdout 返回结果
- 主代理继续执行后续步骤

无需任何框架，纯递归即可实现无限嵌套的子代理。

#### V0 牺牲了什么

- 无代理类型区分
- 无工具过滤（bash 能执行任何命令，包括危险操作）
- 无进度显示
- 输出只是纯 stdout 文本

---

### 5. V1 实现：200 行代码，4 个工具，覆盖 90% 场景

#### 工具列表

```python
TOOLS = [
    {
        "name": "bash",
        "description": "执行 shell 命令",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"]
        }
    },
    {
        "name": "read_file",
        "description": "读取文件文本内容，返回带行号的文本",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "limit": {"type": "integer", "description": "最多读取行数，默认 200"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "将内容写入文件（覆盖写入）",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "edit_file",
        "description": "在文件中替换指定内容（精确字符串替换）",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_content": {"type": "string", "description": "要被替换的原始内容"},
                "new_content": {"type": "string", "description": "替换后的新内容"}
            },
            "required": ["path", "old_content", "new_content"]
        }
    }
]
```

#### V1 系统提示词

```
你是一个工作在 {work_dir} 目录下的编程智能体。

工作流程：
1. 简单思考
2. 使用工具执行
3. 汇报结果

规则：
- 优先使用工具，不说废话
- 直接行动，不做解释
- 不要凭空捏造文件路径，不确定时先用 bash ls 确认
- 修改时尽量精简，不要过度设计
- 完成后做简单总结
```

#### V1 工具执行逻辑

```python
def execute_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "bash":
        # 危险命令拦截
        DANGEROUS_PATTERNS = ["rm -rf /", "sudo rm", "> /dev/sda"]
        if any(p in tool_input["command"] for p in DANGEROUS_PATTERNS):
            return "错误：危险命令被拦截"

        result = subprocess.run(
            tool_input["command"], shell=True,
            capture_output=True, text=True, timeout=30
        )
        return result.stdout + result.stderr

    elif tool_name == "read_file":
        path = tool_input["path"]
        limit = tool_input.get("limit", 200)
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # 带行号返回
        return "".join(f"{i+1:4d} | {line}" for i, line in enumerate(lines[:limit]))

    elif tool_name == "write_file":
        with open(tool_input["path"], "w", encoding="utf-8") as f:
            f.write(tool_input["content"])
        return f"文件 {tool_input['path']} 写入成功"

    elif tool_name == "edit_file":
        with open(tool_input["path"], "r", encoding="utf-8") as f:
            content = f.read()

        if tool_input["old_content"] not in content:
            return "错误：未找到要替换的内容"

        new_content = content.replace(
            tool_input["old_content"],
            tool_input["new_content"],
            1  # 只替换第一次出现
        )
        with open(tool_input["path"], "w", encoding="utf-8") as f:
            f.write(new_content)
        return "编辑成功"

    return "未知工具"
```

---

### 6. V2 实现：300 行代码，新增 TODO 工具，解决任务跑偏

#### 问题：单纯的 while 循环无法防止模型迷失

在长任务中（多轮对话 + 复杂需求），模型很容易：
- 忘记最初的目标
- 在子任务中越陷越深
- 没有明确的进度追踪

#### 解决方案：TODO 工具 + 强制更新机制

```python
TODO_TOOL = {
    "name": "todo_write",
    "description": "更新任务代办列表，用于追踪多步骤任务进度",
    "input_schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "任务描述"},
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed"],
                            "description": "任务状态"
                        },
                        "current_action": {
                            "type": "string",
                            "description": "当前正在执行的具体动作"
                        }
                    },
                    "required": ["content", "status"]
                },
                "maxItems": 20  # 最多 20 条，防止过度规划
            }
        },
        "required": ["items"]
    }
}
```

#### TODO 三条核心规则

1. **最多 20 条**：防止模型过度规划
2. **每次只执行一个任务**：强制串行，避免分叉
3. **执行前必须标记 in_progress，完成后标记 completed**：状态可见

#### 强制 TODO 更新机制

```python
# Agent 循环中追踪 TODO 使用情况
todo_idle_rounds = 0
MAX_IDLE_ROUNDS = 10

# ...在工具执行循环中...
if "todo_write" in [t.name for t in tool_uses]:
    todo_idle_rounds = 0
else:
    todo_idle_rounds += 1

# 超过 10 轮未更新 TODO，强制提醒
if todo_idle_rounds >= MAX_IDLE_ROUNDS:
    messages.append({
        "role": "user",
        "content": f"⚠️ 你已经 {MAX_IDLE_ROUNDS} 轮没有更新代办列表了。"
                   "请立即使用 todo_write 工具更新当前任务状态。"
    })
    todo_idle_rounds = 0
```

#### V2 系统提示词（包含 TODO 规则）

```
你是一个工作在 {work_dir} 的编程智能体。

工作循环：
1. 规划（首先用 todo_write 列出所有子任务）
2. 执行（每次只干一件事）
3. 更新代办（完成后标记 completed）
4. 汇报结果

TODO 规则：
- 使用 todo_write 追踪多步骤任务
- 开始前将任务标记为 in_progress
- 完成后标记为 completed
- 优先使用工具，不说废话，先行动再解释
- 完成后总结变更
```

#### TODO 的精妙之处

每次调用 todo_write，工具返回**完整的当前代办列表**。模型在每轮循环中都能看到：
- 还有哪些任务待完成
- 当前在做什么
- 已经完成了什么

这形成了**自我强化的反馈循环**：模型不再靠"记忆"维持方向，而是靠显式的外部状态追踪。

> "规矩立的好，活才能干得好" —— 约束不是限制，而是专注的保障。

---

### 7. V3 实现：450 行代码，子代理机制，分而治之

#### 问题：单一上下文的局限

当主代理探索了 20 个文件后，这 20 个文件的内容会一直占用上下文。后续任务时，模型会：
- 被大量无关信息干扰，失去焦点
- 消耗大量 token

#### 解决方案：task 工具 + 三种代理类型

```python
AGENT_TYPES = {
    "explore": {
        "description": "只读探索代理：搜索和分析代码，不修改文件",
        "allowed_tools": ["bash", "read_file"],
        "system_prompt": "你是一个探索代理，负责搜索和分析代码。不修改任何文件。完成后返回精炼的摘要。"
    },
    "code": {
        "description": "全能编码代理：实现功能和修复 bug",
        "allowed_tools": ["bash", "read_file", "write_file", "edit_file", "todo_write"],
        "system_prompt": "你是一个编码代理，负责实现功能和修复 bug。可以使用所有工具。"
    },
    "plan": {
        "description": "规划代理：设计实现策略，不直接修改代码",
        "allowed_tools": ["read_file"],
        "system_prompt": "你是一个规划代理，负责分析需求和制定实现策略。只读取文件，不修改代码。"
    }
}
```

#### task 工具定义

```python
TASK_TOOL = {
    "name": "task",
    "description": (
        "创建一个子代理来专注执行子任务。\n"
        "子代理运行在隔离的上下文中，看不到主代理的对话历史。\n"
        "使用此工具可保持主代理对话整洁。\n"
        "子代理类型：explore（探索）/ code（编码）/ plan（规划）\n"
        "示例：task(type='explore', prompt='列出 src/ 下所有 Python 文件并总结功能')"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "enum": ["explore", "code", "plan"],
                "description": "子代理类型"
            },
            "prompt": {
                "type": "string",
                "description": "子任务描述"
            }
        },
        "required": ["type", "prompt"]
    }
}
```

#### run_task 实现：子代理创建

```python
def run_task(agent_type: str, prompt: str, work_dir: str) -> str:
    """创建并运行一个子代理，返回其最终文本摘要"""
    config = AGENT_TYPES.get(agent_type)
    if not config:
        return f"错误：未知代理类型 {agent_type}"

    # 子代理有独立的上下文（空的 messages 列表）
    sub_messages = []

    # 子代理的系统提示词
    sub_system = (
        f"{config['system_prompt']}\n\n"
        f"工作目录：{work_dir}\n"
        "完成任务后返回简明扼要的摘要，不要包含中间过程的细节。"
    )

    # 子代理只能使用被允许的工具
    allowed_tool_names = config["allowed_tools"]
    sub_tools = [t for t in ALL_TOOLS if t["name"] in allowed_tool_names]

    # 子代理运行独立的 while True 循环
    sub_messages.append({"role": "user", "content": prompt})

    while True:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            system=sub_system,
            tools=sub_tools,
            messages=sub_messages
        )

        sub_messages.append({"role": "assistant", "content": response.content})

        tool_uses = [b for b in response.content if b.type == "tool_use"]

        if not tool_uses:
            # 子代理完成，返回最终文本摘要给主代理
            return next(
                (b.text for b in response.content if hasattr(b, "text")),
                "子代理完成（无文本输出）"
            )

        # 执行工具（与主代理相同逻辑）
        tool_results = []
        for tool_use in tool_uses:
            result = execute_tool(tool_use.name, tool_use.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result
            })

        sub_messages.append({"role": "user", "content": tool_results})
```

#### V3 的四个关键设计

1. **上下文隔离**：子代理看不到主代理的历史，不会污染主上下文
2. **工具过滤**：每种代理类型只能使用特定工具（最小权限原则）
3. **专业化分工**：explore 只探索、code 只编码、plan 只规划
4. **结果封装**：子代理只返回最终文本摘要，主代理看不到中间细节

#### V3 典型工作流程

```
用户："使用子代理重构预算追踪模块并增加导出功能"
    ↓
主代理调用 task(type="plan", prompt="分析现有预算模块，制定重构方案")
    ↓
plan 子代理（独立上下文）：
  - 读取相关文件
  - 制定方案
  - 返回：摘要文字（"建议拆分为 3 个模块：..."）
    ↓
主代理收到摘要，调用 task(type="code", prompt="按方案实现：...")
    ↓
code 子代理（独立上下文）：
  - 读取、写入、编辑文件
  - 返回：摘要文字（"已完成重构，创建了 budget.py、export.py..."）
    ↓
主代理汇总：任务完成
```

---

### 8. V4 实现：Skills 机制，知识外化

#### 工具 vs 技能的本质区别

| 维度 | 工具（Tools） | 技能（Skills） |
|------|---------------|----------------|
| 定义 | 模型**能做什么** | 模型**知道怎么做** |
| 实现方式 | Python 代码 | Markdown 文件 |
| 修改者 | 工程师 | 任何人 |
| 更新代价 | 需要重新部署 | 实时生效，零成本 |
| 数量 | 有限（每个需维护） | 无限可扩展 |
| 共享性 | 代码级别 | 社区可共享 |

#### 四层知识结构

```
第 1 层：模型预训练知识（通用能力基座）
    → 修改需要重新训练，代价极高

第 2 层：系统提示词（会话级注入）
    → 每次对话时注入，会话级生效

第 3 层：文件系统（CLAUDE.md、项目配置等）
    → 需要持久化，局部项目使用

第 4 层：Skills 技能包（按需加载的知识）
    → 零成本，即时生效，可共享，可版本控制
```

#### Skills 三层结构（按需加载）

```yaml
# skills/pdf-processing.yaml (第 1 层：元数据，始终加载)
name: pdf-processing
description: PDF 文件处理和内容提取
trigger_when:
  - "用户提到 PDF"
  - "需要处理文档"
  - "文件扩展名为 .pdf"
tools_available: ["bash", "read_file"]
skill_file: skills/pdf-processing.md  # 第 2 层：完整操作指南
resources:
  - examples/pdf-sample.py             # 第 3 层：参考资源，按需读取
```

```markdown
<!-- skills/pdf-processing.md (第 2 层：操作指南，匹配时加载) -->
# PDF 处理技能

## 步骤
1. 检查文件是否存在：bash `ls <path>`
2. 使用 pdfplumber 提取文本：...
3. 处理多页文档：...

## 规则
- 优先使用 pdfplumber，次选 PyPDF2
- 文本超过 10 万字时先提取目录
- 图片 PDF 需要 OCR 处理（pytesseract）

## 示例代码
...
```

#### Skills 加载机制

```python
class SkillsLoader:
    def __init__(self, skills_dir: str):
        self.skills = self._load_skill_metadata(skills_dir)

    def get_skills_context(self, user_message: str) -> str:
        """返回始终加载的技能元数据摘要"""
        lines = ["## 可用技能"]
        for skill in self.skills:
            lines.append(f"- **{skill['name']}**: {skill['description']}")
            lines.append(f"  触发条件: {', '.join(skill['trigger_when'])}")
        return "\n".join(lines)

    def load_skill(self, skill_name: str) -> str:
        """按需加载特定技能的完整操作指南"""
        skill = next((s for s in self.skills if s["name"] == skill_name), None)
        if not skill:
            return ""

        # 读取 skill.md 文件（第 2 层）
        with open(skill["skill_file"], "r") as f:
            return f.read()
```

---

### 9. 完整 Agent REPL 循环总结

```
用户输入
    │
    ▼
messages.append(user_message)
    │
    ▼
┌─────────────────────────────────┐
│         while True 死循环        │
│                                 │
│  response = llm(messages)       │
│                                 │
│  if response.has_tool_use:      │
│      result = execute(tool)     │
│      messages.append(result)    │
│      continue  ←────────────────┤
│  else:                          │
│      return response.text  ─────┼──► 任务完成
│                                 │
└─────────────────────────────────┘
```

**核心：模型是决策者，代码是执行环境。** 代码只负责：
1. 调用 LLM API
2. 执行工具
3. 维护消息历史

---

## 关键术语表

| 术语 | 解释 |
|------|------|
| Agent REPL | 读取-执行-打印循环（Read-Eval-Print Loop），AI 智能体的运行模式 |
| tool_use | Anthropic API 中表示模型返回工具调用请求的内容块类型 |
| message history | 消息历史，智能体的"工作记忆"，包含所有对话和工具结果 |
| while True 死循环 | Agent 的核心循环结构，由模型决定何时退出（不返回工具调用时） |
| system prompt | 系统提示词，定义模型角色、工作目录、可用工具和工作规则 |
| sub-agent | 子代理，独立上下文、特定工具权限的隔离执行单元 |
| context isolation | 上下文隔离，子代理看不到主代理历史，防止相互污染 |
| todo_write | 任务追踪工具，防止模型在长任务中迷失方向 |
| skills | 技能包，以 Markdown 存储的外化知识，按需加载到上下文 |
| tool filtering | 工具过滤，不同代理类型只能访问特定工具（最小权限） |
| input_schema | JSON Schema，描述工具接受的参数格式，模型据此生成调用参数 |
| validation loss | ML 中的验证损失，作为模型质量的客观衡量指标 |

---

## 总结

### 五个版本的演进路径

| 版本 | 代码量 | 新增能力 | 解决的问题 |
|------|--------|---------|-----------|
| V0 | ~50 行 | bash（单工具） | 最小可用 Agent：UNIX 哲学，递归子代理 |
| V1 | ~200 行 | 4 工具（bash/read/write/edit） | 覆盖 90% 编程场景 |
| V2 | ~300 行 | TODO 追踪工具 | 任务跑偏、长任务迷失方向 |
| V3 | ~450 行 | task 子代理工具 + 3 种代理类型 | 上下文污染、token 消耗、专业分工 |
| V4 | 更多 | skills 技能包机制 | 知识外化、按需加载、社区共享 |

### 最重要的三个洞察

1. **复杂能力从简单规则中涌现**：50 行代码 + 1 个工具就能实现完整 Agent，没有魔法。

2. **约束反而提升质量**：给模型设置 TODO 规则、工具过滤、代理类型限制，模型反而工作得更好——因为好的约束 = 好的专注。

3. **模型是决策者，代码是环境**：代码只提供工具执行环境，所有"智能"来自模型。模型越强，整个系统越强；工具再多，模型不行也没用。
