# GSD (Get Shit Done) — CodeMap

**GitHub**: https://github.com/gsd-build/get-shit-done  
**Latest Version**: v1.29.0 (2026-03-25)  
**License**: MIT  
**Repository Owner**: gsd-build  
**Language**: CommonJS CLI + Markdown-based agent definitions  
**Repo Structure**: The skill lives at `~/.agents/skills/gsd/` (installed via clawhub). The repo root at `gsd-build/get-shit-done` contains `get-shit-done/` subdirectory (the actual skill), plus `bin/install.js` (installer) and `tests/` at top level.

---

## 1. 项目概述与定位

**GSD** 是一个**项目全生命周期管理**框架，专为 Claude Code（及其他 AI 编程 runtime）设计。它的核心定位是：将一个软件开发项目的完整生命周期（讨论→规划→执行→验证→交付）组织为一个可自动化执行的**阶段化流程**，每个阶段配有专用子代理。

**目标用户**：个人开发者或小型团队，希望将 AI 编程从"单次问答"提升为"结构化项目管理"。

**核心特点**：
- **Phase-based 生命周期**：每个项目被分解为 Milestone → Phase → Plan → Wave → Task 的五级结构
- **多 runtime 支持**：Claude Code、Codex、Copilot、Windsurf、Cursor、OpenCode、Gemini CLI、Antigravity
- **专用子代理池**：每种任务类型有专门的 agent prompt（研究者、规划者、执行者、调试者等）
- **全自动化 workflow**：通过 `/gsd:new-project` → discuss → plan → execute → verify → ship 端到端自动化
- **Wave-based 并行执行**：同一 wave 内的 plans 可并行执行，checkpoint 控制暂停/恢复
- **Auto-fix 机制**：执行者自动修复 bug、缺失功能、阻塞问题，只对架构变更暂停

---

## 2. 核心架构

### 2.1 整体架构图

```
用户
  │
  ├─ /gsd:new-project ─────────────────────────────────────────────────────┐
  │   → 4个并行 researcher agents → research-synthesizer → roadmapper      │
  │   → PROJECT.md + REQUIREMENTS.md + ROADMAP.md + STATE.md + config.json  │
  │                                                                          │
  ├─ /gsd:discuss-phase ──────────────────────────────────────────────────►│ CONTEXT.md
  │   → Scout codebase → Identify gray areas → Present trade-offs            │
  │                                                                          │
  ├─ /gsd:plan-phase ──────────────────────────────────────────────────────►│ PLAN.md (per phase)
  │   → gsd-planner → gsd-plan-checker (9-dimension validation loop)        │
  │                                                                          │
  ├─ /gsd:execute-phase ───────────────────────────────────────────────────►│ SUMMARY.md
  │   → gsd-executor per plan (wave-based parallelism)                      │
  │   → checkpoint protocol (human-verify / decision / human-action)        │
  │   → deviation rules (auto-fix bugs/missing功能/阻塞)                     │
  │                                                                          │
  ├─ /gsd:verify-work ─────────────────────────────────────────────────────►│ UAT.md + VERIFICATION.md
  │   → Goal-backward 4-level verification (exist → substantive → wired → data-flow)
  │                                                                          │
  └─ /gsd:complete-milestone ──────────────────────────────────────────────►│ milestones/vX-ROADMAP.md
      → Archive phase artifacts → git tag → PROJECT.md update                │
```

### 2.2 项目文件结构（`.planning/` 目录）

```
.planning/
  ├── PROJECT.md          # 项目总体信息（目标、约束、用户画像、技术栈）
  ├── ROADMAP.md         # 里程碑和阶段的线性时间线（含 success_criteria）
  ├── REQUIREMENTS.md    # 可追溯的需求表（REQ-ID → Phase → Plan 映射）
  ├── STATE.md           # 当前状态（当前 milestone/phase/plan, decisions, blockers）
  ├── config.json        # Workflow 偏好配置（auto_advance, discuss_mode, nyquist_validation 等）
  │
  ├── milestones/        # 归档的里程碑
  │   └── v1.0-ROADMAP.md, v1.0-REQUIREMENTS.md
  │
  └── phases/
      └── 01-name/
          ├── 01-01-PLAN.md        # 每个 plan 一个文件
          ├── 01-01-SUMMARY.md      # 执行后产出
          ├── 01-CONTEXT.md         # discuss-phase 产出
          ├── 01-DISCUSSION.md      # 讨论记录
          ├── 01-RESEARCH.md        # 调研输出
          └── 01-VERIFICATION.md   # verify-work 产出
```

### 2.3 五级任务层级结构

```
Milestone (版本: v1.0, v1.1)
  └─ Phase (阶段序号: 01-foundation, 02-auth, ...)
       └─ Plan (计划序号: 01, 02, ...)
            └─ Wave (执行波次: 1, 2, 3...)
                 └─ Task (原子任务: type="auto" | type="checkpoint:*")
```

**层级流转规则：**

| 层级 | 定义 | 决定因素 |
|------|------|---------|
| Phase | 独立可交付的功能块 | ROADMAP.md 中定义 |
| Plan | 2-3个任务的原子执行单元 | Planner 按依赖图分解 |
| Wave | 同一批可并行执行的 plans | `depends_on` 和 `wave` frontmatter 字段 |
| Task | 15-60分钟 Claude 执行时间 | Planner 按文件数和复杂度估计 |

**Wave 计算规则：**
```
Wave(plan) = max(Wave(depends_on)) + 1
若 depends_on = [] → Wave 1（可并行）
```

---

## 3. 核心 Agents 详解

### 3.1 Agent 目录结构

