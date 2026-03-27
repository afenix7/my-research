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
ralph.sh (Bash for loop)
    │
    │  for i in $(seq 1 $MAX_ITERATIONS); do
    │
    ├─→ [Fresh Claude Code Instance]
    │       │
    │       │  1. Read prd.json (passes: false stories)
    │       │  2. Read progress.txt (learnings + Codebase Patterns)
    │       │  3. Check git branch (branch from PRD branchName)
    │       │  4. Pick highest priority incomplete story
    │       │  5. Implement the story (fresh context, no memory)
    │       │  6. Run quality checks (typecheck + test)
    │       │  7. Update nearby CLAUDE.md/AGENTS.md with patterns
    │       │  8. Commit if checks pass (feat: [US-ID] - [Title])
    │       │  9. Update prd.json (set passes: true for story)
    │       │ 10. Append learnings to progress.txt
    │       │ 11. Check: ALL stories pass → <promise>COMPLETE</promise>
    │
    └─←  Loop until COMPLETE or max iterations (default 10) reached
```

### 2.2 文件结构

```
ralph/
├── ralph.sh                  # 核心 Bash 循环脚本 (~120行)
├── CLAUDE.md                 # Claude Code 的 per-iteration prompt 模板
├── prompt.md                 # Amp 的 per-iteration prompt 模板（与 CLAUDE.md 等价）
├── prd.json.example          # PRD JSON 格式完整示例
├── AGENTS.md                 # 项目级 Agent 提示（根目录）
├── skills/
│   ├── prd/
│   │   └── SKILL.md          # PRD 生成 Skill（Claude Code marketplace 触发）
│   └── ralph/
│       └── SKILL.md          # PRD → prd.json 转换 Skill（Claude Code marketplace 触发）
├── .claude-plugin/
│   ├── plugin.json           # 插件清单（name/version/skills path）
│   └── marketplace.json      # Marketplace 发布配置
├── flowchart/                # 交互式 React Flow 流程图（可 npm run dev 本地运行）
├── ralph-flowchart.png       # 流程图静态图
└── archive/                  # 历史运行存档（自动创建）
    └── YYYY-MM-DD-feature-name/
        ├── prd.json          # 存档时的 PRD 快照
        └── progress.txt      # 存档时的学习日志快照
```

---

## 3. 关键文件详解

### 3.1 `ralph.sh` — 核心 Bash 循环

**关键参数**：
```bash
TOOL="amp|claude"         # 默认 "amp"；通过 --tool claude 切换
MAX_ITERATIONS=10         # 默认值；命令行第一个数字参数覆盖
```

**精确执行流程**：

```bash
# Step 1: 参数解析
while [[ $# -gt 0 ]]; do
  case $1 in
    --tool)       TOOL="$2"; shift 2 ;;
    --tool=*)     TOOL="${1#*=}"; shift ;;
    *)            # 数字 → MAX_ITERATIONS
      if [[ "$1" =~ ^[0-9]+$ ]]; then MAX_ITERATIONS="$1"; fi; shift ;;
  esac
done

# Step 2: 确定文件路径（脚本自身所在目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRD_FILE="$SCRIPT_DIR/prd.json"
PROGRESS_FILE="$SCRIPT_DIR/progress.txt"
ARCHIVE_DIR="$SCRIPT_DIR/archive"
LAST_BRANCH_FILE="$SCRIPT_DIR/.last-branch"

# Step 3: Branch 变更 → 自动存档上一个 feature
if [ -f "$PRD_FILE" ] && [ -f "$LAST_BRANCH_FILE" ]; then
  CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE")
  LAST_BRANCH=$(cat "$LAST_BRANCH_FILE")
  if [ -n "$CURRENT_BRANCH" ] && [ -n "$LAST_BRANCH" ] && [ "$CURRENT_BRANCH" != "$LAST_BRANCH" ]; then
    DATE=$(date +%Y-%m-%d)
    FOLDER_NAME=$(echo "$LAST_BRANCH" | sed 's|^ralph/||')   # 去掉 "ralph/" 前缀
    ARCHIVE_FOLDER="$ARCHIVE_DIR/$DATE-$FOLDER_NAME"
    mkdir -p "$ARCHIVE_FOLDER"
    [ -f "$PRD_FILE" ]      && cp "$PRD_FILE" "$ARCHIVE_FOLDER/"
    [ -f "$PROGRESS_FILE" ] && cp "$PROGRESS_FILE" "$ARCHIVE_FOLDER/"
    # 为新 run 重置 progress.txt
    echo "# Ralph Progress Log" > "$PROGRESS_FILE"
    echo "Started: $(date)" >> "$PROGRESS_FILE"
    echo "---" >> "$PROGRESS_FILE"
  fi
