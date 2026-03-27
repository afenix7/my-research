# GSD (Get Shit Done) — CodeMap

**GitHub**: https://github.com/gsd-build/get-shit-done  
**Latest Version**: v1.29.0 (2026-03-25)  
**License**: MIT  
**Repository Owner**: gsd-build (formerly glittercowboy)  
**Language**: Shell/CLI + Markdown-based agent definitions  

---

## 1. 项目概述与定位

**GSD** 是一个**项目全生命周期管理**框架，专为 Claude Code（及其他 AI 编程 runtime）设计。它的核心定位是：将一个软件开发项目的完整生命周期（讨论→规划→执行→验证）组织为一个可自动化执行的**阶段化流程**，每个阶段配有专用子代理。

**目标用户**：个人开发者或小型团队，希望将 AI 编程从"单次问答"提升为"结构化项目管理"。

**核心特点**：
- **Phase-based 生命周期**：每个项目被分解为 Milestone → Phase → Wave → Task 的四级结构
- **多 runtime 支持**：Claude Code、Codex、Copilot、Windsurf、Cursor、OpenCode、Gemini CLI、Antigravity
- **专用子代理池**：每种任务类型有专门的 agent prompt（研究者、规划者、执行者、调试者等）
- **全自动化 workflow**：通过 `/gsd:new-project` → discuss → plan → execute → verify → ship 端到端自动化

---

## 2. 核心架构

### 2.1 整体架构

```
用户
  │
  ├─ /gsd:new-project  ──→ PROJECT.md + ROADMAP.md + STATE.md
  │
  ├─ /gsd:discuss-phase ──→ DiscussAgent (context gathering)
  │                         ↓
  ├─ /gsd:plan-phase ─────→ PlannerAgent → PhasePlan.md (per phase)
  │                         ↓ PlanCheckerAgent (10-dimension validation)
  ├─ /gsd:execute-phase ──→ ExecutorAgent (wave-based, subagent spawning)
  │                         ↓ IntegrationChecker / VerifierAgent
  ├─ /gsd:verify-work ─────→ VerifierAgent (goal-backward analysis)
  │                         ↓
  └─ /gsd:ship ────────────→ PR creation via gh CLI
```

### 2.2 项目结构（顶层目录）

```
get-shit-done/
├── agents/                  # 所有子代理的 Markdown 定义
│   ├── gsd-planner.md
│   ├── gsd-phase-researcher.md
│   ├── gsd-executor.md
│   ├── gsd-verifier.md
│   ├── gsd-debugger.md
│   ├── gsd-codebase-mapper.md
│   ├── gsd-plan-checker.md
│   ├── gsd-integration-checker.md
│   ├── gsd-nyquist-auditor.md
│   ├── gsd-assumptions-analyzer.md
│   └── gsd-advisor-researcher.md
├── commands/                # Slash 命令定义 (gsd:xxx)
│   ├── gsd-new-project.md
│   ├── gsd-discuss-phase.md
│   ├── gsd-plan-phase.md
│   ├── gsd-execute-phase.md
│   ├── gsd-verify-work.md
│   ├── gsd-ship.md
│   ├── gsd-new-milestone.md
│   ├── gsd-roadmap.md
│   └── ... (30+ commands)
├── scripts/                # Shell/JS 工具脚本
│   ├── gsd-tools.cjs        # 核心 CLI 工具函数库
│   ├── installer.cjs        # 多 runtime 安装程序
│   └── ...
├── templates/              # 项目模板
│   ├── PROJECT.md.tmpl
│   ├── ROADMAP.md.tmpl
│   └── ...
├── docs/                   # 文档 (architecture/, feature/, CLI/)
└── tests/                  # 测试 (shell scripts)
```

### 2.3 四级任务结构

```
Milestone (重大里程碑)
  └─ Phase (阶段: discuss / plan / execute / verify)
       └─ Wave (波次: 执行批次)
            └─ Task (任务: 原子级操作)
```

---

## 3. 主要模块分析

### 3.1 子代理系统 (agents/)

GSD 的核心创新之一是**专用 agent 定义文件**。每个 agent 是一个 Markdown 文件，包含 YAML frontmatter（定义 agent 类型、模型等）和自然语言描述的 prompt。

**核心 agents 列表**：

