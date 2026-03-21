# Claude Code (Anthropic) 技术分析：Agent React、上下文管理、Skill、会话隔离、Agent Teams

## 项目概览

**Claude Code** 是 Anthropic 官方推出的 CLI 原生 AI 编程 Agent，支持终端/IDE/Slack/Web 多端运行，深度集成 Anthropic Claude 模型系列（Opus 4.6/Sonnet 4 等）。

- **官方**: https://github.com/anthropics/claude-code [^1]
- **官网**: https://code.claude.com/
- **DeepWiki 文档**: https://deepwiki.com/anthropics/claude-code
- **最新功能**: **Agent Teams** 多 Agent 协作，原生支持 MCP (Model Context Protocol)

---

## 1. Agent React 模式实现

### 核心循环架构

Claude Code uses standard **ReAct loop** pattern with hierarchical task decomposition on top. According to CHANGELOG documentation, the main Agent React loop orchestrates task delegation through the `TaskTool` system **[anthropics/claude-code CHANGELOG.md:32-33]**.

```
User Request
    ↓
Team Lead Agent (主 Agent)
    ↓
任务分解 → 分配给多个 Team Member Agent
    ↓
Team Members 并行执行各自任务（各自 ReAct 循环）
    ↓
Team Lead 汇总结果 → 输出给用户
```

### 内置工具循环

Claude Code 核心循环通过 `spawn_sub_agent` 工具（implemented as `TaskTool`)支持内联子 Agent 创建 **[anthropics/claude-code]**:
- 主 Agent 决定何时将子任务委派给子 Agent
- 子 Agent 在独立会话中运行，有独立上下文
- 子 Agent 完成后结果返回主 Agent
- 主 Agent 合并结果继续推进

### 关键特性

- **/loop 命令**: 支持循环执行提示/斜杠命令（类似 cron），可配置间隔（如 `/loop 5m check deploy`）
- **断路器**: 自动压缩连续失败 3 次后停止，避免无限循环
- **中断处理**: Ctrl+C 中断后恢复提示，双击 Ctrl+C 强制退出包括后台 Agent
- **错误处理**: `StopFailure` 钩子在 API 错误（速率限制、认证失败）时触发

---

## 2. 上下文管理与上下文压缩

Context management and automatic compaction implemented in the `ContextManager` within the context window system, documented in CHANGELOG.md:60-63 **[anthropics/claude-code CHANGELOG.md:60-63]**.

### 自动压缩架构

Claude Code 实现了**带断路器的自动上下文压缩**:

- **触发条件**: 当令牌数接近模型上下文窗口限制时自动触发
- **用户手动触发**: `/compact` 命令手动压缩
- **完全清除**: `/clear` 命令完全清除会话上下文
- **断路器**: 连续 3 次压缩失败后自动停止重试，防止无限循环
- **钩子支持**: `PostCompact` 钩子在压缩完成后触发，扩展可自定义后处理

### 压缩优化

- **令牌估算修复**: 修复了 thinking 和 `tool_use` 块重复计数问题，避免过早压缩
- **内存管理**: 修复长会话中进度消息存活导致内存增长
- **大会话性能**: `--resume` 在分叉多的大会话上提速 45%，峰值内存减少 100-150MB

### 分层记忆

Claude Code 使用**三级分层存储**：
1. **全局记忆**: Markdown 文件存储跨会话共享知识
2. **项目记忆**: 项目级 `.claude/` 目录存储项目特定上下文
3. **会话记忆**: 当前会话完整消息历史

**参考来源：**
- DeepWiki Claude Code context management: https://deepwiki.com/anthropics/claude-code [^2]

---

## 3. SubAgent 创建

### 原生 `spawn_sub_agent` 工具

Claude Code 核心工具集内置 `spawn_sub_agent` tool implemented via `TaskTool` which spawns isolated subagents for parallel tasks and background work **[anthropics/claude-code CHANGELOG.md:32-33]**:

```typescript
// 支持参数
{
  task: string;          // 子任务描述
  model?: string;       // 可选：覆盖模型（比如 "claude-opus-4-5"）
  workingDir?: string;  // 可选：工作目录
}
```

### Agent Teams 多 Agent 架构

**Agent Teams** 是 Claude Code 2026 年 2 月推出的实验性功能，支持真正的多 Agent 并行协作 through multi-agent orchestration via subagent spawning, documented in CHANGELOG.md:202-207 **[anthropics/claude-code CHANGELOG.md:202-207]** describes parallel reviewers with different models and a final validation step.