Installed at `~/.agents/skills/gsd/agents/`:
```
agents/
  ├── gsd-planner.md           # 最核心：创建可执行 PLAN.md
  ├── gsd-executor.md          # 执行 plan，原子提交，checkpoint 协议
  ├── gsd-verifier.md          # Goal-backward 验证（执行后）
  ├── gsd-plan-checker.md       # Plan 质量检查（执行前）
  ├── gsd-debugger.md          # 科学方法调试
  ├── gsd-codebase-mapper.md   # 代码库结构分析
  ├── gsd-integration-checker.md
  ├── gsd-phase-researcher.md
  ├── gsd-project-researcher.md
  ├── gsd-research-synthesizer.md
  ├── gsd-roadmapper.md
  ├── gsd-plan-checker.md
  └── [SKILL.md wrapper files in subdirectories]
```

### 3.2 Agent Frontmatter Schema

```yaml
---
name: gsd-executor
description: Executes GSD plans with atomic commits, deviation handling,
  checkpoint protocols, and state management.
tools: Read, Write, Edit, Bash, Grep, Glob
permissionMode: acceptEdits    # 子代理权限模式
color: yellow                 # UI 颜色标识
# hooks:                       # 可选的 PostToolUse 钩子
#   PostToolUse:
#     - matcher: "Write|Edit"
#       hooks:
#         - type: command
#           command: "npx eslint --fix $FILE 2>/dev/null || true"
---
```

### 3.3 核心 Agents 详细规范

#### gsd-planner（规划者）

**Spawned by**: `/gsd:plan-phase` orchestrator

**职责**: 将 phase 分解为 2-3 个 task 的可执行 plans，构建依赖图，分配 wave 数字

**关键 Prompt 逻辑**:
- **Context Fidelity**: 读取 CONTEXT.md，LOCKED decisions 必须实现，Deferred Ideas 禁止出现
- **Discovery Levels**: Level 0(skip) / Level 1(Context7) / Level 2(full DISCOVERY.md) / Level 3(deep)
- **Task Anatomy**: `<files>` + `<action>` + `<verify><automated>` + `<done>` 四字段必填
- **Task Types**: `auto`(自主) / `checkpoint:human-verify`(90%) / `checkpoint:decision`(9%) / `checkpoint:human-action`(1%)
- **Scope Rules**: 2-3 tasks/plan, 最多 5 files/plan, 15-60min/task
- **Interface-First**: 先定义接口/类型文件，再实现
- **TDD Detection**: 可测 I/O 的场景创建 dedicated TDD plan；否则 standard task + `tdd="true"` attribute

**输出**: `{phase}-{plan}-PLAN.md` 文件，写入 `.planning/phases/XX-name/`

#### gsd-executor（执行者）

**Spawned by**: `/gsd:execute-phase` → wave orchestration → per-plan subagent

**职责**: 执行 plan 的每个 task，原子提交，处理 deviation，checkpoint 暂停，生成 SUMMARY

**关键 Prompt 逻辑**:

1. **Init Phase**: `gsd-tools.cjs init execute-phase` 获取 executor_model, commit_docs, sub_repos, phase_dir, plans
2. **Load PLAN**: 解析 frontmatter (phase, plan, type, autonomous, wave, depends_on)
3. **Execution Patterns**:
   - **Pattern A** (无 checkpoint): 执行全部 tasks → commit → create SUMMARY
   - **Pattern B** (有 checkpoint): 执行到 checkpoint → STOP → return structured checkpoint message
   - **Pattern C** (continuation): 从 `<completed_tasks>` 恢复，继续执行

4. **Deviation Rules** (自动应用，无需用户许可):
   - **Rule 1**: 代码不工作 → 自动修复 bug
   - **Rule 2**: 缺少关键功能(无错误处理/无验证/无auth) → 自动添加
   - **Rule 3**: 阻塞问题(缺少依赖/类型错误/断链) → 自动修复
   - **Rule 4**: 架构变更 → STOP → checkpoint:decision
   - **Fix Attempt Limit**: 单 task 3 次 auto-fix 后 STOP

5. **Checkpoint Protocol**:
   ```
   checkpoint:human-verify → 90% → 停止，等待用户验证 (auto-mode: auto-approve)
   checkpoint:decision    → 9%  → 停止，等待用户决策 (auto-mode: auto-select first)
   checkpoint:human-action→ 1%  → 停止，等待人类操作如 2FA (无法自动化)
   ```

6. **Task Commit Protocol**:
   - 逐文件 `git add` (禁止 `git add .`)
   - commit message: `{type}({phase}-{plan}): {description}` (type: feat/fix/test/refactor/chore)
   - sub_repos 模式: `gsd-tools.cjs commit-to-subrepo` 路由到正确子仓库

7. **Summary Creation**: 使用 template，填写 frontmatter (dependency graph, tech-stack, decisions)，记录 deviations 和 stub tracking

8. **State Updates** (执行后):
   ```bash
   gsd-tools.cjs state advance-plan
   gsd-tools.cjs state update-progress
   gsd-tools.cjs state record-metric --phase --plan --duration --tasks --files
   gsd-tools.cjs roadmap update-plan-progress
   gsd-tools.cjs requirements mark-complete REQ_IDS
   ```

#### gsd-verifier（验证者）

**Spawned by**: `/gsd:verify-work` workflow

**职责**: Goal-backward 验证 phase 是否达成目标，而非仅检查 tasks 是否完成

**Core Principle**: Task completion ≠ Goal achievement

**Verification Levels (4层递进)**:
```
Level 1 (Exists): 文件存在？
Level 2 (Substantive): 文件有实质内容（>10行，有实现逻辑）？
Level 3 (Wired): 文件被 import/used 而非 orphaned？
Level 4 (Data-Flow): 数据源产生真实数据（不是 hardcoded [] / {})?
```