fi

# Step 4: 记录当前 branch
CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE")
[ -n "$CURRENT_BRANCH" ] && echo "$CURRENT_BRANCH" > "$LAST_BRANCH_FILE"

# Step 5: 初始化 progress.txt（如不存在）
if [ ! -f "$PROGRESS_FILE" ]; then
  echo "# Ralph Progress Log" > "$PROGRESS_FILE"
  echo "Started: $(date)" >> "$PROGRESS_FILE"
  echo "---" >> "$PROGRESS_FILE"
fi

# Step 6: 核心 for 循环
for i in $(seq 1 $MAX_ITERATIONS); do
  echo "==============================================================="
  echo "  Ralph Iteration $i of $MAX_ITERATIONS ($TOOL)"
  echo "==============================================================="

  # Claude Code 模式：通过 stdin 管道注入 CLAUDE.md
  if [[ "$TOOL" == "amp" ]]; then
    OUTPUT=$(cat "$SCRIPT_DIR/prompt.md" | amp --dangerously-allow-all 2>&1 | tee /dev/stderr) || true
  else
    # --print: 输出完整响应到 stdout（而非交互式 TUI）
    # --dangerously-skip-permissions: 跳过所有确认提示，无人值守运行
    OUTPUT=$(claude --dangerously-skip-permissions --print < "$SCRIPT_DIR/CLAUDE.md" 2>&1 | tee /dev/stderr) || true
  fi

  # Step 7: 检测完成信号
  if echo "$OUTPUT" | grep -q "<promise>COMPLETE</promise>"; then
    echo "Ralph completed all tasks! Completed at iteration $i of $MAX_ITERATIONS"
    exit 0
  fi

  echo "Iteration $i complete. Continuing..."
  sleep 2
done

