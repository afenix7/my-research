# gstack — CodeMap

**GitHub**: https://github.com/garrytan/gstack  
**Language**: TypeScript (Bun)  
**Runtime**: Bun.serve HTTP server + Playwright + Chromium (headless)  
**License**: MIT  
**Architecture Doc**: ARCHITECTURE.md (21KB, 详尽)  

---

## 1. 项目概述与定位

**gstack** 是 Claude Code 的**持久化浏览器自动化插件**。它的核心定位是：解决"AI agent 需要操作浏览器"时的两个根本问题——**冷启动延迟**（每次命令重新开浏览器 = 3-5秒等待）和**状态丢失**（cookie、登录会话、打开的 tab 全部丢失）。

gstack 通过维护一个**常驻 Chromium 进程**和**本地 HTTP 服务**，让 Claude Code 通过 `$B` 命令前缀来控制浏览器，实现亚秒级响应和持久化状态。

**典型使用场景**：
- Web QA 测试（自动点击、表单填写、截图验证）
- 复杂 Web 应用的操作（需要登录状态的爬虫、Dashboard 操作）
- 端到端测试生成

---

## 2. 核心架构

### 2.1 系统架构图

```
Claude Code                         gstack CLI (Bun binary)
────────────                        ────────────────────────
  Tool call: $B snapshot -i
  ──────────────────────────────→   CLI 读取 .gstack/browse.json
                                    找到 port + token
                                    POST /command (Bearer token)
                                             │
                                  ┌──────────▼───────────┐
                                  │  Bun.serve HTTP Server │
                                  │  • 路由分发             │
                                  │  • Bearer token 鉴权    │
                                  │  • Playwright CDP 调用  │
                                  └──────────┬───────────┘
                                             │ CDP (Chromium DevTools)
                                  ┌──────────▼───────────┐
                                  │  Chromium (headless)   │
                                  │  • 持久化进程           │
                                  │  • cookie/localStorage  │
                                  │  • 30分钟 idle 超时     │
                                  └────────────────────────┘
```

### 2.2 核心技术选型

**为什么用 Bun**：
1. **编译成单一二进制**：`bun build --compile` 产出 ~58MB 单文件，无需 Node.js 环境，适合安装在 `~/.claude/skills/` 这种非标准路径
2. **原生 SQLite**：cookie 解密直接读 Chromium 的 SQLite cookie 数据库，`new Database()` 是 Bun 内置 API，无需 `better-sqlite3`
3. **原生 TypeScript**：开发态 `bun run server.ts`，无编译步骤
4. **内置 HTTP 服务器**：`Bun.serve()` 够用，不需要 Express/Fastify

**为什么用 Playwright Locator 而不是 DOM 注入**：
- CSP (Content Security Policy) 会阻止 DOM 修改
- React/Vue/Svelte 水合过程会剥离注入的属性
- Shadow DOM 无法从外部访问
- Playwright Locator 使用 Chromium 内部维护的 Accessibility 树，外部查询，完全无副作用

### 2.3 项目结构

```
gstack/
├── browse/                   # 核心浏览器自动化
│   ├── server.ts             # Bun HTTP 服务器主文件
│   ├── browser-manager.ts    # Chromium 生命周期管理
│   ├── commands.ts           # 命令注册表 (READ/WRITE/META)
│   ├── snapshot.ts           # ARIA snapshot + ref 分配
│   ├── ref-map.ts            # @e1/@e2 ref → Locator 映射
│   ├── cookie-decrypt.ts     # macOS Keychain → AES-128 解密
│   ├── keychain.ts           # macOS Keychain 访问封装
│   ├── log-buffers.ts        # 环形缓冲区日志系统
│   └── errors.ts             # 统一错误封装 (wrapError)
├── gen-skill-docs.ts         # SKILL.md 模板生成器
├── SKILL.md                  # Claude Code Skill 文档 (auto-generated)
├── SKILL.md.tmpl             # 模板源文件
├── ARCHITECTURE.md           # 架构设计文档
├── BROWSER.md                # 浏览器操作命令参考
├── CLAUDE.md                 # 开发者指南
├── CONTRIBUTING.md           # 贡献指南
├── test/
│   ├── e2e/                  # E2E 测试
│   │   └── helpers/
│   │       ├── session-runner.ts   # Claude -p 子进程运行器
│   │       └── eval-collector.ts   # eval 数据收集器
│   └── unit/                # 单元测试
└── browse/dist/             # 编译输出 (.version 文件在这里)
```