**Key Links 验证模式**:
- Component → API: grep fetch/axios 调用
- API → Database: grep Prisma/query + return
- Form → Handler: grep onSubmit + API call
- State → Render: grep useState + JSX render

**Re-verification Mode**: 读取旧的 VERIFICATION.md，只对 `gaps` 重新验证，passed items 快速回归

#### gsd-plan-checker（规划检查者）

**Spawned by**: `/gsd:plan-phase` 在 planner 生成 PLAN.md 后立即调用

**职责**: 在执行前验证 plans 是否能达成 phase goal

**9个验证维度**:

| Dimension | 检查内容 | 严重性 |
|-----------|---------|--------|
| 1. Requirement Coverage | 每个 ROADMAP requirement ID 是否出现在至少一个 plan 的 `requirements:` 字段 | BLOCKER |
| 2. Task Completeness | 每个 task 是否有 `<files>` + `<action>` + `<verify>` + `<done>` | BLOCKER |
| 3. Dependency Correctness | `depends_on` 无循环引用、无 missing references、无 future references | BLOCKER |
| 4. Key Links Planned | artifacts 是否互联（不只是创建，还需 wiring） | WARNING |
| 5. Scope Sanity | tasks/plan ≤ 3, files/plan ≤ 8, total context ~50% | WARNING |
| 6. Verification Derivation | `must_haves` 是否从 phase goal 反推（用户可观察） | WARNING |
| 7. Context Compliance | 是否遵循 CONTEXT.md 中的 locked decisions，是否排除 deferred ideas | BLOCKER |
| 8. Nyquist Compliance | 每个 task 是否有 `<automated>` verify 命令 | BLOCKER |
| 9. Cross-Plan Data Contracts | 多 plan 共享数据管道时是否有 transformation 冲突 | WARNING |

**Max Revision Loops**: 3次（planner 修复 → checker 重验 → 超过3次失败则放弃）

#### gsd-debugger（调试者）

**Spawned by**: `/gsd:debug` command

**哲学**: User=Reporter(报告症状), Claude=Investigator(寻找根因)

**科学方法流程**:
```
Phase 1: 收集证据 → 观察精确行为(不是"broken"而是"counter shows 3 when clicking once")
Phase 2: 形成假设 → 每个假设必须可证伪
Phase 3: 设计实验 → 一次只改一个变量
Phase 4: 执行 → 观察 → 记录结果
Phase 5: 得出结论 → 支持或反驳假设
```

**调试策略**:
- Binary Search / Divide and Conquer（代码量大时每次排除一半）
- Rubber Duck Debugging（写出完整细节，常能发现盲点）
- Minimal Reproduction（逐步删除无关代码直到最小复现）
- Working Backwards（从期望结果反向追溯）
- Differential Debugging（对比 working vs broken 状态的差异）
- Observability First（加日志再改代码）

**Meta-Debugging**: 调试自己写的代码更难——需要把代码当别人写的来读

---

## 4. Slash Commands 完整列表

### 4.1 生命周期命令

| Command | Description | Key Flags |
|---------|-------------|-----------|
| `/gsd:new-project` | 初始化新项目（questioning → research → requirements → roadmap） | `--auto` |
| `/gsd:new-milestone` | 创建新里程碑 | — |
| `/gsd:roadmap` | 展示/编辑项目路线图 | — |
| `/gsd:complete-milestone` | 归档里程碑（milestones/ + git tag） | `<version>` |

### 4.2 Phase 阶段命令

| Command | Description | Key Flags |
|---------|-------------|-----------|
| `/gsd:discuss-phase` | 调研讨论阶段，提取实现决策到 CONTEXT.md | `--auto`, `--batch`, `--analyze`, `--text` |
| `/gsd:plan-phase` | 创建 PLAN.md（planner → plan-checker 验证循环） | `--auto`, `--research`, `--skip-research`, `--gaps`, `--skip-verify`, `--prd <file>`, `--reviews`, `--text` |
| `/gsd:execute-phase` | 执行 plan（wave-based 并行，checkpoint 协议） | `<phase> [--wave N] [--gaps-only] [--interactive]` |
| `/gsd:verify-work` | UAT 测试验证（persistent state，one-at-a-time） | `[phase]` |
| `/gsd:autonomous` | 全自动执行剩余 phases（discuss→plan→execute per phase） | `[--from N]` |

### 4.3 支持命令

| Command | Description |
|---------|-------------|
| `/gsd:debug` | 科学方法调试（有 checkpoint 协议） |
| `/gsd:research-phase` | 专项领域研究（deep-dive） |
| `/gsd:research-project` | 项目级调研 |
| `/gsd:synthesize` | 合成 research 输出 |
| `/gsd:map-codebase` | 并行代码库结构分析 |
| `/gsd:review-plan` | Plan 评审（cross-AI feedback） |
| `/gsd:add-phase` | 向 roadmap 插入新 phase |
| `/gsd:insert-phase` | 插入 phase 到 roadmap 特定位置 |
| `/gsd:remove-phase` | 从 roadmap 删除 phase |
| `/gsd:add-todo` | 添加 todo 项 |
| `/gsd:check-todos` | 查看 todo 列表状态 |
| `/gsd:create-checkpoint` | 手动创建 checkpoint |
| `/gsd:complete-checkpoint` | 完成 checkpoint 并继续 |
| `/gsd:update-checkpoint` | 更新 checkpoint 内容 |
| `/gsd:continue-phase` | 从 checkpoint 继续 phase |
| `/gsd:pause-work` | 暂停当前工作 |
| `/gsd:resume-work` | 恢复暂停的工作 |
| `/gsd:plan-milestone-gaps` | 为 milestone 缺口创建 fix plans |
| `/gsd:audit-milestone` | 审计 milestone 进度和状态 |
| `/gsd:list-phase-assumptions` | 列出 phase 假设和依赖 |
| `/gsd:integrate` | 集成变更并验证系统兼容性 |
| `/gsd:progress` | 显示项目进度 |
| `/gsd:init-repo` | 初始化 GSD 仓库结构 |
| `/gsd:update` | 更新项目状态和文档 |
| `/gsd:whats-new` | 显示 GSD 新功能 |