| Agent | 职责 | 关键特性 |
|-------|------|---------|
| `gsd-planner` | 阶段规划 | 深度研究 → 分解任务 → 依赖分析 → 逆向验证 |
| `gsd-phase-researcher` | 阶段调研 | 双LLM交叉验证、证据评分、信任度量化 |
| `gsd-executor` | 任务执行 | Wave-based并行执行、checkpoint协议、原子提交 |
| `gsd-verifier` | 目标验证 | Goal-backward 分析、sprints 评审 |
| `gsd-debugger` | 调试调查 | 科学方法（四步）、debug sessions管理 |
| `gsd-codebase-mapper` | 代码库映射 | 多维结构分析、并行 mapper agents |
| `gsd-plan-checker` | 规划质量检查 | 10维评审体系、任务完整性验证 |
| `gsd-integration-checker` | 集成验证 | 端点响应、数据流追踪 |
| `gsd-nyquist-auditor` | 采样质量审计 | Nyquist 采样率验证 |
| `gsd-assumptions-analyzer` | 假设分析 | 依赖识别、风险量化 |
| `gsd-advisor-researcher` | 顾问式调研 | 并行评估、建议生成 |

### 3.2 命令系统 (commands/)

GSD 实现了 **30+ 个 slash 命令**，通过 `gsd-tools.cjs` 中的路由器分发。每个命令对应一个 markdown 文件，定义了触发条件和工作流程。

**主要命令分类**：

**项目生命周期命令**：
- `/gsd:new-project` — 创建新项目，生成 PROJECT.md + ROADMAP.md
- `/gsd:new-milestone` — 创建新里程碑
- `/gsd:roadmap` — 展示项目路线图

**阶段命令**：
- `/gsd:discuss-phase` — 调研讨论阶段（含 `--analyze` 权衡分析）
- `/gsd:plan-phase` — 规划阶段（含 `--reviews` 评审）
- `/gsd:execute-phase` — 执行阶段（wave-based 并行）
- `/gsd:verify-work` — 验证工作

**高级命令**：
- `/gsd:ship` — PR 创建（自动生成丰富 PR body）
- `/gsd:review` — 跨AI评审
- `/gsd:forensics` — 事后调试调查
- `/gsd:profile-user` — 开发者画像（8维行为分析）
- `/gsd:do` — 自然语言命令路由
- `/gsd:note` — 轻量级笔记捕获
- `/gsd:workstreams` — 并行里程碑工作流
- `/gsd:fast` — 跳过规划的快速任务
- `/gsd:next` — 自动推进下一个逻辑步骤
- `/gsd:audit-uat` — 跨阶段 UAT 审计

### 3.3 核心脚本 (`scripts/gsd-tools.cjs`)

这是 GSD 的**工具引擎**，提供：

```javascript
// 关键函数分类
projectManagement: {
  createProject(), initMilestone(), updateState()
  readState(), writeState(), getCurrentPhase()
}
agentSpawning: {
  spawnAgent(), getAvailableAgentTypes()
  getAgentPrompt(), resolveAgentType()
}
phaseWorkflow: {
  executeDiscuss(), executePlan()
  executeExecute(), executeVerify()
}
commandRouting: {
  parseCommand(), dispatchCommand()
  getCommandList()
}
```

### 3.4 规划数据流

```
用户输入 (问题/需求)
    ↓
[GSD-Phase-Researcher] → 领域研究 + 竞品分析
    ↓ (证据 + 信任度)
[GSD-Plan-Checker] → 10维规划验证 (需求覆盖/依赖分析/风险评估)
    ↓
[GSD-Planner] → PhasePlan.md
    ↓ (Wave分解)
[GSD-Executor] → 子代理任务执行
    ↓ (checkpoint协议)
[GSD-Integration-Checker] → 端到端集成验证
    ↓
[GSD-Verifier] → Goal-backward 验证
```

---

## 4. API / 接口设计

GSD **不是一个 API 服务器**，而是一个**命令 + agent + 文件模板**的集合系统。

### 4.1 CLI 接口（命令行）

```bash
# 主要入口命令
gsd-tools <command> [args]

# 或者通过 Claude Code 的 Skill tool
/gsd:<command-name>
```

### 4.2 状态文件协议

GSD 使用文件系统作为状态数据库：

| 文件 | 用途 |
|------|------|
| `PROJECT.md` | 项目总体信息（目标、约束、用户画像） |
| `ROADMAP.md` | 里程碑和阶段的时间线 |
| `STATE.md` | 当前状态（phase、milestone、progress） |
| `.planning/` | 包含 PhasePlan.md、讨论记录、检查点等 |
| `docs/superpowers/` | GSD 特定的文档输出 |

### 4.3 Agent Frontmatter Schema

```yaml
---
name: gsd-executor
description: 执行 GSD 计划中的任务
version: 1.0.0
agent_type: general-purpose  # | coding | research
mode: subagent               # | session
model: inherit               # | sonnet | haiku | inherit
skills:                      # 可选：注入的专用技能
  - tdd
  - systematic-debugging
triggers:
  - /gsd:execute-phase
  - execute phase tasks
---
```

