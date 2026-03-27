# Ralph — CodeMap

**GitHub**: https://github.com/snarktank/ralph  
**License**: MIT  
**Type**: Bash loop + Claude Code Skill 插件  
**Author**: snarktank  
**Based on**: Geoffrey Huntley's Ralph pattern  

---

## 1. 项目概述与定位

**Ralph** 是一个**自主式 AI 编程循环框架**，核心理念是：基于 PRD（Product Requirements Document）驱动 AI agent 反复执行任务，直到所有用户故事（User Stories）完成为止。每次迭代都是一个新的 Claude Code 实例，上下文通过文件系统持久化（git history + `progress.txt` + `prd.json`）。

Ralph 的定位介于"一次性工具"和"完整项目管理框架"之间——它不管理多里程碑，不规划路线图，但它确保**一个特性（feature）从 PRD 到完成的完整闭环**。

**与其他框架的核心区别**：
- GSD：管理整个项目生命周期
- Superpowers：规范单次开发循环的方法论
- **Ralph：确保一个 PRD 的所有 items 都被执行完毕**

---

## 2. 核心架构

### 2.1 整体架构

```
Ralph Loop (ralph.sh)
    │
    │  for i in 1..max_iterations:
    │
    ├─→ [Fresh Claude Code Instance]
    │       │
    │       │  1. Read prd.json (passes: false stories)
    │       │  2. Read progress.txt (learnings)
    │       │  3. Pick highest priority incomplete story
    │       │  4. Implement the story
    │       │  5. Run quality checks (typecheck/test/lint)
    │       │  6. Commit if checks pass
    │       │  7. Update prd.json (passes: true)
    │       │  8. Append learnings to progress.txt
    │       │  9. Check: ALL stories pass → <promise>COMPLETE</promise>
    │
    └─←  Loop until COMPLETE or max iterations reached
```

### 2.2 文件结构

```
ralph/
├── ralph.sh               # 核心 Bash 循环脚本
├── CLAUDE.md             # Claude Code 的 prompt 模板
├── prompt.md             # Amp 的 prompt 模板
├── prd.json.example      # PRD 格式示例
├── AGENTS.md             # Agent 提示（基于 Geoffrey Huntley 模式）
├── skills/
│   ├── prd/              # PRD 生成 Skill
│   │   └── SKILL.md
│   └── ralph/            # PRD → prd.json 转换 Skill
│       └── SKILL.md
├── .claude-plugin/       # Claude Code marketplace 插件清单
├── flowchart/            # 交互式流程图源码
├── ralph-flowchart.png   # 流程图
└── archive/              # 历史运行存档
```

### 2.3 关键数据文件

**prd.json**（PRD 执行状态）：
```json
{
  "project": "MyApp",
  "branchName": "ralph/task-priority",
  "description": "Task Priority System",
  "userStories": [
    {
      "id": "US-001",
      "title": "Add priority field to database",
      "description": "...",
      "acceptanceCriteria": ["criteria1", "criteria2"],
      "priority": 1,
      "passes": false,
      "notes": ""
    }
  ]
}
```

**progress.txt**（学习日志）：
```markdown
# Ralph Progress Log
Started: 2026-03-27
---

## Codebase Patterns
- Use sql<number> template for aggregations
- Always use IF NOT EXISTS for migrations
---

## [2026-03-27 14:00] - US-001
- What was implemented: Added priority column
- Files changed: db/migrations/xxx.sql, models/task.ts
- **Learnings:**
  - Pattern: "use enum for priority values"
  - Gotcha: "don't forget to add index on new column"
  - Useful: "priority defaults to 'medium'"
---
```

---

## 3. 核心流程详解

### 3.1 ralph.sh 循环逻辑

