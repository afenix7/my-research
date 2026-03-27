# opencli (jackwener/opencli) — CodeMap

> **Version:** 1.5.0 | **License:** Apache-2.0 | **npm:** `@jackwener/opencli`
> **Repo:** https://github.com/jackwener/opencli

---

## 1. 项目概述与定位

**opencli** 是一个将**网站、Electron 桌面应用、本地 CLI 工具**统一转换为命令行接口的通用工具。其核心理念是：一次编写适配器，无数次零成本复用。

**定位：AI Agent 的工具路由器**
- AI Agent 通过 `opencli list` 发现可用工具
- 通过统一的命令格式（`opencli <site> <command>`）执行操作
- 输出结构化数据（JSON/YAML/CSV），直接可被 LLM 处理

**竞品对比：**

| 场景 | opencli | Browser-Use | Crawl4AI |
|------|----------|--------------|----------|
| 定时数据提取 | ✅ 零成本确定性 | ❌ LLM 推理成本 | ✅ 可用但需写提取逻辑 |
| AI Agent 网站操作 | ✅ 结构化快速 | ✅ 可用但贵且慢 | ❌ 不适用 |
| 桌面 Electron 应用控制 | ✅ **唯一方案** | ❌ 不可用 | ❌ 不可用 |
| 通用网站探索 | ❌ 无适配器则不可用 | ✅ LLM 驱动 | ❌ 不适用 |

---

## 2. 核心架构 — 双引擎设计