### 角色分工

| 角色 | 职责 |
|------|------|
| **Team Lead** | 任务分解 → 分配子任务 → 结果汇总 → 最终交付 |
| **Team Member** | 执行分配的具体任务 → 独立 ReAct 循环 → 返回结果 |

### 执行模型

1. **Team Lead** 接收用户请求
2. **分解任务**: 将大任务拆分为多个可并行子任务
3. **分配**: 每个子任务 spawn 一个独立 Team Member Agent
4. **并行执行**: 多个 Member 同时运行，各自有独立上下文
5. **邮箱系统**: Agent 之间有内置"邮箱"通信机制
6. **结果汇总**: 所有 Member 完成后，Lead 汇总结果给用户

### 架构特点

- **完全隔离**: 每个 Team Member Agent 有独立会话、独立上下文
- **并行执行**: 多个子任务同时进行，节省时间
- **适合场景**: 大型重构、多模块开发、代码审查、多人协作模拟
- **代价**: 令牌消耗更高，因为多个 Agent 同时运行

### 子 Agent 改进

- **模型覆盖**: 支持在 Agent 调用时覆盖模型参数
- **后台执行**: 杀后台 Agent 保留部分结果在上下文
- **模型继承**: Team Agent 继承 Team Lead 的模型设置
- **清理**: 修复子 Agent spawn 的 bash 进程退出时没有清理问题
- **通知**: 修复后台 Agent 完成通知丢失输出路径问题，方便父 Agent 恢复结果

**参考来源：**
- DeepWiki Agent Teams documentation: https://deepwiki.com/anthropics/claude-code [^2]

---

## 4. Skill 机制

Skill 系统 loads from `.claude/skills/*.md` with plugin discovery from user/project/seed directories **[anthropics/claude-code]**.

### Skill 定义格式

Skill 是可共享的预定义 Agent/指令包，使用 Markdown + YAML frontmatter 定义：

```markdown
---
name: skill-name
description: When to use this skill
model: provider/model-id  # 可选，指定模型
effort: low|medium|high    # 可选，指定努力程度
maxTurns: number           # 可选，最大回合数
disallowedTools: [tool1, tool2]  # 可选，禁止使用的工具
---

# Skill Instructions
这里是详细的技能指令...
```

### Skill 发现

Skill 从多个位置发现：
- **用户全局**: `~/.claude/skills/`
- **项目本地**: `./.claude/skills/`
- **插件打包**: 随 Claude Code 插件分发
- **worktree**: `--worktree` 标志正确加载 worktree 目录中的 skills

### 验证

`claude plugin validate` 命令验证 skill 配置：
- 检查 YAML frontmatter 语法正确
- 检查 schema 符合要求
- 检查 hooks 配置
- 提前发现格式错误

### MCP (Model Context Protocol) 集成

Claude Code 深度原生集成 MCP 作为技能/工具扩展机制：

- **标准协议**: MCP 是 Anthropic 推出的开放工具连接标准
- ** elicitation 支持**: MCP 服务器可以在任务中间请求结构化输入（弹出对话框）
- **权限中继**: 通道服务器可以转发权限批准提示到手机，支持远程审批
- **OAuth 改进**: 支持 CIMD 动态客户端注册，修复刷新令牌过期问题
- **去重**: 自动跳过重复配置的 MCP 服务器

---

## 5. Agent 会话隔离

### 分支/分叉隔离

Claude Code 支持会话分叉（fork/branch）：
- `/branch` 命令从当前会话创建分叉（原 `/fork` 重命名）
- 分叉会话有**独立文件存储**，不影响原会话
- 修复了分叉会话共享计划文件导致互相覆盖的 bug
- 每个分叉有独立工作树，可以实验不同路径不影响主会话

### 工作树隔离

`--worktree` flag loads skills and hooks from the specific worktree directory, documented in CHANGELOG.md:42-43 **[anthropics/claude-code CHANGELOG.md:42-43]**. Claude Code integrates git worktree for working directory isolation:

- `claude --worktree <path>` 在独立 worktree 打开会话
- `worktree.sparsePaths` 配置支持稀疏检出，大单体仓库只检出需要的目录
- `EnterWorktree` / `ExitWorktree` 工具进入/退出隔离工作目录
- 修复了 Task 工具恢复时 cwd 不正确问题
- 修复后台任务通知丢失 worktree 路径信息

### 并发会话隔离

