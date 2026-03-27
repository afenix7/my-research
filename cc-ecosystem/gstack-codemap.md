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
_UPD=$(~/.claude/skills/gstack/bin/gstack-update-check 2>/dev/null || \
  .claude/skills/gstack/bin/gstack-update-check 2>/dev/null || true)
[ -n "$_UPD" ] && echo "$_UPD" || true

mkdir -p ~/.gstack/sessions && touch ~/.gstack/sessions/"$PPID"
_SESSIONS=$(find ~/.gstack/sessions -mmin -120 -type f 2>/dev/null | wc -l | tr -d ' ')
find ~/.gstack/sessions -mmin +120 -type f -delete 2>/dev/null || true

_CONTRIB=$(~/.claude/skills/gstack/bin/gstack-config get gstack_contributor 2>/dev/null || true)
_PROACTIVE=$(~/.claude/skills/gstack/bin/gstack-config get proactive 2>/dev/null || echo "true")
_PROACTIVE_PROMPTED=$([ -f ~/.gstack/.proactive-prompted ] && echo "yes" || echo "no")

_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
echo "BRANCH: $_BRANCH"
echo "PROACTIVE: $_PROACTIVE"
echo "PROACTIVE_PROMPTED: $_PROACTIVE_PROMPTED"

source <(~/.claude/skills/gstack/bin/gstack-repo-mode 2>/dev/null) || true
REPO_MODE=${REPO_MODE:-unknown}
echo "REPO_MODE: $REPO_MODE"

_LAKE_SEEN=$([ -f ~/.gstack/.completeness-intro-seen ] && echo "yes" || echo "no")
echo "LAKE_INTRO: $_LAKE_SEEN"

_TEL=$(~/.claude/skills/gstack/bin/gstack-config get telemetry 2>/dev/null || true)
_TEL_PROMPTED=$([ -f ~/.gstack/.telemetry-prompted ] && echo "yes" || echo "no")
_TEL_START=$(date +%s)
_SESSION_ID="$$-$(date +%s)"
echo "TELEMETRY: ${_TEL:-off}"
echo "TEL_PROMPTED: $_TEL_PROMPTED"

mkdir -p ~/.gstack/analytics
echo '{"skill":"SKILL_NAME","ts":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","repo":"'$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || echo "unknown")'"}' >> ~/.gstack/analytics/skill-usage.jsonl 2>/dev/null || true
```

**Upgrade Available 检测：** 如果输出包含 `UPGRADE_AVAILABLE <old> <new>`，则读取 `~/.claude/skills/gstack/gstack-upgrade/SKILL.md` 并执行内联升级流程（auto-upgrade 若已配置，否则用 AskUserQuestion 询问）。

**Lake Intro（首次运行）：** 如果 `LAKE_INTRO` = `no`，在继续前介绍 Completeness Principle（Boil the Lake 原则），并提供打开 `https://garryslist.org/posts/boil-the-ocean` 的选项。运行 `touch ~/.gstack/.completeness-intro-seen` 标记为已读。

**Telemetry 询问（首次运行）：** 如果 `TEL_PROMPTED` = `no` 且 `LAKE_INTRO` = `yes`，使用 AskUserQuestion：
> Help gstack get better! Community mode shares usage data (which skills you use, how long they take, crash info) with a stable device ID so we can track trends and fix bugs faster. No code, file paths, or repo names are ever sent.
Options: A) Help gstack get better! (recommended) | B) No thanks

**Proactive 询问：** 如果 `PROACTIVE_PROMPTED` = `no` 且 `TEL_PROMPTED` = `yes`，使用 AskUserQuestion 询问是否开启主动建议模式。

**Contributor Mode：** 如果 `_CONTRIB` = `true`，在每个主要工作流步骤结束时评分 gstack 使用体验（0-10），若非满分且有可操作的 bug/改进则写入 `~/.gstack/contributor-logs/`。

**Telemetry 结束时上报：**
```bash
_TEL_END=$(date +%s)
_TEL_DUR=$(( _TEL_END - _TEL_START ))
~/.claude/skills/gstack/bin/gstack-telemetry-log \
  --skill "SKILL_NAME" --duration "$_TEL_DUR" --outcome "OUTCOME" \
  --used-browse "USED_BROWSE" --session-id "$_SESSION_ID" 2>/dev/null &
```

---

### 1. /office-hours — YC Office Hours（想法验证）

**YAML Frontmatter：**
```yaml
---
name: office-hours
preamble-tier: 3
version: 2.0.0
description: |
  YC Office Hours — Refactor Problems, Write Design Docs.
  Six forcing questions surface the real pain, the narrowest wedge,
  and the true insight before writing a single line of code.
  Use when asked "is this worth building", "should I pivot",
  or to refactor a vague idea into a fundable plan.
---
```

**核心流程（Phase by Phase）：**

```
Phase 0: Warm Up
    → 运行 Preamble（upgrade check + telemetry + repo mode）
    → 检测 _LAKE_SEEN / _TEL_PROMPTED / _PROACTIVE_PROMPTED
    → 运行对应引导（Lake Intro / Telemetry / Proactive）
    ↓
Phase 1: Mode Select（AskUserQuestion — STOP until user responds）
    → Re-ground: 项目背景 + 当前分支
    → Simplify: YC vs Builder 两种模式的核心差异
    → Recommend: 选 A（Startup mode）—— 6个 forcing questions 确保深度
    → Options:
        A) Startup mode（推荐）—— 完整 YC 流程，6个 forcing questions
        B) Builder mode —— 设计思维 + 竞品分析 + Hackathon 时间线
        Completeness: A=10/10, B=7/10
    ↓
Phase 2A: Startup Mode — 6个 Forced Questions（每个都 STOP + AskUserQuestion）
    1. Demand Reality（需求现实）
       → 问: 真正在等这个产品的人有多少？他们多绝望？
       → STOP — AskUserQuestion 确认痛点具体性
    2. Status Quo（现状替代）
       → 问: 他们现在用什么？为什么不满？替代方案是什么？
       → STOP — AskUserQuestion 确认替代方案
    3. Desperate Specificity（绝望的具体性）
       → 问: 描述最窄的用户画像和最痛的点
       → STOP — AskUserQuestion 确认用户/痛点具体性
    4. Narrowest Wedge（最窄楔子）
       → 问: 从哪里切进去？第一个版本能解决多少人的多少问题？
       → STOP — AskUserQuestion 确认切入点
    5. Observation（观察）
       → 问: 你对这个领域的真实洞察是什么？别人错过了什么？
       → STOP — AskUserQuestion 确认洞察
    6. Future Fit（未来适配）
       → 问: 10年后这个市场还存在吗？这个公司能长多大？
       → STOP — AskUserQuestion 确认未来适配性
    ↓
Phase 2B: Builder Mode — 3个步骤
    1. 头脑风暴（Divergence）→ 发散：尽可能多列出解决方案/方向
    2. 竞品分析（Layer 1/2/3 search）→ Layer 1已有 Layer 2新方案 Layer 3第一性原理
    3. 收敛（Convergence）→ 选最窄楔子 + 最快路径
    ↓
Phase 3: Forced Convergence
    → 从每个问题提炼: Pain / Wedge / Insight / Future
    → 如果有 TODOS.md → AskUserQuestion: A) Add to TODOS.md  B) Skip
    ↓
Phase 3.5: Cross-Model Second Opinion（AskUserQuestion）
    → Re-ground: Idea 已经过 6个 forcing questions
    → Simplify: 用另一个 AI 模型验证的价值
    → Recommend: B（Skip）—— 已经深度挖掘
    → Options:
        A) Get outside voice — Codex 或 Claude subagent 获取第二意见
        B) Skip — 继续输出 Design Doc
        Completeness: A=9/10, B=7/10
    ↓
Phase 4: Design Doc Drafting
    → 写入/更新 Design Doc（`~/.gstack/projects/{slug}/` 或 conversation context 发现）
    → 结构: Overview → Pain → Wedge → Solution → Why Now → Why Us →
           Competition → Business Model → ask_user_question(launch)
    ↓
Phase 5: Quality Bar
    → Completeness 检查: 每个 section Completeness 评分
    → 10/10: 完整回答了所有问题；7/10: 有 section 跳过或模糊；低于 7 必须补充
    ↓
Phase 6: Output
    → AskUserQuestion（launch）:
        A) Promote to `docs/designs/{FEATURE}.md`（推荐，Commit to repo）
        B) Keep in `~/.gstack/projects/`（本地，个人参考）
        C) Skip — Exit Plan Mode
    ↓
Phase 7: Handoff Notes Cleanup
    → eval "$(~/.claude/skills/gstack/bin/gstack-slug 2>/dev/null)"
    → rm -f ~/.gstack/projects/$SLUG/*-$BRANCH-*.md 2>/dev/null || true
    ↓
STATUS: DONE / DONE_WITH_CONCERNS / BLOCKED
```

