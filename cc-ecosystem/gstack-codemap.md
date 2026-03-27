# gstack CodeMap

> **Garry Tan (Y Combinator President & CEO) 的个人 Claude Code 插件**
> GitHub: `garrytan/gstack` | MIT License | 2026年3月最新

## 项目概述与定位

gstack 是 Garry Tan 将自己打造成"一人开发团队"的完整工作流系统。核心理念：

> **"Turn Claude Code into a virtual engineering team"**

实际成果：60天内 600,000+ 行生产代码（35% 测试），每天 10,000-20,000 行，周产量 ~115k LOC，同时全职运营 YC。

**定位：** 不是工具集合，而是一个完整的软件开发**流程**。覆盖 Think → Plan → Build → Review → Test → Ship → Reflect 全生命周期。

---

## 核心架构

### 系统结构

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code  Session                     │
│                                                             │
│   /office-hours → /plan-ceo-review → /plan-eng-review      │
│        ↓              ↓                   ↓                │
│   Design Doc    Architecture      Test Matrix               │
│        ↓              ↓                   ↓                │
│   /design-review  →  /review  →  /qa  →  /ship  →  /land  │
│        ↓              ↓           ↓        ↓         ↓       │
│   Auto-fix       Auto-fix    Bug fix  PR open   Deployed   │
└─────────────────────────────────────────────────────────────┘
```

### 文件结构

```
gstack/
├── SKILL.md                    # 入口技能（gstack主技能）
├── AGENTS.md                   # Agent定义
├── ARCHITECTURE.md             # 架构文档（21KB）
├── CLAUDE.md                   # 用户级CLAUDE.md配置
├── setup                       # 安装脚本
├── bin/                        # 编译后的二进制CLI
│   ├── gstack-config          # 配置管理
│   ├── gstack-global-discover  # 跨仓库技能发现
│   ├── gstack-review-log      # Review历史记录
│   └── gstack-telemetry-*     # 遥测数据
├── browse/                     # 🌟 核心模块：持久化浏览器
│   ├── src/
│   │   ├── server.ts          # Bun.serve HTTP服务
│   │   ├── browser-manager.ts # Chromium生命周期
│   │   ├── commands.ts        # 命令分发（READ/WRITE/META）
│   │   ├── cookie-import-*.ts # macOS Keychain解密
│   │   ├── sidebar-agent.ts   # Chrome侧边栏子Agent
│   │   └── snapshot.ts        # ARIA ref系统
│   └── test/
├── office-hours/              # YC Office Hours技能
├── plan-ceo-review/           # CEO/Founder评审
├── plan-eng-review/           # Engineering Manager评审
├── plan-design-review/         # Senior Designer评审
├── design-consultation/       # 设计系统生成
├── review/                    # Staff Engineer代码review
├── investigate/               # Debugger系统性调试
├── qa/                       # QA Lead浏览器测试
├── qa-only/                  # QA Reporter（纯报告）
├── cso/                      # Chief Security Officer (OWASP+STRIDE)
├── ship/                     # Release Engineer提交流
├── land-and-deploy/          # 合并+部署+验证
├── canary/                   # SRE灰度监控
├── benchmark/                # Performance Engineer基准测试
├── retro/                    # Eng Manager周回顾
├── document-release/         # Technical Writer文档更新
├── codex/                    # OpenAI Codex第二意见
├── careful/                  # Safety Guardrails
├── freeze/guard/unfreeze/    # 目录编辑锁
├── setup-browser-cookies/   # Cookie导入
├── setup-deploy/            # 部署配置
├── gstack-upgrade/          # 自升级
├── autoplan/                # 自动计划管道
├── connect-chrome/          # Chrome扩展（侧边栏Agent）
└── extension/               # Chrome扩展UI
```

---

## 28个技能全景图

### Sprint流程技能（按执行顺序）

| 技能 | 角色 | 核心职责 |
|------|------|---------|
| `/office-hours` | YC Office Hours | 重构问题，6个强制问题挖掘真实痛点，生成Design Doc |
| `/plan-ceo-review` | CEO/Founder | 重新思考问题，找10星产品，4种模式（扩张/选择性扩张/保持/收缩） |
| `/plan-eng-review` | Eng Manager | 锁定架构、数据流、ASCII图、边缘case、测试矩阵 |
| `/plan-design-review` | Senior Designer | 维度评分0-10，AI Slop检测，交互式设计决策 |
| `/design-consultation` | Design Partner | 从零构建设计系统，研究竞品+生成mockup |
| `/review` | Staff Engineer | 找CI通过但生产爆炸的bug，**自动修复**明显问题 |
| `/investigate` | Debugger | 系统性根因调试，3次失败后停止（Iron Law） |
| `/design-review` | Designer Who Codes | 同plan-design-review但直接修复，原子提交+前后截图 |
| `/qa` | QA Lead | **打开真实浏览器**测试，修复bug，生成回归测试 |
| `/qa-only` | QA Reporter | 纯报告模式，不改代码 |
| `/ship` | Release Engineer | 同步main，跑测试，审计覆盖率，push，开PR |
| `/land-and-deploy` | Release Engineer | 合并PR，等CI/CD，验证生产健康 |
| `/canary` | SRE | 监控控制台错误、性能回退、页面失败 |
| `/benchmark` | Performance Engineer | 基线页面加载、Core Web Vitals、对比PR前后 |
| `/document-release` | Technical Writer | 更新所有漂移的文档（README/ARCHITECTURE/CONTRIBUTING） |
| `/retro` | Eng Manager | 团队感知周回顾，/retro global跨所有项目 |

### 浏览器技能

| 技能 | 角色 | 核心职责 |
|------|------|---------|
| `/browse` | QA Engineer | 真实Chromium浏览器，~100ms/命令，$B connect可看实时动作 |
| `/setup-browser-cookies` | Session Manager | 从Chrome/Arc/Brave/Edge导入Cookie到headless session |

### 权力工具（Power Tools）

| 技能 | 功能 |
|------|------|
| `/codex` | OpenAI Codex第二意见，3种模式（review gate/adversarial/consultation） |
| `/careful` | 危险命令警告（rm -rf/DROP TABLE/force-push） |
| `/freeze` | 目录编辑锁，防范围外修改 |
| `/guard` | `/careful` + `/freeze` 组合 |
| `/unfreeze` | 解除冻结 |
| `/setup-deploy` | 一次性/land-and-deploy配置 |
| `/gstack-upgrade` | 自升级，检测全局/ vendored安装 |
| `/autoplan` | CEO→design→eng自动管道，仅呈现需人类决策点 |

---

## 核心技术细节

### 1. 持久化浏览器（browse模块）

**问题：** 每次命令冷启动浏览器需要3-5秒，20个命令=60秒浪费，且丢失所有状态。

**方案：** 长命Chromium daemon + localhost HTTP。

```
CLI (binary) ──HTTP POST /command──> Bun.serve Server ──CDP──> Chromium (headless)
     ↑                                      │
     │                                      │ 持久化tabs/cookies/localStorage
     └──────── 读取 .gstack/browse.json ───┘
