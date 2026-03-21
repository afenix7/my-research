# pi-mono 项目技术分析：Agent React、上下文管理、SubAgent 创建

## 项目概览

pi-mono (https://github.com/badlogic/pi-mono) 是一个 AI Agent 工具集，包含编码 Agent CLI、统一 LLM API、TUI & Web UI 库、Slack 机器人、vLLM pods 等组件。它是一个成熟的 TypeScript 项目，采用模块化 monorepo 架构。

**官方资源：**
- GitHub 仓库: https://github.com/badlogic/pi-mono [^1]
- DeepWiki 文档: https://deepwiki.com/badlogic/pi-mono
- Agent Skills 标准: https://agentskills.io/

---

## 1. Agent React 模式实现

### 核心架构

pi-mono 实现了一个基于事件驱动的**循环式 Agent 反应模式**，核心代码位于 `packages/agent/src/`:

- **Agent 类** (`packages/agent/src/agent.ts`): 维护 Agent 状态，管理消息队列，提供事件订阅机制 **[badlogic/pi-mono → packages/agent/src/agent.ts]**
- **Agent Loop** (`packages/agent/src/agent-loop.ts`): 实现主反应循环，处理工具调用和流式响应 **[badlogic/pi-mono → packages/agent/src/agent-loop.ts]**

### 反应循环工作流程

```
outer while (true):
  inner while (hasMoreToolCalls || pendingMessages):
    process pending steering messages
    stream assistant response from LLM
    extract tool calls
    execute tool calls (parallel or sequential)
    add tool results to context
  check for follow-up messages
  if none, exit
```

**关键特点：**
- **双重队列系统**: `steeringQueue` 用于运行时插入消息，`followUpQueue` 用于 Agent 完成后添加消息
- **可配置消息传递**: `steeringMode` 和 `followUpMode` 支持 "all" 一次性发送或 "one-at-a-time" 逐次发送
- **事件订阅模式**: Agent 发出 `message_start`, `message_update`, `tool_execution_start`, `tool_execution_end`, `turn_end`, `agent_end` 等事件，允许外部 UI/框架响应
- **并行工具执行**: 默认并行执行多个工具调用，可配置为顺序执行

### 上下文转换钩子

在每次 LLM 调用前，pi-mono 提供两个转换点：

```typescript
// From: packages/agent/src/types.ts
// 1. transformContext: 对 AgentMessage[] 进行转换（压缩、修剪等）
transformContext?: (messages: AgentMessage[], signal?) => Promise<AgentMessage[]>

// 2. convertToLlm: 转换为 LLM 兼容格式
convertToLlm?: (messages: AgentMessage[]) => Message[] | Promise<Message[]>
```

这种设计使得上下文压缩、提示工程等功能可以作为插件插入，不影响核心循环。

**参考来源：**
- DeepWiki: https://deepwiki.com/badlogic/pi-mono (Agent architecture overview) [^2]

---

## 2. 上下文管理与上下文压缩

### 上下文压缩架构

pi-mono 在 `packages/coding-agent/src/core/sessions/` 实现了**结构化 LLM 驱动的上下文压缩**，这是目前见到的最完整的开源实现之一。压缩的编排和持久化主要在 SessionManager 中处理。

**源码位置：**
- 自动压缩触发: `packages/coding-agent/src/modes/interactive/agent-session.ts` **[badlogic/pi-mono]**
- 压缩持久化: `packages/coding-agent/src/core/sessions/session-manager.ts` → `appendCompaction()` 方法 **[badlogic/pi-mono → packages/coding-agent/src/core/sessions/session-manager.ts]**

### 压缩触发条件

压缩通过令牌估算触发：
- 计算当前上下文总令牌数
- 当 `contextTokens > contextWindow - reserveTokens` 时触发压缩
- 默认配置: `reserveTokens = 16384`, `keepRecentTokens = 20000`

### 剪切点查找算法

1. **识别有效剪切点**: 只能在 `user`, `assistant`, `custom`, `bashExecution` 消息处剪切，不能在 `toolResult` 处剪切（必须保持工具调用-结果对应）
2. **反向累积**: 从最新消息向后累积令牌，直到达到 `keepRecentTokens`
3. **确定切分**: 如果剪切发生在回合中间，记录该回合开始的用户消息位置

### 压缩流程

```
prepareCompaction():
  1. 找到上一次压缩的位置边界
  2. 计算当前令牌总数
  3. 寻找剪切点
  4. 分离需要摘要的历史消息和保留的最近消息
  5. 如果分段剪切，分离当前回合前缀
  6. 提取文件操作记录

compact():
  1. 使用 LLM 对历史消息生成结构化摘要
  2. 如果是分段剪切，对当前回合前缀也生成摘要
  3. 合并摘要并追加文件操作列表
  4. 返回 CompactionResult 给 SessionManager 保存

结果：旧消息被单个压缩摘要替换，最近消息保持不变
```

### 摘要格式

pi-mono 使用固定的结构化摘要模板：

```
## Goal
[用户要完成什么目标]

## Constraints & Preferences
[用户提到的约束和偏好]

## Progress
### Done
- [x] 已完成任务

### In Progress
- [ ] 当前工作

### Blocked
- [阻塞问题]

## Key Decisions
- **[决策]**: [简要理由]

## Next Steps
1. [有序下一步列表]

## Critical Context
[关键上下文信息]
```

同时支持迭代更新：如果已有之前的压缩摘要，使用更新提示将新信息合并进去，保留已有信息。

### 文件操作跟踪

压缩过程会显式跟踪文件操作：
- 从消息中提取读取/修改的文件列表
- 在压缩摘要末尾追加结构化的文件列表
- 确保 Agent 仍然知道哪些文件被修改过

### 令牌估算

pi-mono 使用启发式估算 (`chars / 4`)，这在实践中足够准确，避免了对完整分词器的依赖：

```typescript
// Estimation heuristic
- user/assistant: 字符数 / 4
- images: 固定估算 1200 tokens
- tool results: 字符数 / 4
```

**参考来源：**
- DeepWiki Session Management: https://deepwiki.com/badlogic/pi-mono/packages/coding-agent/src/core/sessions [^2]

---

## 3. SubAgent 创建

pi-mono 通过**可扩展的 Agent 发现机制**支持 SubAgent，示例位于 `packages/coding-agent/examples/extensions/subagent/` **[badlogic/pi-mono]**.

### Agent 定义格式

SubAgent 通过 Markdown 文件定义，带有 YAML frontmatter：

```markdown
---
name: my-subagent
description: Does something specific
tools: tool1, tool2
model: provider/model-id
---
# System Prompt
这里是 subagent 的系统提示词
```

### Agent 发现

Agents 从两个位置发现：
1. **User agents**: `~/.pi/agents/`
2. **Project agents**: `./.pi/agents/` (从当前目录向上查找最近的)

加载过程：
- 扫描目录中的 `.md` 文件
- 解析 frontmatter
- 验证必填字段（name, description）
- 缓存为 `AgentConfig` 结构

### 调用方式

在 coding-agent 中，可以通过 @mention 调用 subagents：
- 用户消息中使用 `@agent-name` 触发
- 主 Agent 可以将任务委托给专门的 subagent
- subagent 有自己的权限配置和工具白名单

### 配置选项

每个 subagent 可以独立配置：
- `name`: 标识符，用于 @ 调用
- `description`: 用途描述，帮助主 Agent 判断何时使用
- `tools`: 允许使用的工具列表
- `model`: 指定使用的模型（可不同于主 Agent）
- `systemPrompt`: 自定义系统提示
- `source`: 用户级还是项目级

**源码位置：** Example extension: `packages/coding-agent/examples/extensions/subagent/` **[badlogic/pi-mono]**

---

## 4. Skill 机制

pi-mono 实现了**标准化的 Agent Skills 系统** (https://agentskills.io/)，Skill 是一种可共享、可组合的特殊化指令包。Skills 存储在 `packages/coding-agent/src/skills/` 目录 **[badlogic/pi-mono]**.

### Skill 定义格式

Skill 通过 `SKILL.md` 文件定义，带有 YAML frontmatter：

```markdown
---
name: my-skill-name
description: What this skill does, when to use it
disable-model-invocation: false  # 可选，隐藏不自动推荐
---

# Skill Content
Here are the detailed instructions for this skill...
```

### 命名规范验证

pi-mono 严格验证 skill 名称：
- 必须等于父目录名
- 只能包含小写字母 `a-z`、数字 `0-9`、连字符 `-`
- 不能以连字符开头或结尾
- 不能有连续两个连字符
- 最大长度 64 字符

### Skill 发现

Skill 从三个层级发现：
1. **用户级**: `~/.pi/skills/`
2. **项目级**: `./.pi/skills/`
3. **显式路径**: 配置文件中指定的额外路径

发现规则：
- 如果目录包含 `SKILL.md`，视为 skill 根，不再递归
- 否则递归搜索子目录
- 支持 `.gitignore` 风格忽略规则
- 符号链接被正确跟随和去重

### 格式化为系统提示

Skill 使用 XML 格式插入系统提示：

```xml
<available_skills>
  <skill>
    <name>skill-name</name>
    <description>When to use this skill</description>
    <location>/path/to/SKILL.md</location>
  </skill>
</available_skills>
```

Agent 被指示：当任务匹配 skill 描述时，使用 read 工具加载 skill 文件获取详细指令。

### 特点

- **共享性**: Skills 可以在项目间共享，提交到代码仓库
- **可发现**: 自动从目录结构发现
- **懒加载**: 只有名称/描述放入提示，内容需要时才读取
- **验证**: 严格格式验证帮助提前发现问题

**参考来源：**
- Agent Skills 标准: https://agentskills.io/ [^3]
- DeepWiki Skills documentation: https://deepwiki.com/badlogic/pi-mono/packages/coding-agent/src/skills [^2]

---

## 5. Agent 会话隔离

pi-mono 使用**树形会话结构**支持会话分支和隔离，实现位于 `packages/coding-agent/src/core/sessions/` **[badlogic/pi-mono]**.

**源码位置：**
- 类型定义: `packages/coding-agent/src/core/sessions/types.ts` **[badlogic/pi-mono → packages/coding-agent/src/core/sessions/types.ts]**
- 管理实现: `packages/coding-agent/src/core/sessions/session-manager.ts` **[badlogic/pi-mono → packages/coding-agent/src/core/sessions/session-manager.ts]**

### 持久化格式

每个会话是一个包含行分隔 JSON 条目的文件：
```
- Session header (version 3)
- Entry 1: SessionEntry (message/compaction/branch_summary/custom/etc)
- Entry 2: ...
- ...
```

每个条目都有：
- `id`: UUID
- `parentId`: 父条目 ID
- `type`: 条目类型
- `timestamp`: 时间戳

### 会话分叉 (Forking)

pi-mono 支持从任意点分叉会话，核心实现：
```typescript
// From: packages/coding-agent/src/core/sessions/session-manager.ts
// Each entry has id and parentId, leafId tracks active endpoint
branch(entryId) {
  this.leafId = entryId;
}
buildSessionContext() {
  walk from leafId to root
}
```

- 新会话记录 `parentSession` 引用
- 新会话是完全独立文件，不影响父会话
- 支持从任意条目创建分支

### 树导航

SessionManager 提供 `getTree()` 方法构建完整的会话树：
```typescript
// From: packages/coding-agent/src/core/sessions/types.ts
export interface SessionTreeNode {
  entry: SessionEntry;
  children: SessionTreeNode[];
  label?: string;
}
```

这允许用户探索不同路径，在 UI 中显示会话历史树。

### 分支摘要

当从分支合并回主会话时，可以生成 `branch_summary` 条目：
- 对分支工作进行 LLM 总结
- 插入到主会话上下文
- 保留完整分支结构但不保留所有消息

### 隔离级别

- **完全隔离**: 分叉会话有独立文件，独立消息历史
- **共享上下文**: 可以从父会话继承上下文起点
- **结构化合并**: 通过摘要方式合并回主会话
- **标签支持**: 用户可以给条目加标签/bookmark

**参考来源：**
- DeepWiki Session management: https://deepwiki.com/badlogic/pi-mono/packages/coding-agent/src/core/sessions [^2]

---

## 架构总结

| 特性 | 实现方式 | 源码位置 | 优势 |
|------|----------|----------|------|
| Agent React | 事件驱动的双层循环 | `packages/agent/src/` | 灵活，可观察，支持运行时干预 |
| 上下文压缩 | LLM 生成结构化摘要+保留最近消息 | `packages/coding-agent/src/core/sessions/` | 保持上下文连贯性，有效控制令牌数 |
| SubAgent | Markdown 定义+动态发现 | `examples/extensions/subagent/` | 轻量级，易于用户自定义，项目级配置 |
| Skill 机制 | 标准化 SKILL.md 格式，三级发现 | `packages/coding-agent/src/skills/` | 可共享，可组合，懒加载 |
| 会话隔离 | 树形条目结构，支持分叉 | `packages/coding-agent/src/core/sessions/` | 完全隔离，可实验不同路径 |

pi-mono 的设计特点是**模块化**，核心 agent 循环不关心压缩细节，通过 `transformContext` 钩子接入，压缩算法本身是纯函数，方便测试和扩展。

## 参考资料

[^1]: GitHub Repository - https://github.com/badlogic/pi-mono
[^2]: DeepWiki Documentation - https://deepwiki.com/badlogic/pi-mono
[^3]: Agent Skills Standard - https://agentskills.io/
