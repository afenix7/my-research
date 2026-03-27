# Superpowers — CodeMap

**GitHub**: https://github.com/obra/superpowers  
**Current Version**: v5.0.6 (2026-03-24)  
**License**: MIT  
**Author**: obra  
**Multi-Platform**: Claude Code, Codex, Cursor, OpenCode, Gemini CLI  

---

## 1. 项目概述与定位

**Superpowers** 是为 AI 编程 agent 设计的**结构化开发技能框架**，核心理念是：软件开发需要先**充分讨论和设计**，再**规划**，最后**执行**——这一流程应当由 AI agent 自主驱动，而非每次靠人工提醒。

它不是项目管理工具（如 GSD），而是**一套开发方法论的 Skill 集合**，包含：
- 头脑风暴（Spec-first 设计流程）
- 规划写作（结构化 Plan 文档）
- 子代理驱动开发（Controller-Worker 模式）
- 系统性调试
- TDD 工作流

**v5.0.6（本月 2026-03-24）重大更新**：用 **Inline Self-Review 替代 Subagent Review Loop**，将 plan/spec 评审时间从 ~25 分钟降至 ~30 秒，质量评分无显著差异。

---

## 2. 核心架构

### 2.1 架构哲学

Superpowers 的设计哲学浓缩在一条规则中：
> **No implementation until design is approved**

在 brainstorming skill 中，有一个严格的 `<HARD-GATE>`：在设计被用户批准之前，**绝对不能使用任何实现类 skill、代码或脚手架**。

### 2.2 整体结构

```
superpowers/
├── .claude-plugin/          # Claude Code 官方 marketplace 插件格式
├── .codex/                  # Codex 兼容格式
├── .cursor-plugin/          # Cursor 插件格式
├── .opencode/               # OpenCode 插件格式
├── skills/                  # 核心 Skill 目录（agentskills.io 标准）
│   ├── brainstorming/        # 头脑风暴技能
│   │   ├── SKILL.md
│   │   ├── spec-document-reviewer-prompt.md
│   │   ├── visual-companion.md
│   │   ├── brain-storm-server/  # 协作头脑风暴 Web 服务器
│   │   └── scripts/              # 服务器脚本
│   ├── writing-plans/        # 规划写作技能
│   │   ├── SKILL.md
│   │   ├── plan-document-reviewer-prompt.md
│   │   └── ...
│   ├── subagent-driven-development/  # 子代理驱动开发
│   │   ├── SKILL.md
│   │   ├── controller.md
│   │   ├── implementer.md
│   │   └── code-quality-reviewer.md
│   ├── executing-plans/      # 规划执行技能（备选）
│   ├── systematic-debugging/  # 系统性调试
│   ├── test-driven-development/
│   ├── requesting-code-review/
│   ├── receiving-code-review/
│   ├── finishing-a-development-branch/
│   ├── dispatching-parallel-agents/
│   ├── brainstorming/
│   ├── using-git-worktrees/
│   ├── using-superpowers/    # 顶层入口 Skill
│   └── ...
├── commands/                 # 顶层命令（已废弃，引向 skills）
│   ├── brainstorm.md
│   ├── write-plan.md
│   └── execute-plan.md
├── agents/                   # 可复用的 agent 定义
├── hooks/                    # Session hooks
│   ├── hooks.json            # Claude Code hooks 配置
│   ├── hooks-cursor.json     # Cursor hooks
│   ├── session-start         # 启动注入脚本
│   └── run-hook.cmd          # Windows polyglot wrapper
├── gemini-extension.json     # Gemini CLI 扩展
├── GEMINI.md                 # Gemini 使用说明
├── CHANGELOG.md
└── RELEASE-NOTES.md          # 详细发布说明
```

### 2.3 技能流水线

```
用户发起请求
    ↓
[using-superpowers] — 技能路由（skill routing）
    ↓
[brainstorming] — Spec-first 设计流程
    ↓ (用户批准设计)
[writing-plans] — 结构化规划（Inline Self-Review，替代旧版 subagent review loop）
    ↓
[subagent-driven-development] — Controller-Worker 模式执行
    ↓ (可选)
[executing-plans] — 直接执行（无 subagent 能力的 runtime 备选）
```