**Completeness Principle：** 每个 Phase 的输出选项必须标注 Completeness: X/10。Effort 参考表：
| Task type | Human team | CC+gstack | Compression |
|-----------|-----------|-----------|-------------|
| Feature | 1 week | 30 min | ~30x |
| Tests | 1 day | 15 min | ~50x |
| Bug fix | 4 hours | 15 min | ~20x |

**关键机制：**
- 6个 forcing questions 必须全部回答（缺一不可），每个后 STOP + AskUserQuestion
- Plan 文件路径: conversation context primary，content search fallback
- REPO_MODE=solo: 主动修复看到的问题；REPO_MODE=collaborative: Flag via AskUserQuestion
- 输出文件: `~/.gstack/projects/{slug}/{branch}/plan.md`
- Commit 时: `git add` + `git commit`（bisectable commits）

---

### 2. /plan-ceo-review — CEO/Founder 评审（产品战略）

**YAML Frontmatter：**
```yaml
---
name: plan-ceo-review
preamble-tier: 4
version: 2.0.0
description: |
  CEO/Founder plan review — 4 modes (EXPANSION / SELECTIVE / HOLD / REDUCTION),
  10 review dimensions, automatic scope expansion with cherry-pick ceremony.
  Works in plan mode. Use when a plan has been written and needs a go/no-go
  decision on scope, trajectory, and strategic fit.
---
```

**前置依赖：** Design Doc 或 plan 文件（含 `/office-hours` 输出）

**核心流程（Step 0 → 10 Sections）：**

```
Step 0: Pre-Review Audit
    → git log --oneline -15 + git diff <base> --stat
    → 读取 plan 文件 + CLAUDE.md + DESIGN.md（如果存在）+ TODOS.md
    ↓
Step 0A: AskUserQuestion — 产品值得做吗？（STOP until user responds）
    → Re-ground: 项目/分支 + 当前 plan 内容摘要
    → Simplify: 问"这个产品/功能值得投入吗"
    → Recommend: A（值得）—— Boil the Lake 原则
    → Options: A) Yes — proceed  B) No — exit BLOCKED
    Completeness: A=10/10, B=2/10
    ↓
Step 0B: AskUserQuestion — 选择模式（STOP until user responds）
    → Options:
        A) EXPANSION — Full scope, push up, add platform/infrastructure
        B) SELECTIVE EXPANSION — Hold + cherry-pick opportunity ceremony
        C) HOLD SCOPE — Maintain, no more investment
        D) REDUCTION — Cut scope to minimum viable
        Completeness: A=10/10 (EXPANSION pushes hardest)
    ↓
Step 0C: 实现路径选择（仅 EXPANSION/SELECTIVE，AskUserQuestion）
    → 如果选 EXPANSION: A) Ideal architecture  B) Minimal viable approach
    → 如果选 SELECTIVE: 同样 AskUserQuestion
    ↓
Step 0D: Scope Expansion Ceremony（仅 EXPANSION/SELECTIVE，AskUserQuestion）
    → 提出机会清单（scope expansion + delight items）
    → 逐项询问: A) Add to scope  B) Skip
    → 最终承诺: Accepted / Deferred / Skipped
    ↓
===== 10个 Review Sections（每个后 STOP + AskUserQuestion）=====
    ↓
Section 1: Architecture Review
    → 评估: 系统设计 + 依赖图 + 数据流（Happy/Nil/Empty/Error四路径）
    → 状态机 ASCII 图 + 扩展性 + 单点故障 + 安全边界
    → EXPANSION: "What would make this architecture beautiful?"
    → SELECTIVE: 评估 cherry-pick 对架构的影响
    → STOP + AskUserQuestion
    ↓
Section 2: Error & Rescue Map（强制，不可跳过）
    → 表格: METHOD | WHAT_CAN_GO_WRONG | EXCEPTION_CLASS | RESCUED? |
           RESCUE_ACTION | USER_SEES
    → Generic error catching (`rescue StandardError`) 永远是 smell
    → GAP → 指定 rescue action
    → LLM/AI 调用: malformed / empty / hallucinated JSON / refusal 都是独立 failure mode
    → STOP + AskUserQuestion
    ↓
Section 3: Security & Threat Model
    → 攻击面扩展 + 输入验证 + 授权 + 凭证管理 + 依赖风险
    → 数据分类（PII/支付/凭证）+ 注入向量
    → STOP + AskUserQuestion
    ↓
Section 4: Data Flows
    → 端到端数据流（从请求到持久化）
    → 每个存储的读/写/删除路径
    → STOP + AskUserQuestion
    ↓
Section 5: Go-to-Market（EXPANSION 强制，SELECTIVE 推荐）
    → 用户旅程 + 获取渠道 + 转化漏斗
    → 关键指标（North Star metric）
    → 竞争对手对比 + 独特优势
    → STOP + AskUserQuestion
    ↓
Section 6: Business Model
    → 收入来源 + 定价策略 + LTV/CAC
    → STOP + AskUserQuestion
    ↓
Section 7: Competition & Moat
    → 直接/间接竞争 + 进入壁垒 + 技术护城河
    → 停止竞争的时间点
    → STOP + AskUserQuestion
    ↓
Section 8: Why Now
    → 为什么现在做而非 6个月前/后
    → 市场时机 + 监管变化 + 技术成熟度
    → STOP + AskUserQuestion
    ↓
Section 9: Team & Cohom
    → Founder/Team fit + 历史交付能力
    → STOP + AskUserQuestion
    ↓
Section 10: Legal/Regulatory
    → 已知监管风险 + 合规路径
    → STOP + AskUserQuestion
    ↓
===== Post-Review 步骤 =====
    ↓
Scope Challenge（Step 0 记录）
    → 如果 scope drift 严重: A) Accept as-is  B) Reduce scope
    ↓
Completion Summary（填充并显示）
    → 格式化的汇总表（10 sections 各状态）
    ↓
Review Log
    → 命令写入 ~/.gstack/:
~/.claude/skills/gstack/bin/gstack-review-log \
  '{"skill":"plan-ceo-review","timestamp":"TIMESTAMP","status":"STATUS",\
"unresolved":N,"critical_gaps":N,"mode":"MODE",\
"scope_proposed":N,"scope_accepted":N,"scope_deferred":N,"commit":"COMMIT"}'
    ↓
Review Readiness Dashboard
    → gstack-review-read → 显示仪表板
    → 包含: CEO Review / Design Review / Adversarial / Outside Voice 各状态
    ↓
Plan File Review Report（写文件）
    → 检测 plan 文件是否存在 ## GSTACK REVIEW REPORT
    → 存在则替换，不存在则追加到末尾
    → 格式: markdown table（Review | Trigger | Why | Runs | Status | Findings）
    ↓
Next Steps — Review Chaining（AskUserQuestion）
    → 根据 Dashboard 结果推荐: A) /plan-eng-review  B) /plan-design-review  C) Skip
    ↓
STATUS: DONE / DONE_WITH_CONCERNS / BLOCKED
```