- 修复多个并发 Claude Code 会话 OAuth 认证互相干扰
- 修复同一个项目目录运行多个会话时 Bash 输出丢失问题
- 修复并发插件安装跨实例损坏问题
- 每个会话完全隔离，独立状态

### 稀疏检出

```json
// settings.json
{
  "worktree": {
    "sparsePaths": ["src/", "packages/", "!node_modules/"]
  }
}
```

在大单体仓库只检出需要的路径，节省空间和时间。

### 清理机制

- 改进过期 worktree 清理
- 并行运行中断后自动清理留下的过期 worktree
- 避免磁盘空间泄漏

**参考来源：**
- DeepWiki Worktree management: https://deepwiki.com/anthropics/claude-code [^2]

---

## 6. Agent Teams 专属架构

### 整体协作流程

```
User asks for complex task
    ↓
Team Lead Agent (in current session)
    ↓
1. Decompose into N subtasks
2. For each subtask:
   ↓
   spawn Team Member Agent (new isolated session)
   ↓
   Member runs independent ReAct loop
   ↓
   returns result to Lead via "mailbox"
3. Wait for all members complete
    ↓
Team Lead aggregates all results
    ↓
Presents final result to user
```

Multi-agent orchestration documented in CHANGELOG.md:202-207 describes parallel reviewers with different models and a final validation step **[anthropics/claude-code CHANGELOG.md:202-207]**.

### 隔离保证

| 隔离层面 | 实现方式 |
|----------|----------|
| **上下文** | 每个 Member 独立会话，独立消息历史 |
| **工作目录** | 可继承可独立指定 |
| **模型配置** | 继承 Lead 的模型，可覆盖 |
| **生命周期** | 独立进程/会话，失败不影响其他 |

### 通信机制

- **内置邮箱系统**: Agent 之间可以互相发送消息
- **结果汇总**: Lead 自动收集所有 Member 结果
- **用户可见**: 用户可以在 Leader 会话看到整体进度，也可以查看每个 Member 独立会话

### 使用场景

| 场景 | 为什么 Agent Teams 更好 |
|------|--------------------------|
| **大型重构** | 每个文件/模块可以一个 Agent 并行修改 |
| **代码审查** | 多个 Agent 分别审查不同部分 |
| **多模块新项目** | 每个模块并行开发 |
| **复杂测试调试** | 一个 Agent 读代码，一个写测试，一个调试 |
| **调研报告** | 每个 Agent 调研一个竞品，然后汇总 |

---

## 架构总结

### 设计特点

1. **分层 Agent**: 单 Agent 交互式 + 多 Agent Teams 并行协作，按需选择
2. **渐进压缩**: 自动压缩+断路器，用户可手动触发
3. **MCP 原生**: 深度集成 Model Context Protocol 作为扩展机制
4. **git 集成**: 利用 git worktree 实现真正的工作目录隔离
5. **分支隔离**: 会话分叉支持安全实验，不影响主会话

### 与其他项目对比

| 特性 | pi-mono | OpenCode | Claude Code | Codex CLI |
|------|---------|----------|------------|----------|
| **Agent React** | 双层事件循环 | ACP 事件总线 | ReAct + 分层 Team 协作 | 简约 ReAct |
| **上下文压缩** | LLM 结构化摘要 | 修剪 + LLM 压缩 | 自动压缩 + 断路器 | 滑动窗口 + 摘要 |
| **SubAgent** | Markdown 发现 | 配置定义 + 动态生成 | 内置 `spawn_sub_agent` + Agent Teams | 进程隔离 spawn |
| **Skill 机制** | `SKILL.md` 三级发现 | `SKILL.md` + 远程 Git | `SKILL.md` + MCP 原生 | MCP 服务器配置 |
| **会话隔离** | 树形文件结构 | SQL + parent_id | git worktree + 分支分叉 | 文件级隔离 |
| **Agent Teams** | ❌ 不支持 | ❌ 不支持 | ✅ 原生支持并行协作 | ❌ 不支持 |

Claude Code 作为官方产品，在**多 Agent 并行协作**（Agent Teams）和**标准化扩展**（MCP）方面处于领先，会话隔离深度集成 git worktree 这也是开源项目 pi-condo/OpenCode 没有的特性。

## 参考资料

[^1]: GitHub Repository - https://github.com/anthropics/claude-code
[^2]: DeepWiki Documentation - https://deepwiki.com/anthropics/claude-code
[^3]: Claude Code Official Website - https://code.claude.com/