---

## 5. 核心工作流详解

### 5.1 `/gsd:new-project` 端到端流程

```
用户触发 /gsd:new-project
  ↓
1. Questioning → 用户问答（目标/约束/技术偏好）
  ↓
2. 4个并行 Project Researcher agents:
   - Domain researcher (领域背景)
   - Technical researcher (技术选型)
   - Ecosystem researcher (生态/竞品)
   - User-experience researcher (UX/用户)
  ↓
3. Research Synthesizer → 综合输出
  ↓
4. Roadmapper → ROADMAP.md (phases + milestones + success_criteria)
  ↓
5. 生成文件:
   .planning/PROJECT.md
   .planning/REQUIREMENTS.md (REQ-XXX 格式)
   .planning/ROADMAP.md
   .planning/STATE.md
   .planning/config.json
  ↓
用户 → /gsd:plan-phase 1 开始执行
```

### 5.2 `/gsd:execute-phase` Wave 执行流程

```
Orchestrator (main agent, ~15% context):
  ↓
1. gsd-tools.cjs init execute-phase → 获取 plans 列表
  ↓
2. 分析每个 plan 的 frontmatter:
   - depends_on: [] → Wave 1
   - depends_on: ["01"] → Wave max(depends) + 1
  ↓
3. 分组: { wave1: [p01, p02], wave2: [p03], wave3: [p04, p05] }
  ↓
Per-Wave 执行:
  For wave in [1, 2, 3...]:
    plans_in_wave = filtered(wave)
    If --wave N flag: only execute wave N
    Spawn subagents for all plans_in_wave (parallel)
    Wait all subagents to complete (or checkpoint hit)
    If checkpoint hit: STOP, return structured message
    Continue to next wave
  ↓
After all waves:
  Phase verification (all plans complete)
  Update STATE.md progress
  gsd-tools.cjs state record-session --stopped-at "Completed ${PHASE}-${PLAN}-PLAN.md"
```

### 5.3 Checkpoint 机制详解

**Checkpoint 是 executor 暂停并等待人工介入的点**

**触发场景**:
```
Task 类型:
  type="auto"           → 自主执行，不暂停
  type="checkpoint:human-verify" → 90% 场景：需要用户验证 UI/功能
  type="checkpoint:decision"      → 9% 场景：需要用户在多个选项中做决定
  type="checkpoint:human-action"  → 1% 场景：真正不可避免的人工步骤（2FA/邮件链接）
```

**Checkpoint Return Format** (Structured Message):
```markdown
## CHECKPOINT REACHED

**Type:** [human-verify | decision | human-action]
**Plan:** {phase}-{plan}
**Progress:** {completed}/{total} tasks complete

### Completed Tasks
| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | [name] | [hash] | [key files] |

### Current Task
**Task {N}:** [name]
**Status:** [blocked | awaiting verification | awaiting decision]
**Blocked by:** [specific blocker]

### Checkpoint Details
[Type-specific content]

### Awaiting
[What user needs to do]
```

**Auto-mode Behavior** (`workflow.auto_advance = "true"` in config.json):
```
checkpoint:human-verify → ⚡ Auto-approved, 继续下一 task
checkpoint:decision     → ⚡ Auto-selected option 1, 继续
checkpoint:human-action→ STOP (auth gate 无法自动化)
```

**Continuation Protocol** (checkpoint 恢复时):
```
1. 新 agent spawn，读 `<completed_tasks>` block
2. git log --oneline -5 验证之前 commits 存在
3. 不 redo 已完成任务
4. 从 checkpoint resume point 继续
5. 再次遇到 checkpoint → 再次 return structured message
```

### 5.4 TDD 执行流程

**Dedicated TDD Plan** (整个 plan 是 TDD):
```
Wave 1:
  RED:   Write failing test  → commit: "test({phase}-{plan}): add failing test"
  GREEN: Write minimal code  → commit: "feat({phase}-{plan}): implement {feature}"
  REFACTOR: Clean up         → commit: "refactor({phase}-{plan}): clean up"
```

**Task-level TDD** (standard plan 中的 task 带 `tdd="true"`):
```xml
<task type="auto" tdd="true">
  <name>Task: [name]</name>
  <files>src/feature.ts, src/feature.test.ts</files>
  <behavior>
    - Test 1: [expected behavior]
    - Test 2: [edge case]
  </behavior>
  <action>[Implementation after tests pass]</action>
  <verify>
    <automated>npm test -- --filter=feature</automated>
  </verify>
  <done>[Criteria]</done>
</task>
```

### 5.5 Goal-Backward Verification (gsd-verifier)

```
Step 0: Check for Previous Verification
  ↓ 有旧 VERIFICATION.md + gaps → Re-verification Mode
  ↓ 无 → Initial Mode
Step 1: Load Context (Initial only)
  → ls PLAN.md, SUMMARY.md
  → gsd-tools.cjs roadmap get-phase
Step 2: Establish Must-Haves (Initial only)
  → Option A: must_haves in PLAN frontmatter
  → Option B: Success Criteria from ROADMAP.md
  → Option C: Derive from phase goal (fallback)
Step 3: Verify Observable Truths
  → 每个 truth → supporting artifacts → artifact status
Step 4: Verify Artifacts (4 Levels)
  → Level 1: EXISTS?
  → Level 2: SUBSTANTIVE (>10 lines, real logic)?
  → Level 3: WIRED (imported AND used)?
  → Level 4: DATA-FLOW (data source produces real data)?
Step 5: Verify Key Links
  → Component→API / API→DB / Form→Handler / State→Render
Step 6: Check Requirements Coverage
  → 每个 REQ-ID → supporting truths → SATISFIED / BLOCKED / NEEDS_HUMAN
Step 7: Scan Anti-Patterns
  → TODO/FIXME/placeholder / empty impl / hardcoded empty data / console.log-only
```