**关键机制：**
- **4种模式**: EXPANSION（全速推进）/ SELECTIVE（选择性扩张+樱桃采摘仪式）/ HOLD（维持）/ REDUCTION（收缩）
- **Scope Expansion Ceremony**: EXPANSION/SELECTIVE 时自动提出扩展机会清单，逐项 AskUserQuestion
- **Error & Rescue Map**: 强制表格，Generic rescue 是 smell，LLM failure mode 独立处理
- **10 Sections 全部 STOP + AskUserQuestion**: 不 batch，每个 review 后暂停
- **Review Log**: 写入 `~/.gstack/`（非项目文件），被 `/ship` 的 Dashboard 读取
- **Plan File Review Report**: 写入 plan 文件末尾的 `## GSTACK REVIEW REPORT` section

**输出格式：**
- `~/.gstack/review-logs/plan-ceo-review-{timestamp}.jsonl` — Review 结果
- `~/.gstack/analytics/skill-usage.jsonl` — Telemetry
- `~/.gstack/analytics/eureka.jsonl` — 第一性原理洞察（Eureka moments）
- Plan 文件: `## GSTACK REVIEW REPORT` section 追加/替换

**与 /autoplan 的关系:** `/autoplan` 自动依次调用 plan-ceo-review → plan-design-review → plan-eng-review，形成完整评审管道。CEO Review 单独调用时必须完成全部 10 sections。

---

### 3. /plan-eng-review — Engineering Manager 评审（架构测试）

**YAML Frontmatter：**
```yaml
---
name: plan-eng-review
preamble-tier: 3
version: 2.0.0
description: |
  Engineering Manager plan review — 11 review sections, 10-section review
  (architecture through long-term trajectory), plus 1 design section.
  Each section: rate before/after, explain gap, fix the plan to get to 10.
  Works in plan mode. Required shipping gate.
---
```

**前置依赖：** plan 文件（含 CEO Review 决策）

**核心流程：**

```
Step 0: Pre-Review Audit（同 plan-ceo-review）
    → git log --oneline -15 + git diff <base> --stat
    → 读取 plan 文件 + CLAUDE.md + DESIGN.md（如果存在）+ TODOS.md
    ↓
Step 0A: AskUserQuestion — 确认 scope（STOP until user responds）
    → A) Accept scope as-is
    → B) Propose scope reduction（提出具体缩减项，逐项 AskUserQuestion）
    ↓
===== 11个 Review Sections（Architecture + Code Quality + Test + Performance）=====
    ↓
Section 1: Architecture Review
    → ASCII 依赖图 + 扩展性 + 单点故障 + 状态机
    → 评估: Service/Model/Concern 划分
    → STOP + AskUserQuestion
    ↓
Section 2: Error & Rescue Map（强制）
    → 表格（同 plan-ceo-review Section 2）
    → 评估: Generic rescue 检测 + LLM failure mode
    → STOP + AskUserQuestion
    ↓
Section 3: Security & Threat Model
    → 攻击面 + 输入验证 + 授权 + 凭证 + 依赖
    → STOP + AskUserQuestion
    ↓
Section 4: Data Flows
    → 端到端数据流 + 存储路径
    → STOP + AskUserQuestion
    ↓
Section 5: Code Quality Review
    → 评估: 抽象层次 + 命名 + 错误处理 + 日志 + 可测试性
    → STOP + AskUserQuestion
    ↓
Section 6: Test Review
    → 表格: CODEPATH | FAILURE_MODE | TEST_TYPE | ISOLATED?
    → Test Coverage Audit: 测试是否覆盖了所有关键路径
    → ASCII 图: 测试与代码路径的映射
    → AskUserQuestion: 对每个 gap — A) Fix it now  B) Log as TODO
    ↓
Section 7: Performance Review
    → 评估: N+1 查询 + 循环复杂度 + 索引策略 + 缓存
    → STOP + AskUserQuestion
    ↓
Section 8: Observability Review
    → 评估: 日志 + 指标 + 告警 + 分布式追踪
    → STOP + AskUserQuestion
    ↓
Section 9: Deployment Review
    → 评估: 环境配置 + 密钥管理 + 部署策略 + 回滚
    → STOP + AskUserQuestion
    ↓
Section 10: Long-Term Trajectory
    → 评估: 技术债 + 可扩展性预留 + 重构时机
    → STOP + AskUserQuestion
    ↓
Section 11: Design（从 /plan-design-review 交叉）
    → 如果 plan 包含 UI 变更: 使用 Design Review 评分方法
    → STOP + AskUserQuestion
    ↓
===== Post-Review 步骤 =====
    ↓
TODOS.md Review
    → 检查 git log 中的 prior commits
    → 提出 TODO items: A) Add to TODOS.md  B) Skip  C) Build now in this PR
    ↓
Diagrams
    → 为数据流/状态机/处理 pipeline 绘制 ASCII 图
    → 识别应在实现文件中添加 inline ASCII diagram comments 的位置
    ↓
Failure Modes
    → 表格: NEW_CODEPATH | FAILURE_WAY | TEST_COVERED? | ERROR_HANDLING? | SILENT?
    → 如果有 critical gap（无测试 + 无错误处理 + silent failure）→ 标记 CRITICAL GAP
    ↓
Completion Summary（填充并显示）
    → Step 0: Scope Challenge — ___（scope accepted / scope reduced）
    → Architecture Review: ___ issues
    → Code Quality Review: ___ issues
    → Test Review: diagram produced, ___ gaps
    → Performance Review: ___ issues
    → NOT in scope: written
    → What already exists: written
    → TODOS.md updates: ___ items proposed
    → Failure modes: ___ critical gaps
    → Outside voice: ran (codex/claude) / skipped
    → Lake Score: X/Y recommendations chose complete option
    ↓
Retrospective Learning
    → 检查 git log 中的 prior review cycles
    → 如果当前 plan 涉及之前有问题的区域 → 更 aggressive review
    ↓
Review Log
    → ~/.claude/skills/gstack/bin/gstack-review-log \
  '{"skill":"plan-eng-review","timestamp":"TIMESTAMP","status":"STATUS",\
"unresolved":N,"critical_gaps":N,"issues_found":N,"mode":"MODE","commit":"COMMIT"}'
    ↓
Review Readiness Dashboard
    → gstack-review-read → 显示仪表板
    → Eng Review (DIFF vs PLAN) / CEO Review / Design Review / Adversarial / Outside Voice
    ↓
Plan File Review Report
    → 写入/替换 plan 文件的 ## GSTACK REVIEW REPORT section
    ↓
Next Steps — Review Chaining（AskUserQuestion）
    → A) /plan-design-review（仅当有 UI scope 且无 design review）
    → B) /plan-ceo-review（仅当重大产品变更且无 CEO review）
    → C) Ready to implement — run /ship when done
    ↓
STATUS: DONE / DONE_WITH_CONCERNS / BLOCKED
```