# Step 8: 达到最大迭代次数
echo "Ralph reached max iterations ($MAX_ITERATIONS) without completing all tasks."
exit 1
```

**Bash for 循环工作原理**：
- `$(seq 1 $MAX_ITERATIONS)` 生成序列 1, 2, 3, ..., MAX_ITERATIONS
- 每次迭代 `$i` 持有当前迭代号（1-indexed）
- **每次循环都是独立启动**的 Claude Code/Amp 进程，进程间无状态共享
- `set -e`：任何命令失败都退出（非 `|| true` 捕获的命令）
- `sleep 2`：两次迭代间等待 2 秒（给文件系统时间写入）

---

### 3.2 `prd.json` — 完整字段定义

**prd.json 是 Ralph 的"状态机"**，整个迭代驱动靠它：

```json
{
  // === 项目元数据 ===
  "project": "string",          // 项目名称（仅用于标识，无代码生成用途）
  "branchName": "ralph/xxx",    // Git branch 名称（自动创建/检出新 branch）
  "description": "string",      // 功能描述（人类可读，无代码生成用途）

  // === 核心状态数组：passes 字段驱动循环 ===
  "userStories": [
    {
      // --- 标识 ---
      "id": "US-001",           // 唯一故事 ID（顺序编号，格式: US-XXX）
      "title": "string",         // 简短标题（用于 commit message）

      // --- 内容 ---
      "description": "string",  // As a [user], I want [feature] so that [benefit].
      "acceptanceCriteria": [    // 可验证的检查项（关键：必须可被 AI "检查"）
        "string",                // 示例: "Add priority column to tasks table..."
        "string",                // 示例: "Typecheck passes"
        "string"                 // 示例: "Verify in browser using dev-browser skill"
      ],

      // --- 执行控制 ---
      "priority": 1,             // 整数，1=最高。Ralph 按 priority ASC 选取
      "passes": false,           // 核心状态位。false = 未完成，true = 已完成
      "notes": ""                // 可选注释（AI 可以在此记录临时笔记）
    }
  ]
}
```

**完整示例**（来自 `prd.json.example`）：

```json
{
  "project": "MyApp",
  "branchName": "ralph/task-priority",
  "description": "Task Priority System - Add priority levels to tasks",
  "userStories": [
    {
      "id": "US-001",
      "title": "Add priority field to database",
      "description": "As a developer, I need to store task priority so it persists across sessions.",
      "acceptanceCriteria": [
        "Add priority column to tasks table: 'high' | 'medium' | 'low' (default 'medium')",
        "Generate and run migration successfully",
        "Typecheck passes"
      ],
      "priority": 1,
      "passes": false,
      "notes": ""
    },
    {
      "id": "US-002",
      "title": "Display priority indicator on task cards",
      "description": "As a user, I want to see task priority at a glance.",
      "acceptanceCriteria": [
        "Each task card shows colored priority badge (red=high, yellow=medium, gray=low)",
        "Priority visible without hovering or clicking",
        "Typecheck passes",
        "Verify in browser using dev-browser skill"
      ],
      "priority": 2,
      "passes": false,
      "notes": ""
    }
  ]
}
```

**passes 字段状态机**：

| 状态 | 含义 | 行为 |
|------|------|------|
| `passes: false` | 未开始或进行中 | Ralph 的每次迭代会尝试完成一个 `passes: false` 的故事 |
| `passes: true` | 已完成并验证通过 | Ralph 跳过该故事，选取下一个 priority 最低（最高优先）且 `passes: false` 的故事 |
| 全部 `passes: true` | 全部完成 | Ralph 输出 `<promise>COMPLETE</promise>`，ralph.sh 退出 0 |

---

### 3.3 `CLAUDE.md` — Per-Iteration Agent 指令

`ralph.sh` 通过 **`cat CLAUDE.md | claude --print`** 将内容通过 **stdin 管道**注入 Claude Code。这是 Claude Code 的 `--print` 模式核心用法。

**完整的 11 步工作流**：

```
┌─────────────────────────────────────────────────────────┐
│ Step 1: Read prd.json                                   │
│   → 了解还有哪些 stories 未完成（passes: false）        │
│   → 了解当前项目的 branchName                          │
├─────────────────────────────────────────────────────────┤
│ Step 2: Read progress.txt                              │
│   → 优先读取 ## Codebase Patterns（顶部的全局模式）    │
│   → 了解前几次迭代发现的模式和坑                        │
├─────────────────────────────────────────────────────────┤
│ Step 3: 检查/创建 Git branch                           │
│   → 从 PRD branchName 字段获取目标 branch             │
│   → 若不存在，从 main 创建；已在则切换                 │
├─────────────────────────────────────────────────────────┤
│ Step 4: 选取最高优先级故事                              │
│   → 找 passes: false 且 priority 数字最小的故事       │
│   → 这是本次迭代唯一要实现的故事                        │
├─────────────────────────────────────────────────────────┤
│ Step 5: 实现该故事                                      │
│   → 按 acceptanceCriteria 逐项实现                       │
│   → 单次上下文中完成（无历史记忆）                      │
├─────────────────────────────────────────────────────────┤
│ Step 6: 运行质量检查                                    │
│   → typecheck + lint + test（项目自定义命令）          │
│   → 必须全部通过才能提交                                 │
├─────────────────────────────────────────────────────────┤
│ Step 7: 更新附近 CLAUDE.md / AGENTS.md                 │
│   → 发现可复用模式时写入相关目录的 CLAUDE.md           │
│   → 非强制，但可帮助后续迭代和人类开发者                 │
├─────────────────────────────────────────────────────────┤
│ Step 8: 提交代码                                        │
│   → git add .                                          │
│   → git commit -m "feat: [Story ID] - [Title]"         │
│   → 仅在质量检查全绿时执行                              │
├─────────────────────────────────────────────────────────┤
│ Step 9: 更新 prd.json                                   │
│   → jq 或手动编辑：目标故事的 passes 设为 true        │
├─────────────────────────────────────────────────────────┤
│ Step 10: 追加 progress.txt                             │
│   → APPEND（永不覆盖）：时间戳 + Story ID + 实现内容    │
│   → + Files changed + Learnings（模式/坑/上下文）      │
├─────────────────────────────────────────────────────────┤
│ Step 11: 检查停止条件                                   │
│   → 全部 passes: true → 输出 <promise>COMPLETE</promise>
│   → 仍有 false → 正常结束，ralph.sh 启动下一次迭代     │
└─────────────────────────────────────────────────────────┘
```

---

### 3.4 `progress.txt` — 学习积累机制

**格式规范**（append-only，永远不覆盖旧内容）：

```
# Ralph Progress Log
Started: 2026-03-27
---