---

## 3. 主要模块分析

### 3.1 brainstorming 技能

**核心流程**（v5.0.6 最新版）：

```
1. 项目背景理解
2. 需求探索（强制 checklist）
3. 利益相关者分析
4. Spec 撰写
5. 【Inline Self-Review】（v5.0.6 新增，替代 25min subagent review loop）
   - placeholder scan
   - internal consistency
   - scope check
   - ambiguity check
6. 用户设计评审（必须通过）
7. 交接 writing-plans
```

**关键文件**：
- `skills/brainstorming/SKILL.md` — 主 Skill 文件
- `skills/brainstorming/spec-document-reviewer-prompt.md` — Spec 评审 prompt
- `skills/brainstorming/visual-companion.md` — 视觉协作伙伴指南

**Visual Companion（v5.0.0 新增）**：
- 一个可选的浏览器协作界面
- 当问题涉及视觉内容（mockups、diagrams、comparisons）时提供
- Brainstorm Server 基于 WebSocket，零外部依赖（内置 http + crypto）
- 支持 Claude Code / Codex / Gemini CLI 等多 runtime

### 3.2 writing-plans 技能

**核心流程**（v5.0.6 新版）：

```
1. 接收 brainstorming 的 spec
2. 【Inline Self-Review】替代 subagent review loop
   - spec coverage check
   - placeholder scan
   - type consistency
3. Plan 撰写
4. 【No Placeholders 验证】— 明确列出 4 类 plan 失败情况
5. 交接 subagent-driven-development
```

**文档结构**：
```markdown
# Plan: [Feature Name]

## Context
## Goals  
## Requirements (from spec)
## Approach
## File Structure (新增 v5.0.0)
## Tasks
- [ ] **Step 1:** ...
- [ ] **Step 2:** ...
## Verification
## Risks
```

**子代理状态协议**（v5.0.0 新增）：
```
Subagent 返回以下状态之一：
- DONE — 任务完成
- DONE_WITH_CONCERNS — 完成但有顾虑
- BLOCKED — 被阻塞
- NEEDS_CONTEXT — 需要更多上下文
```

### 3.3 subagent-driven-development 技能

Controller-Worker 模式：

```
Controller (主 agent)
  ├→ Worker 1 (implementer) — 任务执行
  ├→ Worker 2 (implementer) — 并行任务
  └→ Code Quality Reviewer — 质量检查
  
Worker 状态: DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT
Controller 处理:
  - 重新调度 + 更多上下文
  - 升级模型能力
  - 分解任务
  - 升级给人类
```

**设计原则**：
- **Context Isolation**：每个子代理只收到它需要的上下文
- **File Structure First**：在定义任务之前先规划文件结构和职责分配
- **Architecture Awareness**：每个 agent 都内嵌架构意识

### 3.4 systematic-debugging 技能

```
1. 问题复现（收集原始错误信息）
2. 假设形成（4类调试技术）
3. 假设验证（一次只改一个变量）
4. 根本原因确认
5. 修复验证
```

### 3.5 Hook 系统

**SessionStart Hook**：`hooks/session-start` 在每次 Claude Code 会话启动时注入 Superpowers 的指令上下文。

```bash
# hooks.json
{
  "hooks": [{
    "name": "session-start",
    "command": "hooks/session-start",
    "when": "sessionStart"
  }]
}
```

- 支持 Claude Code、Codex、Cursor、OpenCode、Gemini CLI 多平台
- `async: false`（v4.3.0 修复，之前是 async 导致第一次消息缺少上下文）
- 兼容 Windows polyglot wrapper（`run-hook.cmd`）

---

## 4. API / 接口设计

Superpowers **不通过 HTTP API 暴露**，而是作为 Claude Code Skill 通过文件系统的 Skill 协议集成。

### 4.1 Skill 协议（agentskills.io 标准）

每个 skill 是一个包含 `SKILL.md` 的目录：

```yaml
---
name: brainstorming
description: Structured brainstorming with spec-first approach
version: 1.0.0
triggers:
  - brainstorm
  - design discussion
  - feature planning
---
```