**关键机制：**
- **11 Sections**: Architecture + Error & Rescue + Security + Data Flows + Code Quality + Test + Performance + Observability + Deployment + Long-Term Trajectory + Design
- **Outside Voice（可选）**: Codex 或 Claude subagent 获取独立第二意见，在所有 sections 完成后 AskUserQuestion 触发
- **Test Review 特殊机制**: 生成 ASCII 图映射 CODEPATH → TEST_TYPE → ISOLATED?，对每个 gap AskUserQuestion
- **Failure Modes 表格**: 识别 critical gap（无测试 + 无处理 + silent），必须标记
- **Retrospective Learning**: 检查 git log 中的 prior review cycles，对之前有问题的区域更 aggressive
- **Review Log 写入**: `~/.gstack/`（被 `/ship` Dashboard 读取）
- **Review Readiness Dashboard**: 区分 DIFF (来自 `/review`) vs PLAN (来自 `/plan-eng-review`)

**Lake Score:** 追踪 X/Y 个建议中选择了完整选项（Boil the Lake 执行度指标）

---

### 4. /plan-design-review — Senior Designer 评审（设计质量）

**YAML Frontmatter：**
```yaml
---
name: plan-design-review
preamble-tier: 3
version: 2.0.0
description: |
  Designer's eye plan review — interactive, like CEO and Eng review.
  Rates each design dimension 0-10, explains what would make it a 10,
  then fixes the plan to get there. Works in plan mode. For live site
  visual audits, use /design-review. Use when asked to "review the design plan"
  or "design critique".
  Proactively suggest when the user has a plan with UI/UX components.
---
```

**前置依赖：** plan 文件（含 UI/UX 组件）

**核心流程：**

```
Step 0: Detect platform and base branch
    → git remote get-url origin → 判断 GitHub/GitLab/unknown
    → gh auth status / glab auth status → CLI 可用性
    → 确定 base branch（PR 目标分支或 default branch）
    ↓
Pre-Review System Audit
    → git log --oneline -15 + git diff <base> --stat
    → 读取 plan 文件 + CLAUDE.md + DESIGN.md（如果存在）+ TODOS.md
    → UI Scope Detection: 分析 plan 是否涉及 UI/UX 变更
    → 如果无 UI scope → "This plan has no UI scope. A design review isn't applicable." + exit
    ↓
Retrospective Check
    → 检查 git log 中的 prior design review cycles
    → 对之前有设计问题的区域更 aggressive
    ↓
Step 0A: Initial Design Rating（0-10）
    → 评估 plan 的设计完整性
    → "This plan is a 3/10 because it describes backend but never specifies user-facing UI"
    → 解释 THIS plan 的 10 分是什么样
    ↓
Step 0B: DESIGN.md Status
    → 如果存在: "All design decisions will be calibrated against your stated design system"
    → 如果不存在: "No design system found. Recommend running /design-consultation first"
    ↓
Step 0C: Existing Design Leverage
    → 识别代码库中现有的 UI patterns/components
    → 不要 reinvent 已有的东西
    ↓
Step 0D: Focus Areas（AskUserQuestion — STOP until user responds）
    → "I've rated this plan {N}/10 on design completeness. The biggest gaps are {X, Y, Z}. Want me to review all 7 dimensions, or focus on specific areas?"
    ↓
Design Outside Voices（并行，可选，AskUserQuestion）
    → A) Yes — run outside design voices
    → B) No — proceed without
    ↓
If Yes:
    → Codex availability check: which codex 2>/dev/null
    → Codex design voice: codex exec（flag 任意 AI Slop rejection criteria）
    → Claude subagent: 独立完整性 review
    ↓
===== 7个 Design Review Passes（每个后 STOP + AskUserQuestion）=====
    ↓
Pass 1: Interaction State Coverage（强制，不可跳过）
    → 表格: SCREEN | HAPPY_PATH | EMPTY_STATE | ERROR_STATE | LOADING_STATE | FIRST_TIME_USER | POWER_USER
    → 每个 SCREEN 的所有状态是否都有设计 spec
    → STOP + AskUserQuestion
    ↓
Pass 2: AI Slop Risk Assessment（强制，不可跳过）
    → 检查: Generic SaaS card grid / Beautiful image weak brand / 强 headline 无 action / Busy imagery behind text / Carousel 无 narrative purpose
    → 如果任意一项 apply → AI Slop detected → 建议具体改进
    → STOP + AskUserQuestion
    ↓
Pass 3: Information Architecture
    → 评估: Screen hierarchy / Navigation / Content organization / Search & filtering
    → 评估: 每个 screen 的信息优先级（What does user see first/second/third?）
    → STOP + AskUserQuestion
    ↓
Pass 4: Visual & Rendering
    → 评估: Typography / Color / Spacing / Layout / Motion / Iconography
    → 如果有 screenshot/URL → 直接 review
    → STOP + AskUserQuestion
    ↓
Pass 5: UX Writing & Microcopy
    → 评估: 按钮文案 / 错误提示 / Empty states / Onboarding flow
    → 评估: Tone consistency / Clarity / Action language
    → STOP + AskUserQuestion
    ↓
Pass 6: User Journey & Emotional Arc
    → Storyboard the journey: First 5 seconds（visceral）/ 5 minutes（behavioral）/ 5 years（reflective）
    → 评估: Trust signals / Safety / Identity
    → STOP + AskUserQuestion
    ↓
Pass 7: Accessibility & Inclusion
    → 评估: Keyboard nav / Screen readers / Color contrast / Touch targets / RTL
    → 评估: Motion sensitivity / Cognitive load
    → STOP + AskUserQuestion
    ↓
===== Post-Review 步骤 =====
    ↓
Completion Summary（填充并显示）
    → Initial Score / Overall Score / Decisions Made / Unresolved Decisions
    ↓
Review Log
    → ~/.claude/skills/gstack/bin/gstack-review-log \
  '{"skill":"plan-design-review","timestamp":"TIMESTAMP","status":"STATUS",\
"initial_score":N,"overall_score":N,"unresolved":N,"decisions_made":N,"commit":"COMMIT"}'
    ↓
Review Readiness Dashboard
    → gstack-review-read → 显示仪表板
    → 区分 FULL（来自 /plan-design-review）vs LITE（来自 /design-review-lite）
    ↓
Plan File Review Report
    → 写入 plan 文件的 ## GSTACK REVIEW REPORT section
    ↓
Next Steps — Review Chaining（AskUserQuestion）
    → A) /plan-eng-review next（required gate）
    → B) /plan-ceo-review（仅当 fundamental product gaps 且无 CEO review）
    → C) Skip — I'll handle reviews manually
    ↓
STATUS: DONE / DONE_WITH_CONCERNS / BLOCKED
```