## Codebase Patterns                    ← 顶部全局模式区（最优先读取）
- Use sql<number> template for aggregations
- Always use IF NOT EXISTS for migrations
- Export types from actions.ts for UI components
---

## [2026-03-27 14:00] - US-001
- What was implemented: Added priority column and migration
- Files changed: db/migrations/xxx.sql, models/task.ts
- **Learnings for future iterations:**
  - Pattern: "use enum for priority values"
  - Gotcha: "don't forget to add index on new column"
  - Useful: "priority defaults to 'medium'"
---

## [2026-03-27 14:05] - US-002
- What was implemented: Added colored priority badges to task cards
- Files changed: components/TaskCard.tsx, styles/badges.css
- **Learnings for future iterations:**
  - Pattern: "reuse existing Badge component with color variants"
  - Gotcha: "badge colors must match design system tokens"
  - Useful: "the badge component accepts 'variant' prop"
---
```

**学习积累机制的工作原理**：

1. **每次迭代结束时追加**：不是覆盖，而是 `>>`（append）到 progress.txt
2. **`## Codebase Patterns` 区块**：位于文件顶部，在 `---` 分隔线之后；用于放置最通用、最重要的模式
3. **CLAUDE.md 的 Step 2 强制读取**：每次新迭代开始时，Agent 被指示"check Codebase Patterns section first"
4. **随时间增长**：每次迭代添加一个 `## [DateTime] - [Story ID]` 块
5. **双重持久化**：learnings 同时写入 `progress.txt` 和相关目录的 `CLAUDE.md/AGENTS.md`

---

### 3.5 `skills/prd/SKILL.md` — PRD 生成 Skill

**触发条件**（Claude Code marketplace 自动语义匹配）：
- `"create a prd"` / `"write prd for"` / `"plan this feature"`
- `"requirements for"` / `"spec out"`

**工作流**：

```
用户触发 PRD skill
    ↓
Step 1: 澄清性问题（Socratic 提问）
    → 提供 lettered 选项（A/B/C/D 快速回复格式）
    → 聚焦：目标用户、核心功能、范围边界、成功标准
    ↓
Step 2: 生成结构化 PRD（Markdown）
    → 保存到 tasks/prd-[feature-name].md
    ↓
PRD 包含：
  - Introduction/Overview
  - Goals（可测量目标）
  - User Stories（US-XXX 格式，每个包含 acceptance criteria）
  - Functional Requirements（FR-XX 编号列表）
  - Non-Goals（明确不包括什么）
  - Technical Considerations（可选）
  - Success Metrics（可选）
  - Open Questions（可选）
```

**关键设计原则**：PRD 的每个 User Story 必须**在单次上下文中可完成**，这是 Ralph 能工作的基础前提。

---

### 3.6 `skills/ralph/SKILL.md` — PRD → prd.json 转换 Skill

**触发条件**：
- `"convert this prd"` / `"turn this into ralph format"`
- `"create prd.json from this"` / `"ralph json"`

**转换规则**：

| Markdown PRD | prd.json |
|---|---|
| 每个 User Story | 一个 `userStories[]` 元素 |
| Story 标题 | `title` |
| Story 描述（As a...） | `description` |
| Acceptance Criteria | `acceptanceCriteria[]` |
| Story 顺序 | `priority`（依赖链优先） |
| — | `passes: false`（初始状态） |
| — | `notes: ""`（初始为空） |

**关键约束**：
- 每个 story 必须可在一轮上下文中完成（"一个焦点变更"原则）
- 依赖顺序：schema → backend → UI
- 每个 acceptance criteria 必须**可被 AI 检查**（非模糊描述）
- **每个 story 必须以 "Typecheck passes" 结尾**
- **UI story 必须包含 "Verify in browser using dev-browser skill"**

---