---

## 3. 主要模块分析

### 3.1 BrowserManager (`browser-manager.ts`)

Chromium 生命周期管理的核心模块：

```typescript
class BrowserManager {
  browser: Browser | null
  page: Page | null
  
  launch(): Promise<void>    // 冷启动 Chromium
  ensureReady(): Promise<void>  // 保证 browser + page 就绪
  getPage(): Page
  close(): void              // 关闭 browser
}
```

关键特性：
- **版本自动重启**：CLI 读取 `browse/dist/.version`，若与运行中 server 不匹配则 kill 旧进程重启
- **crash recovery**：Chromium 断开连接时 server 立即退出，CLI 检测到下次自动重启
- **idle timeout**：30分钟无操作自动关闭

### 3.2 命令系统 (`commands.ts`)

命令按副作用分类：

```typescript
// READ — 只读查询，无状态修改
const READ_COMMANDS = new Set([
  'text', 'html', 'links', 'console', 'cookies',
  'network', 'tabs', 'url', 'title', 'screenshot'
])

// WRITE — 页面状态修改，非幂等
const WRITE_COMMANDS = new Set([
  'goto', 'click', 'fill', 'press', 'select',
  'check', 'uncheck', 'hover', 'scroll', 'upload'
])

// META — 服务级操作
const META_COMMANDS = new Set([
  'snapshot', 'chain', 'tabs', 'screenshot', 'help'
])
```

每个命令经过统一分发：
```typescript
if (READ_COMMANDS.has(cmd))  → handleReadCommand(cmd, args, bm)
if (WRITE_COMMANDS.has(cmd)) → handleWriteCommand(cmd, args, bm)
if (META_COMMANDS.has(cmd))  → handleMetaCommand(cmd, args, bm, shutdown)
```

### 3.3 Ref 系统 (`ref-map.ts` + `snapshot.ts`)

这是 gstack 最关键的技术创新之一——**让 AI 通过 @e1/@e2 这样的引用来操作页面元素，而不是写 CSS selector 或 XPath**。

**工作流程**：
1. `snapshot` 命令调用 `page.accessibility.snapshot()` 获取 ARIA 树
2. Parser 遍历 ARIA 树，分配顺序引用：`@e1`, `@e2`, `@e3`...
3. 每个 ref 对应一个 Playwright Locator：`getByRole(role, { name }).nth(index)`
4. 存储 `Map<string, RefEntry>` 在 BrowserManager 实例上

**Staleness 检测**：
```typescript
resolveRef(@e3) → refMap.get("e3")
               → count = await locator.count()  // 异步验证
               → if count === 0 → throw "Ref @e3 is stale — run 'snapshot' to get fresh refs"
```
每次 `framenavigated` 事件清空 refMap——导航后 locators 全部失效，强制重新 snapshot。

**Cursor-interactive refs (`@c`)**：通过 `-C` flag 找到不在 ARIA 树中的可点击元素（`cursor: pointer`、`onclick` 属性、自定义 `tabindex`）。

### 3.4 Cookie 安全系统 (`cookie-decrypt.ts` + `keychain.ts`)

```
用户导入 Cookie
    ↓
macOS Keychain 访问（需用户点击"Allow"）
    ↓ (PBKDF2 + AES-128-CBC 解密)
内存中的明文 cookie
    ↓
注入 Playwright Context
    ↓ (从不写入磁盘)
Context 关闭 → 缓存清除
```

安全设计要点：
- **Keychain 访问必须用户授权**：macOS Keychain 对话框，用户必须手动点击
- **数据库只读复制**：从 Chromium cookie DB 复制到 tempfile 再打开，避免锁冲突
- **Session 级 key 缓存**：Keychain password + AES key 仅在 server 生命周期内缓存，server 关闭即清除
- **日志无 cookie 值**：所有日志输出截断 cookie value