**关键机制：**
- **Priority Hierarchy**: Step 0 > Interaction State Coverage > AI Slop Risk > Information Architecture > User Journey > everything else
- **AI Slop Detection**: 6个 hard rejection criteria，任何一个 apply 都标记
- **Interaction State Coverage**: 表格覆盖 6 种状态（Happy/Empty/Error/Loading/FirstTime/PowerUser）
- **Outside Voices**: 可选（AskUserQuestion），Codex + Claude subagent 并行运行
- **Design Review Dashboard**: 区分 FULL（/plan-design-review 全面视觉审计）vs LITE（/design-review-lite 代码级检查）
- **评分系统**: 每个 pass rate before/after (0-10)，解释 gap + fix the plan to get to 10

**Cognitive Patterns（自动运行）：**
- Seeing the system, not the screen
- Empathy as simulation（mental simulation: bad signal / one hand free / boss watching）
- Hierarchy as service（what first/second/third?）
- Edge case paranoia（47-char names / zero results / network fails / colorblind / RTL）
- Subtraction default（Rams: "as little design as possible"）

---

### 5. /review — Pre-landing PR Review（代码质量关）

**YAML Frontmatter：**
```yaml
---
name: review
preamble-tier: 3
version: 2.0.0
description: |
  Automated Pre-Landing PR Review — Diff-scoped, automated fixes where possible.
  Scans for SQL safety, LLM trust boundaries, conditional side effects.
  Scope Drift Detection prevents building the wrong thing.
  Works on any PR. Use when asked to "review this PR".
---
```

**触发词：** "review this PR"、"code review"、"pre-landing review"

**前置依赖：** `/ship` 自动调用（也支持单独运行）

**核心流程（Step 0 → 7）：**

```
Step 0: Platform Detection
    → git remote get-url origin 2>/dev/null
    → 如果包含 "github.com" → platform = GitHub
    → 如果包含 "gitlab" → platform = GitLab
    → 否则: gh auth status（成功→GitHub）/ glab auth status（成功→GitLab）
    → 如果都不成功 → platform = unknown（使用 git-native commands）
    ↓
Step 1: Branch Check
    → git branch --show-current
    → 如果在 base branch（main/master）→ ABORT: "Already on base branch"
    → git fetch origin <base> --quiet && git diff origin/<base> --stat
    → 如果 diff 为空 → ABORT: "No changes to review"
    ↓
Step 1.5: Scope Drift Detection（关键！AskUserQuestion）
    → 读取: TODOS.md + PR description + commit messages
    → 提取 stated intent（本来要做什么）
    → 对比: git diff 文件变更 vs stated intent
    → 如果 scope drift 严重（建了不该建的）→ STOP + AskUserQuestion:
        A) Accept and continue review
        B) Stop — this isn't what was asked
    ↓
Step 2: Plan File Discovery
    → 优先: conversation context 中的 plan 文件路径
    → Fallback: 内容搜索 ~/.claude/plans / .gstack/plans
    → 验证: plan 文件相关性（diff 中的文件是否在 plan 中有对应）
    ↓
Step 3: Actionable Item Extraction
    → 从 plan file 提取: checkbox items / numbered steps / imperative statements
    → 最多 50 项
    → 按类型分类: CODE / TEST / MIGRATION / CONFIG / DOCS
    ↓
Step 4: Code Quality Review（4大类，自动执行）
    ├─ SQL Safety（4维审查）
    │   ├─ Parameterized queries（参数化查询）
    │   ├─ ORM usage（ORM 使用正确性）
    │   ├─ Transaction boundaries（事务边界）
    │   └─ Raw SQL / string concatenation（原始 SQL 拼接检测）
    ├─ LLM Trust Boundary
    │   ├─ Prompt injection vectors（prompt 注入风险）
    │   ├─ Output validation（输出验证）
    │   ├─ Rate limiting（速率限制）
    │   └─ Malicious input handling（恶意输入处理）
    ├─ Conditional Side Effects
    │   └─ Side effects in conditional branches（条件分支中的副作用）
    └─ Structural Issues
        ├─ Error handling（错误处理完整性）
        ├─ Resource cleanup（资源释放）
        ├─ Concurrency issues（并发问题）
        └─ Error propagation（错误传播）
    ↓
Step 5: Automated Fixes + Fix-First Loop
    → 能自动修的（dead code / N+1 queries / stale comments）→ 直接 Edit
    → BLOCK level issues → AskUserQuestion（A) Fix now  B) Log as TODO  C) Skip）
    → HIGH level issues → AskUserQuestion（same options）
    → MEDIUM/LOW → 自动 Log as TODO
    ↓
Step 5.7: Adversarial Review（auto-scaled，AskUserQuestion）
    → Small diff (<50 lines): skip adversarial entirely
    → Medium diff (50-199 lines): cross-model adversarial
    → Large diff (200+ lines): 4 passes (Claude structured + Codex structured + Claude adversarial subagent + Codex adversarial)
    → AskUserQuestion: A) Run adversarial review  B) Skip
    ↓
Step 5.8: Persist Review Results
    → 写入 ~/.gstack/review-logs/review-{timestamp}.jsonl
    → 包含: skill / timestamp / status / unresolved / scope_drift_detected / issues_found
    ↓
Step 6: Write Review Report
    → 格式: PR comment 或 stdout
    → 内容: Review Summary + Fixes Applied + Issues Found + Fix-First Summary
    ↓
STATUS: DONE / DONE_WITH_CONCERNS
```

**关键机制：**
- **Scope Drift Detection（Step 1.5）**: 对比 stated intent（从 TODOS.md/PR description/commit messages）vs actual diff，防止"本来要做A结果做了B"
- **SQL Safety 4维审查**: Parameterized queries / ORM / Transaction boundaries / Raw SQL detection
- **LLM Trust Boundary**: Prompt injection / Output validation / Rate limiting / Malicious input- **Adversarial Review（Step 5.7，auto-scaled）**:
  - Small (<50 lines): skip
  - Medium (50-199): cross-model adversarial
  - Large (200+): 4 passes (Claude structured + Codex structured + Claude adversarial subagent + Codex adversarial)
- **Fix-First Loop**: BLOCK/HIGH → AskUserQuestion，A) Fix now B) Log C) Skip；MEDIUM/LOW → auto Log as TODO
- **Iron Law**: 3次尝试后失败 → STOP + escalate
- **Review Log 写入**: `~/.gstack/review-logs/review-{timestamp}.jsonl`（被 `/ship` Dashboard 读取）

**输出格式：**
- `~/.gstack/review-logs/review-{timestamp}.jsonl` — Review 结果
- `~/.gstack/analytics/skill-usage.jsonl` — Telemetry
- PR comment 或 stdout — Review Report

**与 /ship 的关系:** `/ship` 读取 `~/.gstack/review-logs/` 中的 Review Log，Eng Review 必须为 CLEAR 才能 ship。