```
┌──────────────────────────────────────────────────────┐
│                   opencli CLI (Commander.js)          │
├──────────────────────────────────────────────────────┤
│                    Engine Layer                        │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  Registry  │  │Dynamic Loader│  │Output Formatter│   │
│  └────────────┘  └──────────────┘  └──────────────┘   │
├──────────────────────────────────────────────────────┤
│                   Adapter Layer                       │
│  ┌────────────────────┐  ┌────────────────────────┐  │
│  │YAML Declarative    │  │TypeScript Adapters     │  │
│  │Pipeline Engine      │  │(browser/desktop/AI)    │  │
│  └────────────────────┘  └────────────────────────┘  │
├──────────────────────────────────────────────────────┤
│                 Connection Layer                     │
│  ┌────────────────────┐  ┌────────────────────────┐  │
│  │Browser Bridge      │  │CDP (Chrome DevTools)   │  │
│  │(Chrome Ext + WS)   │  │+ AppleScript (Electron) │  │
│  └────────────────────┘  └────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

---

## 3. 文件结构

```
jackwener/opencli/
├── src/                          # TypeScript 源代码
│   ├── main.ts                   # CLI 入口点
│   ├── cli.ts                    # Commander.js CLI 配置 + 内置命令
│   ├── commanderAdapter.ts       # Registry → Commander 桥接层
│   ├── discovery.ts              # 适配器发现、manifest 加载、YAML 解析
│   ├── execution.ts              # 参数验证、命令执行
│   ├── registry.ts               # 中央命令注册表
│   ├── serialization.ts          # 命令序列化辅助
│   ├── runtime.ts                # 浏览器会话 & 超时管理
│   ├── browser.ts                # Browser Bridge WebSocket 连接管理
│   ├── output.ts                 # 统一输出格式化 (table/json/yaml/md/csv)
│   ├── doctor.ts                 # 诊断工具 (daemon/extension/browser 连通性)
│   ├── analysis.ts               # AI 分析相关
│   ├── cascade.ts                # 级联认证策略发现
│   ├── build-manifest.ts         # 构建时命令 manifest 生成
│   ├── capabilityRouting.ts      # 能力路由 (public/cookie/header/intercept/ui)
│   ├── pipeline/                 # YAML 声明式管道引擎
│   │   ├── runner.ts
│   │   ├── template.ts
│   │   ├── transform.ts
│   │   └── steps/
│   │       ├── fetch.ts           # HTTP 请求 (带 cookie/header 策略)
│   │       ├── map.ts            # 数据转换/模板表达式
│   │       ├── limit.ts          # 结果截断
│   │       ├── filter.ts         # 条件过滤
│   │       └── download.ts       # 媒体下载
│   ├── adapters/                 # TypeScript 适配器目录
│   │   ├── browser/             # 浏览器适配器基类
│   │   ├── desktop/             # 桌面应用适配器 (CDP + AppleScript)
│   │   ├── public/              # 公共 API 适配器
│   │   └── cli/                 # 外部 CLI 适配器
│   └── clis/                    # 预置命令目录 (50+ 平台适配器 YAML)
├── extension/                    # Chrome 扩展源代码 (Browser Bridge)
├── docs/                         # VitePress 文档
│   ├── adapters/                 # 各平台适配器文档
│   │   ├── desktop/            # Cursor, Codex, Antigravity, ChatGPT, Notion, Discord, Doubao
│   │   ├── browser/            # 各浏览器适配器文档
│   │   └── public/            # 公共 API 适配器文档
│   ├── developer/              # 开发者文档
│   │   ├── architecture.md
│   │   ├── yaml-adapter.md
│   │   ├── ts-adapter.md
│   │   ├── testing.md
│   │   ├── ai-workflow.md
│   │   └── contributing.md
│   └── comparison.md           # 与竞品对比
├── scripts/                      # 构建脚本
├── .agents/                      # Agent 技能定义 (AGENT.md)
├── SKILL.md                      # OpenClaw Skill 定义 (40KB)
├── CLI-EXPLORER.md               # CLI Explorer 工具文档
├── CLI-ONESHOT.md                # 单次命令文档
├── TESTING.md                    # 测试指南
└── package.json                  # v1.5.0, Node >= 20.0.0, Bun >= 1.0
```

---

## 4. 主要命令

### 4.1 内置命令

```bash
opencli list                          # 列出所有可用命令
opencli list -f yaml                 # YAML 格式列出
opencli doctor                       # 诊断 Browser Bridge / daemon / Chrome 连通性
opencli register <cli-name>          # 注册本地 CLI 到 opencli 注册表
opencli plugin install github:user/repo  # 安装社区插件
opencli plugin list                  # 列出已安装插件
opencli plugin update <name>         # 更新插件
opencli plugin uninstall <name>      # 卸载插件
```

### 4.2 平台命令 (50+)

**浏览器命令** (需要 Chrome 已登录目标网站):
```bash
opencli bilibili hot --limit 5       # B站热门视频
opencli zhihu hot -f json            # 知乎热榜
opencli xiaohongshu search <keyword> # 小红书搜索
opencli twitter trending             # Twitter 趋势
opencli reddit hot                   # Reddit 热帖
opencli boss search <job>           # BOSS直聘搜索
opencli weixin download --url <mp.weixin.qq.com/...>  # 微信文章导出
```

**桌面应用命令** (CDP + AppleScript):
```bash
opencli cursor status                # Cursor IDE 状态
opencli cursor send "prompt"        # 发送 Composer prompt
opencli cursor extract-code         # 提取代码
opencli notion search <query>       # Notion 搜索
opencli notion write --page-id <id> --content "..." # 写 Notion 页面
opencli chatgpt send "question"    # ChatGPT macOS 桌面版
```

**公共 API 命令** (无需登录):
```bash
opencli hackernews top --limit 5    # Hacker News
opencli wikipedia search <term>      # 维基百科
opencli arxiv search <query>        # 学术论文
opencli youtube search <term>        # YouTube 搜索
```

**下载命令**:
```bash
opencli bilibili download BV1xxx --output ./ --quality 1080p  # 需要 yt-dlp
opencli xiaohongshu download <note-id> --output ./            # 小红书图文/视频
opencli twitter download <user> --limit 20                   # Twitter 媒体
opencli zhihu download <article-url> --download-images        # 知乎文章 Markdown
```

### 4.3 AI Agent 专用命令 (opencli 的核心卖点)

```bash
opencli explore <site>              # 发现网站 API，自动探索可用端点
opencli synthesize <site>           # 根据探索结果自动生成适配器代码
opencli cascade <site>              # 级联发现认证策略 (public → cookie → header → intercept → ui)
```

这三个命令是 AI Agent **自举 (self-bootstrapping)** 的关键：Agent 可以通过 `explore` 了解未知网站，然后 `synthesize` 生成适配器，再通过 `cascade` 找到合适的认证方式。

### 4.4 输出格式

所有命令支持 `-f/--format` 参数：
```bash
opencli bilibili hot -f table       # 终端富表格 (默认)
opencli bilibili hot -f json       # JSON (管道输给 jq/LLM)
opencli bilibili hot -f yaml       # YAML
opencli bilibili hot -f md         # Markdown
opencli bilibili hot -f csv        # CSV
opencli bilibili hot -v            # Verbose 模式 (显示管道调试步骤)
```

---

## 5. 技术实现细节

### 5.1 认证策略 (5 级)

| 策略 | 机制 | 适用场景 |
|------|------|---------|
| `public` | 直接 HTTP 请求，无认证 | HackerNews, BBC, Wikipedia |
| `cookie` | 通过 Browser Bridge 复用 Chrome cookie | Bilibili, Zhihu, 需要登录的站点 |
| `header` | 自定义 Authorization/API-Key 头 | API Key 认证服务 |
| `intercept` | 网络请求拦截 (XHR/GraphQL) | Twitter (Timeline API) |
| `ui` | DOM 可访问性快照 + 交互 | 桌面应用、写操作 |

### 5.2 Browser Bridge 架构

```
Chrome (用户已登录)  ←→  Browser Bridge Chrome Extension  ←→  WebSocket Daemon  ←→  opencli CLI
                            (读取 Chrome cookie)              (Node.js/Win/macOS)    (TypeScript)