---

## 6. 数据结构与接口定义

### 6.1 PLAN.md Frontmatter Schema

```yaml
---
phase: 01-name              # Phase 标识 (XX-name)
plan: 01                    # Plan 序号
type: execute | tdd        # plan 类型
wave: 1                     # 执行波次 (从 depends_on 推导)
depends_on: []              # 依赖的 plan IDs (e.g., ["01", "02"])
files_modified: []         # 本 plan 涉及的文件 (用于并行检测)
autonomous: true           # false 则包含 checkpoint
requirements: [AUTH-01, AUTH-02]  # 必须非空！映射到 REQUIREMENTS.md
user_setup: []             # 人类必需的配置 (env vars, account creation)
gap_closure: false         # true = 是 verify-work 创建的 fix plan

must_haves:                # Goal-backward 验证标准
  truths:                  # 必须为 TRUE 的可观察行为
    - "User can see existing messages"
    - "User can send a message"
  artifacts:               # 必须存在的文件
    - path: "src/components/Chat.tsx"
      provides: "Message list rendering"
  key_links:               # 关键连接
    - from: "Chat.tsx"
      to: "api/chat"
      via: "fetch in useEffect"
---
```

### 6.2 STATE.md Schema (部分)

```
# Current State

**Milestone:** v1.0
**Current Phase:** 02-auth
**Current Plan:** 01
**Progress:** ████████░░ 67%

## Phase Status

| Phase | Status | Plans | Completed |
|-------|--------|-------|-----------|
| 01-foundation | ✅ Complete | 3 | 3/3 |
| 02-auth | 🔄 In Progress | 2 | 1/2 |

## Decisions (锁定)

- D-01: Use jose library for JWT (not jsonwebtoken)
- D-02: Card layout for dashboard

## Blockers

- None currently

## Last Session

- Timestamp: 2026-03-27T10:30:00Z
- Stopped at: Completed 02-auth-01-PLAN.md
```

### 6.3 ROADMAP.md Schema (部分)

```
# Project Roadmap

## Milestone: v1.0 (Current)

### Phase 01: Foundation
- **Status:** ✅ Complete
- **Requirements:** REQ-01, REQ-02, REQ-03
- **Success Criteria:**
  - [x] User can sign up
  - [x] User can log in
  - [x] Dashboard displays

### Phase 02: Auth & Permissions
- **Status:** 🔄 In Progress
- **Requirements:** AUTH-01, AUTH-02, AUTH-03
- **Plans:** 01, 02
- **Success Criteria:**
  - [ ] Role-based access control
  - [ ] Session management
```

### 6.4 config.json Schema

```json
{
  "workflow": {
    "_auto_chain_active": "false",
    "auto_advance": "false",
    "discuss_mode": "discuss",
    "nyquist_validation": "true",
    "quality_degradation_curve": {
      "peak": 30,
      "good": 50,
      "degrading": 70,
      "poor": 100
    }
  },
  "git": {
    "commit_docs": "false",
    "sub_repos": []
  },
  "execution": {
    "executor_model": "inherit"
  }
}
```

### 6.5 gsd-tools.cjs 核心 CLI 命令

```bash
# Project initialization
gsd-tools.cjs init execute-phase "${PHASE}"
gsd-tools.cjs init phase-op "${PHASE}"
gsd-tools.cjs init milestone-op

# State management
gsd-tools.cjs state advance-plan
gsd-tools.cjs state update-progress
gsd-tools.cjs state record-metric --phase "${PHASE}" --plan "${PLAN}" --duration "${DURATION}" --tasks "${TASK_COUNT}" --files "${FILE_COUNT}"
gsd-tools.cjs state record-session --stopped-at "..."
gsd-tools.cjs state add-decision --phase "${PHASE}" --summary "${decision}"

# Roadmap
gsd-tools.cjs roadmap get-phase "${PHASE_NUM}"
gsd-tools.cjs roadmap get-phase "${PHASE_NUM}" --raw
gsd-tools.cjs roadmap update-plan-progress "${PHASE_NUMBER}"

# Requirements
gsd-tools.cjs requirements mark-complete REQ_ID1 REQ_ID2 ...

# Verification
gsd-tools.cjs verify artifacts "${PLAN_PATH}"
gsd-tools.cjs verify key-links "${PLAN_PATH}"
gsd-tools.cjs verify commits HASH1 HASH2 ...

# Config
gsd-tools.cjs config-get workflow.auto_advance
gsd-tools.cjs config-get workflow.discuss_mode

# Multi-repo
gsd-tools.cjs commit-to-subrepo "${message}" --files file1 file2 ...

# Subagent spawning (used by orchestrators)
gsd-tools.cjs spawn-executor "${PLAN}" "${PHASE}" "${WAVE}"
```

---

## 7. 多 Agent 协调机制

### 7.1 Agent Spawning 模式

GSD 使用 Claude Code 的 Task tool 启动子代理：

**Orchestrator Pattern** (execute-phase):
```
Main Agent (orchestrator, ~15% context)
  ↓ spawns parallel
gsd-executor (plan 01, ~100% fresh context)
gsd-executor (plan 02, ~100% fresh context)
gsd-executor (plan 03, ~100% fresh context)
  ↓ (each produces SUMMARY.md)
Orchestrator collects results
  ↓
Next wave OR phase complete
```