```bash
# 关键参数
TOOL="amp|claude"        # 选择 AI 工具
MAX_ITERATIONS=10        # 默认最大迭代次数

# 核心循环
for i in $(seq 1 $MAX_ITERATIONS); do
  if [[ "$TOOL" == "amp" ]]; then
    amp --dangerously-allow-all < prompt.md
  else
    claude --dangerously-skip-permissions --print < CLAUDE.md
  fi

  # 检测完成信号
  if echo "$OUTPUT" | grep -q "<promise>COMPLETE</promise>"; then
    exit 0  # 全部完成
  fi
done
exit 1  # 达到最大迭代次数
```

**关键设计**：
- `--dangerously-skip-permissions`：Claude Code 以无人值守模式运行，跳过所有确认提示
- `--print`：将完整输出打印到 stdout，便于捕获 `<promise>COMPLETE</promise>` 信号
- **Branch 自动存档**：当 `branchName` 改变时，自动将上一次的 `prd.json` 和 `progress.txt` 存档到 `archive/YYYY-MM-DD-branch/`

### 3.2 CLAUDE.md — 单次迭代的 Agent 指令

每次 Claude Code 实例启动时，`ralph.sh` 将 `CLAUDE.md` 的内容通过 stdin 传给 Claude Code。这份指令定义了一个迭代的工作流程：

```
1. Read prd.json           → 了解还有哪些 stories 未完成
2. Read progress.txt        → 学习前几次迭代发现的模式和坑
3. Pick highest priority story (passes: false)
4. Implement that story
5. Run quality checks        → 必须 typecheck + test 全绿才提交
6. Update CLAUDE.md files   → 如果发现了可复用的模式，写入相关目录的 CLAUDE.md
7. Commit with message: feat: [US-ID] - [Title]
8. Update prd.json: set passes: true
9. Append learnings to progress.txt
10. Check: if ALL passes → <promise>COMPLETE</promise>
```

**Learnings 机制**是 Ralph 的精髓——每次迭代的"经验"通过 `progress.txt` 和 `AGENTS.md` 传递给下一次迭代，最终形成可持续积累的项目知识库。

### 3.3 PRD Skill 和 Ralph Skill

Ralph 提供了两个 Claude Code Skills：

**`/prd` Skill**（PRD 生成）：
- 加载 `skills/prd/SKILL.md`
- 通过 Socratic 提问澄清需求
- 输出 `tasks/prd-[feature-name].md`

**`/ralph` Skill**（PRD 转换）：
- 加载 `skills/ralph/SKILL.md`
- 将 Markdown PRD 转换为 `prd.json`
- 提取 user stories、priority、acceptance criteria

### 3.4 Claude Code Marketplace 安装

```bash
/plugin marketplace add snarktank/ralph
/plugin install ralph-skills@ralph-marketplace
```

Skills 自动触发的语义条件：
- `"create a prd"` / `"write prd for"` → 触发 PRD skill
- `"convert this prd"` / `"turn into ralph format"` → 触发 Ralph skill

---

## 4. 与 Claude Code 的集成机制

### 4.1 双工具支持架构

Ralph 的 `ralph.sh` 实际上是一个**与具体 AI 工具无关的循环框架**：

```bash
if [[ "$TOOL" == "amp" ]]; then
  amp --dangerously-allow-all < prompt.md
else
  claude --dangerously-skip-permissions --print < CLAUDE.md
fi
```

`CLAUDE.md` 和 `prompt.md` 是两份独立的 prompt 模板，内容结构相似但针对不同工具的语法调整。

### 4.2 持久化机制（跨迭代记忆）

每次迭代是新启动的 Claude Code 实例，**无共享上下文**。跨迭代的"记忆"来自三个来源：

| 来源 | 内容 | 用途 |
|------|------|------|
| **git history** | 每次迭代的 commits | AI 自动可见（Claude Code 会读 git 历史） |
| **`progress.txt`** | 每次迭代的 learnings | **Codebase Patterns** section 被优先读取 |
| **`prd.json`** | stories 的 `passes` 状态 | 驱动哪些 stories 还未完成 |

### 4.3 Claude Code 的 `--dangerously-skip-permissions`

