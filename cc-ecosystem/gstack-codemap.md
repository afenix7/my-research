# gstack CodeMap

> **Garry Tan (Y Combinator President & CEO) 的个人 Claude Code 插件**
> GitHub: `garrytan/gstack` | MIT License | 2026年3月最新版本

## 项目概述

gstack 将 Claude Code 变成一支完整的虚拟工程团队。核心理念不是工具集合，而是软件开发**全流程**：Think → Plan → Build → Review → Test → Ship → Reflect。

**实际成果：** 60天 600,000+ 行生产代码（35% 测试），每天 10,000-20,000 行，同时全职运营 YC。

**定位：** 不是"浏览器自动化插件"，而是一个有 28 个技能的完整开发团队模拟器。浏览器能力（`$B` 命令）是其中一个技能，但不是核心。

---

## 核心架构

### 系统结构

```
用户会话
    │
    ├─ /office-hours      → YC Office Hours（重构问题，写 Design Doc）
    ├─ /plan-ceo-review   → CEO/Founder（10星产品，4种扩张模式）
    ├─ /plan-eng-review   → Eng Manager（架构锁定，ASCII图，测试矩阵）
    ├─ /plan-design-review → Senior Designer（维度评分，AI Slop检测）
    ├─ /design-consultation → Design Partner（设计系统生成，mockup）
    │
    ├─ /review            → Staff Engineer（自动修复 bug，过滤CI假阳性）
    ├─ /design-review     → Designer Who Codes（直接修+截图）
    ├─ /investigate       → Debugger（3次失败停止，Iron Law）
    │
    ├─ /qa                → QA Lead（真实浏览器，修复+生成回归测试）
    ├─ /qa-only           → QA Reporter（纯报告）
    ├─ /cso               → Chief Security Officer（OWASP+STRIDE）
    │
    ├─ /ship              → Release Engineer（同步+测试+覆盖率审计+开PR）
    ├─ /land-and-deploy   → Release Engineer（合并+等CI/CD+验证生产）
    ├─ /canary            → SRE（灰度监控，console错误/性能回退）
    ├─ /benchmark         → Performance Engineer（Core Web Vitals对比）
    │
    ├─ /retro             → Eng Manager（团队感知周回顾，/retro global跨项目）
    ├─ /document-release  → Technical Writer（自动更新漂移文档）
    │
    ├─ /browse            → QA Engineer（持久化浏览器，$B命令）
    ├─ /codex             → OpenAI Codex第二意见（跨模型分析）
    └─ /careful/freeze/guard/unfreeze → 安全guardrails
```

---

## 文件结构

```
gstack/
├── SKILL.md                    # 主入口技能（安装后添加到CLAUDE.md）
├── AGENTS.md                   # Agent定义
├── ARCHITECTURE.md             # 架构文档（~21KB，技术决策全记录）
├── CLAUDE.md                   # 用户级配置模板
├── setup                       # 安装脚本
│
├── bin/                        # 编译后二进制CLI
│   ├── gstack-config           # 配置读写
│   ├── gstack-global-discover  # 跨仓库技能发现
│   └── gstack-telemetry-*      # 遥测
│
├── browse/                     # ★ 核心：持久化浏览器模块
│   ├── src/
│   │   ├── server.ts          # Bun.serve HTTP服务（路由+命令分发）
│   │   ├── browser-manager.ts  # Chromium生命周期+tab管理
│   │   ├── commands.ts         # 命令注册表（READ/WRITE/META三分类）
│   │   ├── snapshot.ts         # ARIA ref系统实现
│   │   ├── read-commands.ts    # 读命令处理
│   │   ├── write-commands.ts   # 写命令处理
│   │   ├── meta-commands.ts    # 元命令处理
│   │   ├── cookie-import-browser.ts  # macOS Keychain解密
│   │   ├── sidebar-agent.ts    # Chrome侧边栏子Agent
│   │   ├── buffers.ts          # 三环缓冲（console/network/dialog）
│   │   └── activity.ts        # 实时活动feed
│   └── test/
│
├── office-hours/              # YC Office Hours
├── plan-ceo-review/           # CEO评审
├── plan-eng-review/           # 工程评审
├── review/                    # 代码review（自动修复）
├── qa/                        # QA浏览器测试
├── ship/                      # 提交流
├── land-and-deploy/          # 部署
├── retro/                     # 周回顾
├── codex/                    # Codex第二意见
├── careful/                   # 危险命令警告
├── freeze/guard/unfreeze/    # 目录锁
└── extension/                # Chrome扩展（侧边栏Agent UI）
```

---

## 28个技能详解

### Sprint流程技能（执行顺序）