**Skill() Flat Invocation** (autonomous mode):
```javascript
Skill("gsd-executor")
  .with(PARAM)
  .run()
```

### 7.2 Agent 间通信协议

Agents 通过文件系统传递状态（无直接消息）：

```
gsd-planner → writes → {phase}-{plan}-PLAN.md
gsd-executor → reads → PLAN.md
gsd-executor → writes → {phase}-{plan}-SUMMARY.md
gsd-verifier → reads → SUMMARY.md + codebase
gsd-verifier → writes → {phase}-VERIFICATION.md
gsd-tools.cjs state → writes → STATE.md
```

### 7.3 Project Context Discovery Protocol

每个 agent 启动时必须执行：
```
1. Read ./CLAUDE.md (if exists) — project-specific constraints
2. Check .claude/skills/ or .agents/skills/
   → List available skills
   → Read SKILL.md for each skill
   → Load specific rules/*.md files as needed
   → DO NOT load full AGENTS.md (100KB+ context cost)
3. Follow skill rules relevant to current task
```

---

## 8. 关键机制深度解析

### 8.1 Quality Degradation Curve（上下文质量曲线）

| Context 使用率 | 质量 | Claude 状态 |
|-------------|------|-----------|
| 0-30% | PEAK | 全面、深入、严谨 |
| 30-50% | GOOD | 自信、稳定 |
| 50-70% | DEGRADING | 效率优先，最小化输出开始 |
| 70%+ | POOR | 仓促、最小化 |

**规则**: 每个 plan 应在 ~50% context 内完成 → 2-3 tasks max → 5 files max

### 8.2 Context Fidelity（CONTEXT.md 决策传递）

`/gsd:discuss-phase` 产出 CONTEXT.md，有三个 section：

| Section | 含义 | Planner 行为 |
|---------|------|------------|
| `## Decisions` | 用户锁定决策 | 必须实现，禁止违背 |
| `## Claude's Discretion` | 用户放权领域 | Planner 自由判断 |
| `## Deferred Ideas` | 用户主动推迟 | Planner 禁止包含 |

**Self-check**: Planner 返回前验证：
- [ ] 每个 D-XX 都有 task 实现它
- [ ] Task action 引用了 D-XX ID
- [ ] 没有 task 实现 Deferred Ideas

### 8.3 Deviation Rules 详解

**Rule 优先级**:
1. Rule 4 (架构变更) → STOP → checkpoint:decision
2. Rules 1-3 → 自动修复
3. 不确定 → Rule 4 (询问用户)

**Scope Boundary**:
- 只修复当前 task **直接导致**的问题
- 预先存在的 warnings/lint errors 在无关文件中 → 记录到 `deferred-items.md`，不修复

**Fix Attempt Limit**: 单 task 3次 auto-fix 后 STOP → SUMMARY 记录 "Deferred Issues"

### 8.4 Discovery Levels（调研深度）

| Level | 触发条件 | 耗时 | 产出 |
|-------|---------|------|------|
| 0 - Skip | 纯内部工作，现有模式 | 0 | 无 |
| 1 - Quick | Context7 resolve + query | 2-5min | 无 DISCOVERY.md |
| 2 - Standard | 新库/外部集成/选型 | 15-30min | DISCOVERY.md |
| 3 - Deep | 架构决策/长期影响 | 1+hour | Full research |

### 8.5 Stub Tracking（桩代码检测）

**GSD 认为 stub 的模式**:
```
= [] / = {} / = null / = ""  (流向渲染层，且无 fetch/useEffect 覆盖)
"not available" / "coming soon" / "placeholder" / "TODO"
props = {[]} / props = {{}} / props = {null} (调用处硬编码空值)
console.log-only implementation
```

**Verifier 行为**: 发现 stub → 在 VERIFICATION.md 中标记 → plan 不标记为 complete

---

## 9. 与 Claude Code 的集成机制

### 9.1 安装架构

```
clawhub install gsd
  ↓
~/.agents/skills/gsd/
  ├── SKILL.md            # 顶层入口，定义 triggers
  ├── agents/             # 子代理定义 (*.md files)
  ├── commands/           # slash commands (*/SKILL.md wrappers)
  ├── workflows/          # 详细工作流定义 (*.md)
  ├── references/         # 参考文档 (*.md)
  └── templates/          # 文件模板

~/.claude/get-shit-done/  # (符号链接到 ~/.agents/skills/gsd/ 中的子目录)
  ├── bin/gsd-tools.cjs   # CLI 工具
  ├── workflows/
  ├── references/
  └── templates/
```

### 9.2 Slash Command 触发流程

```
用户输入: /gsd:execute-phase 2
  ↓
Claude Code Skill Tool
  ↓
~/.agents/skills/gsd/commands/gsd/execute-phase/SKILL.md
  ↓ (frontmatter: agent: gsd-executor OR process: execute workflow)
  ↓
@~/.claude/get-shit-done/workflows/execute-phase.md (详细 workflow)
  ↓
gsd-tools.cjs init execute-phase → orchestrator spawns gsd-executor subagents
```

### 9.3 Multi-Runtime 工具映射

`gsd-tools.cjs` 中的 `ToolMapper` 将通用工具名映射到各 runtime：

| 通用工具 | Claude Code | Codex | Windsurf |
|---------|-------------|-------|---------|
| Read | Read | read_file | read_file |
| Write | Write | write_file | write_file |
| Bash | Bash | bash | shell |
| Grep | Grep | search | find |

---

## 10. 优缺点分析

### 优点