---

### 6. /qa — QA Lead 浏览器测试（真实浏览器+Bug修复）

**YAML Frontmatter：**
```yaml
---
name: qa
preamble-tier: 3
version: 2.0.0
description: |
  QA Lead browser testing — real browser, real bugs, real fixes.
  Fix Loop: find bug, fix, re-verify. Max 3 passes per bug (Iron Law).
  Regression tests auto-generated for every bug found.
  Use when asked to "test this site", "find bugs", or "QA this".
---
```

**触发词：** "qa"、"test this site"、"find bugs"、"test and fix"

**前置依赖：** staging 环境 URL

**核心流程（Phase 0 → 11 + Fix Loop）：**

```
Phase 0: Platform Detection + Branch Check
    → 同 /review Step 0 + Step 1
    ↓
Phase 1: Test Depth Selection（AskUserQuestion — STOP until user responds）
    → A) Quick — critical + high severity
    → B) Standard — + medium severity
    → C) Exhaustive — + cosmetic
    Completeness: A=7/10, B=9/10, C=10/10
    ↓
Phase 2: Get staging URL
    → 如果有 PR: gh pr view --json url → staging 环境
    → 如果没有: AskUserQuestion 请求 URL
    ↓
Phase 3: Baseline Health Score（Before Score）
    → $B browse snapshot -i
    → 评估: 页面渲染 / 表单 / 链接 / console errors
    → 记录: baseline health score
    ↓
Phase 4-7: Bug Discovery Loop
    ↓
===== Fix Loop（Bug → Fix → Re-verify，max 3 passes per bug）=====
Loop:
    a) 探索性测试（$B browse 工具）
       $B goto <staging_url>
       $B snapshot -i（获取 @e1/@e2/... 可交互元素 refs）
       $B click @e3（通过 ref 操作元素）
       $B fill @e5 "test"（表单填充）
       $B console --errors（检查 console 错误）
       $B network（检查 API 响应）
       $B js <expr>（在页面上下文执行 JS）
    
    b) 发现 bug
       → 分类: Critical / High / Medium / Cosmetic
       → 记录: bug description + 重现步骤 + 截图
    
    c) AskUserQuestion（STOP until user responds）
       → A) Fix it now（立即修复，推荐）
       → B) Fix after qa（记入 TODO）
       → C) Skip（跳过）
       Completeness: A=10/10, B=7/10, C=3/10
    
    d) 如果选 A: Fix bug
       → 读源码 → Edit/Write 修改
       → 原子提交（一个 bug 一个 commit，bisectable）
       → 重新运行 $B verify 验证修复
       → 如果 verify 通过: 标记 FIXED
       → 如果 verify 失败: 重新 Fix（最多 3 次，Iron Law）
    
    e) 重复直到所有 bug 处理完
===========================================
    ↓
Phase 8: Fix Loop Completion
    → FIXED: 修复完成 + 验证通过
    → WONTFIX: 用户选择 B 或 C
    → REGRESSION: 修复引入了新问题
    ↓
Phase 9: Health Score After
    → 修复后的 health score
    → Before vs After 对比
    ↓
Phase 10: Regression Test Generation（Boil the Lake）
    → 根据所有发现的 bug，生成 Playwright 测试脚本
    → 写入 test/ 目录
    → 原子提交
    ↓
Phase 11: Ship-Readiness Summary
    → 评估是否可以 ship（基于剩余 critical/high bug 数量）
    → 输出建议
    ↓
STATUS: DONE / DONE_WITH_CONCERNS / BLOCKED
```

**关键机制：**
- **Fix Loop（/qa 独有）**: 发现 bug → 立即修 → 验证 → 再测 → 直到 clean
- **Iron Law（Fix Loop）**: 同一 bug 3 次修复尝试后失败 → STOP + escalate（防止 Agent 在错误方向上循环）
- **$B browse 工具序列**: `goto` → `snapshot -i`（获取 refs）→ `click @e3` / `fill @e5 "text"` → `console --errors` → `network`
- **Regression Test Generation**: `/qa` 发现的每个场景都要有 Playwright 测试（Boil the Lake）
- **Test Depth（3层）**: Quick / Standard / Exhaustive 由用户选择
- **Base Branch Detection**: 同 `/review`，使用 `gh pr view --json baseRefName` 或 `glab mr view`

**输出格式：**
- `test/*.spec.ts` 或 `test/*.test.ts` — 回归测试（Playwright）
- 原子 commits（一个 bug 一个 commit）
- `~/.gstack/analytics/skill-usage.jsonl` — Telemetry

**与 /ship 的关系:** `/ship` 检查测试覆盖率（硬 gate），`/qa` 生成的回归测试是覆盖率的重要组成部分。

---

### 7. /ship — Release Engineer 提交流（全自动化）

**YAML Frontmatter：**
```yaml
---
name: ship
preamble-tier: 3
version: 2.0.0
description: |
  Release Engineer — Pre-flight checks, review readiness dashboard,
  test coverage gate, base branch sync, semantic version bump,
  changelog, bisectable commits, PR creation. Fully automated.
  Use when asked to "ship", "deploy", "push to main".
---
```

**触发词：** "ship"、"deploy"、"push to main"、"create a PR"

**前置依赖：** Review readiness dashboard（Eng Review 必须是 CLEAR）

**核心流程（Step 0 → 8.75）：**

