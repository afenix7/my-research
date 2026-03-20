# OpenCode 项目技术分析：Agent React、上下文管理、SubAgent 创建

## 项目概览

OpenCode (https://github.com/anomalyco/opencode) 是一个开源 AI 编程助手，类似 Claude Code，支持 75+ AI 提供商，多平台（终端、桌面、IDE 扩展），本地优先隐私设计。它使用 Effect-TS 架构，TypeScript 开发。

---

## 1. Agent React 模式实现

### Agent 类型系统

OpenCode 内置了预定义的 Agent 类型系统，每个 Agent 都有明确的模式分类：

```typescript
mode: z.enum(["subagent", "primary", "all"])
```

- **primary**: 主 Agent，默认交互式使用（build, plan）
- **subagent**: 专门的子 Agent，由主 Agent 调用（general, explore）
- **all**: 可作为主 Agent 也可作为子 Agent

### 内置 Agent 配置

OpenCode 默认提供这些 Agent：

| Agent | Mode | 用途 |
|-------|------|------|
| `build` | primary | 默认 Agent，全权限访问执行开发任务 |
| `plan` | primary | 规划模式，禁止所有编辑工具，只做计划 |
| `general` | subagent | 通用子 Agent，用于复杂搜索和多步骤任务 |
| `explore` | subagent | 专门用于代码库探索的子 Agent |
| `compaction` | primary (hidden) | 上下文压缩专用 Agent |
| `title` | primary (hidden) | 生成会话标题 |
| `summary` | primary (hidden) | 生成会话摘要 |

### Agent 注册和发现

Agent 通过配置驱动方式定义：
1. 静态默认定义在代码中
2. 用户配置文件中的定义覆盖/扩展默认配置
3. 支持自定义 Agent，可指定权限、模型、温度等参数

### 反应循环架构

OpenCode 使用 **ACP (Agent Client Protocol)** 处理会话，通过 `SessionProcessor` 处理每个 Agent 回合：

- 基于 Bus 事件系统，反应式更新
- 每个消息作为包含多个 Part 的结构处理
- Part 可以是 text、tool、file、compaction 等类型
- 处理过程异步可中止，支持用户取消

---

## 2. 上下文管理与上下文压缩

OpenCode 实现了**两级上下文压缩**: **pruning 修剪** + **LLM 摘要压缩**。

### 第一级：修剪 (Pruning)

**策略**: 向后遍历，保留最近 N 个令牌的完整工具调用，标记旧工具调用为压缩状态（实际上丢弃输出）。

参数（可配置）:
```
PRUNE_MINIMUM = 20,000 tokens  // 至少修剪这么多才执行
PRUNE_PROTECT = 40,000 tokens   // 保留最近这么多
```

**受保护的工具**: 某些工具不修剪，比如 `skill`。

**工作流程**:
1. 从最新消息向后遍历
2. 累加工具输出令牌，直到达到 `PRUNE_PROTECT`
3. 超过的旧工具调用标记为 `compacted`，实际上不再发送它们的完整输出到 LLM
4. 只在修剪量超过 `PRUNE_MINIMUM` 时才应用更改

这种方法非常轻量，不需要 LLM 参与，快速回收令牌。

### 第二级：LLM 压缩摘要

当上下文溢出模型限制时，OpenCode 调用内置 `compaction` Agent 生成完整对话摘要。

#### 触发条件

```typescript
const context = model.limit.context;
const reserved = config.compaction?.reserved ?? buffer;
const usable = context - maxOutputTokens;
return count >= usable;  // 触发压缩
```

默认 `COMPACTION_BUFFER = 20,000`，保留足够空间给输出。

#### 压缩过程

```typescript
process():
  1. 找到父用户消息
  2. 如果是溢出情况，向后查找最近未压缩的用户消息作为重放起点
  3. 获取 compaction Agent 配置和模型
  4. 创建新的压缩消息，使用专用 compaction 模式
  5. 使用默认提示模板（可插件替换）调用 LLM 生成摘要
  6. 摘要模板要求结构化输出：Goal, Instructions, Discoveries, Accomplished, Relevant files
  7. 如果是自动压缩且成功，插入继续提示让 Agent 继续工作
```

#### 摘要模板

OpenCode 的压缩提示要求:
```
Provide a detailed summary for continuing the conversation above.
Focus on information that would be helpful for continuing:
- What we did
- What we're doing
- Which files we're working on
- What we're going to do next
- Key decisions and why they were made

Stick to this template:
---
## Goal
[goal(s)]

## Instructions
[important user instructions]

## Discoveries
[things learned that are useful]

## Accomplished
[what's done, what's in progress, what's left]

## Relevant files / directories
[list of files that are relevant]
---
```

#### 插件扩展点

OpenCode 提供插件钩子允许自定义压缩行为:
- `experimental.session.compacting`: 在压缩前修改提示
- `experimental.chat.messages.transform`: 转换消息列表

### 上下文修剪与压缩对比

| 方法 | 时机 | LLM 需要 | 作用 |
|------|------|----------|------|
| Pruning | 定期 | 不需要 | 移除旧工具完成的输出，保留结构 |
| Compaction | 溢出时 | 需要 | 摘要整个历史对话为结构化总结 |

---

## 3. SubAgent 创建

### 声明式 SubAgent 定义

SubAgent 在配置中声明定义，每个 subagent 有：

```typescript
{
  name: string;              // 标识名
  description: string;       // 描述，说明什么时候用
  mode: "subagent";         // 标记为子 Agent
  permission: PermissionRuleset;  // 独立权限配置
  model?: {                  // 可指定专用模型
    providerID;
    modelID;
  };
  prompt?: string;           // 自定义系统提示
  temperature?: number;      // 温度
  topP?: number;
  color?: string;            // UI 颜色
  hidden?: boolean;          // 是否在列表隐藏
}
```

### 内置 SubAgent 示例

**general subagent**:
- 用途: "General-purpose agent for researching complex questions and executing multi-step tasks. Use this agent to execute multiple units of work in parallel."
- 权限: 限制对 todo 读写，可以并行执行独立任务

**explore subagent**:
- 用途: "Fast agent specialized for exploring codebases. Use this when you need to quickly find files by patterns..."
- 权限: 允许 grep, glob, list, bash, webfetch, websearch, codesearch, read 等搜索工具
- 专门用于快速代码探索，不允许修改

### 调用方式

用户可通过 `@agent-name` 在消息中调用 subagent：
- TUI 有专门的 subagent 对话对话框
- 可导航到 subagent 的会话查看输出
- subagent 在独立会话中运行，不干扰主会话上下文

### 动态 Agent 生成

OpenCode 支持**AI 动态生成新 Agent**:

```typescript
Agent.generate({ description, model? }):
  // LLM 生成 JSON 配置
  // 返回: { identifier, whenToUse, systemPrompt }
```

使用 LLM 根据自然语言描述自动创建 Agent 配置，这允许用户自然语言说"帮我创建一个专门用于代码审查的 Agent"，系统自动生成配置。

### 权限模型

每个 SubAgent 有独立的权限规则集：
- 基于模式匹配的 allow/ask/deny
- 可针对目录、工具、文件类型设置不同权限
- 默认配置继承后可覆盖
- 这保证了 subagent 只能做它设计该做的事，提高安全性

---

## 4. Skill 机制

OpenCode 兼容标准 Agent Skills 格式，同时支持远程 Skill 仓库拉取。

### Skill 发现

Skill 从多个位置扫描发现：
1. **全局外部**: `~/.claude/skills/`, `~/.agents/skills/`
2. **项目外部**: 从项目目录向上查找 `.claude/skills/`, `.agents/skills/`
3. **配置目录**: 配置文件中指定的自定义路径 `skills.paths[]`
4. **配置远程 URL**: 配置文件中指定 `skills.urls[]`，自动拉取到本地

发现模式：
- 搜索 `**/SKILL.md` 模式
- 任何包含 `SKILL.md` 的目录被识别为一个 Skill
- 支持 `.gitignore` 过滤

### Skill 格式

与 pi-mono 相同的标准格式：
```markdown
---
name: skill-name
description: When to use this skill
---

# Detailed Instructions
...
```

### 权限检查

Skill 需要通过权限检查才能被对应 Agent 使用：
```typescript
PermissionNext.evaluate("skill", skill.name, agent.permission)
```
只有权限允许的 Skill 才会出现在 Agent 可用列表中。

### 远程 Skill 支持

OpenCode 支持直接从 URL 拉取 Skill：
- 配置 `skills.urls` 允许 Git 仓库
- 自动克隆/拉取到本地缓存
- 支持版本管理

### 格式化输出

两种格式化选项：
- **verbose**: XML 格式包含 name/description/location
- **concise**: 简单列表 `name: description`

---

## 5. Agent 会话隔离

OpenCode 使用**关系数据库持久化 + 父子引用**实现会话隔离和分叉。

### 数据模型

- 每个会话在数据库有独立记录
- `parent_id` 字段引用父会话（如果分叉）
- 每个消息有多块 Part，支持增量更新
- Project → Workspace → Session → Message → Part 层级结构

### 分叉 (Forking)

创建子会话：
```typescript
parentID: SessionID  // 可选，来自现有会话
title: getForkedTitle(parentTitle)  // "Name (fork #1)"
projectID: same as parent  // 同一个项目
```

子会话完全独立：
- 独立消息历史
- 独立权限配置（可继承可覆盖）
- 不影响父会话
- 父会话保持不变，可继续使用

### 隔离特性

| 隔离层面 | 实现方式 |
|----------|----------|
| **消息历史** | 独立数据库记录，完全隔离 |
| **权限配置** | 可独立配置，默认继承 |
| **工作目录** | 可继承父会话，可指定不同目录 |
| **状态** | 独立处理，一个失败不影响其他 |

### UI 导航

- TUI 支持查看会话树
- 可快速切换不同分叉
- 可导航到子会话查看详情
- 支持归档不需要的会话

---

## 架构总结

### 设计特点

1. **配置驱动**: 所有 Agent（包括 subagent）通过配置定义，不需要改代码
2. **两级压缩**: 轻量修剪解决日常令牌增长，完整摘要解决溢出情况
3. **权限隔离**: 每个 subagent 独立权限，安全调用专用能力
4. **基于 Effect-TS**: 整个使用代数效应处理异步，错误处理干净
5. **Skill 共享**: 支持远程 Skill 仓库，易于社区分享

### 与 pi-mono 的对比

| 特性 | pi-mono | OpenCode |
|------|---------|----------|
| Agent 循环 | 双层循环+事件钩子 | ACP 协议+事件总线 |
| 上下文压缩 | 单次 LLM 压缩全历史，保留最近 N 令牌 | 修剪+压缩两级，更渐进 |
| SubAgent | Markdown 文件定义，项目级支持 | 配置定义+动态生成，权限隔离 |
| Skill 机制 | 标准格式，三级发现 | 标准格式+远程拉取 |
| 会话隔离 | 树形文件结构 | 数据库 + parent_id 引用 |
| 摘要格式 | 固定结构 Goal/Progress/Decisions/Next Steps | 类似结构，增加了 Relevant files 部分 |

OpenCode 的架构更适合**多 Agent 协作**，内置了对子 Agent 的一等公民支持，而 pi-mono 的压缩实现更模块化，更容易集成到不同宿主。