### 3.7 `.claude-plugin/` — Marketplace 插件配置

**`plugin.json`**（插件清单）：
```json
{
  "name": "ralph-skills",
  "version": "1.0.0",
  "description": "Skills for the Ralph autonomous agent system...",
  "skills": "./skills/"
}
```

**`marketplace.json`**（发布配置）：
```json
{
  "name": "ralph-marketplace",
  "owner": { "name": "snarktank" },
  "metadata": { "description": "...", "version": "1.0.0" },
  "plugins": [{
    "name": "ralph-skills",
    "source": "./",
    "skills": "./skills/",
    "keywords": ["ralph", "prd", "automation", "agent", "planning"]
  }]
}
```

**Marketplace 安装命令**：
```bash
/plugin marketplace add snarktank/ralph
/plugin install ralph-skills@ralph-marketplace
```

---

## 4. 与 Claude Code 的精确集成方式

### 4.1 `--print` 模式 + stdin 管道

```bash
claude --dangerously-skip-permissions --print < CLAUDE.md
```

**精确机制**：
1. Bash 通过 `< CLAUDE.md` 将文件内容作为 **stdin** 传给 Claude Code
2. `--print` 让 Claude Code **将完整响应输出到 stdout**（而非启动交互式 TUI）
3. `--dangerously-skip-permissions` 跳过所有确认提示，使无人值守运行成为可能
4. 输出被 `tee /dev/stderr` 同时打印到终端和捕获到变量 `$OUTPUT`
5. `ralph.sh` 检查 `$OUTPUT` 是否包含 `<promise>COMPLETE</promise>`

**为什么不用 `--resume` 或 attach existing session**：
- Ralph 的核心设计是**每次迭代 fresh context**（隔离）
- `--print` + stdin 是让 Claude Code 执行完 prompt 后自动退出的最简方式

### 4.2 持久化机制（跨迭代记忆）

每次迭代是新启动的 Claude Code 实例，**无共享上下文内存**。跨迭代的"记忆"来自三个来源的叠加：

| 来源 | 内容 | 用途 |
|------|------|------|
| **git history** | 每次迭代的 commits | AI 自动可见（Claude Code 会读 git 历史 + diff） |
| **`progress.txt`** | 每次迭代的 learnings | Step 2 强制读取；Codebase Patterns 区块优先 |
| **`prd.json`** | stories 的 `passes` 状态 | 驱动哪些 stories 还未完成 |
| **附近 `CLAUDE.md/AGENTS.md`** | 目录级模式 | Step 7 写入；特定目录的人类可读知识 |

---

## 5. 完整循环流程 Step by Step

### 阶段 0：初始化（首次运行前）

```
用户创建 PRD (markdown)
    ↓
用户调用 /ralph skill → 转换为 prd.json
    ↓
用户运行 ./ralph.sh --tool claude [max_iterations]
    ↓
ralph.sh 解析参数，初始化 progress.txt
    ↓
进入 for 循环
```

### 阶段 1：迭代 i = 1（每次循环相同）

```
┌──────────────────────────────────────────────┐
│  ralph.sh: for i in $(seq 1 $MAX_ITERATIONS) │
│               ↓                              │
│  Bash: claude --print < CLAUDE.md           │
│               ↓                              │
│  Claude Code (fresh instance) starts        │
│  读取 prd.json → 找 passes: false 故事      │
│  读取 progress.txt → 找 Codebase Patterns   │
│  检查 git branch → 切换/创建                 │
│               ↓                              │
│  选取 priority=1 的故事（最高优先）          │
│               ↓                              │
│  实现故事：                                   │
│    - 修改代码                                │
│    - 运行 typecheck + test                  │
│    - 更新附近 CLAUDE.md（如有模式发现）       │
│    - git commit                             │
│    - 更新 prd.json (passes: true)           │
│    - 追加 progress.txt                       │
│               ↓                              │
│  检查：全部 passes: true？                    │
│    YES → 输出 <promise>COMPLETE</promise>   │
│    NO  → 正常结束 iteration                  │
└──────────────────────────────────────────────┘
               ↓
  ralph.sh: sleep 2 → 下一轮 for 循环
               ↓
  迭代 i = 2（重复相同流程）
```

### 阶段 2：重复直到停止

