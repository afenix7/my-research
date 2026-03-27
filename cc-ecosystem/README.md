# Claude Code 插件生态研究报告

**研究日期**: 2026-03-27  
**研究员**: Subagent (cc-plugin-research)  
**研究对象**: GSD、gstack、Superpowers

---

## 总览

| 项目 | GitHub | 版本 | 定位 | 语言/技术 |
|------|--------|------|------|----------|
| **GSD** | gsd-build/get-shit-done | v1.29.0 (2026-03-25) | 全生命周期项目管理 | Shell + Markdown |
| **gstack** | garrytan/gstack | 活跃开发中 | 持久化浏览器自动化 | TypeScript/Bun |
| **Superpowers** | obra/superpowers | v5.0.6 (2026-03-24) | 结构化开发技能框架 | Shell + Markdown |

---

## 核心定位对比

```
GSD ──────────────→ 项目管理 (Milestone → Phase → Wave → Task)
Superpowers ──────→ 开发方法论 (Spec → Plan → Implement)
gstack ───────────→ 浏览器能力扩展 ($B commands for browser automation)
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

---

## 架构哲学对比

### 状态管理

| | GSD | Superpowers | gstack |
|--|-----|------------|--------|
| **状态存储** | 文件系统（STATE.md 等） | 文档流（Plan/Spec markdown） | 内存 + .gstack/browse.json |
| **状态粒度** | 项目/里程碑/阶段 | 一次开发循环 | Browser session |
| **持久性** | 跨会话持久 | 跨会话（Plan 文档） | Server 生命周期 |

### 错误处理哲学

- **GSD**: 以 phase 为单位验证，10维 Plan-Checker 检测规划缺陷；Verifier 执行 goal-backward 验证
- **Superpowers**: HARD-GATE + Inline Self-Review checklist，每个阶段明确 gate
- **gstack**: 每个错误都附带 AI 可操作的下一步建议

---

## 技术复杂度排名

```
GSD ████████████████████████████████████ 极高
    (30+ commands, 10+ agents, 4-level 任务结构, 8 runtime)

Superpowers ██████████████████           中等
    (5 核心 skills, 4 平台适配层)

gstack ████████                         相对简洁
    (Bun HTTP server + Playwright, ~10 routes)
```

---

## 集成方式对比

| | GSD | Superpowers | gstack |
|--|-----|------------|--------|
| **安装方式** | clone → 符号链接到 `~/.agents/skills/` | marketplace 或 clone | 二进制 + SKILL.md |
| **激活方式** | `/gsd:xxx` slash 命令 | 语义触发（描述需求）或 slash | `$B xxx` 前缀命令 |
| **依赖 Claude Code 版本** | 不限 | 不限 | 不限 |
| **Skill 格式** | Markdown agents + commands | agentskills.io skill dirs | SKILL.md (auto-gen from template) |

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

### 可以组合使用：
```
GSD (项目管理层)
  └─ /gsd:execute-phase
       └─ [Superpowers skills] (开发方法论)
            └─ [gstack] (浏览器操作能力)
```

---

## 版本活跃度

| 项目 | 发布节奏 | 最近更新 |
|------|---------|---------|
| **GSD** | 每1-3天一个版本 | 2026-03-25 (v1.29.0) |
| **Superpowers** | 不规律，主要版本发布 | 2026-03-24 (v5.0.6) |
| **gstack** | 不规律 | 持续活跃 |

---

## 文件清单

```
/root/my-research/cc-ecosystem/
├── gsd-codemap.md          # GSD 详细 CodeMap
├── gstack-codemap.md       # gstack 详细 CodeMap
├── superpowers-codemap.md   # Superpowers 详细 CodeMap（含本月更新分析）
└── README.md                # 本对比分析文档
```