### 3.5 日志架构 (`log-buffers.ts`)

三个环形缓冲区（各 50,000 条，O(1) push）：

```
Browser events → CircularBuffer (in-memory)
                     ↓ (每1秒异步 flush)
              .gstack/*.log (append-only)
```

类型：`console 事件`、`network 请求`、`dialog 事件` 各自独立 buffer。
- HTTP 处理从不阻塞于磁盘 I/O
- Server crash 最多丢失 1 秒日志
- 内存有界（50K × 3 buffers）
- 磁盘文件 append-only，可被外部工具读取

---

## 4. API / 接口设计

### 4.1 HTTP API (localhost only, Bearer token auth)

```
POST /command
  Authorization: Bearer <uuid-v4-token>
  Body: { cmd: string, args: string[] }
  Response: plain text

GET /health
  (无 auth, localhost only)
  Response: { status: "ok", pid: number, port: number }

GET /cookie-picker
  (无 auth, localhost only, 只显示 domain/count，不显示值)
```

### 4.2 状态文件协议

```json
// .gstack/browse.json (mode 0o600, atomic write via tmp+rename)
{
  "pid": 12345,
  "port": 34567,
  "token": "uuid-v4",
  "startedAt": "ISO timestamp",
  "binaryVersion": "git-rev"
}
```

### 4.3 端口选择策略

随机端口 10000-60000（最多重试5次），允许同一机器上最多 10 个 Conductor workspace 各跑独立的 browse daemon，零配置零冲突。

### 4.4 Claude Code Skill 接口

```bash
$B snapshot -i          # 获取页面快照 + ref
$B click @e3           # 点击 ref e3
$B fill @e2 "hello"    # 填写表单
$B screenshot          # 截图
$B goto https://...    # 导航
$B console --last 50   # 读取控制台日志
$B cookies --import   # 导入浏览器 cookie
```

SKILL.md 模板系统保证文档与代码同步：
- `SKILL.md.tmpl` 包含手写 prose + `{{PLACEHOLDER}}`
- `gen-skill-docs.ts` 在构建时填充 placeholders（命令表、flag 引用等）
- CI 可验证文档新鲜度：`gen:skill-docs --dry-run` + `git diff --exit-code`

---

## 5. 与 Claude Code 的集成机制

### 5.1 安装方式

gstack 作为 Claude Code Skill 安装：
1. 下载编译好的二进制（或 `bun build --compile` 自己编译）
2. 二进制文件放到 `~/.claude/skills/gstack/` 
3. `SKILL.md` 被 Claude Code 的 Skill tool 读取
4. Claude Code 通过 `$B` 前缀调用 gstack 命令

### 5.2 命令分发流程

```
Claude Code tool call: $B snapshot -i
    ↓
gstack CLI 读取 .gstack/browse.json
    ↓
发现 server 未运行 → 启动 server (约3秒)
    ↓
CLI POST /command { cmd: "snapshot", args: ["-i"] }
    ↓
Bun HTTP Server 路由到 handleMetaCommand()
    ↓
Playwright accessibility.snapshot() + ref 分配
    ↓
返回带 @e1/@e2 标注的纯文本
    ↓
Claude Code 模型理解文本，执行下一步
```

### 5.3 错误哲学

gstack 的错误信息专为 AI agent 设计，每个错误都告诉 agent **下一步该怎么做**：

| 错误 | gstack 给出的指导 |
|------|-----------------|
| "Element not found" | "Run `snapshot -i` to see available elements" |
| "Selector matched multiple" | "Use @refs from `snapshot` instead" |
| Timeout | "Page may be slow or URL may be wrong" |

---

## 6. 测试基础设施

### 6.1 三层测试模型

| Tier | 内容 | 成本 | 速度 |
|------|------|------|------|
| 1 — 静态验证 | 解析 `$B` 命令，校验命令注册表 | 免费 | <2s |
| 2 — E2E via `claude -p` | 真实 Claude session 运行每个 skill | ~$3.85 | ~20min |
| 3 — LLM-as-judge | Sonnet 评分文档质量 | ~$0.15 | ~30s |