| 技能 | 角色 | 输入 | 输出 |
|------|------|------|------|
| `/office-hours` | YC Office Hours | 原始想法 | Design Doc |
| `/plan-ceo-review` | CEO | Design Doc | 产品重新定义（4模式） |
| `/plan-eng-review` | Eng Manager | 批准的计划 | 架构图+测试矩阵+边缘case |
| `/plan-design-review` | Senior Designer | 设计规格 | 维度评分（0-10）+ 改进建议 |
| `/design-consultation` | Design Partner | 产品需求 | 完整设计系统 + Mockup |
| `/review` | Staff Engineer | 代码diff | Bug报告 + **自动修复PR** |
| `/investigate` | Debugger | 错误现象 | 根因分析（3次失败停止） |
| `/design-review` | Designer Who Codes | 设计规格 | 修复后的代码 + 前后截图 |
| `/qa` | QA Lead | staging URL | Bug修复 + 回归测试 |
| `/qa-only` | QA Reporter | staging URL | 纯Bug报告 |
| `/ship` | Release Engineer | 批准的功能 | PR + 覆盖率报告 |
| `/land-and-deploy` | Release Engineer | PR | 生产验证 |
| `/canary` | SRE | 部署后 | 监控报告 |
| `/benchmark` | Performance Engineer | PR | 性能对比报告 |
| `/document-release` | Technical Writer | 代码diff | 更新的文档 |
| `/retro` | Eng Manager | 时间范围 | 团队周报 |

### 浏览器技能

| 技能 | 角色 | 功能 |
|------|------|------|
| `/browse` | QA Engineer | 持久化Chromium，40+命令 |
| `/setup-browser-cookies` | Session Manager | Keychain cookie导入 |

### Power Tools

| 技能 | 功能 |
|------|------|
| `/codex` | OpenAI Codex第二意见 |
| `/careful` | 危险命令警告 |
| `/freeze` | 目录编辑锁 |
| `/guard` | `/careful` + `/freeze` |
| `/unfreeze` | 解除冻结 |
| `/autoplan` | CEO→design→eng自动管道 |
| `/setup-deploy` | 部署配置 |
| `/gstack-upgrade` | 自升级 |

---

## 关键数据结构和流程

### 1. 状态文件（State File）

**路径：** `<project>/.gstack/browse.json`（通过 `BROWSE_STATE_FILE` 环境变量设置）

**结构：**
```typescript
interface BrowseState {
  pid: number;           // Chromium进程PID
  port: number;         // HTTP服务端口（10000-60000随机）
  token: string;        // UUID v4 bearer token（mode 0600）
  startedAt: string;    // ISO timestamp
  binaryVersion: string; // git rev-parse HEAD，版本不匹配则自动重启
}
```

**作用：** CLI通过读取此文件找到运行中的server。如果文件缺失或health check失败，CLI启动新server。

---

### 2. Ref Map（@e1/@e2/@c1）

**RefEntry 结构：**
```typescript
interface RefEntry {
  locator: Locator;      // Playwright Locator对象
  role: string;          // ARIA role (button, link, textbox...)
  name: string;          // ARIA name (button的文本内容)
}
```

**refMap 生命周期：**
```typescript
private refMap: Map<string, RefEntry> = new Map();
// 例: { "e1" → { locator: page.locator('button[name="Submit"]').first(), role: "button", name: "Submit" }, ... }
```

**@c 系列（Cursor-interactive）：**
```typescript
// 在 @c 系列中额外扫描：
// - cursor: pointer 的非标准元素
// - 有 onclick 属性的元素
// - 有 tabindex>=0 的元素
// 用 nth-child 选择器构建 Playwright Locator
private refMap: Map<string, RefEntry> = new Map();
// 例: { "c1" → { locator: page.locator('div:nth-child(3)'), role: "cursor-interactive", name: "Submit" } }
```

**Staleness检测流程：**
```
resolveRef("e3")
  → refMap.get("e3")               // 获取RefEntry
  → entry.locator.count()          // 异步检查元素是否仍存在
  → if count === 0: throw "Ref @e3 is stale — run 'snapshot -i' to get fresh refs"
  → if count > 0: locator.click()  // 正常执行
```

---

### 3. Snapshot 命令流程（snapshot -i）

**核心流程：**
```
1. page.locator('body').ariaSnapshot()  → YAML-like accessibility tree文本

2. 解析每行 → ParsedNode:
   interface ParsedNode {
     indent: number;      // 缩进级别（用于计算depth）
     role: string;       // "button", "link", "textbox"...
     name: string | null; // ARIA name
     props: string;      // 如 "[level=1]"
     children: string;   // 内联文本内容
     rawLine: string;
   }

3. 两遍扫描：
   - 第一遍：统计每个 role+name 组合出现次数（用于 nth() 消歧）
   - 第二遍：分配 @e1, @e2... 并构建 Playwright Locator
     locator = page.getByRole(role, { name: name | undefined }).nth(seenIndex)

4. 存入 refMap: bm.setRefMap(refMap)

5. 输出文本（带缩进）：
   @e1 [button] "Submit"
   @e2 [link] "About"
     @e3 [textbox] "Email"
```

**ARIA tree 示例输入：**
```
- heading "Dashboard" [level=1]
- button "Submit"
- link "About":
  - /url: /about
- textbox "Email"
```

**输出：**
```
@e1 [heading] "Dashboard" [level=1]
@e2 [button] "Submit"
@e3 [link] "About"
@e4 [textbox] "Email"
```

**SnapshotOptions 参数：**
```typescript
interface SnapshotOptions {
  interactive?: boolean;       // -i: 只包含interactive元素
  compact?: boolean;           // -c: 移除空结构节点
  depth?: number;              // -d N: 限制树深度
  selector?: string;           // -s SEL: 作用域限定
  diff?: boolean;              // -D: 与上次snapshot对比
  annotate?: boolean;          // -a: 带ref标注的截图
  outputPath?: string;         // -o: 截图输出路径
  cursorInteractive?: boolean; // -C: 扫描cursor:pointer元素
}
```

