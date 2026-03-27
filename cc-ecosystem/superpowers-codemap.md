# Superpowers (obra/superpowers) Code Map

> Claude Code 开发方法论框架。GitHub: https://github.com/obra/superpowers
> 当前版本: v5.0.6 (2026-03-24)
> 架构: Agent Skill System（无中心服务器，Skills驱动工作流）

---

## 目录

1. [核心架构](#1-核心架构)
2. [核心技能速查](#2-核心技能速查)
3. [brainstorming 技能详解](#3-brainstorming-技能详解)
4. [writing-plans 技能详解](#4-writing-plans-技能详解)
5. [subagent-driven-development 技能详解](#5-subagent-driven-development-技能详解)
6. [executing-plans 技能详解](#6-executing-plans-技能详解)
7. [finishing-a-development-branch 技能详解](#7-finishing-a-development-branch-技能详解)
8. [systematic-debugging 技能详解](#8-systematic-debugging-技能详解)
9. [using-git-worktrees 技能详解](#9-using-git-worktrees-技能详解)
10. [brainstorming-server 详解](#10-brainstorming-server-详解)
11. [Inline Self-Review 机制（v5.0.6）](#11-inline-self-review-机制v506)
12. [Controller-Worker Subagent 模式](#12-controller-worker-subagent-模式)
13. [关键数据结构和接口](#13-关键数据结构和接口)
14. [各技能文件路径](#14-各技能文件路径)
15. [版本历史关键变更](#15-版本历史关键变更)

---

## 1. 核心架构

### 1.1 设计哲学

```
Superpowers = Skills（技能定义）+ 强制工作流（DOT流程图）+ 护栏（Red Flags/Gates）
```

- **Skills 是核心**：所有工作流程都封装为可复用的 Skill 文件
- **DOT 流程图作为规范**：技能中的 DOT 图是执行的权威定义，不是装饰
- **Checklist 强制依从**：关键技能使用强制任务清单（如 TodoWrite one-per-item）
- **Gates 阻止绕过**：`<HARD-GATE>` 强制停止某些行为，不可跳过
- **无中心服务器**：轻量级 shim plugin，仅负责 bootstrap 和 session-start hook
- **Skills 独立版本化**：Skills 在独立仓库，plugin 自动更新

### 1.2 核心文件布局

```
superpowers/
├── hooks/
│   └── session-start          # Session 启动时注入 context（polyglot脚本）
├── skills/
│   ├── using-superpowers/     # 入口技能：何时/如何调用其他技能
│   ├── brainstorming/         # 构思 → 设计阶段
│   │   ├── SKILL.md
│   │   ├── visual-companion.md
│   │   ├── scripts/
│   │   │   ├── server.cjs     # Brainstorm Server（零依赖）
│   │   │   ├── start-server.sh
│   │   │   ├── stop-server.sh
│   │   │   ├── frame-template.html
│   │   │   └── helper.js
│   │   ├── spec-document-reviewer-prompt.md  # (已废弃，v5.0.6改为inline)
│   │   └── spec-self-review-checklist.md    # (v5.0.6新增)
│   ├── writing-plans/         # 设计 → 实现计划阶段
│   │   ├── SKILL.md
│   │   ├── plan-document-reviewer-prompt.md  # (已废弃，v5.0.6改为inline)
│   │   └── plan-self-review-checklist.md    # (v5.0.6新增)
│   ├── subagent-driven-development/  # Subagent驱动执行
│   │   ├── SKILL.md
│   │   ├── implementer-prompt.md
│   │   ├── spec-reviewer-prompt.md
│   │   └── code-quality-reviewer-prompt.md
│   ├── executing-plans/       # 同一会话内顺序执行
│   │   └── SKILL.md
│   ├── finishing-a-development-branch/  # 收尾合并
│   │   └── SKILL.md
│   ├── systematic-debugging/   # Bug调查四阶段法
│   │   ├── SKILL.md
│   │   ├── root-cause-tracing.md
│   │   ├── defense-in-depth.md
│   │   └── condition-based-waiting.md
│   ├── using-git-worktrees/   # Git worktree 隔离工作区
│   │   └── SKILL.md
│   ├── requesting-code-review/ # 代码审查
│   │   └── code-reviewer.md
│   └── test-driven-development/
│       └── ...
├── commands/                   # 斜杠命令（已废弃，重定向到skills）
│   ├── brainstorm.md
│   └── write-plan.md
├── agents/                     # Agent 定义文件
│   └── code-reviewer.md
├── docs/
│   └── superpowers/
│       ├── specs/             # 设计文档输出位置
│       └── plans/             # 实现计划输出位置
└── RELEASE-NOTES.md
```

### 1.3 工作流总体流程

```
用户需求
    │
    ▼
┌─────────────────┐
│ brainstorming  │ ← 强制入口（<HARD-GATE> 禁止在设计批准前实现）
│  构思 → 设计    │
└────────┬────────┘
         │ 输出: docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md
         ▼
┌─────────────────┐
│ writing-plans   │ ← 把设计变成可执行计划
│  设计 → 计划     │
└────────┬────────┘
         │ 输出: docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md
         ▼
┌──────────────────────────────────────────────────┐
│ subagent-driven-development  ← 推荐（subagent-capable平台）   │
│  OR                                              │
│ executing-plans              ← 备选（无subagent平台）          │
│  计划 → 实现                                      │
└────────┬─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ finishing-a-development-branch │
│  验证 → 合并/PR/保留/丢弃      │
└─────────────────────────────┘
```

---

## 2. 核心技能速查

| 技能名称 | 文件 | 触发条件 | 核心约束 |
|---------|------|---------|---------|
| `using-superpowers` | `skills/using-superpowers/SKILL.md` | **每个会话必须**（session-start hook自动注入） | 1%规则、Red Flags拦截 |
| `brainstorming` | `skills/bstorming/SKILL.md` | 任何创造性工作（功能/组件/行为修改） | `<HARD-GATE>` 禁止实现直到设计批准 |
| `writing-plans` | `skills/writing-plans/SKILL.md` | 有spec/需求的多步骤任务 | 必须TDD、No Placeholders |
| `subagent-driven-development` | `skills/subagent-driven-development/SKILL.md` | 有实现计划+任务独立+在同一会话 | 必需git worktree |
| `executing-plans` | `skills/executing-plans/SKILL.md` | 有实现计划+无subagent支持 | 必需git worktree |
| `finishing-a-development-branch` | `skills/finishing-a-development-branch/SKILL.md` | 实现完成+测试通过 | 4选项结构化收尾 |
| `systematic-debugging` | `skills/systematic-debugging/SKILL.md` | 任何bug/测试失败/异常行为 | 铁律：根因调查先于修复 |
| `using-git-worktrees` | `skills/using-git-worktrees/SKILL.md` | 开始feature工作/执行实现计划前 | 必需验证.gitignore |
| `requesting-code-review` | `skills/requesting-code-review/SKILL.md` | 代码审查请求 | 使用`superpowers:code-reviewer` agent |

---

## 3. brainstorming 技能详解

### 3.1 技能元数据

```yaml
name: brainstorming
description: "You MUST use this before any creative work - creating features,
              building components, adding functionality, or modifying behavior.
              Explores user intent, requirements and design before implementation."
```

### 3.2 `<HARD-GATE>` 强制机制

```
<HARD-GATE>
Do NOT invoke any implementation skill, write any code, scaffold any project,
or take any implementation action until you have presented a design and the
user has approved it. This applies to EVERY project regardless of perceived simplicity.
</HARD-GATE>
```

**机制说明**：
- `<HARD-GATE>` 是一个字面标记，不是配置项
- 模型在执行任何创造性工作前必须检查此块
- 违反此规则被视为严重过程违规
- 适用于所有项目，包括"简单"任务（Anti-Pattern 明确指出："simple" projects are where unexamined assumptions cause the most wasted work）
- **唯一出口**：向用户展示设计并获得批准

### 3.3 强制 Checklist（TodoWrite 逐项完成）

Agent 必须为以下每项创建 TodoWrite 并按顺序完成：

```
1. Explore project context — check files, docs, recent commits
2. Offer visual companion (if topic will involve visual questions) — 独立消息，不混合其他内容
3. Ask clarifying questions — 一次一个问题
4. Propose 2-3 approaches — 含权衡和推荐
5. Present design — 按复杂度缩放各节，每节后询问是否正确
6. Write design doc — 保存到 docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md 并提交
7. Spec self-review — 快速内联检查（见3.5节）
8. User reviews written spec — 让用户审阅spec文件后再继续
9. Transition to implementation — 调用 writing-plans skill
```

### 3.4 详细执行流程（Step by Step）

```
Step 1: 接收用户请求
   ↓
Step 2: 探索项目上下文
   - 检查文件结构、docs、近期commits
   - 评估范围：如果请求描述多个独立子系统，立即标记（不要花时间细化细节）
   - 如果项目太大，分解为子项目
   ↓
Step 3: 视觉问题评估
   - "Visual questions ahead?" 决策点
   - 如果是 → 发送独立的 Visual Companion 提议消息（不含其他内容）
   - 等待用户响应后再继续
   ↓
Step 4: 逐个提出澄清问题（一次一个）
   - 理解：目的、约束、成功标准
   - 优选多选题，但开放式也可
   - 只问必要问题
   ↓
Step 5: 提出 2-3 种方案（含权衡）
   - 对话式呈现，带推荐和理由
   - 先给出推荐选项
   ↓
Step 6: 展示设计（分段按复杂度）
   - 每个 section 后询问"看起来对吗？"
   - 覆盖：架构、组件、数据流、错误处理、测试
   - 准备好返回澄清
   ↓
Step 7: 写设计文档
   - 写入 docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md
   - git commit
   ↓
Step 8: Spec Self-Review（内联，见3.5）
   - 发现问题即时修复
   ↓
Step 9: 用户审阅 Gate
   - "Spec written and committed to <path>. Please review..."
   - 等待用户响应
   - 如果需要更改 → 修改 → 重新审阅
   ↓
Step 10: 调用 writing-plans skill（唯一合法出口）
```

### 3.5 Spec Self-Review Checklist（v5.0.6 Inline 版本）

**执行时机**：设计文档写完后、提交前

**检查项**：
```
1. Placeholder scan
   - 任何 "TBD"、"TODO"、不完整section或模糊需求？
   - 如有 → 立即修复

2. Internal consistency
   - 各section是否相互矛盾？
   - 架构描述是否与功能描述一致？
   - 如有 → 立即修复

3. Scope check
   - 是否足够聚焦于单个实现计划？
   - 是否需要进一步分解？
   - 如有 → 修复

4. Ambiguity check
   - 是否有需求可被两种方式解释？
   - 如有 → 选择一种并明确化
```

**特点**：
- 在同一上下文中内联执行，无需子agent调度
- 耗时约30秒（vs 原来 subagent loop 的~25分钟）
- 回归测试：5个版本×5次trial，质量分数与subagent loop无显著差异
- 发现 3-5 个真实 bug per run

### 3.6 关键 Anti-Pattern

```
Anti-Pattern: "This Is Too Simple To Need A Design"

Every project goes through this process. A todo list, a single-function
utility, a config change — all of them.

"Simple" projects are where unexamined assumptions cause the most
wasted work.

The design can be short (a few sentences for truly simple projects),
but you MUST present it and get approval.
```

### 3.7 Visual Companion

**何时使用**：
- 视觉内容（mockups、layouts、diagrams）→ 浏览器
- 文本内容（requirements、concepts、tradeoffs）→ 终端

**每问题决策**：不是"关于UI的问题"就自动是视觉问题
- "What does personality mean in this context?" → 概念问题 → 终端
- "Which wizard layout works better?" → 视觉问题 → 浏览器

---

## 4. writing-plans 技能详解

### 4.1 技能元数据

```yaml
name: writing-plans
description: "Use when you have a spec or requirements for a multi-step task,
              before touching code"
```

### 4.2 计划文档强制 Header

```markdown
# [Feature Name] Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

### 4.3 详细执行流程（Step by Step）

```
Step 1: 阅读 spec 文件
   ↓
Step 2: Scope Check
   - 如果 spec 覆盖多个独立子系统
   - 建议分解为多个计划（每个子系统一个）
   - 每个计划应产生可独立测试的软件
   ↓
Step 3: 映射文件结构（在定义任务之前）
   - 每个文件的职责是什么？
   - 设计单元边界清晰
   - 文件按职责拆分，非按技术层
   - 遵循既有代码库模式
   ↓
Step 4: 分解任务（Bite-Sized）
   - 每个步骤 = 一个动作（2-5分钟）
   - 典型模式：
     * "Write the failing test" - step
     * "Run it to make sure it fails" - step
     * "Write minimal implementation" - step
     * "Run tests to verify they pass" - step
     * "Commit" - step
   ↓
Step 5: 对每个 Task 填写
   - **Files:**
     * Create: exact/path/to/file.py
     * Modify: exact/path/to/existing.py:123-145
     * Test: tests/exact/path/to/test.py
   - **Steps** (使用 `- [ ]` checkbox 语法)
   ↓
Step 6: Self-Review（内联，v5.0.6，见4.4）
   ↓
Step 7: 执达方式选择
   - "Plan complete... Two execution options:
     1. Subagent-Driven (recommended)
     2. Inline Execution"
   ↓
Step 8: 根据选择调用对应 skill
   - Subagent-Driven → superpowers:subagent-driven-development
   - Inline → superpowers:executing-plans
```

### 4.4 Plan Self-Review Checklist（v5.0.6 Inline 版本）

**执行时机**：完整计划写完后

```
1. Spec coverage
   - 浏览spec的每个section/需求
   - 能否指出实现它的任务？
   - 列出任何缺口

2. Placeholder scan
   - 搜索 plan 中的红旗模式：
     * "TBD", "TODO", "implement later", "fill in details"
     * "Add appropriate error handling" / "add validation" / "handle edge cases"
     * "Write tests for the above"（无实际测试代码）
     * "Similar to Task N"（重复代码，工程师可能按任意顺序阅读）
     * 描述做什么但不展示怎么做的步骤（代码步骤必须有代码块）

3. Type consistency
   - 早期任务定义的类型/方法签名/属性名
   - 与后期任务中使用的是否一致？
   - 例：Task 3 中是 `clearLayers()` 但 Task 7 中是 `clearFullLayers()`
```

### 4.5 No Placeholders 规则

**计划失败（Plan Failures）**——以下情况绝不能出现：
- "TBD"、"TODO"、"implement later"、"fill in details"
- "Add appropriate error handling" / "add validation" / "handle edge cases"（无具体说明）
- "Write tests for the above"（无实际测试代码）
- "Similar to Task N"（重复代码——工程师可能乱序阅读任务）
- 描述做什么但不展示怎么做的步骤（代码步骤必须有代码块）
- 引用未在任何任务中定义的类型/函数/方法

---

## 5. subagent-driven-development 技能详解

### 5.1 技能元数据

```yaml
name: subagent-driven-development
description: "Use when executing implementation plans with independent tasks
              in the current session"
```

### 5.2 核心原理

```
Fresh subagent per task + two-stage review (spec compliance → quality)
= high quality, fast iteration
```

**为什么用 subagent**：
- 将任务委托给专业agent，隔离上下文
- 精确构建指令和上下文，确保专注和成功
- Subagent 永远不继承当前 session 的上下文或历史
- Controller 构造它们所需的精确信息
- 这也保留了 Controller 自己用于协调工作的上下文

### 5.3 详细执行流程（Step by Step）

```
Phase 0: 初始化
Step 0.1: 阅读计划文件（一次）
Step 0.2: 提取所有任务及完整文本和上下文
Step 0.3: 创建 TodoWrite（所有任务）
Step 0.4: 确认 git worktree 已设置（必需）
   → 如未设置，调用 using-git-worktrees skill
   ↓

Phase 1: 任务循环（对每个未完成任务）
   ↓
   Step 1.1: 获取任务文本和上下文（已提取）
   ↓
   Step 1.2: 派发 Implementer subagent
   ↓
   Step 1.3: Implementer 提问？
       - 是 → 回答问题，提供上下文
       - 否 → 继续实现
   ↓
   Step 1.4: Implementer 实现、测试、提交、self-review
   ↓
   Step 1.5: Implementer 报告状态
       - DONE → 进入 Step 1.6
       - DONE_WITH_CONCERNS → 读concerns，如有严重问题先解决，否则继续 Step 1.6
       - NEEDS_CONTEXT → 提供缺失上下文，re-dispatch
       - BLOCKED → 评估blocker类型：
           * 上下文问题 → 提供更多上下文，re-dispatch 同模型
           * 需要更多推理 → re-dispatch 更强模型
           * 任务太大 → 拆分为更小部分
           * 计划本身错误 → 升级给人类
   ↓
   Step 1.6: 派发 Spec Reviewer subagent
   ↓
   Step 1.7: Spec Reviewer 检查代码 vs spec
       - 通过 → 进入 Step 1.8
       - 未通过 → Implementer 修复问题
       - 重新派发 Spec Reviewer 审查
       - 重复直到通过（最多3次迭代）
   ↓
   Step 1.8: 派发 Code Quality Reviewer subagent
   ↓
   Step 1.9: Code Quality Reviewer 审查
       - 通过 → 进入 Step 1.10
       - 未通过 → Implementer 修复问题
       - 重新派发 Code Quality Reviewer
       - 重复直到通过
   ↓
   Step 1.10: 在 TodoWrite 中标记任务完成
   ↓
   Step 1.11: 还有更多任务？
       - 是 → 返回 Step 1.1
       - 否 → 进入 Phase 2
   ↓

Phase 2: 最终审查
   Step 2.1: 派发 Final Code Reviewer（整个实现）
   ↓
   Step 2.2: Final Reviewer 审查
   ↓
   Step 2.3: 调用 finishing-a-development-branch skill
```

### 5.4 两阶段 Review 机制

#### Stage 1: Spec Compliance Review（spec-reviewer-prompt.md）

**目的**：验证实现与规范完全匹配（不多不少）

**关键原则**：
```
CRITICAL: Do Not Trust the Report
- Implementer 快速完成 → 报告可能不完整、不准确或过于乐观
- 必须独立验证一切
```

**审查项**：
```
Missing requirements:
  - 是否实现了所有被要求的内容？
  - 是否有被跳过或遗漏的要求？
  - 他们声称有效但实际未实现的东西？

Extra/unneeded work:
  - 是否构建了未要求的东西？
  - 是否过度工程化或添加了不必要的功能？
  - 是否添加了 spec 中没有的"nice to haves"？

Misunderstandings:
  - 是否以不同于预期的方式解释需求？
  - 是否解决了错误的问题？
  - 是否实现了正确的功能但方式不对？
```

**报告格式**：
```
✅ Spec compliant（如果检查代码后一切匹配）
❌ Issues found: [具体列出缺少或额外的内容，带 file:line 引用]
```

#### Stage 2: Code Quality Review（code-quality-reviewer-prompt.md）

**目的**：验证实现构建良好（干净、可测试、可维护）

**前提**：必须 Spec Compliance 通过后才能派发

**额外检查项**（除标准代码审查外）：
```
- 每个文件是否有单一明确职责和良好定义的接口？
- 单元是否分解为可独立理解和测试？
- 实现是否遵循计划中的文件结构？
- 此实现是否创建了已经很大的新文件，或显著增长了现有文件？
  （不要标记既有文件大小——只关注此变更贡献的部分）
```

**报告格式**：
```
Strengths
Issues
  Critical (Must Fix)
  Important (Should Fix)
  Minor (Nice to Have)
Assessment: Ready to merge? Yes/No/With fixes
```

### 5.5 Implementer 子agent Prompt 模板

**关键字段**：
```
Task tool (general-purpose):
  description: "Implement Task N: [task name]"
  prompt: |
    You are implementing Task N: [task name]

    ## Task Description
    [FULL TEXT of task from plan - 直接粘贴，不让 subagent 读文件]

    ## Context
    [场景设置：任务位置、依赖、架构上下文]

    ## Before You Begin
    [如果有问题现在就问——在开始工作前提起任何concerns]

    ## Your Job
    1. 实现任务具体内容
    2. 写测试（如果任务说TDD就按TDD）
    3. 验证实现有效
    4. 提交你的工作
    5. Self-review（见下方）
    6. 报告

    Work from: [directory]

    ## Self-Review Checklist
    Completeness:
      - 我是否完全实现了spec中的所有内容？
      - 我是否遗漏了任何需求？
      - 是否有我未处理的边界情况？

    Quality:
      - 这是我最好的工作吗？
      - 名称是否清晰准确？
      - 代码是否干净可维护？

    Discipline:
      - 我是否避免过度构建（YAGNI）？
      - 我是否只构建了被要求的内容？
      - 我是否遵循了代码库既有模式？

    Testing:
      - 测试是否实际验证行为（不只是mock行为）？
      - 我是否按要求遵循TDD？
      - 测试是否全面？

    ## Report Format
    Status: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
    [报告实现内容、测试结果、文件变更、自我审查结果]
```

### 5.6 Model Selection 策略

```
机械实现任务（隔离函数、清晰spec、1-2文件）
  → 使用快速、便宜的模型

集成和判断任务（多文件协调、模式匹配、调试）
  → 使用标准模型

架构、设计和审查任务
  → 使用最强可用模型

Task complexity signals:
  - 触及1-2文件+完整spec → 便宜模型
  - 触及多文件+集成相关 → 标准模型
  - 需要设计判断或广泛代码库理解 → 最强模型
```

### 5.7 Status 协议

```
DONE:
  → 进入 spec compliance review

DONE_WITH_CONCERNS:
  → 读concerns
  → 如果关于正确性或范围：先解决再审查
  → 如果是观察（如"this file is getting large"）：记录并继续审查

NEEDS_CONTEXT:
  → 提供缺失上下文
  → Re-dispatch

BLOCKED:
  → 评估blocker类型：
     * 上下文问题 → 提供更多上下文，re-dispatch 同模型
     * 需要更多推理 → re-dispatch 更强模型
     * 任务太大 → 拆分为更小
     * 计划错误 → 升级给人类
```

---

## 6. executing-plans 技能详解

### 6.1 技能元数据

```yaml
name: executing-plans
description: "Use when you have a written implementation plan to execute
              in a separate session with review checkpoints"
```

### 6.2 与 subagent-driven-development 的区别

| 特性 | subagent-driven | executing-plans |
|------|----------------|-----------------|
| 会话 | 同一会话（无上下文切换） | 单独会话 |
| Subagent | 每个任务新鲜 subagent | 顺序执行 |
| Review | 每任务两次 review | 无自动review |
| 速度 | 快（无人在环） | 慢（人类参与） |
| 质量 | 高 | 中 |
| 适用平台 | Claude Code/Codex（subagent-capable） | 无subagent平台 |

### 6.3 详细执行流程（Step by Step）

```
Step 1: 加载和审阅计划
   1.1: 读取计划文件
   1.2: 批判性审阅——识别任何问题或concerns
   1.3: 如有concerns → 先向人类合作伙伴提出
   1.4: 如无concerns → 创建 TodoWrite 并继续
   ↓

Step 2: 执行任务（顺序）
   对每个任务：
   2.1: 标记为 in_progress
   2.2: 严格按计划每个步骤执行
   2.3: 按规定运行验证
   2.4: 标记为 completed
   ↓

Step 3: 完成开发
   3.1: 调用 finishing-a-development-branch skill
   ↓

遇到以下情况立即停止并请求帮助：
   - 遇到blocker（缺失依赖、测试失败、指令不清）
   - 计划有阻止开始的重大缺口
   - 不理解某条指令
   - 验证反复失败
```

### 6.4 注意

**注意**：此 skill 告知用户 Superpowers 在有 subagent 支持的平台上效果更好。如果 subagent 可用，应使用 `subagent-driven-development`。

---

## 7. finishing-a-development-branch 技能详解

### 7.1 技能元数据

```yaml
name: finishing-a-development-branch
description: "Use when implementation is complete, all tests pass, and you
              need to decide how to integrate the work"
```

### 7.2 详细执行流程（Step by Step）

```
Step 1: 验证测试
   运行项目测试套件
   - 如失败 → 列出失败，不进入 Step 2
   - 如通过 → 继续 Step 2
   ↓

Step 2: 确定基础分支
   git merge-base HEAD main (或 master)
   ↓

Step 3: 呈现4个结构化选项
   "Implementation complete. What would you like to do?

   1. Merge back to <base-branch> locally
   2. Push and create a Pull Request
   3. Keep the branch as-is (I'll handle it later)
   4. Discard this work

   Which option?"
   ↓

Step 4: 执行选择
   选项1 (Merge Locally):
     git checkout <base>
     git pull
     git merge <feature>
     <run tests>
     git branch -d <feature>
     → 清理 worktree

   选项2 (PR):
     git push -u origin <feature>
     gh pr create --title ... --body ...
     → 保留 worktree

   选项3 (Keep):
     报告 worktree 位置
     → 不清理 worktree

   选项4 (Discard):
     先确认："Type 'discard' to confirm"
     git checkout <base>
     git branch -D <feature>
     → 清理 worktree
```

### 7.3 关键约束

```
Never:
  - 测试失败时继续
  - 不验证测试就合并
  - 不确认就删除工作
  - 未经明确请求就 force-push

Always:
  - 选项前验证测试
  - 呈现精确的4个选项
  - 选项4要求输入"discard"确认
  - 仅对选项1和4清理worktree
```

---

## 8. systematic-debugging 技能详解

### 8.1 技能元数据

```yaml
name: systematic-debugging
description: "Use when encountering any bug, test failure, or unexpected
              behavior, before proposing fixes"
```

### 8.2 铁律

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

### 8.3 四阶段流程（Step by Step）

```
Phase 1: Root Cause Investigation
  1.1: 仔细阅读错误信息
       - 不要跳过错误或警告
       - 它们通常包含确切解决方案
       - 完整阅读stack traces
       - 记录行号、文件路径、错误码

  1.2: 稳定复现
       - 能可靠触发吗？
       - 确切步骤是什么？
       - 是否每次都发生？
       - 如不可复现 → 收集更多数据，不要猜测

  1.3: 检查近期变更
       - 什么变更可能导致此问题？
       - Git diff，近期 commits
       - 新依赖、配置变更
       - 环境差异

  1.4: 多组件系统收集证据
       （系统有多个组件时：CI→build→signing、API→service→database）
       在提出修复之前：
       对每个组件边界：
         - 记录进入组件的数据
         - 记录离开组件的数据
         - 验证环境/配置传播
         - 检查每层状态
       运行一次收集证据显示哪里break
       然后分析证据识别失败组件
       然后调查该特定组件

  1.5: Trace Data Flow（深度调用栈时）
       从 root-cause-tracing.md 查看完整技术

  *** 只有完成 Phase 1 才能进入 Phase 2 ***

Phase 2: Pattern Analysis
  2.1: 找工作中的类似例子
       - 同一代码库中找类似工作的代码

  2.2: 对比参考实现
       - 如实现模式，阅读参考完整实现
       - 不要略读——每一行都读

  2.3: 识别差异
       - 工作和break之间有什么不同？
       - 列出每个差异，无论多小

  2.4: 理解依赖
       - 此组件还需要什么？
       - 需要什么设置、配置、环境？
       - 它做什么假设？

Phase 3: Hypothesis and Testing
  3.1: 形成单一假设
       - 清晰陈述："我认为X是根本原因因为Y"

  3.2: 最小化测试
       - 做最小可能变更来测试假设
       - 一次一个变量
       - 不要一次修复多个

  3.3: 验证后再继续
       - 有效 → Phase 4
       - 无效 → 形成新假设
       - 不要在顶部加更多修复

Phase 4: Implementation
  4.1: 创建失败测试用例
       - 最简单的复现
       - 可自动化测试最好
       - 修复前必须有

  4.2: 实现单一修复
       - 解决已识别的根本原因
       - 一次一个变更
       - 无"顺便改进"

  4.3: 验证修复
       - 测试现在通过？
       - 其他测试没break？
       - 问题确实解决？

  4.4: 如修复无效
       - STOP
       - 数：我尝试了多少修复？
       - 如 < 3：返回 Phase 1，用新信息重新分析
       - 如 ≥ 3：STOP 并质疑架构（Step 4.5）

  4.5: 如3+修复失败：质疑架构
       指示架构问题的模式：
       - 每个修复在不同地方揭示新共享状态/耦合/问题
       - 修复需要"大规模重构"才能实现
       - 每个修复在其他地方产生新症状
       → STOP 并质疑基本原则
       → 与人类合作伙伴讨论后再尝试更多
```

---

## 9. using-git-worktrees 技能详解

### 9.1 技能元数据

```yaml
name: using-git-worktrees
description: "Use when starting feature work that needs isolation from current
              workspace or before executing implementation plans"
```

### 9.2 详细执行流程（Step by Step）

```
Step 1: 目录选择（优先级顺序）
   1.1: 检查现有目录
        ls -d .worktrees 2>/dev/null    # 优先（隐藏）
        ls -d worktrees 2>/dev/null     # 备选
        找到 → 使用它

   1.2: 检查 CLAUDE.md
        grep -i "worktree.*director" CLAUDE.md
        有偏好 → 无条件使用

   1.3: 询问用户
        "No worktree directory found. Where should I create worktrees?
         1. .worktrees/ (project-local, hidden)
         2. ~/.config/superpowers/worktrees/<project-name>/ (global)
         Which?"

Step 2: 安全验证（项目本地目录）
   2.1: 检查目录是否被 gitignore
        git check-ignore -q .worktrees
        或 git check-ignore -q worktrees

   2.2: 如 NOT ignored
        立即修复：
        - 添加到 .gitignore
        - git commit
        - 继续 worktree 创建

Step 3: 创建 Worktree
   3.1: 检测项目名
        project=$(basename "$(git rev-parse --show-toplevel)")

   3.2: 创建 worktree
        git worktree add "$path" -b "$branch_name"
        cd "$path"

Step 4: 运行项目设置（自动检测）
   Node.js: if [ -f package.json ]; then npm install; fi
   Rust:    if [ -f Cargo.toml ]; then cargo build; fi
   Python:  if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
   Go:      if [ -f go.mod ]; then go mod download; fi

Step 5: 验证干净基线
   运行测试确保 worktree 起始干净
   - 如测试失败 → 报告失败，询问是否继续或调查
   - 如测试通过 → 报告就绪

Step 6: 报告位置
   "Worktree ready at <full-path>
    Tests passing (<N> tests, 0 failures)
    Ready to implement <feature-name>"
```

---

## 10. Brainstorm Server 详解

### 10.1 零依赖实现（v5.0.2+）

**文件**：`skills/brainstorming/scripts/server.cjs`

**依赖**：仅 Node.js 内置模块
```javascript
const crypto = require('crypto');  // 内置
const http = require('http');       // 内置
const fs = require('fs');           // 内置
const path = require('path');       // 内置
```

### 10.2 核心架构

```
HTTP 服务器（Node.js 内置 http 模块）
    │
    ├── GET /            → 服务最新 HTML screen
    ├── GET /files/<f>   → 服务 content/ 下的文件
    └── WebSocket Upgrade → 用户事件（点击选择）
                              │
                              └── 写入 state/events（JSONL）

文件监控（Node.js 内置 fs.watch）
    └── content/ 目录变化 → broadcast reload 到所有 WebSocket 客户端
```

### 10.3 WebSocket 协议实现（RFC 6455）

**手工实现，无 ws 等第三方库**：
```javascript
// 帧编码
function encodeFrame(opcode, payload) {
  const fin = 0x80;
  const len = payload.length;
  let header;
  if (len < 126) {
    header = Buffer.alloc(2);
    header[0] = fin | opcode;
    header[1] = len;
  } else if (len < 65536) {
    header = Buffer.alloc(4);
    header[0] = fin | opcode;
    header[1] = 126;
    header.writeUInt16BE(len, 2);
  } else {
    header = Buffer.alloc(10);
    header[0] = fin | opcode;
    header[1] = 127;
    header.writeBigUInt64BE(BigInt(len), 2);
  }
  return Buffer.concat([header, payload]);
}

// 帧解码
function decodeFrame(buffer) {
  const secondByte = buffer[1];
  const opcode = buffer[0] & 0x0F;
  const masked = (secondByte & 0x80) !== 0;
  // ... 解码逻辑
}
```

### 10.4 服务启动流程（start-server.sh）

```bash
# 1. 解析参数
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR=""
FOREGROUND="false"
BIND_HOST="127.0.0.1"

# 2. 自动检测需要 foreground 的环境
#    - Codex CI (CODEX_CI env var)
#    - Windows/Git Bash (OSTYPE=msys*|cygwin*|mingw*, MSYSTEM env var)
if [[ -n "${CODEX_CI:-}" ]]; then FOREGROUND="true"; fi
case "${OSTYPE:-}" in
  msys*|cygwin*|mingw*) FOREGROUND="true" ;;
esac

# 3. 生成唯一 session 目录
SESSION_ID="$$-$(date +%s)"
SESSION_DIR="${PROJECT_DIR}/.superpowers/brainstorm/${SESSION_ID}"

# 4. 解析 Owner PID（grandparent of this script）
#    $PPID = ephemeral shell running this script (dies when script exits)
#    Owner PID = $PPID's parent (the actual harness)
OWNER_PID="$(ps -o ppid= -p "$PPID" 2>/dev/null | tr -d ' ')"

# 5. 启动 server
#    Foreground: 直接运行
#    Background: nohup + disown
env BRAINSTORM_DIR="$SESSION_DIR" \
    BRAINSTORM_HOST="$BIND_HOST" \
    BRAINSTORM_URL_HOST="$URL_HOST" \
    BRAINSTORM_OWNER_PID="$OWNER_PID" \
    node server.cjs

# 6. 输出 JSON 连接信息
#    {"type":"server-started","port":52341,
#     "url":"http://localhost:52341",
#     "screen_dir":"/path/to/content",
#     "state_dir":"/path/to/state"}
```

### 10.5 Owner PID 生命周期管理

```javascript
function ownerAlive() {
  if (!ownerPid) return true;
  try {
    process.kill(ownerPid, 0);  // 信号0 = 检查进程是否存在
    return true;
  } catch (e) {
    return e.code === 'EPERM';  // EPERM = 有权限但进程存在
  }
}

// 启动时验证：若owner已死（EPERM以外错误），禁用监控
if (ownerPid) {
  try { process.kill(ownerPid, 0); }
  catch (e) {
    if (e.code !== 'EPERM') {
      ownerPid = null;  // 禁用owner监控，仅靠idle timeout
    }
  }
}

// 每60秒检查
const lifecycleCheck = setInterval(() => {
  if (!ownerAlive()) shutdown('owner process exited');
  else if (Date.now() - lastActivity > 30*60*1000) shutdown('idle timeout');
}, 60 * 1000);
```

### 10.6 Session 目录结构（v5.0.6 重构）

```
session_dir/
├── content/          # Agent 写入 HTML，HTTP 服务给浏览器
│   ├── platform.html
│   ├── layout.html
│   └── layout-v2.html
└── state/            # Server 状态和用户交互（不再通过HTTP暴露）
    ├── server-info       # {"type":"server-started",...}
    ├── server-stopped    # {"type":"server-stopped",...}
    ├── server.pid        # Server PID
    ├── server.log        # Server stdout/stderr
    └── events            # 用户浏览器点击事件（JSONL）
```

### 10.7 Visual Companion 内容循环

```
Agent                    Browser                    User
  │                          │                        │
  │ Write HTML to content/   │                        │
  │────── Write tool ───────→│                        │
  │                          │                        │
  │─── Tell user URL ───────→│                        │
  │                          │                        │
  │                     Serve newest HTML             │
  │←─────────────────── GET / ←───────────────────────│
  │                          │                        │
  │                    [User clicks]                  │
  │←───────────────── WebSocket ──────────────────────│
  │                          │                        │
  │ Read events (JSONL)      │                        │
  │←─── Read state/events ───│                        │
  │                          │                        │
  [Loop: next question]      │                        │
```

### 10.8 内容片段 vs 完整文档

```javascript
function isFullDocument(html) {
  const trimmed = html.trimStart().toLowerCase();
  return trimmed.startsWith('<!doctype') || trimmed.startsWith('<html');
}
```

- **内容片段**（默认）：Server 自动包装到 frame template
- **完整文档**：以 `<!DOCTYPE` 或 `<html>` 开头 → Server 不修改

### 10.9 CSS 类系统（Visual Companion）

| 类名 | 用途 | 关键结构 |
|------|------|---------|
| `.options` | A/B/C 选择 | `<div class="option" data-choice="a" onclick="toggleSelect(this)">` |
| `.options[data-multiselect]` | 多选 | 同上结构，用户可多选 |
| `.cards` | 视觉设计卡 | `.card[data-choice]` + `.card-image` + `.card-body` |
| `.mockup` | 模拟界面预览 | `.mockup-header` + `.mockup-body` |
| `.split` | 并排对比 | 两个 `.mockup` 子元素 |
| `.pros-cons` | 优缺点 | `.pros` + `.cons` 各含 `<ul>` |
| `.mock-nav` | 导航 mock | 文本导航栏 |
| `.mock-sidebar` | 侧边栏 mock | 文本侧栏 |
| `.mock-button` | 按钮 mock | CSS styled |
| `.mock-input` | 输入框 mock | CSS styled |

---

## 11. Inline Self-Review 机制（v5.0.6）

### 11.1 背景

**原来的问题**：subagent review loop（派发子agent审查+最多3次迭代）使执行时间加倍（~25分钟overhead），但回归测试显示质量分数与是否运行review loop无关（5个版本×5次trial）。

### 11.2 v5.0.6 变更

```
原来：
  brainstorm → 派发 spec-document-reviewer subagent → 最多3次迭代 → writing-plans
  writing-plans → 派发 plan-document-reviewer subagent → 最多3次迭代 → execution

现在：
  brainstorm → Inline Spec Self-Review Checklist（约30秒） → writing-plans
  writing-plans → Inline Plan Self-Review Checklist（约30秒） → execution
```

### 11.3 Spec Self-Review Checklist（brainstorming）

```markdown
1. Placeholder scan
   - 任何 "TBD"、"TODO"、不完整sections？
   - 任何模糊需求？

2. Internal consistency
   - 各section相互矛盾？
   - 架构与功能描述一致？

3. Scope check
   - 聚焦于单个实现计划？
   - 需要进一步分解？

4. Ambiguity check
   - 需求可被两种方式解释？
```

### 11.4 Plan Self-Review Checklist（writing-plans）

```markdown
1. Spec coverage
   - 每个spec section/需求都有对应任务？
   - 列出任何缺口

2. Placeholder scan
   - 无 "TBD"、"TODO"、"implement later"
   - 无 "Add appropriate error handling"（无具体说明）
   - 无 "Write tests for the above"（无代码）
   - 无 "Similar to Task N"（应重复代码）
   - 无描述做什么但不展示怎么做的步骤

3. Type consistency
   - 早期任务的类型/方法名与后期一致？
```

### 11.5 关键特性

- **同一上下文内联执行**：无需子agent派发，无额外延迟
- **即时修复**：发现问题立即修复，无需重新审查循环
- **量化对比**：
  - 内联 self-review：~30秒，发现 3-5 个真实 bug/run
  - Subagent review loop：~25分钟，质量无显著差异
- **无迭代限制**：找到问题就修复，修复完即完成

---

## 12. Controller-Worker Subagent 模式

### 12.1 核心概念

```
Controller（主agent）
    │
    ├── 维护完整计划上下文
    ├── 负责任务编排和调度
    ├── 做架构决策
    └── 协调多轮review
    │
    └──→ Worker (Implementer subagent)
            │
            ├── 接收精确构造的指令（含完整任务文本+上下文）
            ├── 不继承 Controller 的会话历史
            ├── 执行孤立任务
            ├── 可提问（在开始前和执行中）
            └── 报告状态（DONE/DONE_WITH_CONCERNS/BLOCKED/NEEDS_CONTEXT）
```

### 12.2 上下文隔离原则

所有 delegation skills 现在明确包含：

```
Subagents receive only the context they need, preventing context window pollution.
```

- Worker subagent **永远不**继承 Controller session 的历史
- Controller 为每个 Worker 构造精确所需的指令和上下文
- 指令包含完整任务文本（不引用文件路径让Worker自己读）

### 12.3 任务文本传递方式

```
错误做法：
  "Read the plan file at docs/superpowers/plans/2026-03-27-feature.md
   and implement Task 3."

正确做法：
  "You are implementing Task 3: [Component Name]

   ## Task Description
   [FULL TEXT of task - paste complete task text here]

   ## Context
   [Scene-setting: where this fits, dependencies, architectural context]
   [Full text of dependent interfaces/types from earlier tasks]

   ## Files
   - Create: exact/path/to/file.py
   - Modify: exact/path/to/existing.py:123-145
   - Test: tests/exact/path/to/test.py"
```

### 12.4 双向沟通协议

```
Controller                    Worker
    │                            │
    │──── Dispatch ─────────────→│
    │                            │
    │←─── Questions ─────────────│ (before starting)
    │                            │
    │──── Answer ───────────────→│
    │                            │
    │←─── DONE/BLOCKED/etc ──────│ (after work)
    │                            │
    │ (if issues)                │
    │──── Fix instructions ──────→│
    │←─── Re-review ─────────────│
```

### 12.5 Status 协议

| Status | 含义 | Controller Action |
|--------|------|-----------------|
| `DONE` | 完成，无问题 | 进入 spec review |
| `DONE_WITH_CONCERNS` | 完成但有疑虑 | 读concerns；正确性/范围问题先解决；观察性则记录继续 |
| `NEEDS_CONTEXT` | 缺信息 | 提供缺失上下文，re-dispatch |
| `BLOCKED` | 无法完成 | 评估类型：上下文问题→更多上下文；需要推理→更强模型；太大→拆分；计划错误→升级人类 |
---

## 13. 关键数据结构和接口

### 13.1 Plan Document 格式

```markdown
# [Feature Name] Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---

## Task 1: [Task Name]

**Files:**
- Create: exact/path/to/file.py
- Modify: exact/path/to/existing.py:123-145
- Test: tests/exact/path/to/test.py

**Steps:**
- [ ] **Step 1:** [Exact action with code block if applicable]
- [ ] **Step 2:** [Verification step]
- [ ] **Step 3:** Commit with message

---

## Task 2: [Task Name]
...
```

### 13.2 Spec Document 格式

```markdown
# [Topic] Design

**Created:** YYYY-MM-DD

## Goal
[One sentence]

## Context
[Background, constraints, existing system]

## Requirements
[What the system must do]

## Architecture
[How it works - components, data flow]

## Component: [Name]
[Detailed spec for each component]

## Data Model
[Types, schemas]

## Error Handling
[How errors are handled]

## Testing Approach
[How to verify it works]
```

### 13.3 Implementer Subagent Dispatch 格式

```yaml
Task tool (general-purpose):
  description: "Implement Task N: [task name]"
  prompt: |
    You are implementing Task N: [task name]

    ## Task Description
    [FULL TEXT from plan]

    ## Context
    [Scene-setting + type signatures from dependent tasks]

    ## Files
    [Exact paths from plan]

    ## Before You Begin
    [Ask any questions now]

    ## Self-Review Checklist
    [Completeness / Quality / Discipline / Testing]

    ## Report Format
    Status: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
```

### 13.4 Spec Reviewer Subagent Dispatch 格式

```yaml
Task tool (general-purpose):
  description: "Review spec compliance for Task N"
  prompt: |
    You are reviewing whether an implementation matches its specification.

    ## What Was Requested
    [FULL TEXT of task requirements]

    ## What Implementer Claims They Built
    [From implementer's report]

    ## CRITICAL: Do Not Trust the Report
    [Must verify by reading actual code]

    ## Your Job
    [Missing / Extra / Misunderstandings checks]

    ## Output
    ✅ Spec compliant
    OR
    ❌ Issues found: [file:line references]
```

### 13.5 Code Quality Reviewer Dispatch 格式

```yaml
Task tool (superpowers:code-reviewer):
  WHAT_WAS_IMPLEMENTED: [from implementer's report]
  PLAN_OR_REQUIREMENTS: Task N from [plan-file]
  BASE_SHA: [commit before task]
  HEAD_SHA: [current commit]
  DESCRIPTION: [task summary]
```

### 13.6 Brainstorm Server Startup JSON

```json
{
  "type": "server-started",
  "port": 52341,
  "host": "127.0.0.1",
  "url_host": "localhost",
  "url": "http://localhost:52341",
  "screen_dir": "/path/to/project/.superpowers/brainstorm/12345-1706000000/content",
  "state_dir": "/path/to/project/.superpowers/brainstorm/12345-1706000000/state"
}
```

### 13.7 Browser Event Format（JSONL）

```jsonl
{"type":"click","choice":"a","text":"Option A - Simple Layout","timestamp":1706000101}
{"type":"click","choice":"c","text":"Option C - Complex Grid","timestamp":1706000108}
{"type":"click","choice":"b","text":"Option B - Hybrid","timestamp":1706000115}
```

### 13.8 TodoWrite Task 格式

```json
{
  "content": "Task 1: [task name]",
  "status": "pending|in_progress|completed",
  "ACTIVEForm": "Implementing Task 1: [task name]"
}
```

### 13.9 Finishing 4 Options Format

```
Implementation complete. What would you like to do?

1. Merge back to <base-branch> locally
2. Push and create a Pull Request
3. Keep the branch as-is (I'll handle it later)
4. Discard this work

Which option?
```

---

## 14. 各技能文件路径

| 技能 | 主文件 | 辅助文件 |
|------|--------|---------|
| using-superpowers | `skills/using-superpowers/SKILL.md` | - |
| brainstorming | `skills/brainstorming/SKILL.md` | `visual-companion.md`, `scripts/server.cjs`, `scripts/start-server.sh`, `scripts/stop-server.sh`, `scripts/frame-template.html`, `scripts/helper.js`, `spec-document-reviewer-prompt.md` |
| writing-plans | `skills/writing-plans/SKILL.md` | `plan-document-reviewer-prompt.md` |
| subagent-driven-development | `skills/subagent-driven-development/SKILL.md` | `implementer-prompt.md`, `spec-reviewer-prompt.md`, `code-quality-reviewer-prompt.md` |
| executing-plans | `skills/executing-plans/SKILL.md` | - |
| finishing-a-development-branch | `skills/finishing-a-development-branch/SKILL.md` | - |
| systematic-debugging | `skills/systematic-debugging/SKILL.md` | `root-cause-tracing.md`, `defense-in-depth.md`, `condition-based-waiting.md` |
| using-git-worktrees | `skills/using-git-worktrees/SKILL.md` | - |
| requesting-code-review | `skills/requesting-code-review/SKILL.md` | `code-reviewer.md` |
| test-driven-development | `skills/test-driven-development/SKILL.md` | - |

---

## 15. 版本历史关键变更

### v5.0.6 (2026-03-24) ← 当前版本

- **Inline Self-Review 替代 subagent review loop**：brainstorming 和 writing-plans 中的 subagent 审查循环被内联 checklist 替代，节省 ~25分钟，质量无显著差异
- **Brainstorm Server session 目录重构**：`content/` 和 `state/` 分离，state 不再通过 HTTP 暴露
- **Owner-PID lifecycle bug 修复**：EPERM 误判为"进程死亡"；WSL grandparent PID 问题
- **Codex App 兼容性**：添加 named agent dispatch mapping 和 worktree-aware skill 行为

### v5.0.2 (2026-03-11)

- **零依赖 Brainstorm Server**：移除 ~1200行 vendored node_modules，使用内置 `http`/`fs`/`crypto` 模块
- **自定义 WebSocket RFC 6455 实现**：手工帧编码/解码，无 ws 依赖
- **原生 `fs.watch()` 替代 Chokidar**

### v5.0.0 (2026-03-09)

- **Specs/Plans 目录重构**：`docs/superpowers/specs/` 和 `docs/superpowers/plans/`
- **Subagent-driven-development 强制**（subagent-capable平台）
- **Visual Brainstorming Companion**：WebSocket server + browser helper
- **Document Review System**：Spec/Plan 审查循环

### v4.3.0 (2026-02-12)

- **`<HARD-GATE>` 强制机制**：brainstorming skill 现在强制执行工作流，DOT 流程图作为权威规范

### v4.0.0 (2025-12-17)

- **两阶段代码审查**：Spec compliance review + Code quality review
- **DOT 流程图作为可执行规范**：Prose 成为支持内容
- **技能描述陷阱修复**：description 覆盖流程图内容的问题

### v3.0.1 (2025-10-16)

- **Anthropic 第一方 Skills 系统**

### v2.0.0 (2025-10-12)

- **Skills 仓库分离**：Plugin 成为轻量 shim，Skills 独立仓库版本化

---

## 附录 A: Red Flags 快速参考

### using-superpowers 中的 Rationalization Patterns

| 你在想的 | 实际意思是 |
|---------|----------|
| "这只是简单问题" | 问题=任务，检查技能 |
| "我需要先更多上下文" | 检查技能在澄清问题之前 |
| "让我先探索代码库" | 技能告诉你如何探索，先检查 |
| "我可以用git快速检查" | 文件缺对话上下文，检查技能 |
| "这不需要正式技能" | 有技能就用 |
| "我记住了这个技能" | 技能在演进，读当前版本 |
| "这不算任务" | 行动=任务，检查技能 |
| "技能有点overkill" | 简单的事变复杂，用它 |
| "我就先做这一件事" | 先检查再行动 |
| "这感觉很高效" | 无纪律行动浪费时间，技能阻止 |
| "我知道什么意思" | 知道概念≠使用技能，调用它 |

### systematic-debugging 中的 Stop Signals

```
"Quick fix for now, investigate later"
"Just try changing X and see if it works"
"Add multiple changes, run tests"
"Skip the test, I'll manually verify"
"It's probably X, let me fix that"
"I don't fully understand but this might work"
"Pattern says X but I'll adapt it differently"
"Here are the main problems: [lists fixes without investigation]"
"**One more fix attempt** (when already tried 2+)"
"Each fix reveals new problem in different place"
→ 全部 = STOP，返回 Phase 1
```

---

## 附录 B: 指令优先级

```
1. User's explicit instructions (CLAUDE.md, AGENTS.md, direct requests) — 最高
2. Superpowers skills — 覆盖默认系统行为
3. Default system prompt — 最低

如 CLAUDE.md 说"不用 TDD" 但技能说"永远用 TDD" → 遵从用户指令
```

## 附录 C: Skill 类型

```
Rigid (TDD, debugging):
  → 完全遵循，不适应

Flexible (patterns):
  → 按上下文调整原则
  → 技能本身说明是哪种
```