Tier 1 在每次 `bun test` 运行；Tier 2+3 仅在 `EVALS=1` 环境下运行。

### 6.2 E2E Session Runner

```typescript
// session-runner.ts — spawn Claude -p 作为独立子进程
1. Write prompt to temp file (avoid shell escaping)
2. Spawn: sh -c 'cat prompt | claude -p --output-format stream-json --verbose'
3. Stream NDJSON from stdout (实时进度)
4. Race against timeout
5. Parse NDJSON → structured results
```

### 6.3 Eval 持久化

```typescript
// eval-collector.ts — 双写策略
1. savePartial() — 原子覆写 _partial-e2e.json (每次测试后)
2. finalize() — 写带时间戳的最终文件 (e2e-YYYYMMDD-HHMMSS.json)
```

---

## 7. 优缺点分析

### 优点

1. **持久化浏览器彻底解决冷启动问题**：首次 ~3秒，之后每次 ~100-200ms
2. **状态跨命令保持**：登录 cookie、localStorage、打开的 tab 全部持久化
3. **Ref 系统解放 AI**：不再需要 AI 写 CSS selector，ref 是语义化的、可读的
4. **安全性设计周全**：Bearer token、Keychain 授权、只读 DB 复制、日志无敏感数据
5. **跨平台优雅降级**：多 workspace 端口隔离、WSL/Windows/macOS 特殊处理
6. **文档-代码强一致性**：gen-skill-docs.ts 确保文档永远反映实际 API
7. **错误信息 AI 友好**：每个错误都附带可操作的修复建议
8. **E2E 测试覆盖完整**：3 层测试策略，eval 结果可 jq 查询

### 缺点

1. **仅支持 macOS**：Keychain 访问是 macOS 专有，Linux/Windows cookie 导入未实现
2. **仅支持 Chromium**：Firefox、Safari 无支持
3. **无 iframe 支持**：ref 系统不跨 frame 边界（最常请求的缺失功能）
4. **HTTP 非加密**：虽然 localhost + Bearer token，理论上同一机器其他进程可嗅探 token
5. **无 WebSocket 流式响应**：HTTP 轮询模式，大响应有一定延迟
6. **不使用 MCP 协议**：作者明确选择不用 MCP（认为 JSON schema 开销不必要）
7. **Server 单点故障**：Chromium crash 后整个 server 退出，虽然 CLI 会重启，但中间有一小段不可用
8. **文档生成需要构建步骤**：SKILL.md 不是源码的一部分，需要构建时生成

---

## 8. 与 Claude Code 原生 Browser Tool 的对比

| 维度 | gstack | Claude Code 原生 |
|------|--------|-----------------|
| 冷启动 | ~100ms（server已运行） | ~2-3秒（每次新建） |
| 状态持久 | ✅ cookie/tab/localStorage 跨命令保持 | ❌ 每次重新创建 |
| 元素引用 | @e1/@e2 ref + staleness 检测 | CSS/XPath（脆弱） |
| macOS cookie 导入 | ✅ Keychain → 明文注入 | ❌ 不支持 |
| 多 workspace | 零冲突（随机端口） | N/A |
| 协议复杂度 | 简单 HTTP + 文本 | 原生 Playwright |

---

## 9. 关键文件速查

| 文件 | 作用 |
|------|------|
| `browse/server.ts` | HTTP 服务器主文件 |
| `browse/browser-manager.ts` | Chromium 生命周期管理 |
| `browse/commands.ts` | 命令注册表（READ/WRITE/META 分类） |
| `browse/snapshot.ts` | ARIA snapshot + ref 分配 |
| `browse/ref-map.ts` | @ref → Locator 映射 + staleness 检测 |
| `browse/cookie-decrypt.ts` | Keychain → AES 解密流程 |
| `ARCHITECTURE.md` | 完整架构文档（~21KB） |
| `BROWSER.md` | 命令参考文档（~24KB） |
| `SKILL.md.tmpl` | 文档模板源文件 |
| `test/helpers/session-runner.ts` | E2E 测试子进程运行器 |