```

- **Chrome Extension**: 读取 Chrome 已登录网站的 cookies，通过 WebSocket 发送给 daemon
- **WebSocket Daemon**: 轻量级后台服务 (端口 9222 等)，在运行浏览器命令时自动启动
- **零配置**: 运行任何浏览器命令时自动启动 daemon，无需手动安装启动

### 5.3 桌面应用控制 (CDP + AppleScript)

opencli 是**唯一**能通过 CLI 控制桌面 Electron 应用的工具：

```typescript
// 架构示例 (src/adapters/desktop/cursor.ts)
class CursorAdapter {
  async send(prompt: string) {
    // 1. 通过 CDP 连接 Cursor 窗口
    // 2. 注入 JavaScript 到页面执行
    // 3. 读取 Claude/Composer 回复
    // 4. 通过 AppleScript 模拟快捷键提交
  }
}
```

支持的桌面应用：Cursor, Codex, Antigravity Ultra, ChatGPT (macOS), ChatWise, Notion, Discord, Doubao

### 5.4 双引擎适配器

**YAML 声明式** — 适合简单 API/页面抓取：
```yaml
name: hackernews
domain: news.ycombinator.com
strategy: public
steps:
  - fetch:
      url: https://hn.algolia.com/api/v1/search?query={{query}}&tags=front_page
  - map:
      fields: [title, url, author, points]
  - limit: {{limit}}
