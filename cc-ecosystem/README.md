# Claude Code 插件生态研究报告

**研究日期**: 2026-03-27  
**研究员**: Subagent (cc-plugin-research)  
**研究对象**: GSD、gstack、Superpowers、**Ralph**

---

## 总览

| 项目 | GitHub | 版本 | 定位 | 语言/技术 |
|------|--------|------|------|----------|
| **GSD** | gsd-build/get-shit-done | v1.29.0 (2026-03-25) | 全生命周期项目管理 | Shell + Markdown |
| **gstack** | garrytan/gstack | 活跃开发中 | 持久化浏览器自动化 | TypeScript/Bun |
| **Superpowers** | obra/superpowers | v5.0.6 (2026-03-24) | 结构化开发技能框架 | Shell + Markdown |
| **Ralph** | snarktank/ralph | 活跃开发中 | PRD驱动自主循环框架 | Bash + Markdown |

---

## 核心定位对比

```
GSD ──────────────→ 项目管理 (Milestone → Phase → Wave → Task)
Superpowers ──────→ 开发方法论 (Spec → Plan → Implement)
gstack ───────────→ 浏览器能力扩展 ($B commands for browser automation)
Ralph ────────────→ PRD闭环执行 (PRD → Stories → Loop → Ship)
```

### GSD — 项目全生命周期管理
GSD 是**唯一一个真正端到端的 AI 项目管理框架**。它从立项（`/gsd:new-project`）到 Ship（`/gsd:ship`）完整覆盖，通过 Milestone/Phase/Wave/Task 四级结构组织工作。适合想要"AI 帮我管项目"而不是"AI 帮我写代码"的用户。

**代表特性**：
- 里程碑路线图管理
- Wave-based 并行执行（checkpoint 可恢复）
- Advisor mode（多头研究 + 权衡分析）
- 开发者画像（8维行为分析）
- 跨平台 8 runtime 支持

### Superpowers — 开发方法论框架
Superpowers 的核心贡献是**把软件开发最佳实践（Spec-first、TDD、Code Review）固化为 AI 可执行的 Skill 流程**。它不管理项目进度，但确保每次开发循环都遵循正确的方法论。

**v5.0.6 本月重大更新**：
- Inline Self-Review 替代 Subagent Review Loop（30秒 vs ~25分钟，质量无显著差异）
- Brainstorm Server 安全修复（session 目录隔离）
- Owner-PID lifecycle bug 修复

**代表特性**：
- `<HARD-GATE>` 强制 Spec-first
- Controller-Worker subagent 模式
- 零依赖 Brainstorm Server（内置 http/crypto）
- 多平台（Claude/Codex/Cursor/OpenCode/Gemini）

### gstack — 持久化浏览器自动化
gstack 解决的是**AI 无法持久操作浏览器**的根本问题——通过常驻 Chromium daemon 将每次工具调用的延迟从 ~3秒降至 ~100ms，并保持 cookie/localStorage/tabs 跨调用持久化。

**代表特性**：
- `@e1/@e2` Ref 系统（AI 可读的元素引用，无需 CSS selector）
- macOS Keychain 安全 Cookie 导入
- 版本自动重启（binary 更新后自动热切换）
- CDP-based Playwright，ARIA snapshot

### Ralph — PRD驱动自主循环
Ralph 是一个**基于 PRD 的无人值守循环框架**。核心思路：把一个功能需求拆成 user stories，循环调用 Claude Code/Amp 直到所有 stories 完成。每次迭代都是 fresh instance，通过 `prd.json` + `progress.txt` + git history 实现跨迭代记忆。

**代表特性**：
- PRD 驱动（User Story 为执行单元）
- 完全无人值守（overnight coding）
- 学习积累机制（progress.txt + AGENTS.md）
- 双工具支持（Claude Code + Amp）
- 自动存档历史运行

---

## 架构哲学对比

### 状态管理

| | GSD | Superpowers | gstack | Ralph |
|--|-----|------------|--------|-------|
| **状态存储** | STATE.md 等 | Plan/Spec markdown | 内存 + .gstack/browse.json | prd.json + progress.txt |
| **状态粒度** | 项目/里程碑/阶段 | 一次开发循环 | Browser session | 单个 PRD |
| **持久性** | 跨会话 | 跨会话 | Server 生命周期 | 跨迭代（文件） |