```

- **首次调用：** ~3秒（启动server+chromium）
- **后续调用：** ~100-200ms（纯HTTP）
- **idle超时：** 30分钟后自动关闭
- **状态文件：** `.gstack/browse.json`（原子写入，mode 0600）
- **版本自动重启：** binary hash不匹配时自动杀旧启新

### 2. Ref系统（@e1/@e2/@c1）

**目标：** Agent用自然语言引用页面元素，不需要CSS selector或XPath。

**工作原理：**
```
1. $B snapshot -i
   → Playwright accessibility.snapshot()
   → 遍历ARIA树，分配 @e1, @e2, @e3...
   → 每个ref记录 role + name + Locator

2. $B click @e3
   → resolveRef("e3") → locator.count() 检查（防止stale）
   → locator.click()
```

**为什么不用DOM注入（data-ref属性）：**
- CSP（Content Security Policy）阻止
- React/Vue/Svelte hydration会剥离
- Shadow DOM无法穿透

**Locators方案：** 使用Playwright `getByRole()`外部查询，不修改DOM，无上述问题。

**Staleness检测：** 每个ref在执行前 `count()` 检查，元素消失时快速失败（~5ms）而非等30秒超时。

**@c系列（Cursor-interactive）：** 捕获`cursor:pointer`/`onclick`/`tabindex`的自定义组件（如`<div onclick>`），ARIA树里没有但实际可点击。

### 3. 安全模型

- **localhost only：** HTTP server绑定127.0.0.1，非0.0.0.0
- **Bearer token auth：** 每次启动生成UUID token，写入mode 0600文件
- **Keychain用户授权：** macOS Keychain访问需用户点击"Allow"
- **Cookie解密在内存：** PBKDF2+AES-128-CBC从Keychain解密，不落盘
- **数据库只读：** 复制Cookie DB到tmp文件读取，避免锁冲突
- **无日志cookie值：** console/network/dialog日志永不包含cookie内容

### 4. Cookie导入流程（macOS）

```
用户运行 /setup-browser-cookies
    ↓
读取 Chrome/Arc/Brave/Edge cookie路径（hardcoded常量）
    ↓
复制cookie DB到 /tmp/.gstack-cookies-*.db（只读）
    ↓
调用 macOS Keychain 读取 AES key（用户弹窗授权）
    ↓
内存解密cookie值
    ↓
注入到Playwright context
    ↓
启动browser session
```

### 5. SKILL.md模板系统

```
SKILL.md.tmpl（人类写的prose + 占位符）
       ↓
gen-skill-docs.ts（构建时读取代码元数据）
       ↓