1. **真正端到端的项目管理**：从立项到 ship 完整覆盖，不是零散工具集合
2.2. **多 runtime 广泛支持**：一个框架覆盖 8 个主流 AI 编程环境
3. **专用 agent 设计**：不是通用 LLM，而是针对每个任务优化的专用 prompt（planner/executor/verifier/debugger 各有不同）
4. **极高的迭代速度**：2026年3月保持每1-3天一个版本的发布节奏
5. **wave-based 执行**：既支持并行效率，又通过 checkpoint 保证可恢复性
6. **Advisor mode**：多头研究 + 权衡分析，真正辅助决策而非盲目执行
7. **Security 意识**：内置 prompt injection 检测、path traversal 防护（validatePath, execFileSync）
8. **国际化**：支持韩语、日语、葡萄牙语文档
9. **Goal-backward verification**：不只看 tasks 是否完成，而是验证 goals 是否达成（存在≠ substantive≠ wired≠ flowing）
10. **Auto-fix 机制**：executor 自动修复 bug/missing功能（Rules 1-3），无需用户干预，只有架构变更才暂停

### 缺点

1. **复杂度极高**：30+ 命令、10+ agents、5级任务结构，学习曲线陡峭
2. **强 opinionated**：高度规范化的流程对某些团队可能过于约束
3. **状态管理依赖文件系统**：`STATE.md`、`PROJECT.md` 的格式漂移可能导致解析失败
4. **对非 GSD 工作流的兼容性差**：一旦进入 GSD 流程，很难中途切换到其他方式
5. **子代理数量爆炸**：一个 execute-phase 可能 spawn 多个子代理，上下文消耗大
6. **Agent 能力受限于模型**：Phase-researcher 需要强模型，executor 需要 Coding 模型，模型选择不当会导致失败
7. **SKILL.md 文件维护成本高**：frontmatter 字段、triggers、agent_type 需要严格一致性
8. **Windows 兼容性持续问题**：8.3 short path、EPERM/EACCES、CRLF frontmatter 腐蚀问题多次出现
9. **Nyquist Compliance 规则过于复杂**：Dimension 8 的 sampling continuity / Wave 0 completeness 增加了 plan-checker 的负担
10. **Checkpoint 返回结构复杂**：executor 产生的 structured checkpoint message 需要 orchestrator 正确解析

---

## 11. 技术债务与已知问题（从 Changelog 推断）

- **Windows 兼容性问题持续出现**：8.3 short path、EPERM/EACCES、CRLF frontmatter 解析腐蚀
- **`jq` 依赖曾被错误地当作 hard dependency**：后移除
- **Codex config.toml corruption**：非 boolean `[features]` keys 导致损坏
- **WSL + Windows Node.js 版本 mismatch 检测**：边界情况未完全覆盖
- **git short SHA collision**：小项目的 phase plan 归档可能有 SHA 冲突风险

---

## 12. 最新版本亮点 (v1.29.0 — 2026-03-25)

- **Windsurf 完整支持**：新增 Codeium runtime
- **Agent skill injection**：可向子代理注入项目特定技能（skill injection）
- **UI-phase / UI-review**：UI 设计专项工作流
- **Security scanning CI**：prompt injection、base64、secret 扫描
- **Portuguese/Korean/Japanese 文档**：国际化扩展
- **Configurable discuss modes**：新增 `assumptions` mode
- **Portuguese 贡献者**：新增贡献者

---

## 13. 关键文件速查

| 文件 | 作用 |
|------|------|
| `~/.agents/skills/gsd/agents/gsd-planner.md` | 最核心的规划 agent (~19KB) |
| `~/.agents/skills/gsd/agents/gsd-executor.md` | 执行的 agent (~16KB) |
| `~/.agents/skills/gsd/agents/gsd-verifier.md` | Goal-backward 验证 (~14KB) |
| `~/.agents/skills/gsd/agents/gsd-plan-checker.md` | Plan 质量检查 (~14KB) |
| `~/.agents/skills/gsd/agents/gsd-debugger.md` | 科学方法调试 (~14KB) |
| `~/.agents/skills/gsd/commands/gsd/execute-phase/SKILL.md` | 执行阶段命令入口 |
| `~/.agents/skills/gsd/commands/gsd/plan-phase/SKILL.md` | 规划阶段命令入口 |
| `~/.agents/skills/gsd/commands/gsd/new-project/SKILL.md` | 新项目命令入口 |
| `~/.agents/skills/gsd/workflows/execute-phase.md` | Wave 并行执行详细工作流 |
| `~/.agents/skills/gsd/workflows/plan-phase.md` | Plan→Check→Revise 循环工作流 |
| `~/.agents/skills/gsd/references/checkpoints.md` | Checkpoint 机制参考 |
| `~/.agents/skills/gsd/references/questioning.md` | Questioning 技术参考 |
| `~/.agents/skills/gsd/references/tdd.md` | TDD 模式参考 |
| `~/.agents/skills/gsd/references/continuation-format.md` | Checkpoint 恢复格式参考 |
| `~/.agents/skills/gsd/references/git-integration.md` | Git 集成参考 |
| `~/.agents/skills/gsd/SKILL.md` | 顶层 Skill 入口 |

---

## 14. PLAN.md 完整示例

