# CC-Combo: Claude Code 配置组合切换工具 - 研究报告

## 项目概述

CC-Combo 是一个命令行工具，用于创建、管理和快速切换不同的 AI 编辑器配置组合（combo）。每个 combo 可以包含：
- Claude Code 配置（settings.json、环境变量、权限设置等）
- 插件集合
- 全局技能
- 全局 Agents
- MCP 服务器配置

第一阶段聚焦 Claude Code，架构设计具备可扩展性，未来可支持 opencode、codex、copilot cli、openclaw 等其他工具。

## 现有配置结构分析

### 1. Claude Code 配置结构

**位置：**
- 全局配置目录：`~/.claude/`（可通过 `CLAUDE_CONFIG_DIR` 环境变量覆盖）
- 项目级配置：`./.claude/settings.json`, `./.claude/settings.local.json`

**目录结构：**
```
~/.claude/
├── settings.json          # 主要配置文件，JSON 格式
├── settings.local.json    # 本地特定配置
├── claude_desktop_config.json  # MCP 服务器配置
├── plugins/               # 已安装插件
├── skills/                # 全局技能
├── agents/                # 代理配置
├── commands/              # 自定义命令
└── backups/               # 备份
```

**settings.json 格式示例：**
```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.anthropic.com",
    "ANTHROPIC_AUTH_TOKEN": "sk-xxx",
    "ANTHROPIC_MODEL": "claude-opus-4-6"
  },
  "permissions": {
    "Bash": "allow"
  }
}
```

**MCP 配置格式 (`claude_desktop_config.json`):**
```json
{
  "mcpServers": {
    "server-name": {
      "type": "stdio",
      "command": "node",
      "args": ["./server.js"],
      "serverUrl": "http://..."  // for http type
    }
  }
}
```

**关键发现：**
- Claude Code 读取全局配置，环境变量可覆盖配置目录位置
- 配置都是 JSON 格式，易于读写
- MCP 配置单独存储在 `claude_desktop_config.json`
- 插件和技能是基于文件系统的目录结构

---

### 2. OpenClaw 配置结构

**位置：**
- 主配置：`~/.openclaw/openclaw.json`
- 技能：`~/.openclaw/skills/`
- 代理：`~/.openclaw/agents/`
- 工作区：`~/.openclaw/workspace/`

**openclaw.json 格式：**
```json
{
  "meta": { ... },
  "env": { ... },
  "models": {
    "mode": "merge",
    "providers": {
      "provider-name": {
        "baseUrl": "https://...",
        "apiKey": "sk-xxx",
        "api": "anthropic-messages",
        "models": [...]
      }
    }
  }
}
```

---

### 3. GitHub Copilot CLI 配置结构

**位置：**
- 配置：`~/.copilot/config.json`

**格式示例：**
```json
{
  "banner": "never",
  "trusted_folders": ["/root"],
  "copilot_tokens": { ... },
  "model": "gpt-5.4"
}
```

---

## 架构设计

### 设计原则

1. **可扩展性优先** - 使用适配器模式支持多种工具
2. **声明式配置** - 每个 combo 是一个定义清晰的 JSON/YAML 文件
3. **原子切换** - 切换时只修改目标工具的配置文件，不影响其他
4. **安全备份** - 切换前自动备份当前配置
5. **符号链接优先** - 使用 symlink 减少磁盘占用

### CC-Combo 存储结构

```
~/.cc-combo/
├── combos/                    # 所有全局配置组合
│   ├── default/              # combo 名称
│   │   ├── combo.json        # combo 元数据和定义
│   │   ├── claude/           # Claude Code 配置快照
│   │   │   ├── settings.json
│   │   │   ├── settings.local.json
│   │   │   ├── claude_desktop_config.json
│   │   │   ├── plugins/      # 插件（可以是 symlink 或拷贝）
│   │   │   ├── skills/       # 全局技能
│   │   │   └── agents/       # 全局 Agents
│   │   ├── openclaw/         # 未来扩展
│   │   │   └── openclaw.json
│   │   └── ...
│   ├── gsd/                  # GSD 专用 combo
│   │   └── claude/...
│   ├── superpowers/          # Superpowers 专用 combo
│   │   └── claude/...
│   └── full-agency/          # 全量 Agency 模式
│       └── ...
└── current.json              # 当前全局激活的 combo 记录

# 项目级 combo（在项目目录内）
my-project/
└── .cc-combo.json            # 项目级 combo 配置
```