### 4.2 顶层 Skill 路由（`using-superpowers`）

```markdown
# Skill Routing Rules

用户意图 → 匹配 Skill:
- 想要讨论/探索 → brainstorming
- 想要写实现计划 → writing-plans
- 想要 AI 执行计划 → subagent-driven-development
- 遇到 bug → systematic-debugging
```

**指令优先级**（v5.0.0 明确）：
1. 用户显式指令（CLAUDE.md / AGENTS.md / 直接请求）— **最高优先**
2. Superpowers Skills — 覆盖默认系统行为
3. 默认系统 prompt — **最低优先**

### 4.3 命令格式（已废弃 slash 命令）

v5.0.0 开始 `/brainstorm`、`/write-plan`、`/execute-plan` 显示废弃提示，指向对应 skills。

---

## 5. 与 Claude Code 的集成机制

### 5.1 安装方式

**Claude Code 官方 marketplace**（推荐）：
```
/plugin-add https://github.com/obra/superpowers
```

**手动安装**：
```bash
git clone https://github.com/obra/superpowers.git ~/.claude/skills/superpowers
```

### 5.2 多平台适配层

Superpowers 维护了 4 套平台适配代码（`.claude-plugin/`、`.codex/`、`.cursor-plugin/`、`.opencode/`），同时还有 `gemini-extension.json` 支持 Gemini CLI。

工具映射表：
| Claude Code | Codex | OpenCode | Gemini |
|-------------|-------|---------|--------|
| Read | read_file | read_file | read_file |
| Write | write_file | write_file | write_file |
| Edit | replace | replace_in_file | str_replace |
| Bash | bash | shell | bash |
| Task | spawn_agent | — | — |
| Multiple | multiple | — | — |

### 5.3 Brainstorm Server

```javascript
// skills/brainstorming/scripts/server.cjs
// 零外部依赖：内置 http + fs + crypto

// HTTP: 提供静态 HTML + WebSocket upgrade
// WS: 自定义 RFC 6455 实现（ping/pong/close handshake）
// FS Watch: 内置 fs.watch() 替代 Chokidar

// v5.0.2: 移除了 ~1200 行 vendored node_modules
// v5.0.3: vendored node_modules 重新加入（保证开箱即用）
```

---

## 6. 本月重大更新详解 (v5.0.6 — 2026-03-24)

### 6.1 Inline Self-Review 替代 Subagent Review Loop

**背景问题**：之前的 v5.0.0 实现的 subagent review loop（dispatch 新的 subagent 来评审 plan/spec）导致：
- 执行时间增加 ~25 分钟 overhead
- 回归测试：5 版本 × 5 试次 = 质量评分与无 review loop 时**无显著差异**

**新方案**：
```
brainstorming skill:
  - 移除 Spec Review Loop (subagent dispatch + 3-iteration cap)
  - 替换为 Inline Spec Self-Review checklist:
      1. placeholder scan
      2. internal consistency  
      3. scope check
      4. ambiguity check

writing-plans skill:
  - 移除 Plan Review Loop (subagent dispatch + 3-iteration cap)
  - 替换为 Inline Self-Review checklist:
      1. spec coverage
      2. placeholder scan
      3. type consistency
  - 新增 "No Placeholders" 章节定义 4 类 plan 失败：
      1. TBD descriptions
      2. vague descriptions
      3. undefined references
      4. "similar to Task N"
```

**效果**：~30 秒完成评审，质量与 25 分钟 subagent loop 相当。

### 6.2 Brainstorm Server 安全修复

**Session 目录重构**（v5.0.6）：
- 之前：server state 和 user interaction data 与 served content 混合在同一目录
- 修复后：
  ```
  session-dir/
    content/   ← HTML 文件（HTTP 可访问）
    state/     ← events, server-info, pid, log（HTTP 不可访问）
  ```

### 6.3 Owner-PID Lifecycle Bug 修复