SKILL.md（提交到git，自动生成章节）
```

**占位符体系：**

| 占位符 | 来源 | 生成内容 |
|--------|------|---------|
| `{{COMMAND_REFERENCE}}` | `commands.ts` | 分类命令表 |
| `{{SNAPSHOT_FLAGS}}` | `snapshot.ts` | Flag参考+示例 |
| `{{PREAMBLE}}` | `gen-skill-docs.ts` | 更新检查+session跟踪+贡献者模式 |
| `{{BASE_BRANCH_DETECT}}` | `gen-skill-docs.ts` | PR目标技能动态检测 |
| `{{QA_METHODOLOGY}}` | `gen-skill-docs.ts` | /qa和/qa-only共享方法论 |
| `{{REVIEW_DASHBOARD}}` | `gen-skill-docs.ts` | /ship前检查的Review就绪仪表板 |

**Preamble（五件事一次bash命令搞定）：**
1. 升级检查 → `gstack-update-check`
2. Session跟踪 → 3+并发时进入"ELI16模式"
3. 贡献者模式 → 写field reports到`~/.gstack/contributor-logs/`
4. AskUserQuestion格式 → 统一上下文+问题+推荐+选项
5. Search Before Building → 三层知识（经典/新潮/第一性原理）

### 6. 三层测试模型

| Tier | 内容 | 成本 | 速度 |
|------|------|------|------|
| 1 — 静态验证 | 解析所有`$B`命令，与registry对比 | 免费 | <2s |
| 2 — E2E via `claude -p` | 真实Claude session跑每个技能 | ~$3.85 | ~20min |
| 3 — LLM-as-judge | Sonnet评分文档清晰度/完整性/可操作性 | ~$0.15 | ~30s |

### 7. Conductor集成

[Conductor](https://conductor.build) 支持多Claude Code并行：
- 每个workspace独立session
- 典型配置：10-15个并行sprint
- 适用场景：1个office-hours、1个review、1个implementing、1个qa on staging...

---

## 与Claude Code的集成方式

### Skill tool接口

所有技能通过 `/skill` 命令调用：
```
/office-hours
/plan-ceo-review
/review
/qa
/ship
...
```

### CLAUDE.md集成

安装后添加到项目CLAUDE.md：
```markdown
## gstack
- 使用 gstack 的 /browse skill 进行所有网页浏览
- 禁止使用 mcp__claude-in-chrome__* 工具
- 可用技能：/office-hours, /plan-ceo-review, /review, /qa, /ship ...
```

### Skill注册发现机制

- **全局安装：** `~/.claude/skills/gstack/`
- **项目安装：** `.claude/skills/gstack/`（git提交后队友自动获得）
- **自动发现：** Claude Code启动时扫描skills目录

### 多Agent支持

`./setup --host codex` 支持：
- Claude Code
- OpenAI Codex CLI
- Gemini CLI  
- Cursor
- 任何支持SKILL.md标准的Agent

---

## 重大更新（本月 v5.0.6）

### Inline Self-Review（2026-03-24）

**原有问题：** 每次review需要约25分钟的subagent review loop（Agent调用Agent）。

**解决方案：** 用inline self-review checklist替代，将时间缩短到~30秒。

**实现：** 在主Agent内完成所有检查项，而非派生子Agent循环。

### 并行Sprint增强

- 设计团队协作流程（design-consultation → design-review → plan-eng-review）
- `/qa`作为重大解锁：从6个并行worker扩展到12个
- 智能review路由：CEO不管infra bug fix，design review不审backend变更

---

## 优缺点分析

### 优点

1. **完整流程覆盖** — 不是工具集合，而是端到端软件开发流程
2. **真实浏览器** — `/browse` + `$B connect`让Agent有眼睛，可看真实页面
3. **高性能daemon** — 100ms级命令响应（vs 3-5秒冷启动）
4. **自动化程度高** — review自动修bug，qa自动生成回归测试
5. **安全设计** — Keychain/cookie处理非常严谨
6. **多Agent并行** — Conductor支持10-15个并行sprint
7. **零依赖部署** — 编译后单二进制，无node_modules
8. **MIT许可** — 完全开源无Premium

### 缺点

1. **macOS only（关键功能）** — Keychain cookie导入只支持macOS
2. **Chrome扩展依赖** — 侧边栏Agent需要Chrome扩展
3. **Windows/Linux不完整** — cookie解密未实现，browse core可用但认证flow有限
4. **学习曲线陡** — 28个技能+多Agent协调需要时间适应
5. **Conductor付费** — 多sprint并行需要[Conductor](https://conductor.build)
6. **单人背书** — 主要是Garry Tan个人工作流，YC投资背书但社区验证有限

---

## 与其他插件对比

| 维度 | gstack | GSD | Superpowers | ralph |
|------|--------|-----|-------------|-------|
| **定位** | 完整开发团队 | 项目管理 | 开发方法论 | 自主编码循环 |
| **技能数** | 28个 | 10+ agents, 30+ commands | 6个核心模式 | 2个脚本 |
| **浏览器** | ✅ 持久化daemon | ❌ | ❌ | ❌ |
| **多Agent并行** | ✅ Conductor | ✅ 内置 | ❌ | ❌ |
| **Review自动化** | ✅ 自动修复 | ⚠️ 验证型 | ✅ Inline checklist | ❌ |
| **学习曲线** | 陡 | 中 | 低 | 低 |
| **许可** | MIT | MIT | MIT | MIT |