### Combo 定义格式 (`combo.json`)

```json
{
  "name": "volcengine-ark",
  "description": "火山引擎方舟配置",
  "createdAt": "2026-03-28T00:00:00Z",
  "tools": {
    "claude": {
      "enabled": true,
      "settings": {
        "env": {
          "ANTHROPIC_BASE_URL": "https://ark.cn-beijing.volces.com/api/coding",
          "ANTHROPIC_AUTH_TOKEN": "{{token}}",
          "ANTHROPIC_MODEL": "ark-code-latest"
        }
      },
      "mcpServers": {
        "deepwiki": {
          "serverUrl": "https://mcp.deepwiki.com/mcp"
        },
        "miniMax": {
          "type": "stdio",
          "command": "npx",
          "args": ["@minimax/mcp-server"]
        }
      },
      "plugins": [
        "anthropics/cclaude-code-review",
        "anthropics/cclaude-feature-development"
      ],
      "skills": [
        "gsd",
        "design-review"
      ],
      "agents": [
        "deep-research",
        "code-reviewer"
      ]
    }
  }
}
```

### 支持的工具（第一阶段）

| 工具 | 配置目标位置 | 可配置内容 | 状态 |
|------|-------------|-----------|------|
| Claude Code | `~/.claude/` | settings.json, MCP, plugins, skills, agents | ✅ 第一阶段支持 |
| OpenClaw | `~/.openclaw/openclaw.json` | env, models, providers | 🔄 未来扩展 |
| GitHub Copilot CLI | `~/.copilot/config.json` | model, tokens | 🔄 未来扩展 |
| OpenCode | 待研究 | - | 🔄 未来扩展 |
| Codex | 待研究 | - | 🔄 未来扩展 |

---

## CLI 命令设计

### 核心命令

```bash
# 创建新 combo（交互式 TUI 多选）
cc-combo create <name>

# 编辑已有 combo（交互式 TUI）
cc-combo edit <name>

# 从当前配置创建 combo
cc-combo capture <name>

# AI 扫描现有配置，推荐 combo 分组
cc-combo suggest [--ai]

# 列出所有 combos
cc-combo list

# 切换到指定 combo（全局）
cc-combo use <name>

# 使用项目级 combo（在项目目录执行）
cc-combo use --local <name>

# 初始化项目级 combo
cc-combo init [name]

# 删除 combo
cc-combo delete <name>

# 重命名 combo
cc-combo rename <old> <new>

# 显示当前 combo 信息
cc-combo current

# 验证 combo 配置
cc-combo validate <name>

# 回滚到上一个配置
cc-combo rollback
```

### Claude Code 特定命令

```bash
# 添加 MCP 服务器到 combo
cc-combo claude mcp add <combo> <name> --type stdio --command "node" --args "./server.js"

# 添加插件到 combo
cc-combo claude plugin add <combo> <plugin-name>

# 添加全局技能到 combo
cc-combo claude skill add <combo> <skill-name>

# 添加全局 Agent 到 combo
cc-combo claude agent add <combo> <agent-name>

# 添加环境变量到 combo
cc-combo claude env set <combo> <KEY> <value>
```

---

## 核心工作流程

### 切换流程 (`cc-combo use <name>`)

1. **验证** - 检查 combo 是否存在且配置有效
2. **备份** - 将当前活跃配置备份到 `backups/` 时间戳目录
3. **应用** - 将 combo 配置写入目标工具的配置位置：
   - 对于配置文件：直接复制/覆盖
   - 对于插件/技能目录：使用符号链接或复制
4. **记录** - 更新 `current.json` 记录当前激活的 combo
5. **完成** - 提示用户重启 Claude Code 生效

### 捕获流程 (`cc-combo capture <name>`)

1. 读取当前 Claude Code 配置
2. 提取 settings、MCP、已安装插件列表、技能列表、Agents 列表
3. 创建新 combo 并保存所有内容
4. 生成 `combo.json` 元数据

### 创建流程 (`cc-combo create <name>`)

