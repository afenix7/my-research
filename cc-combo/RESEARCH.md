# CC-Combo: Claude Code 配置组合切换工具 - 研究报告

## 项目概述

CC-Combo 是一个命令行工具，用于创建、管理和快速切换不同的 AI 编辑器配置组合（combo）。每个 combo 可以包含：
- Claude Code 配置（settings.json、环境变量、权限设置等）
- 插件集合
- 全局技能
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
├── combos/                    # 所有配置组合
│   ├── default/              # combo 名称
│   │   ├── combo.json        # combo 元数据和定义
│   │   ├── claude/           # Claude Code 配置快照
│   │   │   ├── settings.json
│   │   │   ├── settings.local.json
│   │   │   ├── claude_desktop_config.json
│   │   │   ├── plugins/      # 插件（可以是 symlink 或拷贝）
│   │   │   └── skills/       # 全局技能
│   │   ├── openclaw/         # 未来扩展
│   │   │   └── openclaw.json
│   │   └── ...
│   ├── volcengine/
│   │   └── claude/...
│   └── openrouter/
│       └── ...
└── current.json              # 当前激活的 combo 记录
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
      ]
    }
  }
}
```

### 支持的工具（第一阶段）

| 工具 | 配置目标位置 | 可配置内容 | 状态 |
|------|-------------|-----------|------|
| Claude Code | `~/.claude/` | settings.json, MCP, plugins, skills | ✅ 第一阶段支持 |
| OpenClaw | `~/.openclaw/openclaw.json` | env, models, providers | 🔄 未来扩展 |
| GitHub Copilot CLI | `~/.copilot/config.json` | model, tokens | 🔄 未来扩展 |
| OpenCode | 待研究 | - | 🔄 未来扩展 |
| Codex | 待研究 | - | 🔄 未来扩展 |

---

## CLI 命令设计

### 核心命令

```bash
# 创建新 combo
cc-combo create <name>

# 从当前配置创建 combo
cc-combo capture <name>

# 列出所有 combos
cc-combo list

# 切换到指定 combo
cc-combo use <name>

# 编辑 combo
cc-combo edit <name>

# 删除 combo
cc-combo delete <name>

# 重命名 combo
cc-combo rename <old> <new>

# 显示当前 combo 信息
cc-combo current

# 验证 combo 配置
cc-combo validate <name>
```

### Claude Code 特定命令

```bash
# 添加 MCP 服务器到 combo
cc-combo claude mcp add <combo> <name> --type stdio --command "node" --args "./server.js"

# 添加插件到 combo
cc-combo claude plugin add <combo> <plugin-name>

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
2. 提取 settings、MCP、已安装插件列表、技能列表
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
- **CLI 框架**: Commander.js 或 yargs
- **交互**: Inquirer.js 或 Prompts
- **配置解析**: JSON (原生支持)
- **文件操作**: fs/promises (原生) + extra 原生方法
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

---

## 第一阶段实现路线图

### Phase 1: 基础架构
- [ ] 初始化 TypeScript 项目
- [ ] 实现存储层（`~/.cc-combo` 目录结构）
- [ ] 定义 Combo 类型和接口
- [ ] 实现 Claude Code 适配器
- [ ] 基础命令: `list`, `current`, `use`

### Phase 2: 创建和捕获
- [ ] 实现 `create` 命令
- [ ] 实现 `capture` 命令（从当前配置创建 combo）
- [ ] 实现配置验证
- [ ] 备份机制

### Phase 3: 编辑管理
- [ ] 实现 `delete`, `rename`
- [ ] 实现 `claude mcp add`, `claude env set` 等子命令
- [ ] 实现 `validate` 命令

### Phase 4: 测试文档
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