### 4.4 跨 Runtime 命令转换

GSD 支持 8 个不同的 AI 编程 runtime，每个 runtime 有不同的工具集。`installer.cjs` 包含针对每个 runtime 的：
- 安装命令生成
- 工具映射表（如 Claude Code 的 `Read` → Codex 的 `read_file`）
- Skill 目录配置

---

## 5. 与 Claude Code 的集成机制

### 5.1 集成方式

GSD 通过 **Claude Code 的 Skill Tool 接口**集成：

1. **安装**：将整个仓库 clone 到 `~/.agents/skills/gsd/`
2. **激活**：用户输入 `/gsd:<command>` 或描述任务意图
3. **路由**：`gsd-tools.cjs` 解析命令并调用对应工作流
4. **Agent Spawning**：GSD 通过 Claude Code 的 `/slash Skill:agent_name` 启动专用子代理

### 5.2 安装机制

`installer.cjs` 动态检测当前 runtime（Claude Code / Codex / Copilot / Windsurf 等），生成对应的：
- Skill 目录符号链接
- `commands/` 中的命令文件引用
- `SKILL.md` 中的触发规则

### 5.3 多 Runtime 支持架构

```
GSD Core (一致)
  ├─ RuntimeDetector → identify current runtime
  ├─ ToolMapper → map universal tools to runtime-specific tools
  ├─ CommandConverter → convert gsd commands to runtime syntax
  └─ SkillInstaller → install to correct skills directory
        │
        ├─ Claude Code: ~/.claude/commands/
        ├─ Codex: ~/.codex/agents/
        ├─ Copilot: ~/.github/copilot-instructs/
        └─ ...
```

---

## 6. 优缺点分析

### 优点

1. **真正端到端的项目管理**：从立项到 ship 完整覆盖，不是零散工具集合
2. **多 runtime 广泛支持**：一个框架覆盖 8 个主流 AI 编程环境
3. **专用 agent 设计**：不是通用 LLM，而是针对每个任务优化的专用 prompt
4. **极高的迭代速度**：2026年3月保持每1-3天一个版本的发布节奏
5. **wave-based 执行**：既支持并行效率，又通过 checkpoint 保证可恢复性
6. **Advisor mode**：多头研究 + 权衡分析，真正辅助决策而非盲目执行
7. **Security 意识**：内置 prompt injection 检测、path traversal 防护
8. **国际化**：支持韩语、日语、葡萄牙语文档

### 缺点

1. **复杂度极高**：30+ 命令、10+ agents、4级任务结构，学习曲线陡峭
2. **强opinionated**：高度规范化的流程对某些团队可能过于约束
3. **状态管理依赖文件系统**：`STATE.md`、`PROJECT.md` 的格式漂移可能导致解析失败
4. **对非 GSD 工作流的兼容性差**：一旦进入 GSD 流程，很难中途切换到其他方式
5. **子代理数量爆炸**：一个 execute-phase 可能spawn 多个子代理，上下文消耗大
6. **Agent 能力受限于模型**：Phase-researcher 需要强模型，executor 需要 Coding 模型，模型选择不当会导致失败
7. **SKILL.md 文件维护成本高**：frontmatter 字段、triggers、agent_type 需要严格一致性

---

## 7. 技术债务与已知问题（从 Changelog 推断）

- Windows 兼容性问题持续出现（8.3 short path、EPERM/EACCES）
- `jq` 依赖曾被错误地当作 hard dependency
- CRLF frontmatter 解析腐蚀问题多次出现
- Codex config.toml corruption from 非boolean `[features]` keys
- WSL + Windows Node.js 版本 mismatch 检测

---

## 8. 最新版本亮点 (v1.29.0 — 2026-03-25)

- **Windsurf 完整支持**：新增 Codeium runtime
- **Agent skill injection**：可向子代理注入项目特定技能
- **UI-phase / UI-review**：UI 设计专项工作流
- **Security scanning CI**：prompt injection、base64、secret 扫描
- **Portuguese/Korean/Japanese 文档**

---

## 9. 关键文件速查

| 文件 | 作用 |
|------|------|
| `agents/gsd-planner.md` | 最核心的规划 agent (45KB+) |
| `commands/gsd-execute-phase.md` | 执行阶段主命令 |
| `scripts/gsd-tools.cjs` | CLI 工具引擎 |
| `scripts/installer.cjs` | 多 runtime 安装程序 |
| `templates/PROJECT.md.tmpl` | 项目模板 |
| `ETHOS.md` | 开发者哲学 |