**两个 bug 导致 60 秒内 false shutdown**：
1. **EPERM from cross-user PIDs**（Tailscale SSH 等）：EPERM 被当作"进程已死"
2. **WSL grandparent PID** 问题：GPID 解析到短生命周期子进程，在第一次 lifecycle check 前就已退出

**修复**：EPERM 视为"存活"，启动时验证 owner PID——若已死则禁用 PID 监控，仅靠 30 分钟 idle timeout。

---

## 7. 优缺点分析

### 优点

1. **Spec-first 强制执行**：`<HARD-GATE>` 彻底防止 AI 跳过设计直接写代码
2. **多平台统一体验**：一个框架覆盖 5 个主流 AI 编程环境
3. **零运行时依赖**（brainstorm server v5.0.2+）：内置 http/crypto/fs，不依赖 npm 包
4. **Inline Self-Review 高效**：用 30 秒替代 25 分钟，质量无损失
5. **Context Isolation 设计**：子代理只收到必要上下文，防止上下文污染
6. **指令优先级清晰**：用户意图 > Skills > 默认 prompt，避免冲突
7. **Subagent 状态协议**：Controller 能精确处理 DONE/BLOCKED/NEEDS_CONTEXT 等各种情况
8. **Visual Companion**：针对视觉化讨论场景提供浏览器协作
9. **文件锁定机制**：多 workspace 并行时防止状态文件冲突

### 缺点

1. **Skill 激活依赖语义匹配**：AI 必须"理解"当前需要哪个 skill，不总是能正确触发
2. **多 Skill 调用开销大**：一个完整流程涉及 brainstorming → writing-plans → subagent-driven，每层都有 LLM 调用成本
3. **Subagent 能力依赖平台**：executing-plans 是备选（无 subagent 时才用），但效果不如 subagent-driven
4. **Brainstorm Server 需要额外进程**：不是所有环境都能方便地启动后台 Node.js 进程
5. **Visual Companion 复杂度高**：对于简单问题，提供 browser 协作是过度工程
6. **迁移成本**（v5.0.0 breaking changes）：Specs/plans 目录重构，需要手动迁移旧文件
7. **Plan 文档质量依赖 AI**：即使有 checklist，AI 仍然可能写出空洞 plan
8. **不处理项目管理**：没有里程碑、进度跟踪——Superpowers 只管"一次开发循环"，不负责整体项目节奏

---

## 8. 与 GSD 的功能对比

| 维度 | Superpowers | GSD |
|------|------------|-----|
| **定位** | 开发方法论 Skill 框架 | 全生命周期项目管理 |
| **流程** | Spec → Plan → Implement | discuss → plan → execute → verify → ship |
| **Agent 模型** | Controller-Worker 子代理 | Phase-specific 专用 agents（10+种） |
| **时间线管理** | ❌ 无 | ✅ Milestone / Phase / Wave / Task |
| **Review 机制** | Inline Self-Review（30秒） | Plan-Checker（10维验证） |
| **多 runtime** | 5个（Claude/Codex/Cursor/OpenCode/Gemini） | 8个（+ Copilot/Windsurf/Antigravity） |
| **Skill 架构** | Skill dir（agentskills.io） | Markdown agents + commands |
| **复杂度** | 中（5个核心 skills） | 极高（30+ commands, 10+ agents） |
| **自动化程度** | 半自动（每步需人工介入） | 高（端到端自动 wave 执行） |
| **状态管理** | 文件系统 | STATE.md / PROJECT.md / ROADMAP.md |

---

## 9. 关键文件速查

| 文件 | 作用 |
|------|------|
| `skills/using-superpowers/SKILL.md` | 顶层入口，skill 路由规则 |
| `skills/brainstorming/SKILL.md` | 设计-first 流程 |
| `skills/writing-plans/SKILL.md` | 规划写作（v5.0.6 inline review） |
| `skills/subagent-driven-development/SKILL.md` | Controller-Worker 执行 |
| `skills/brainstorming/scripts/server.cjs` | 零依赖 brainstorm server |
| `hooks/session-start` | 会话启动上下文注入 |
| `gemini-extension.json` | Gemini CLI 扩展 |
| `RELEASE-NOTES.md` | 详细版本历史（~56KB） |