---

### 4. 三缓冲系统（Console/Network/Dialog）

**CircularBuffer 实现（50,000条目，O(1) push）：**
```typescript
interface LogEntry {
  timestamp: number;
  level: 'log' | 'warn' | 'error' | 'debug';
  text: string;
}

interface NetworkEntry {
  timestamp: number;
  method: string;
  url: string;
  status?: number;
  duration?: number;
  size?: number;
}

interface DialogEntry {
  timestamp: number;
  type: 'alert' | 'confirm' | 'prompt';
  message: string;
}

// 内存缓冲 → 每秒异步刷盘
consoleBuffer  → ~/.gstack/browse-console.log
networkBuffer  → ~/.gstack/browse-network.log
dialogBuffer   → ~/.gstack/browse-dialog.log
```

**为什么用环缓冲：**
- HTTP请求处理从不阻塞于磁盘I/O
- 日志在server崩溃后仍可恢复（最多1秒数据丢失）
- 内存有界（50K × 3缓冲）
- 磁盘文件只追加，可被外部工具读取

---

### 5. Cookie导入流程（macOS Keychain）

```
用户: $B cookie-import-browser chrome --domain github.com
    ↓
1. 确定浏览器cookie数据库路径（hardcoded常量）
   Chrome: ~/Library/Application Support/Google/Chrome/Default/Cookies
    ↓
2. 复制到临时文件（只读，打开时加SHARED_LOCK）
   → /tmp/.gstack-cookies-{random}.db
   原因：避免SQLite锁冲突
    ↓
3. 调用 macOS Keychain 读取 AES-128-CBC 解密密钥
   （弹窗需要用户点击"Allow"/"Always Allow"）
    ↓
4. PBKDF2(AES key derivation) → 内存解密cookie值
   密钥/解密结果从不写入磁盘
    ↓
5. 构造Playwright cookies数组 → context.addCookies(cookies)
    ↓
6. 启动browser session（已认证状态）
```

**安全约束：**
- Keychain访问需要用户主动授权
- Cookie值仅在内存解密
- 数据库只读副本
- server进程退出时密钥缓存清零

---

### 6. HTTP命令分发流程

**server.ts 路由设计：**
```
POST /command → 主命令入口
GET  /health  → 健康检查（无auth）
GET  /tabs    → tab列表
GET  /refs    → 当前refMap
POST /cookie-picker → cookie选择器UI
GET  /cookie-picker → cookie picker页面
```

**命令分发核心逻辑（commands.ts）：**
```typescript
export const READ_COMMANDS = new Set([
  'text', 'html', 'links', 'forms', 'accessibility',
  'js', 'eval', 'css', 'attrs', 'console', 'network',
  'cookies', 'storage', 'perf', 'dialog', 'is',
]);

export const WRITE_COMMANDS = new Set([
  'goto', 'back', 'forward', 'reload',
  'click', 'fill', 'select', 'hover', 'type', 'press',
  'scroll', 'wait', 'viewport', 'cookie', 'cookie-import',
  'cookie-import-browser', 'header', 'useragent',
  'upload', 'dialog-accept', 'dialog-dismiss',
]);

export const META_COMMANDS = new Set([
  'tabs', 'tab', 'newtab', 'closetab',
  'status', 'stop', 'restart',
  'screenshot', 'pdf', 'responsive', 'chain', 'diff',
  'url', 'snapshot', 'handoff', 'resume',
  'connect', 'disconnect', 'focus', 'inbox', 'watch', 'state', 'frame',
]);

// server.ts 分发：
if (READ_COMMANDS.has(cmd))    → handleReadCommand(cmd, args, bm)
if (WRITE_COMMANDS.has(cmd))   → handleWriteCommand(cmd, args, bm)
if (META_COMMANDS.has(cmd))    → handleMetaCommand(cmd, args, bm, shutdown)
```

---

### 7. BrowserManager 核心状态

```typescript
class BrowserManager {
  // 进程连接
  private browser: Browser | null = null;
  private context: BrowserContext | null = null;
  private pages: Map<number, Page> = new Map();  // tab管理
  private activeTabId: number = 0;
  private nextTabId: number = 1;

  // Ref系统
  private refMap: Map<string, RefEntry> = new Map();
  private lastSnapshot: string | null = null;    // diff基线

  // Dialog处理
  private dialogAutoAccept: boolean = true;
  private dialogPromptText: string | null = null;

  // Watch模式
  private watching = false;
  private watchInterval: ReturnType<typeof setInterval> | null = null;
  private watchSnapshots: string[] = [];

  // Headed模式
  private connectionMode: 'launched' | 'headed' = 'launched';
  private isHeaded: boolean = false;
  private consecutiveFailures: number = 0;

  // 元数据
  public serverPort: number = 0;
}
```

---

### 8. Sidebar Agent 会话管理

**SidebarSession 结构：**
```typescript
interface SidebarSession {
  id: string;              // UUID
  name: string;            // "Chrome sidebar"
  claudeSessionId: string | null;  // 用于 --resume
  worktreePath: string | null;     // git worktree隔离路径
  createdAt: string;       // ISO timestamp
  lastActiveAt: string;
}
```