```
Step 0: Platform Detection
    → 同 /review Step 0
    ↓
Step 1: Pre-flight Check
    → git branch --show-current
    → 如果在 base branch → ABORT: "Already on base branch"
    → git status + git diff --stat
    → uncommitted changes → 自动包含（不询问用户）
    ↓
Step 1.5: Review Readiness Dashboard
    → ~/.claude/skills/gstack/bin/gstack-review-read
    → 读取 ~/.gstack/review-logs/ 中的 Review 条目
    → 显示:
        +====================================================================+
        |                    REVIEW READINESS DASHBOARD                       |
        +====================================================================+
        | Review          | Runs | Last Run            | Status    | Required |
        |-----------------|------|---------------------|-----------|----------|
        | Eng Review      |  1   | 2026-03-16 15:00    | CLEAR     | YES      |
        | CEO Review      |  0   | —                   | —         | no       |
        | Design Review   |  0   | —                   | —         | no       |
        | Adversarial     |  0   | —                   | —         | no       |
        | Outside Voice   |  0   | —                   | —         | no       |
        +--------------------------------------------------------------------+
        | VERDICT: CLEARED — Eng Review passed                                |
        +====================================================================+
    → Staleness detection: 对每个有 commit hash 的 entry，比较与 HEAD 是否一致
       → 如果不一致: git rev-list --count STORED..HEAD → "Note: {skill} may be stale — {N} commits since review"
    ↓
    Verdict logic:
    → CLEARED: Eng Review 有 1+ entry（7天内），status="clean" 或 skip_eng_review=true
    → NOT CLEARED: Eng Review 缺失 / 过期（>7天）/ 有 open issues
    ↓
    如果 Eng Review NOT CLEAR → BLOCK（必须先 review）
    如果有 ASK items → AskUserQuestion（是否继续）
    ↓
Step 2: Base Branch Sync
    → git fetch origin <base>
    → git merge origin/<base> --no-edit
    → 如果有冲突: 尝试 auto-merge
    → 如果 auto-merge 失败 → BLOCK（显示冲突文件）
    ↓
Step 3.25: Greptile Comment Check（如果有 PR）
    → 如果有 PR: 检查是否有未响应的 Greptile review comments
    → 如果有: AskUserQuestion（是否处理）
    ↓
Step 3.4: Test Coverage Audit
    → 运行测试套件（bun test / npm test 等）
    → 计算覆盖率
    → 如果 coverage < 阈值（如 < 70%）→ AskUserQuestion: A) Override  B) Abort
    → 硬 gate: coverage 低于阈值必须用户确认才能继续
    ↓
Step 3.45: Plan Completion Audit
    → 读取 plan file 的 actionable items
    → 检查每个 CODE/TEST/MIGRATION item 的完成状态
    → 如果有 item NOT DONE 且无用户 override → BLOCK
    ↓
Step 3.47: Plan Verification Failures
    → 验证测试是否真的覆盖了 plan 中的要求
    → 如果测试覆盖不足: 自动生成缺失测试
    ↓
Step 3.5: Design Review with Codex Voice（可选）
    → 如果 plan 包含 UI 变更且无 design review:
       → AskUserQuestion: A) Run /plan-design-review  B) Skip
    ↓
Step 3.6: Greptile Comment Resolution（持续）
    → 处理所有未响应的 Greptile comments
    → AskUserQuestion per comment: A) Resolve  B) Reply  C) Skip
    ↓
Step 4: Adversarial Review Check（auto-scaled）
    → Small (<50 lines): skip
    → Medium (50-199): cross-model adversarial
    → Large (200+): 4 passes
    → AskUserQuestion: A) Run adversarial review  B) Skip
    ↓
Step 4.75: Version Bump
    → AskUserQuestion（如果需要 MAJOR/MINOR bump）:
       A) MAJOR — breaking change
       B) MINOR — new feature
       C) PATCH — bug fix
    → MICRO/PATCH → 自动决定
    → 更新 VERSION 或 package.json
    ↓
Step 5: CHANGELOG Update
    → 从 git diff 自动生成 changelog 条目
    → 格式: - {feature/fix}: {description}
    → 追加到 CHANGELOG.md
    ↓
Step 6: TODO Cleanup
    → 检查 TODOS.md 中的 items 是否在 PR 中完成
    → AskUserQuestion: A) Update TODOS.md  B) Skip
    ↓
Step 7: Commit + Push
    → git add -A
    → git commit -m "release: v{x.y.z} {changelog summary}"
    → 推送方式:
       → 如果有 PR: git push origin HEAD
       → 如果无 PR 且 base=main/master: AskUserQuestion
    ↓
Step 8: PR Creation
    → gh pr create / glab mr create
    → PR body 包含:
       - Release Summary（VERSION / CHANGELOG）
       - Review Readiness 状态
       - Coverage 报告
       - Ship-readiness summary
    ↓
Step 8.5: Document Release
    → AskUserQuestion: A) Run /document-release  B) Skip
    ↓
Step 8.75: Metrics
    → 统计: 文件数 / 插入行 / 删除行 / commit 数 / test 数
    → 显示: PR URL
    ↓
    ~/.claude/skills/gstack/bin/gstack-telemetry-log \
      --skill "ship" --duration "$_TEL_DUR" --outcome "success"
    ↓
STATUS: DONE
```

**关键机制：**
- **Review Readiness Dashboard（Step 1.5）**: 强制 gate，Eng Review 不是 CLEAR 就 BLOCK
- **Test Coverage Gate（Step 3.4）**: 硬 gate，非软检查，低于阈值必须用户确认 override
- **Plan Completion Audit（Step 3.45）**: plan 中写的事情没做完，不让 ship
- **Verdict Logic**: Eng Review（CLEAR/NOT CLEAR）+ 7天过期 + skip_eng_review 配置
- **Staleness Detection**: 比较 review commit hash 与 HEAD，不一致时显示 "N commits since review"
- **Greptile Comments（Step 3.25/3.6）**: 检查并处理未响应的 review comments
- **Adversarial Review Check（Step 4，auto-scaled）**: auto-scale based on diff size
- **Bisectable Commits（Step 7）**: 每个 release 一个 commit，bisectable
- **CHANGELOG 自动生成（Step 5）**: 从 git diff 提取 changelog 条目
- **Document Release（Step 8.5）**: 可选调用 `/document-release`

**Review Tiers（Dashboard 显示）：**
| Tier | Required | Gates Shipping | Auto-scale |
|------|----------|----------------|------------|
| Eng Review | Default | YES | N/A |
| CEO Review | No | NO | N/A |
| Design Review | No | NO | N/A |
| Adversarial | Auto | NO | 50/200+ lines |
| Outside Voice | No | NO | N/A |

**输出格式：**
- CHANGELOG.md 更新
- PR/MR 创建（包含 coverage + review status）
- `~/.gstack/analytics/skill-usage.jsonl` — Telemetry

---

### 8. /investigate — Debugger 系统性调试

**YAML Frontmatter：**
```yaml
---
name: investigate
preamble-tier: 3
version: 2.0.0
description: |
  Systematic debugging — reproduce, hypothesize, verify, fix.
  Iron Law: stop after 3 failed fix attempts on the same path.
  Debug Report + regression test for every bug found.
  Use when asked to "debug", "investigate", or "why is this broken".
---
```

**核心流程（Step 1 → 5 + Iron Law）：**

```
Step 1: Reproduce
    → $B goto <failing_url> 或本地运行命令
    → 记录错误现象（截图 + console + network）
    → 用 Read/Grep 检查源码
    ↓
Step 2: Hypothesize
    → 根据错误信息，列出 3 个最可能的根因
    → 优先级排序
    ↓
Step 3: Verify Hypothesis
    → 用 Read/Grep 检查源码
    → 用 $B js <expr> 在页面上下文执行 JS
    → 用 Bash 运行诊断命令
    ↓
Step 4: Fix
    → 如果找到根因 → Edit 修复
    → 运行 $B verify 验证修复
    ↓
    如果 verify 失败:
       → 回到 Step 2（下一个假设，不是重复同样的路径）
       → Iron Law: 3 次尝试后 → STOP + escalate
    ↓
Step 5: Debug Report
    → 根因分析（Root Cause）
    → 修复方案（Fix Applied）
    → 防止建议（Regression Test 建议 + 如何防止在其他地方出现）
    ↓
STATUS: DONE / DONE_WITH_CONCERNS / BLOCKED
```

**关键机制：**
- **Iron Law**: 同一路径 3 次修复尝试后失败 → STOP + escalate（不重复同样的错误路径）
- 每次失败后必须明确换假设，不是重复试同样的修复
- Debug Report 包含 regression test 建议
- `$B js <expr>` 在页面上下文执行 JavaScript 用于诊断

**输出格式：**
- `~/.gstack/analytics/skill-usage.jsonl` — Telemetry

---

### 9. /cso — Chief Security Officer（安全审查）

**YAML Frontmatter：**
```yaml
---
name: cso
preamble-tier: 3
version: 2.0.0
description: |
  Chief Security Officer review — OWASP Top 10, STRIDE threat modeling,
  dependency vulnerability scanning, secret detection.
  7-phase execution: Recon → Map → Threat → Audit → Verify → Report → Handoff.
  Use when asked to "security review", "audit this code", or "check for vulnerabilities".
---
```