Claude Code 的 `--dangerously-skip-permissions` flag 允许无人值守执行：
- 跳过所有 "Are you sure?" 确认提示
- 跳过所有需要人工授权的工具调用
- 输出完整结果到 stdout（而非交互式 TUI）

---

## 5. 优缺点分析

### 优点

1. **极简主义**：整个框架只有 1 个 shell 脚本 + 2 个 prompt 模板，理解成本极低
2. **PRD 驱动**：以用户故事为单位，确保每个 acceptance criteria 都有被验证的机会
3. **上下文隔离**：每次迭代都是 fresh instance，避免上下文污染导致的模型行为漂移
4. **学习积累**：`progress.txt` 和 `AGENTS.md` 更新机制让项目知识随时间增长
5. **反馈循环强**：要求 typecheck + test 必须通过才能 commit，CI 永远是绿的
6. **自动化程度高**：设置好后可以扔到后台跑（overnight coding），无需人工干预
7. **双工具支持**：同时支持 Amp 和 Claude Code
8. **存档机制**：不同 feature 的运行历史自动存档，不会互相干扰

### 缺点

1. **无里程碑/路线图管理**：只能处理单个 PRD，无法管理多特性或跨周项目
2. **Story 大小依赖人工分解**：如果 PRD item 太大（超过 context window），模型会在中途耗尽上下文
3. **无 Phase 概念**：没有 discuss、plan、verify 的阶段性区分，AI 可能直接跳到实现
4. **跨 Feature 需要人工协调**：无法自动处理 Feature 之间的依赖关系
5. **Learnings 质量不稳定**：完全依赖模型的自觉性，没有强制机制确保有价值的 pattern 被记录
6. **不处理多轮对话式澄清**：PRD 生成依赖 Skill 的 Socratic 提问，但没有强制验证
7. **无并行能力**：所有 stories 串行执行（即使单个 story 内部可以并行）

---

## 6. 与 GSD / Superpowers 的关键差异

| 维度 | Ralph | GSD | Superpowers |
|------|-------|-----|-------------|
| **入口** | PRD（结构化需求文档） | 对话式讨论 → 项目创建 | Skill 触发（描述任务） |
| **执行单元** | User Story | Phase / Wave / Task | Plan Step |
| **循环模式** | 外部 Bash 循环，新实例 | Agent 内置 wave 执行 | Skill 链式调用 |
| **上下文隔离** | 每次迭代全新实例 | 共享上下文（同一 session） | 共享上下文 |
| **记忆机制** | progress.txt + git + AGENTS.md | STATE.md + PROJECT.md | Plan/Spec 文档 |
| **无人工干预** | 可完全无人值守（overnight） | 通常需要 checkpoint 审批 | 半自动（每步有 gate） |
| **多工具支持** | Amp + Claude Code | 8 runtimes | 5 platforms |
| **Skill 系统** | 有（PRD + Ralph） | 有（30+ commands） | 有（10+ skills） |

---

## 7. 适用场景

**适合 Ralph**：
- 需要"实现这个功能"的完整闭环（从需求到验证）
- 夜间/周末无人值守的开发
- 有清晰 acceptance criteria 的明确需求
- 需要确保"不遗漏任何需求项"

**不适合 Ralph**：
- 探索性开发（需求不清楚，无法写 PRD）
- 需要多特性协调（Feature 之间的依赖管理）
- 想要阶段性审批（discuss → plan → verify）
- 大型跨周/跨里程碑项目

---

## 8. 关键文件速查

| 文件 | 作用 |
|------|------|
| `ralph.sh` | 核心 Bash 循环脚本（120行） |
| `CLAUDE.md` | Claude Code 单次迭代 prompt（无人值守模式） |
| `prd.json.example` | PRD 数据格式示例 |
| `skills/prd/SKILL.md` | PRD 生成 Skill |
| `skills/ralph/SKILL.md` | PRD → prd.json 转换 Skill |
| `.claude-plugin/` | Claude Code marketplace 清单 |
| `flowchart/` | 交互式流程图源码（可本地运行 `npm run dev`） |