```
Iteration 1 → Story US-001 完成（passes: true）
Iteration 2 → Story US-002 完成
...
Iteration N → 最后 Story 完成
    ↓
Output contains <promise>COMPLETE</promise>
    ↓
ralph.sh: exit 0
```

**停止条件**：
- **正常停止**：所有 `userStories[].passes == true` → `<promise>COMPLETE</promise>` → exit 0
- **异常停止**：达到 `MAX_ITERATIONS` → exit 1

---

## 6. 自动化代码模式积累机制

### 6.1 三层积累架构

```
progress.txt (全局学习日志)
    │
    ├─→ ## Codebase Patterns（顶部，全局通用模式）
    │       被每次新迭代 Step 2 优先读取
    │
    └─→ ## [DateTime] - US-XXX（按时间追加的故事块）
            包含该故事的 Learnings + Files changed

附近目录的 CLAUDE.md / AGENTS.md (目录级知识)
    │
    └─→ 每次迭代 Step 7 按修改的目录选择性写入
        仅写入"真正可复用的知识"
```

### 6.2 积累的触发条件

| 场景 | 积累到哪里 | 触发者 |
|------|-----------|--------|
| 发现通用模式（跨项目可用） | progress.txt 的 `## Codebase Patterns` | Agent 自动（CLAUDE.md Step 7） |
| 发现项目级模式 | progress.txt 的 `## [DateTime] - US-XXX` | Agent 自动（CLAUDE.md Step 10） |
| 发现目录级模式 | 目录的 `CLAUDE.md` 或 `AGENTS.md` | Agent 自动（CLAUDE.md Step 7） |

### 6.3 模式的质量信号

**好的模式**（应积累）：
- API 约定（"这个模块所有 API 调用都用 X 模式"）
- 坑（"修改 X 时必须同时更新 Y"）
- 依赖关系（"需要 dev server 在 PORT 3000"）
- 命名约定（"字段名必须与 template 完全匹配"）

**应避免**：
- 故事特定的实现细节
- 临时调试笔记
- 已在 progress.txt 中记录的内容

---

## 7. 双工具支持：Amp vs Claude Code

Ralph 的 `ralph.sh` 实际上是**与具体 AI 工具无关的循环框架**，两种工具的调用方式完全对称：

```bash
# Amp 模式
cat "$SCRIPT_DIR/prompt.md" | amp --dangerously-allow-all

# Claude Code 模式
claude --dangerously-skip-permissions --print < "$SCRIPT_DIR/CLAUDE.md"
```

**`prompt.md` vs `CLAUDE.md` 的差异**：

| 方面 | prompt.md (Amp) | CLAUDE.md (Claude Code) |
|------|----------------|------------------------|
| 线程追踪 | 包含 `Thread: https://ampcode.com/threads/$AMP_CURRENT_THREAD_ID` | 无（Claude Code 无线程概念） |
| AGENTS.md vs CLAUDE.md | 写入 `AGENTS.md` | 写入 `CLAUDE.md` |
| dev-browser skill | 使用 `dev-browser` skill | 同样使用 `dev-browser` skill |
| 核心逻辑 | 完全相同 | 完全相同 |

---

## 8. 优缺点分析

### 优点

1. **极简主义**：整个框架只有 1 个 shell 脚本 + 2 个 prompt 模板，理解成本极低
2. **PRD 驱动**：以用户故事为单位，确保每个 acceptance criteria 都有被验证的机会
3. **上下文隔离**：每次迭代都是 fresh instance，避免上下文污染导致的模型行为漂移
4. **学习积累**：`progress.txt` + `## Codebase Patterns` + `CLAUDE.md/AGENTS.md` 三层积累机制
5. **反馈循环强**：要求 typecheck + test 必须通过才能 commit，CI 永远是绿的
6. **无人值守**：设置好后可扔后台运行（overnight coding），无需人工干预
7. **双工具支持**：同时支持 Amp 和 Claude Code
8. **自动存档**：不同 feature 的运行历史自动存档到 `archive/YYYY-MM-DD-feature/`
9. **Marketplace 集成**：通过 Claude Code marketplace 一键安装 skills

### 缺点

