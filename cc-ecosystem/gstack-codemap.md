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