### 循环与执行模式

| | GSD | Superpowers | gstack | Ralph |
|--|-----|------------|--------|-------|
| **执行模式** | Wave-based 子代理并行 | Controller-Worker 子代理 | CLI → HTTP → CDP | 外部 Bash 循环 + Fresh 实例 |
| **上下文** | 共享（同一 session） | 共享（Skill 链） | 内存（持久化 browser） | 完全隔离（每次新实例） |
| **人工介入** | Checkpoint 审批 | Phase gate | 无 | 仅 max iterations 耗尽 |
| **反馈循环** | Verify + Integration check | Self-review checklist | Playwright assertions | typecheck + test 必须绿 |

---

## 技术复杂度排名

```
GSD ████████████████████████████████████ 极高
    (30+ commands, 10+ agents, 4-level 任务结构, 8 runtime)

Superpowers ██████████████████           中等
    (5 核心 skills, 4 平台适配层)

Ralph ████████                         极简
    (1  shell 脚本 + 2 prompt 模板 + 2 skills)

gstack ████████████                   相对简洁
    (Bun HTTP server + Playwright, ~10 routes)
```

---

## 集成方式对比

| | GSD | Superpowers | gstack | Ralph |
|--|-----|------------|--------|-------|
| **安装** | clone → symlink skills/ | marketplace 或 clone | 二进制 + SKILL.md | clone → copy scripts |
| **激活** | `/gsd:xxx` slash | 语义触发或 slash | `$B xxx` 前缀 | `./ralph.sh [N]` bash |
| **Skill 格式** | Markdown agents + commands | agentskills.io skill dirs | SKILL.md (auto-gen) | 有（PRD + Ralph skills） |
| **运行时** | Claude Code session 内 | Claude Code session 内 | 独立 Bun 进程 | 独立 Bash 进程 |

---

## 选择指南

### 使用 GSD 当你需要：
- 管理一个**跨多周/多里程碑**的大型项目
- 需要 AI 自动跟踪**项目进度和待办**
- 希望有**强规范**的开发流程（phase → wave → task）
- 你是个人开发者，想要某种程度的"AI 项目管理"

### 使用 Superpowers 当你需要：
- 确保每次开发都遵循**正确的方法论**（先设计后实现）
- 想让 AI 在实现前**充分讨论和评审**
- 在多个 AI 编程环境间**切换**（Claude/Codex/Cursor/OpenCode）
- 想要**结构化 Plan 文档**作为团队共享资产

### 使用 gstack 当你需要：
- AI agent **自动化 Web QA** 或端到端测试
- 需要**持久化登录状态**的 Web 操作
- 操作**复杂的 SPA**（React/Vue 应用）而不想每次重新登录
- 想让 AI **无需写 CSS selector** 就能操作页面元素

### 使用 Ralph 当你需要：
- 有**明确的 PRD**（结构化需求文档），想让它"自己跑完"
- **无人值守开发**（夜间/周末，丢给 AI 自己干活）
- 确保**每个 acceptance criteria** 都被验证
- 单个功能开发的**完整闭环**（不遗漏任何需求项）

### 可以组合使用：

```
GSD (项目管理层)
  └─ /gsd:execute-phase
       └─ [Superpowers skills] (开发方法论)
            └─ [Ralph] (PRD 执行)
                 └─ [gstack] (浏览器操作能力)
```

---

## 版本活跃度

| 项目 | 发布节奏 | 最近更新 |
|------|---------|---------|
| **GSD** | 每1-3天一个版本 | 2026-03-25 (v1.29.0) |
| **Superpowers** | 不规律，主要版本发布 | 2026-03-24 (v5.0.6) |
| **gstack** | 不规律 | 持续活跃 |
| **Ralph** | 不规律 | 持续活跃 |

---

## 文件清单

```
/root/my-research/cc-ecosystem/
├── gsd-codemap.md           # GSD 详细 CodeMap
├── gstack-codemap.md        # gstack 详细 CodeMap
├── superpowers-codemap.md   # Superpowers 详细 CodeMap（含本月更新分析）
├── ralph-codemap.md         # Ralph 详细 CodeMap
└── README.md                # 本对比分析文档
```