**Worktree隔离流程：**
```
spawnClaude(userMessage)
    ↓
createWorktree(sessionId)  // 创建独立git worktree
    ↓
git worktree add --detach ~/.gstack/worktrees/{short-id} {current-commit}
    ↓
sidebarAgent进程在worktree中运行claude
    ↓
会话结束后: git worktree remove --force {path}
```

**为什么用worktree：** Claude Code可能在多个标签页同时运行，worktree隔离确保不会发生文件冲突和git状态污染。

---

### 9. Handoff/Resume 流程

```
正常流程: Agent连续执行$browse命令
    ↓
连续3次失败 → $B handoff
    ↓
1. 在真实Chrome窗口打开当前URL
2. 所有cookies/tabs/ localStorage保持
3. 用户在真实浏览器操作解决（CAPTCHA/MFA/人为判断）
4. $B resume
    ↓
重新 snapshot -i → 获取新refs
→ Agent继续执行
```

**实现：** handoff不启动新browser，而是连接到用户已有的真实Chrome（通过Chrome DevTools Protocol）。

---

### 10. SKILL.md 模板系统

```
SKILL.md.tmpl（人类写的prose + {{占位符}}）
       ↓
gen-skill-docs.ts（构建时执行）
       ↓
SKILL.md（提交到git）
```

**占位符体系：**

| 占位符 | 来源 | 生成 |
|--------|------|------|
| `{{COMMAND_REFERENCE}}` | `commands.ts` | 分类命令表 |
| `{{SNAPSHOT_FLAGS}}` | `snapshot.ts` | Flag参考+示例 |
| `{{PREAMBLE}}` | `gen-skill-docs.ts` | 更新检查+session跟踪+贡献者模式 |
| `{{BROWSE_SETUP}}` | `gen-skill-docs.ts` | 二进制发现+安装说明 |
| `{{BASE_BRANCH_DETECT}}` | `gen-skill-docs.ts` | PR目标动态检测 |
| `{{QA_METHODOLOGY}}` | `gen-skill-docs.ts` | /qa和/qa-only共享方法论 |
| `{{REVIEW_DASHBOARD}}` | `gen-skill-docs.ts` | /ship前检查仪表板 |
| `{{TEST_BOOTSTRAP}}` | `gen-skill-docs.ts` | 测试框架检测+CI配置 |
| `{{CODEX_PLAN_REVIEW}}` | `gen-skill-docs.ts` | /plan-ceo-review和/plan-eng-review的跨模型计划评审 |

**Preamble（五件事一次bash命令）：**
```bash
gstack-update-check && \
session_tracker && \
contributor_mode_check && \
echo "PREAMBLE_BLOCK"
```

---

## 与Claude Code的集成方式

### Skill tool接口
```
用户: /office-hours
Claude: → 读取 ~/.claude/skills/gstack/office-hours/SKILL.md
     → 执行技能逻辑
     → 写 Design Doc
```

### CLAUDE.md集成
```markdown
## gstack
- 使用 gstack 的 /browse skill 进行所有网页浏览
- 禁止使用 mcp__claude-in-chrome__* 工具
- 可用技能：/office-hours, /plan-ceo-review, /review, /qa, /ship, ...
```

### 多Agent支持
```bash
./setup --host codex   # 支持 Claude Code / Codex / Gemini / Cursor
```

---

## 重大更新（本月 v5.0.6）

### Inline Self-Review（2026-03-24）

**原有问题：** 每次 review 需要约 25 分钟的 subagent review loop。

**解决方案：** 用 inline self-review checklist 替代。

```
原来: Agent → subagent review loop (25min)
现在: Agent → inline checklist (30s)
```

**质量对比：** 在基准测试集上，inline checklist 与 subagent review 在以下维度无显著差异：
- Bug发现率（真实生产bug）
- False positive率
- 建议可操作性评分

### 其他本月更新
- Brainstorm Server session 目录隔离修复
- Owner-PID lifecycle bug 修复
- `$B watch` 增强（周期性snapshot）

---

## 优缺点

### 优点
1. **完整Sprint覆盖** — 端到端流程，而非工具集合
2. **真实浏览器** — Agent有眼睛，可看真实页面状态
3. **持久化架构** — ~100ms/命令，状态跨命令保持
4. **Ref系统优雅** — 用ARIA tree而非DOM注入，绕开CSP/Shadow DOM
5. **自动化程度高** — review自动修bug，qa自动生成回归测试
6. **安全设计严谨** — Keychain/cookie处理有完整的安全文档
7. **零依赖部署** — 编译后单二进制，无node_modules
8. **MIT许可** — 无Premium tier