**核心流程（7 Phases）：**

```
Phase 0: Recon
    → 检测 git hosting platform（同 /review Step 0）
    → 确定 base branch（同 /review Step 0）
    → git fetch + git diff origin/<base> --stat
    ↓
Phase 1: Scope Mapping
    → 读取: PR description + commit messages + TODOS.md
    → 识别: 新增/修改的文件（重点关注：auth / payment / data 处理 / API endpoints）
    → 识别: 依赖新增（Gemfile / package.json / requirements.txt / go.mod 变更）
    ↓
Phase 2: Threat Modeling（OWASP Top 10 + STRIDE）
    → 评估: A01 Broken Access Control / A02 Cryptographic Failures /
            A03 Injection / A04 Insecure Design / A05 Security Misconfiguration /
            A06 Vulnerable Components / A07 Auth Failures / A08 Data Integrity /
            A09 Logging Failures / A10 SSRF
    → STRIDE: Spoofing / Tampering / Repudiation / Information Disclosure /
              Denial of Service / Elevation of Privilege
    ↓
Phase 3: Security Audit
    → 依赖漏洞: npm audit / bundle audit / safety check / grype / trivy
    → Secret 检测: 搜索 API keys / tokens / credentials（禁止 hardcode）
    → 输入验证: 参数化查询 / 输出编码 / Content Security Policy
    ↓
Phase 4: Manual Verification（可选）
    → $B goto <staging_url>（如果适用）
    → $B snapshot -i + $B console --errors
    → 执行 XSS/SQLi 测试（如果适用）
    ↓
Phase 5: Findings Report
    → JSONL 格式写入 ~/.gstack/security-findings.jsonl
    → 格式: {"phase":"...","category":"...","severity":"CRITICAL|HIGH|MEDIUM|LOW",...}
    ↓
Phase 6: Handoff
    → 如果有 critical/high issues → AskUserQuestion:
        A) Fix now — 立即修复
        B) Fix after merge — 记入 TODO
        C) Skip — 忽略
    ↓
STATUS: DONE / DONE_WITH_CONCERNS / BLOCKED
```

**关键机制：**
- **OWASP Top 10 + STRIDE**: 双框架威胁建模
- **Dependency Scanning**: npm audit / bundle audit / safety / grype / trivy
- **Secret Detection**: 搜索 API keys / tokens / credentials 硬编码
- **Findings JSONL**: 结构化安全发现报告，写入 `~/.gstack/security-findings.jsonl`
- **Severity Levels**: CRITICAL / HIGH / MEDIUM / LOW

**输出格式：**
- `~/.gstack/security-findings.jsonl` — JSONL 安全发现报告
- `~/.gstack/analytics/skill-usage.jsonl` — Telemetry

---

### 10. 跨技能数据流

```
~/.gstack/（用户配置目录，非项目文件）
    ├── sessions/
    │   └── {PID}（Session 跟踪，120分钟过期）
    ├── analytics/
    │   ├── skill-usage.jsonl（Skill 使用统计）
    │   ├── eureka.jsonl（第一性原理洞察）
    │   └── contributor-logs/{slug}.md（Contributor field reports）
    ├── review-logs/
    │   ├── plan-ceo-review-{timestamp}.jsonl
    │   ├── plan-eng-review-{timestamp}.jsonl
    │   ├── plan-design-review-{timestamp}.jsonl
    │   ├── review-{timestamp}.jsonl（/review Pre-landing）
    │   └── codex-review-{timestamp}.jsonl（Codex adversarial）
    └── security-findings.jsonl（/cso 安全发现）

Plan File（项目文件，gstack 控制）
    ↑
    ├── /office-hours → 写入 Plan: Overview + Vision + 6 forcing questions 输出
    ├── /plan-ceo-review → 写入 Plan: CEO Decisions + ## GSTACK REVIEW REPORT
    ├── /plan-eng-review → 写入 Plan: Architecture + Test Matrix + ## GSTACK REVIEW REPORT
    └── /plan-design-review → 写入 Plan: Design Spec + ## GSTACK REVIEW REPORT

TODOS.md（项目文件）
    ↓
    /review → Scope drift 对比基准
    /ship → Plan items 完成度审计
    /qa → Fix 后更新 TODO items

~/.claude/skills/gstack/bin/
    ├── gstack-review-log（写入 review-logs/）
    ├── gstack-review-read（读取 review-logs/ → Dashboard）
    ├── gstack-config（读写用户配置）
    ├── gstack-repo-mode（检测 repo 模式）
    └── gstack-update-check（升级检查）
```

**数据流详解：**
1. `/office-hours` → 写 Plan → `/plan-ceo-review` 读 Plan → 写 CEO Decisions
2. `/plan-ceo-review` → 写 Review Log → `/ship` Dashboard 读 Review Log
3. `/review`（Pre-landing）→ 写 Review Log → `/ship` Dashboard 读 Review Log
4. `/plan-eng-review` → 写 Plan + Review Log → `/ship` Dashboard 读 Review Log
5. `/ship` → 读 Dashboard → BLOCK if Eng Review not CLEAR → 创建 PR

---

### 11. 统一协议（所有技能共享）

**Completion Status Protocol：**
每个技能结束时必须报告：
- `DONE` — 全部完成，每条结论有证据
- `DONE_WITH_CONCERNS` — 完成但有问题需告知用户
- `BLOCKED` — 无法继续，说明阻塞原因和已尝试的步骤
- `NEEDS_CONTEXT` — 缺少必要信息，明确说明需要什么

**Escalation 规则（Iron Law）：**
- 同一任务 3 次尝试失败 → STOP
- 安全敏感变更不确定 → STOP
- 超出可验证范围 → STOP
- Escalation 格式：`STATUS: BLOCKED | REASON: ... | ATTEMPTED: ... | RECOMMENDATION: ...`

**Boil the Lake 原则：**
AI 让边际成本接近零，所以永远选完整方案而非捷径：
| Task type | Human team | CC+gstack | Compression |
|-----------|-----------|-----------|-------------|
| Boilerplate | 2 days | 15 min | ~100x |
| Tests | 1 day | 15 min | ~50x |
| Feature | 1 week | 30 min | ~30x |
| Bug fix | 4 hours | 15 min | ~20x |

**AskUserQuestion 固定格式：**
1. **Re-ground**（重述上下文）：State the project + branch + current plan/task
2. **Simplify**（让16岁能看懂）：Plain English，无 raw function names，无 internal jargon
3. **Recommend**（推荐）：`RECOMMENDATION: Choose [X] because [one-line reason]`，包含 `Completeness: X/10`
4. **Options**（A/B/C）：Effort 显示 human ~X / CC ~Y

Calibration: 10 = complete implementation（all edge cases, full coverage），7 = happy path，3 = shortcut

**Plan Mode Exception：**
在 plan mode 下，某些写文件操作被允许：
- `~/.gstack/review-logs/*.jsonl` — Review 结果
- `~/.gstack/analytics/*.jsonl` — Telemetry
- Plan 文件的 `## GSTACK REVIEW REPORT` section（写/替换）
- Commit: `git add` + `git commit`（bisectable）