1. **无里程碑/路线图管理**：只能处理单个 PRD，无法管理多特性或跨周项目
2. **Story 大小依赖人工分解**：如果 PRD item 太大，模型会在中途耗尽上下文
3. **无 Phase 概念**：没有 discuss/plan/verify 的阶段性区分，AI 可能直接跳到实现
4. **跨 Feature 需要人工协调**：无法自动处理 Feature 之间的依赖关系
5. **Learnings 质量不稳定**：完全依赖模型的自觉性，无强制机制确保有价值 pattern 被记录
6. **不处理多轮对话式澄清**：PRD 生成依赖 Skill 的 Socratic 提问，但没有强制验证
7. **无并行能力**：所有 stories 串行执行
8. **依赖外部 AI 工具**：需要提前配置并认证 Amp 或 Claude Code

---

## 9. 与 GSD / Superpowers 的关键差异

| 维度 | Ralph | GSD | Superpowers |
|------|-------|-----|-------------|
| **入口** | PRD（结构化需求文档） | 对话式讨论 → 项目创建 | Skill 触发（描述任务） |
| **执行单元** | User Story | Phase / Wave / Task | Plan Step |
| **循环模式** | 外部 Bash for 循环，新实例 | Agent 内置 wave 执行 | Skill 链式调用 |
| **上下文隔离** | 每次迭代全新实例（fresh） | 共享上下文（同一 session） | 共享上下文 |
| **记忆机制** | progress.txt + git + CLAUDE.md/AGENTS.md | STATE.md + PROJECT.md | Plan/Spec 文档 |
| **无人干预** | 完全无人值守（Bash loop） | 通常需要 checkpoint 审批 | 半自动（每步有 gate） |
| **多工具支持** | Amp + Claude Code | 8 runtimes | 5 platforms |
| **Skill 系统** | PRD + Ralph skills（Marketplace） | 30+ commands | 10+ skills |
| **Archive 机制** | 自动存档不同 feature | 无 | 无 |
| **Marketplace** | Claude Code marketplace 插件 | 无 | 无 |

---

## 10. 适用场景

**适合 Ralph**：
- 需要"实现这个功能"的完整闭环（从需求到验证）
- 夜间/周末无人值守的开发（可放在后台运行）
- 有清晰 acceptance criteria 的明确需求
- 需要确保"不遗漏任何需求项"
- 想要积累代码库模式的项目

**不适合 Ralph**：
- 探索性开发（需求不清楚，无法写 PRD）
- 需要多特性协调（Feature 之间的依赖管理）
- 想要阶段性审批（discuss → plan → verify）
- 大型跨周/跨里程碑项目

---

## 11. 关键文件速查

| 文件 | 作用 | 行数/大小 |
|------|------|----------|
| `ralph.sh` | 核心 Bash for 循环脚本 | ~120行 |
| `CLAUDE.md` | Claude Code per-iteration prompt | ~150行 |
| `prompt.md` | Amp per-iteration prompt（与 CLAUDE.md 等价） | ~150行 |
| `prd.json.example` | PRD JSON 完整示例 | ~70行 |
| `skills/prd/SKILL.md` | PRD 生成 Skill | ~200行 |
| `skills/ralph/SKILL.md` | PRD → prd.json 转换 Skill | ~220行 |
| `.claude-plugin/plugin.json` | 插件清单 | ~10行 |
| `.claude-plugin/marketplace.json` | Marketplace 发布配置 | ~20行 |
| `flowchart/` | 交互式 React Flow 流程图 | 可本地 npm run dev |

---

## 12. 执行命令参考

```bash
# Claude Code Marketplace 安装
/plugin marketplace add snarktank/ralph
/plugin install ralph-skills@ralph-marketplace

# 运行 Ralph（默认 Amp，最多 10 次迭代）
./ralph.sh

# 运行 Ralph（指定 Claude Code，最多 20 次迭代）
./ralph.sh --tool claude 20

# 运行 Ralph（显式 Amp）
./ralph.sh --tool amp 5

# 查看当前状态
cat prd.json | jq '.userStories[] | {id, title, passes}'
cat progress.txt

# 手动存档（可选，ralph.sh 自动处理）
mkdir -p archive/$(date +%Y-%m-%d)-feature-name
cp prd.json archive/$(date +%Y-%m-%d)-feature-name/
cp progress.txt archive/$(date +%Y-%m-%d)-feature-name/
```