```

**TypeScript 编程式** — 适合复杂逻辑、桌面应用、AI 操作：
```typescript
// src/adapters/desktop/cursor.ts
export async function send(prompt: string, context?: string) {
  const { cdpConnection } = await getDesktopSession('cursor');
  await cdpConnection.evaluate(`composer.submit('${prompt}', '${context}')`);
  return cdpConnection.evaluate('composer.getResponse()');
}
```

### 5.5 外部 CLI Hub

opencli 作为**统一代理层**，对外部 CLI (gh, docker, obsidian 等) 仅做透传：

```bash
opencli gh pr list --limit 5    # 直接透传给系统中的 gh CLI
opencli docker ps               # 直接透传给 docker
```

自动安装机制：若系统未安装 `gh`，opencli 会自动尝试 `brew install gh` 然后执行。

### 5.6 核心依赖

| 依赖 | 用途 |
|------|------|
| `commander` | CLI 参数解析和子命令 |
| `ws` | WebSocket 客户端/服务端 (Browser Bridge) |
| `js-yaml` | YAML 适配器解析 |
| `turndown` | HTML → Markdown 转换 (文章导出) |
| `chalk` | 终端彩色输出 |
| `cli-table3` | 终端表格渲染 |

---

## 6. 与 Claude Code 的集成方式

### 6.1 AGENT.md 集成

opencli 提供了完整的 OpenClaw Skill (`SKILL.md`，40KB)，使 Claude Code 可以：

1. **工具发现**: 在 `AGENT.md` / `.cursorrules` 中配置让 AI 执行 `opencli list` 发现可用工具
2. **自注册**: AI 可以通过 `opencli register mycli` 将找到的本地 CLI 注册到 opencli
3. **结构化输出**: 所有命令输出 JSON/YAML 格式，可直接作为 AI 的上下文

### 6.2 OpenClaw Agent Reach 集成

opencli 项目本身也使用 **OpenClaw** 作为 AI Agent 运行时：
- `.agents/skills/cross-project-adapter-migration/` — 跨项目适配器迁移 Skill
- `.agents/workflows/cross-project-adapter-migration.md` — 自动化工作流
- 这使得 opencli 可以用 AI Agent 来自动维护和迁移适配器

### 6.3 互补使用模式

```
需要操作已知平台?  → opencli (快速、免费、确定性)
需要探索未知网站? → Browser-Use/Stagehand (LLM 驱动)
需要扩展?         → opencli synthesize (AI 生成适配器)
```

---

## 7. 优缺点分析

### ✅ 优点

1. **零 LLM 运行时成本**: 适配器预构建，运行 10000 次也不花一分钱 Token
2. **确定性输出**: 相同命令每次返回相同 Schema，可管道、脚本化、CI 友好
3. **极速响应**: 适配器命令秒级返回，不像 LLM 驱动方案需要 10-60 秒
4. **复用 Chrome 登录态**: 凭证不离开浏览器，安全且无需单独 OAuth/API Key 配置
5. **覆盖极广**: 50+ 平台，包括 Reddit/HackerNews/Twitter 等全球平台和 Bilibili/Zhihu/小红书/豆瓣等中国平台
6. **唯一桌面应用控制方案**: CDP + AppleScript 驱动 Electron 应用，无竞品
7. **易扩展**: 只需在 `clis/` 目录放置 `.yaml` 或 `.ts` 文件即可自动注册
8. **AI Agent 原生**: 内置 `explore`/`synthesize`/`cascade` 让 AI 自举发现和创建新适配器
9. **多运行时支持**: 同时支持 Node.js ≥20 和 Bun ≥1.0

### ❌ 缺点

1. **需要预置适配器**: 未知网站没有适配器则完全无法使用，不适合通用爬虫
2. **依赖 Chrome 登录态**: 无法在无头浏览器/CI 环境中操作需要登录的网站（对比 Browser-Use 的 cookie 注入方案）
3. **适配器维护负担**: 网站 DOM/API 变更时适配器可能损坏，需要社区持续维护
4. **桌面应用支持仅限 macOS**: AppleScript 方案天然 macOS-only，Windows/Linux 用户无法使用桌面应用功能
5. **扩展性有局限**: YAML 声明式管道能力有限，复杂逻辑必须写 TypeScript，对贡献者要求更高
6. **文档较分散**: 核心文档分散在 README、VitePress docs、SKILL.md、CLI-EXPLORER.md 多处

---

## 8. 快速参考

```bash
# 安装
npm install -g @jackwener/opencli

# 自我诊断
opencli doctor

# 查看所有命令
opencli list

# 常用操作
opencli hackernews top --limit 5
opencli bilibili hot --limit 10 -f json
opencli zhihu hot -f yaml
opencli twitter trending -f table

# 下载内容
opencli bilibili download BV1xxx --output ./video --quality 1080p
opencli xiaohongshu download <note-id> --output ./xhs

# 写操作 (需桌面应用)
opencli cursor send "Explain this code"
opencli notion write --page-id <id> --content "Hello world"

# 桌面适配器诊断
opencli cursor status
opencli chatgpt status
```

---

## 9. 相关资源

- **npm:** https://www.npmjs.com/package/@jackwener/opencli
- **文档:** https://jackwener.github.io/opencli/ (VitePress)
- **Releases (含 Chrome 扩展):** https://github.com/jackwener/opencli/releases
- **中文 README:** https://github.com/jackwener/opencli/blob/main/README.zh-CN.md
- **对比指南:** `docs/comparison.md`
- **架构文档:** `docs/developer/architecture.md`
- **Skill 定义:** `SKILL.md` (OpenClaw Skill, 40KB)

---

*本 codemap 由 `quant-team-leader` subagent 生成 (2026-03-27)*