```yaml
---
phase: 02-auth
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/auth/jwt.ts
  - src/auth/middleware.ts
  - prisma/schema.prisma
autonomous: true
requirements: [AUTH-01, AUTH-02]
gap_closure: false

must_haves:
  truths:
    - "User can authenticate with email/password"
    - "JWT tokens are stored in httpOnly cookies"
    - "Protected routes reject unauthenticated requests"
  artifacts:
    - path: "src/auth/jwt.ts"
      provides: "JWT creation and validation"
    - path: "src/auth/middleware.ts"
      provides: "Route protection middleware"
    - path: "prisma/schema.prisma"
      provides: "User model with hashed password"
  key_links:
    - from: "middleware.ts"
      to: "jwt.ts"
      via: "validateToken() call"
    - from: "jwt.ts"
      to: "prisma/schema.prisma"
      via: "Prisma User.findUnique()"
---

<objective>
Implement JWT-based authentication with httpOnly cookie storage and route protection middleware.
</objective>

<context>
@.planning/PROJECT.md
@.planning/REQUIREMENTS.md
@.planning/ROADMAP.md
@.planning/phases/02-auth/02-CONTEXT.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: JWT utilities</name>
  <files>src/auth/jwt.ts</files>
  <action>
Create `src/auth/jwt.ts` with:
- `createToken(userId: string): Promise<string>` using jose library
  - Sign RS256 JWT with AUTH_JWT_PRIVATE_KEY env var
  - Include { userId, iat, exp } claims
  - Set expiry to 15 minutes
- `validateToken(token: string): Promise<{userId: string} | null>`
  - Verify signature using AUTH_JWT_PUBLIC_KEY env var
  - Return null if expired or invalid
- Export types: `JwtPayload`, `TokenPair`
</action>
  <verify>
<automated>grep -c "createToken\|validateToken\|sign\|verify" src/auth/jwt.ts</automated>
  </verify>
  <done>createToken returns valid JWT string, validateToken returns payload for valid JWT, null for invalid/expired</done>
</task>

<task type="auto">
  <name>Task 2: Auth middleware</name>
  <files>src/auth/middleware.ts</files>
  <action>
Create `src/auth/middleware.ts`:
- `authMiddleware(req, res, next)` function
- Extract JWT from `req.cookies.auth_token`
- Call validateToken(), attach { userId } to req if valid
- Return 401 if token missing or invalid
- Export `attachUser(req, res, next)` for routes that need userId
</action>
  <verify>
<automated>grep -c "authMiddleware\|attachUser\|validateToken" src/auth/middleware.ts</automated>
  </verify>
  <done>Middleware rejects requests without valid JWT with 401, attaches userId to request object on success</done>
</task>

<task type="checkpoint:human-verify">
  <name>Task 3: Verify locally</name>
  <action>Test the auth flow manually: start server, POST /auth/login, verify httpOnly cookie set, GET /protected route with cookie returns 200, without cookie returns 401</action>
  <done>Manual test passes: login sets cookie, protected route works with cookie, rejects without it</done>
</task>

</tasks>

<success_criteria>
- JWT tokens are cryptographically signed (RS256)
- Tokens expire after 15 minutes
- httpOnly cookie prevents XSS access
- Protected routes return 401 without valid token
</success_criteria>

<output>
After completion, create `.planning/phases/02-auth/02-auth-01-SUMMARY.md`
</output>
```

---

## 15. CHECKPOINT Return 完整示例

```markdown
## CHECKPOINT REACHED

**Type:** human-verify
**Plan:** 02-auth-01
**Progress:** 2/3 tasks complete

### Completed Tasks
| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Task 1: JWT utilities | a3f2b1c | src/auth/jwt.ts |
| 2 | Task 2: Auth middleware | 9d4e8f1 | src/auth/middleware.ts |

### Current Task
**Task 3:** Task 3: Verify locally
**Status:** awaiting verification
**Blocker:** Requires human to run server and test cookie-based auth

### Checkpoint Details
**What was built:**
- JWT creation with RS256 signing (15min expiry)
- httpOnly cookie storage
- Route protection middleware
- Prisma schema with bcrypt password hashing

**Manual verification needed:**
1. `npm run dev` to start server
2. `curl -X POST http://localhost:3000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"test123"}' \
     -c cookies.txt`
3. Verify `auth_token` appears in cookies.txt with httpOnly flag
4. `curl http://localhost:3000/api/protected -b cookies.txt` → should return 200
5. `curl http://localhost:3000/api/protected` (no cookie) → should return 401

### Awaiting
Run the 5 verification steps above and report results here.
Once verified, reply "APPROVED" and execution will continue.
If issues found, describe them and execution will create fix plans.
```

---

## 16. Executor Subagent Prompt 关键片段

```yaml
# Frontmatter
name: gsd-executor
description: >
  Executes GSD plans with atomic commits, deviation handling,
  checkpoint protocols, and state management.
tools: Read, Write, Edit, Bash, Grep, Glob
permissionMode: acceptEdits
color: yellow

# Core responsibility block
<role>
You are a GSD executor. You implement plan prompts exactly.

**CRITICAL: Mandatory Initial Read**
If the prompt contains a <files_to_read> block, you MUST use
the Read tool to load every file listed before any other action.
</role>

# Execution context reference
<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/references/ui-brand.md
</execution_context>

# Auto-fix deviation rules
<deviation_rules>
**Auto-fix (no approval needed):**
1. Code doesn't work → auto-fix the bug
2. Missing functionality (no error handling, no validation) → add it
3. Blocking issue (missing dep, type error, broken link) → fix it

**Stop and ask (requires approval):**
4. Architectural change → STOP, checkpoint:decision

**Fix limit:** 3 attempts per task, then STOP
</deviation_rules>

# Checkpoint protocol
<checkpoint_protocol>
When task.type = "checkpoint:*":
1. HALT execution immediately
2. Output structured checkpoint message (see format above)
3. Include <completed_tasks> block with git commit hashes
4. Include <resume_point> with next action
5. Do NOT continue until continuation prompt received
</checkpoint_protocol>

# Task commit rules
<commit_rules>
1. One logical change per commit
2. git add <specific_file> (never git add .)
3. Message format: {type}({phase}-{plan}): {description}
   - type: feat | fix | test | refactor | chore | docs
4. If auto mode: auto-commit after each task
5. If interactive mode: commit after user approval
</commit_rules>
```