### 缺点
1. **macOS only（关键功能）** — Keychain cookie导入只支持macOS，Linux/Windows可用browse但认证flow有限
2. **Chrome扩展依赖** — 侧边栏Agent需要Chrome扩展（Chromium不可用）
3. **学习曲线陡** — 28个技能+多Agent协调需要时间适应
4. **Conductor付费** — 多sprint并行需要 [Conductor](https://conductor.build)
5. **单人背书** — 主要是Garry Tan个人工作流，YC背书但社区验证有限
6. **Bun runtime强依赖** — setup需要Bun v1.0+，非Node.js

---

## 命令分类速查

| 分类 | 命令 |
|------|------|
| **Navigation** | `goto`, `back`, `forward`, `reload`, `url` |
| **Reading** | `text`, `html`, `links`, `forms`, `accessibility` |
| **Inspection** | `js`, `eval`, `css`, `attrs`, `is`, `console`, `network`, `cookies`, `storage`, `perf`, `dialog` |
| **Interaction** | `click`, `fill`, `select`, `hover`, `type`, `press`, `scroll`, `wait`, `upload`, `viewport`, `cookie`, `header`, `useragent`, `dialog-accept`, `dialog-dismiss` |
| **Visual** | `screenshot`, `pdf`, `responsive`, `diff` |
| **Snapshot** | `snapshot [-i] [-c] [-d N] [-s sel] [-D] [-a] [-o path] [-C]` |
| **Tabs** | `tabs`, `tab <id>`, `newtab [url]`, `closetab [id]` |
| **Server** | `status`, `stop`, `restart`, `handoff`, `resume`, `connect`, `disconnect`, `focus` |
| **Meta** | `chain`, `inbox`, `watch [stop]`, `state save|load <name>`, `frame` |

---

## 核心开发审核流程详解

### Preamble 统一的前置动作

每个技能启动时都执行同一个 Preamble Bash 脚本（tier 3 或 4），做的事情完全一样：

```bash
# 1. 升级检查
_UPD=$(gstack-update-check)
[ -n "$_UPD" ] && echo "$_UPD"

# 2. Session跟踪（PPID文件，120分钟过期）
mkdir -p ~/.gstack/sessions && touch ~/.gstack/sessions/"$PPID"
_SESSIONS=$(find ~/.gstack/sessions -mmin -120 -type f | wc -l)

# 3. Contributor模式检测
_CONTRIB=$(gstack-config get gstack_contributor)
_PROACTIVE=$(gstack-config get proactive)

# 4. Repo模式检测（solo vs collaborative）
source <(gstack-repo-mode)
REPO_MODE=${REPO_MODE:-unknown}

# 5. Lake Intro检查（首次运行显示"Boil the Lake"原则）
_LAKE_SEEN=$([ -f ~/.gstack/.completeness-intro-seen ] && echo "yes" || echo "no")

# 6. Telemetry设置检查
_TEL=$(gstack-config get telemetry)

# 7. 遥测开始时间
_TEL_START=$(date +%s)
_SESSION_ID="$$-$(date +%s)"

# 8. 遥测写入 analytics/skill-usage.jsonl
```

这保证了所有技能共享同一套上下文（版本/权限/用户偏好），Agent 无需每次重新问。

---

### 1. /office-hours — YC Office Hours（想法验证）

**触发词：** "brainstorm"、"I have an idea"、"office hours"、"is this worth building"

**核心流程：**

```
用户描述想法
    ↓
运行 preamble（升级检查+telemetry+Lake原则介绍）
    ↓
AskUserQuestion: 选择模式
    ├─ A) Startup mode（YC创业公司模式）
    └─ B) Builder mode（个人项目/hackathon/开源模式）
    ↓
Startup mode：6个强制问题挖掘真实痛点
    1. Demand Reality（需求现实）— 有多少人真的在等这个？
    2. Status Quo（现状替代）— 他们现在用什么？为什么不满？
    3. Desperate Specificity（绝望的具体性）— 描述最窄的用户和最痛的点
    4. Narrowest Wedge（最窄楔子）— 从哪里切进去？
    5. Observation（观察）— 你对这个领域的真实洞察是什么？
    6. Future Fit（未来适配）— 10年后这个市场还存在吗？
    ↓
生成 Design Doc（写文件或更新现有文档）
    ↓
输出 STATUS: DONE / DONE_WITH_CONCERNS / BLOCKED
    ↓
遥测上报（skill=office-hours, outcome={}, duration={}）
```

**Builder mode 额外步骤：**
- 设计思维头脑风暴（发散→收敛）
- 竞品分析（Layer 1/2/3 search）
- Hackathon 时间线规划

**关键设计细节：**
- 6个问题必须全部回答，缺一不可（"forcing questions"）
- AskUserQuestion 必须用固定4段式格式（Re-ground → Simplify → Recommend → Options）
- Plan 文件路径通过内容搜索自动发现（conversation context primary，content search fallback）
- `Completeness Principle`：每个选项必须标注 Completeness: X/10

---

### 2. /plan-ceo-review — CEO/Founder 评审（产品战略）

**触发词：** 用户完成 Design Doc 后自动建议，或用户主动调用

**前置依赖：** 需要 Design Doc 或 office-hours 输出

**核心流程：**

```
读取 Design Doc 或 plan 文件
    ↓
运行 preamble
    ↓
AskUserQuestion: 这个产品值得做吗？
    ↓
6个CEO强制评审维度：
    1. 市场规模（Market Size）
    2. 竞争护城河（Competitive Moat）
    3. 团队适配（Team Fit）
    4. 10星产品潜力（10x Product）
    5. 增长策略（Go-to-market）
    6. 退出路径（Exit optionality）
    ↓
4种扩张/收缩决策：
    ├─ Expand（扩张）：全力投入
    ├─ Selective Expand（选择性扩张）：专注某个细分
    ├─ Maintain（维持）：保持现状，不投入更多
    └─ Contract（收缩）：关停或转型
    ↓
将决策写入 plan 文件的 "CEO Review Decisions" 章节
    ↓
更新 plan 文件的 GSTACK REVIEW REPORT（Review Status 表）
    ↓
输出 PR/MR 链接 + STATUS
```

**关键设计细节：**
- `/autoplan` 会自动依次调用 plan-ceo-review → plan-eng-review → plan-design-review，形成完整评审管道
- CEO Review 可以被 `/autoplan` 跳过（通过配置），但单独调用时必须完成
- 每次评审结果写入 `~/.gstack/review-logs/review-{timestamp}.jsonl`，Ship 前读取

---

### 3. /plan-eng-review — Engineering Manager 评审（架构测试）

**触发词：** CEO Review 完成后，或用户主动调用

**前置依赖：** 需要 plan 文件（含 CEO 决策）

**核心流程：**

```
读取 plan 文件
    ↓
运行 preamble
    ↓
AskUserQuestion: 确认实现方案（基于 CEO Review 的产品方向）
    ↓
6个EM强制评审维度：
    1. 架构设计（Architecture）
    2. 数据模型（Data Model）
    3. API 设计（API Design）
    4. 边缘 case（Edge Cases）
    5. 测试矩阵（Test Matrix）— 每个功能点对应的测试类型
    6. 部署策略（Deployment Strategy）
    ↓
ASCII 图：画出关键数据流
    ↓
输出 plan-eng-review 章节（更新 plan 文件）
    ↓
更新 GSTACK REVIEW REPORT
    ↓
遥测上报
```

**关键设计细节：**
- 必须输出 ASCII 数据流图（文字描述不够，必须可视化）
- Test Matrix：每个功能点 → 测试类型（单元/集成/E2E/压力测试）的映射表
- Edge Cases：列出所有边界条件和失败模式
- 如果 plan 文件中没有可操作项（actionable items），跳过完成度审计

---

### 4. /review — Pre-landing PR Review（代码质量关）

**触发词：** "review this PR"、"code review"、"pre-landing review"

**前置依赖：** 最好是 /ship 触发（自动调用），但也可以单独运行

**核心流程（非交互式，自动化程度高）：**

```
Step 0: 平台检测
    → git remote get-url → 判断 GitHub/GitLab/unknown
    → gh auth status / glab auth status → 确认CLI可用性
    → 确定 base branch（PR目标分支或 default branch）
    ↓
Step 1: 分支检查
    → git branch --show-current
    → 如果在 base branch → abort
    → git fetch origin <base> --quiet && git diff origin/<base> --stat
    → 如果没有 diff → abort
    ↓
Step 1.5: Scope Drift 检测（关键！）
    → 读取 TODOS.md + PR description + commit messages
    → 提取 stated intent（本来要做什么）
    → 对比 git diff 中的文件变更 vs stated intent
    → 如果 scope drift 严重（建了不该建的），报告并 stop
    ↓
Step 2: Plan File 发现
    → 优先从 conversation context 获取 plan 文件路径
    → fallback：内容搜索 ~/.claude/plans / .gstack/plans
    → 验证 plan 文件相关性
    ↓
Step 3: 可操作项提取（从 plan file）
    → 提取 checkbox items、numbered steps、imperative statements
    → 最多50项，按类型分类（CODE/TEST/MIGRATION/CONFIG/DOCS）
    ↓
Step 4: 代码质量审查（4大类）
    ├─ SQL Safety：参数化查询、ORM使用、事务边界
    ├─ LLM Trust Boundary：prompt注入风险、输出验证
    ├─ Conditional Side Effects：条件分支中的副作用
    └─ Structural Issues：错误处理、资源释放、并发问题
    ↓
Step 5: 自动修复
    → 能自动修的（dead code、N+1查询、stale comments）→ 直接 Edit
    → 需要用户判断的 → AskUserQuestion（BLOCK级别才停）
    ↓
Step 6: 写评审报告 → PR comment 或 stdout
    ↓
Step 7: 更新 review log → ~/.gstack/review-logs/review-{timestamp}.jsonl
    ↓
遥测上报
```

**关键设计细节：**
- `/review` 是自动化程度最高的技能，几乎不需要用户交互
- 3次尝试后失败 → STOP + escalate（Iron Law）
- SQL Safety 是重点审查项（gstack 的核心场景之一是 YC 创业公司，数据操作多）
- Scope Drift 检测是独有机制：防止"本来要做A，结果做了B"的情况

---

### 5. /qa — QA Lead 浏览器测试（真实浏览器+Bug修复）

**触发词：** "qa"、"test this site"、"find bugs"、"test and fix"

**前置依赖：** staging 环境 URL

**核心流程（迭代式 Fix Loop）：**

```
Step 0: 平台检测 + base branch（同上）
    ↓
Step 1: AskUserQuestion: 选择测试深度
    ├─ A) Quick（critical + high severity）
    ├─ B) Standard（+ medium severity）
    └─ C) Exhaustive（+ cosmetic）
    ↓
Step 2: 获取 staging URL
    → 如果有 PR → gh pr view --json url → staging 环境
    → 如果没有 → AskUserQuestion 请求 URL
    ↓
Step 3: 健康度基线评分（Before Score）
    → 运行 $B browse snapshot -i
    → 评估页面渲染、表单、链接、console errors
    → 记录 baseline health score
    ↓
===== 迭代 Fix Loop（Bug → Fix → Re-verify）=====
Loop:
    a) 探索性测试（用 $B browse 工具）
       → $B goto <staging_url>
       → $B snapshot -i（获取可交互元素）
       → $B click @e3、$B fill @e5 "test" 等操作
       → $B console --errors（检查 console 错误）
       → $B network（检查 API 响应）
    
    b) 发现 bug
       → 分类：Critical / High / Medium / Cosmetic
       → 记录 bug：描述 + 重现步骤 + 截图
    
    c) AskUserQuestion: 如何处理
       → A) Fix it now（立即修复，推荐）
       → B) Fix after qa（记入 TODO）
       → C) Skip（跳过）
    
    d) 如果选 A：修复 bug
       → 读源码 → Edit/Write 修改
       → 原子提交（一个 bug 一个 commit）
       → 重新运行 $B verify 验证修复
       → 如果 verify 通过：标记 FIXED
       → 如果 verify 失败：重新 Fix（最多3次）
    
    e) 重复直到所有 bug 处理完
=========================================
    ↓
Step 4: 生成健康度报告（After Score）
    → 修复前 vs 修复后 health score 对比
    → FIXED / WONTFIX / REGRESSION 分类汇总
    ↓
Step 5: 生成回归测试（Boil the Lake）
    → 根据发现的 bug，生成 Playwright 测试脚本
    → 写入 test/ 目录
    → commit 原子化
    ↓
Step 6: Ship-Readiness Summary
    → 评估是否可以 ship（基于剩余 critical/high bug）
    → 输出建议
    ↓
遥测上报
```

**关键设计细节：**
- Fix Loop 是 `/qa` 独有的：发现bug → 立即修 → 验证 → 再测 → 直到clean
- `$B` 命令通过 `$B snapshot -i` → `$B click @e3` → `$B fill @e5 "text"` 序列操作，模拟真实用户交互
- 每次修复后自动 re-verify，不需要用户重新触发
- 回归测试自动生成（Completeness Principle：QA发现了的所有场景都要有测试）
- 三层测试粒度（Quick/Standard/Exhaustive）由用户选择

---

### 6. /ship — Release Engineer 提交流（全自动化）

**触发词：** "ship"、"deploy"、"push to main"、"create a PR"

**前置依赖：** Review readiness dashboard（Review 必须是 CLEAR）

**核心流程（Step by Step）：**

```
Step 0: 平台检测（同 review）
    ↓
Step 1: Pre-flight Check
    → git branch --show-current
    → 如果在 base branch → abort
    → git status + git diff --stat
    → uncommitted changes → 自动包含（不询问）
    ↓
Step 2: Review Readiness Dashboard
    → gstack-review-read → 读取 ~/.gstack/review-logs/
    → 显示各 Review 的 Runs / Last Run / Status
    ┌─────────────────────────────────────────────────────┐
    │ Eng Review      | 1   | 2026-03-16 15:00 | CLEAR  │
    │ CEO Review      | 0   | —                | —      │
    │ Design Review   | 0   | —                | —      │
    │ Adversarial     | 0   | —                | —      │
    └─────────────────────────────────────────────────────┘
    ↓
    如果 Eng Review 不是 CLEAR → BLOCK（需要先 review）
    如果有 ASK items → AskUserQuestion（是否继续）
    ↓
Step 3: Base Branch 同步
    → git fetch origin <base>
    → git merge origin/<base> --no-edit
    → 如果有冲突 → 尝试 auto-merge
    → 如果 auto-merge 失败 → BLOCK（显示冲突文件）
    ↓
Step 3.4: 测试覆盖率 Gate
    → 运行测试套件
    → 计算覆盖率
    → 如果覆盖率 < 阈值（如 < 70%）→ AskUserQuestion（是否override）
    → 硬 gate：coverage 低于阈值必须用户确认才能继续
    ↓
Step 3.45: Plan Items 完成度审计
    → 读取 plan file 的 actionable items
    → 检查每个 CODE/TEST/MIGRATION item 的完成状态
    → 如果有 item NOT DONE 且无用户 override → BLOCK
    ↓
Step 3.47: Plan Verification Failures
    → 验证测试是否真的覆盖了 plan 中的要求
    → 如果测试覆盖不足 → 自动生成缺失测试
    ↓
Step 4: 版本号 Bump（语义化版本）
    → AskUserQuestion（如果需要 MAJOR/MINOR bump）
    → MICRO/PATCH → 自动决定
    → 更新 VERSION 或 package.json
    ↓
Step 5: CHANGELOG 更新
    → 从 git diff 自动生成 changelog 条目
    → 格式：- {feature/fix}: {description}
    → 追加到 CHANGELOG.md
    ↓
Step 6: Commit + Push
    → git add -A
    → git commit -m "release: v{x.y.z} {changelog summary}"
    → git push origin HEAD
    ↓
Step 7: 创建 PR
    → gh pr create / glab mr create
    → PR body 包含：
      - CHANGELOG 条目
      - Review readiness 状态
      - Coverage 报告
      - Ship-readiness summary
    ↓
输出 PR URL
    ↓
遥测上报
```

**关键设计细节：**
- `/ship` 是完全非交互式的（用户说 ship = 全自动执行）
- Review Readiness Dashboard 是强制 gate（Eng Review 不是 CLEAR 就停下）
- 测试覆盖率是硬 gate，不是软检查
- 版本号 bump：MICRO/PATCH 自动，MINOR/MAJOR 需要用户确认
- Plan items 完成度检查：如果 plan 里写了要做的事没做完，不让 ship

---

### 7. /investigate — Debugger 系统性调试

**触发词：** "debug"、"investigate"、"why is this broken"

**核心流程（Iron Law：3次失败后停止）：**

```
Step 1: 复现问题
    → $B goto <failing_url> 或本地运行命令
    → 记录错误现象（截图 + console + network）
    ↓
Step 2: 假设生成
    → 根据错误信息，列出3个最可能的根因
    → 优先级排序
    ↓
Step 3: 验证假设
    → 用 Read/Grep 检查源码
    → 用 $B js <expr> 在页面上下文执行 JS
    → 用 Bash 运行诊断命令
    ↓
Step 4: 修复
    → 如果找到根因 → Edit 修复
    → 运行验证
    ↓
    如果失败 → 回到 Step 2（下一个假设）
    ↓
    如果3次都失败 → STOP + escalate
    （不重复同样的错误路径）
    ↓
Step 5: 写 Debug Report
    → 根因分析
    → 修复方案
    → 防止建议（如何测试这个不会在其他地方出现）
    ↓
遥测上报
```

**关键设计细节：**
- "Iron Law"：同一路径试3次就停，防止 Agent 在错误方向上无限循环
- 每次失败后要明确换假设，不是重复试同样的修复
- Debug Report 要包含"防止建议"（regression test）

---

### 8. /autoplan — CEO→Design→Eng 自动管道

**触发词：** "autoplan"、"run the full review pipeline"

**核心流程（顺序执行4个 Review）：**

```
Step 1: AskUserQuestion: 选择模式
    ├─ A) Full pipeline（CEO→Design→Eng 全链路）
    ├─ B) Eng only（只跑工程评审）
    └─ C) Custom（选择性执行）
    ↓
If Full pipeline:
    a) /office-hours（如果还没有 Design Doc）
    b) /plan-ceo-review（产品战略）
    c) /plan-design-review（设计质量）
    d) /plan-eng-review（工程架构）
    ↓
If Eng only:
    → /plan-eng-review
    ↓
每个 Review 完成后：
    → 更新 plan 文件的 GSTACK REVIEW REPORT
    → Review 结果写入 ~/.gstack/review-logs/
    ↓
输出完整的 Review 汇总表
    ↓
遥测上报
```

**关键设计细节：**
- `/autoplan` 是 gstack 的"一键启动完整评审"入口
- 每个 Review 完成后都更新同一个 plan 文件（所以最后有完整的 Review Report）
- Review 结果持久化到 `~/.gstack/review-logs/`，被 `/review` 和 `/ship` 读取（跨会话共享）

---

### 9. 跨技能数据流

```
Plan File（共享文档）
    ↑
    ├── /office-hours → 写入 Plan: Overview + Vision
    ├── /plan-ceo-review → 写入 Plan: CEO Decisions
    ├── /plan-eng-review → 写入 Plan: Architecture + Test Matrix
    └── /plan-design-review → 写入 Plan: Design Spec

~/.gstack/review-logs/（Review 结果持久化）
    ↑
    ├── /review → 写入 review-{timestamp}.jsonl
    ├── /plan-eng-review → 写入 plan-eng-review-{timestamp}.jsonl
    ├── /plan-ceo-review → 写入 plan-ceo-review-{timestamp}.jsonl
    └── /autoplan → 调用以上全部

~/.gstack/review-logs/
    ↓ (被读取)
    /ship → 读取 Review Readiness Dashboard
    /review → 读取历史 Review 状态

TODOS.md（Scope drift 对比基准）
    ↓
    /review → 对比 Plan items vs 实际 diff
    /ship → Plan items 完成度审计
```

---

### 10. 统一协议（所有技能共享）

**Completion Status Protocol：**
每个技能结束时必须报告：
- `DONE` — 全部完成，每条结论有证据
- `DONE_WITH_CONCERNS` — 完成但有问题需告知用户
- `BLOCKED` — 无法继续，说明阻塞原因和已尝试的步骤
- `NEEDS_CONTEXT` — 缺少必要信息，明确说明需要什么

**Escalation 规则（Iron Law）：**
- 同一任务3次尝试失败 → STOP
- 安全敏感变更不确定 → STOP
- 超出可验证范围 → STOP
- Escalation 格式：`STATUS: BLOCKED | REASON: ... | ATTEMPTED: ... | RECOMMENDATION: ...`

**Boil the Lake 原则：**
AI让边际成本接近零，所以永远选完整方案而非捷径：
- Feature：完整实现 vs 概念验证 → 选完整
- Test：100%覆盖 vs 只测主路径 → 选100%
- Bug fix：全部边缘case vs 只修主路径 → 选全部

**AskUserQuestion 固定格式：**
1. Re-ground（重述上下文）
2. Simplify（让16岁能看懂）
3. Recommend（推荐方案+Completeness评分）
4. Options（A/B/C并列）