1. 交互式询问配置（环境变量、MCP、插件等）
2. 创建空 combo 结构
3. 用户可之后编辑

---

## 技术选型

- **语言**: TypeScript
- **运行时**: Node.js (>= 18)
- **CLI 框架**: Commander.js
- **交互式多选**: [inquirer](https://www.npmjs.com/package/inquirer) 内置支持多选 checkbox 列表
- **TUI 增强**: 可选 [blessed](https://www.npmjs.com/package/blessed) 或 [ink](https://www.npmjs.com/package/ink) 更丰富的终端交互
- **配置解析**: JSON (原生支持)
- **文件操作**: fs/promises (原生) + fs-extra
- **AI 调用**: 使用当前环境的 Claude Code 自身或通过环境变量配置 API key
- **打包**: tsup 打包，npm 分发

## 项目结构

```
cc-combo/
├── src/
│   ├── cli.ts              # CLI 入口
│   ├── commands/           # 命令实现
│   │   ├── create.ts
│   │   ├── capture.ts
│   │   ├── list.ts
│   │   ├── use.ts
│   │   ├── delete.ts
│   │   └── ...
│   ├── core/              # 核心模块
│   │   ├── combo.ts       # Combo 定义类型
│   │   ├── storage.ts     # 存储管理
│   │   └── validator.ts   # 配置验证
│   ├── adapters/          # 工具适配器（可扩展）
│   │   ├── interface.ts   # Adapter 接口定义
│   │   ├── claude.ts      # Claude Code 适配器
│   │   ├── openclaw.ts    # OpenClaw 适配器（未来）
│   │   └── copilot.ts     # Copilot CLI 适配器（未来）
│   └── utils/             # 工具函数
│       ├── fs.ts
│       ├── json.ts
│       └── logger.ts
├── package.json
├── tsconfig.json
└── README.md
```

### 适配器接口设计

```typescript
interface ToolAdapter {
  // 工具名称
  readonly name: string;

  // 获取当前配置，保存到 combo
  capture(): Promise<ComboConfig>;

  // 将 combo 配置应用到系统
  apply(combo: Combo): Promise<void>;

  // 备份当前配置
  backup(backupDir: string): Promise<void>;

  // 验证配置是否合法
  validate(config: ComboConfig): ValidationResult;

  // 获取目标配置路径
  getTargetPath(): string;
}
```

这种设计使得添加新工具非常简单，只需要实现一个新的适配器。

---

## 关键问题与解决方案

### Q1: 插件和技能很大，每个 combo 都拷贝会占用很多空间？
**A**: 可选两种模式：
- 默认使用符号链接（symlink）到全局存储
- 支持 `--copy` 选项完整拷贝，实现隔离

### Q2: 切换后需要重启 Claude Code 才能生效吗？
**A**: 是的，因为 Claude Code 只在启动时读取配置。需要在切换完成后提示用户重启。

### Q3: 如何处理敏感信息（如 API Token）？
**A**:
- combo 配置中支持模板变量 `{{TOKEN_VAR}}`
- 可以从环境变量注入
- 或者提示用户输入，不存储在配置文件中

### Q4: 项目级配置怎么办？
**A**: 第一阶段只处理全局配置，项目级配置可在未来版本支持。

### Q5: 回滚机制？
**A**: 每次切换前自动备份，`cc-combo rollback` 可以恢复到上一个配置。

### Q6: 多个框架（gsd、superpowers、gstack、ralph）一起安装会互相影响怎么办？
**A**: 这正是 CC-Combo 设计的核心场景！每个 combo 只激活你需要的那一组技能/agents，切换后只加载当前 combo 定义的内容，避免不同框架互相干扰，同时减少上下文膨胀。

### Q7: 支持项目级 combo 吗？
**A**: 支持。项目级 combo 存储在项目目录的 `.cc-combo.json`，使用 `cc-combo init` 在项目初始化，`cc-combo use --local` 切换到项目级配置。

---

## 核心使用场景

### 场景 1: 框架隔离切换

你的主要场景：
- **GSD 模式**：只加载 gsd 相关技能，干净专注做项目管理
- **Superpowers 模式**：只加载 superpowers 技能集合
- **GStack 模式**：只加载 gstack QA 测试相关技能
- **Ralph 模式**：只加载 ralph 相关技能
- ** Agency 全量模式**：加载全部 100+ agents （当需要时才用）

好处：
- ✅ 避免不同框架技能提示词重叠冲突
- ✅ 减少上下文长度，避免 Claude Code 提示"上下文太长"
- ✅ 切换像 Docker 一样简单：`cc-combo use gsd`

### 场景 2: TUI 交互式创建

创建/编辑 combo 时，使用带多选的 TUI 控件：
- 从**所有已安装全局技能**中勾选需要加入这个 combo 的
- 从**所有已安装 agents**中勾选
- 从**已安装插件**中勾选
- 从**已配置 MCP servers**中勾选

交互式工作流：
```bash
cc-combo create gsd
? 请选择要包含的全局技能: (空格键选择，回车确认)
❯ ◉ gsd
  ◯ design-review
  ◯ qa
  ◯ deep-research
...
```

### 场景 3: AI 辅助自动推荐 combo

LLM 扫描你现有的 Claude Code/OpenCode/OpenClaw 配置，分析技能/agents，自动分组生成推荐的 combo：

```bash
cc-combo suggest --ai
```

工作流程：
1. 扫描 `~/.claude/skills/`、`~/.claude/agents/`、`~/.claude/plugins/`
2. 提取所有技能/agents 的描述信息
3. LLM 分析分组，建议哪些技能/agents 应该放在一起
4. 自动生成 combo 定义文件，可直接应用或编辑调整

LLM 环境准备：
- 提供清晰的提示词："根据以下技能列表，将它们分组为逻辑上内聚的 combo，每个 combo 专注一个特定工作场景..."
- 可以调用本机 CLI 工具读取文件内容，具备完整上下文
- 输出直接是可导入的 combo.json 格式

### 场景 4: 项目级 combo

在项目目录初始化项目特定配置：
```bash
cd my-project
cc-combo init
cc-combo use --local project-x
```

使用场景：
- 不同项目需要不同的 MCP 服务配置
- 特定项目需要特定插件/技能
- 团队协作时可以将 .cc-combo.json 提交到仓库共享配置

---

## 第一阶段实现路线图

### Phase 1: 基础架构
- [ ] 初始化 TypeScript 项目
- [ ] 实现存储层（`~/.cc-combo` 目录结构）
- [ ] 定义 Combo 类型和接口（包含 agents）
- [ ] 实现 Claude Code 适配器
- [ ] 基础命令: `list`, `current`, `use`, `delete`, `rename`
- [ ] 备份与回滚机制

### Phase 2: 交互式创建与编辑
- [ ] 实现 `create` 命令 + TUI 多选
- [ ] 实现 `edit` 命令，交互式修改 combo
- [ ] 支持交互式选择 skills/agents/plugins/MCP
- [ ] 实现 `capture` 命令（从当前配置创建 combo）
- [ ] 实现配置验证

### Phase 3: AI 辅助推荐
- [ ] 实现 `suggest --ai` 命令
- [ ] 扫描现有技能/agents/plugins
- [ ] 构造 LLM 提示，调用 AI 分析分组
- [ ] 自动生成 combo 定义

### Phase 4: 项目级支持
- [ ] 支持项目级 combo
- [ ] `cc-combo init` 初始化项目配置
- [ ] `--local` 标志使用项目级 combo
- [ ] 支持 `.cc-combo.json` 提交到仓库

### Phase 5: 完善与测试
- [ ] 实现所有 Claude 子命令（`mcp add`, `plugin add`, `skill add`, `agent add`, `env set`）
- [ ] 单元测试
- [ ] README 文档
- [ ] 发布准备

---

## 下一步开发建议

1. 先搭建基础项目结构
2. 实现 `list` 和 `use` 命令验证核心逻辑
3. 逐步添加其他命令
4. 第一个版本聚焦 Claude Code，确保稳定可用
5. 后续再添加其他工具支持

## 总结

CC-Combo 的设计采用**适配器模式**，通过统一的接口抽象不同工具的配置操作，既满足了第一阶段 Claude Code 的需求，又保留了未来扩展到其他工具的灵活性。核心是通过将不同配置组合存储在 `~/.cc-combo/combos/` 目录，切换时通过备份-应用流程快速切换。
