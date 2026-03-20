# OpenAI Codex / Codex CLI 技术分析

## 项目概览

**Codex** 最初是 OpenAI 2021 年发布的代码生成模型，是 GitHub Copilot 的基础模型，将自然语言转换为可运行代码。近期（2025年4月）OpenAI 发布了 **Codex CLI**，一个开源本地编码 Agent 工具。

- 官方: https://github.com/openai/codex
- 模型: 基于 OpenAI o3/o4-mini 模型
- 特点: 本地运行 CLI，支持多模型，开源可扩展

---

## 1. Agent React 模式实现

Codex CLI 使用**标准 ReAct 循环**（Reasoning + Acting），这是目前 LLM Agent 最常见的模式：

```
while not done:
  1. LLM 推理下一步该做什么（Reasoning）
  2. 执行工具调用获得结果（Acting）
  3. 将结果放回上下文，重复循环
```

不同于 pi-mono 和 OpenCode 的复杂事件系统，Codex CLI 设计更简洁，聚焦终端交互。

---

## 2. 上下文管理与上下文压缩

公开信息中，Codex CLI 的上下文管理策略：

### 基本方法
- **滑动窗口**: 保留最近 N 轮对话，丢弃最旧的
- **摘要压缩**: 当上下文接近模型限制时，对历史对话生成摘要
- **智能修剪**: 移除已经执行完成的工具调用输出，只保留结果摘要

### 与 pi-mono/OpenCode 对比

| 项目 | 压缩策略 | 特点 |
|------|----------|------|
| pi-mono | 单次 LLM 压缩 + 保留最近 | 结构化摘要，保持文件操作追踪 |
| OpenCode | 修剪 + LLM 压缩两级 | 渐进式，轻量修剪先做 |
| Codex CLI | 滑动窗口 + 摘要 | 更简单，适合 CLI |

Codex CLI 作为 OpenAI 官方产品，应该深度集成 OpenAI API 的原生上下文缓存特性（openai 新的 context caching API），减少 tokens 消耗。

---

## 3. SubAgent 创建

Codex CLI 原生支持 **Spawn 子 Agent** 模式：

- **子进程执行**: 主 Agent 可以 spawn 新的 Codex CLI 进程处理子任务
- **隔离上下文**: 子 Agent 有独立上下文，不影响主会话
- **结果汇总**: 子任务完成后，结果返回主 Agent 合并

这种设计利用了 CLI 工具的特性，通过进程隔离实现简单可靠的子 Agent。

---

## 4. Skill 机制

Codex CLI 支持**自定义 Skills / MCP 服务器**：

### MCP 优先

Codex 原生支持 Model Context Protocol (MCP)，这是 OpenAI 推广的新技能/工具标准：
- 每个 Skill 可以是一个 MCP 服务器
- MCP 服务器提供工具列表和 schema
- 动态连接到 MCP 服务器获取工具
- 支持本地和远程 MCP 服务器

### 配置方式

Skills/MCP 在 `codex.json` 配置文件中声明：
```json
{
  "mcpServers": {
    "skill-name": {
      "command": "command-to-start-server",
      "args": [],
      "env": {}
    }
  }
}
```

### 对比 pi-mono/OpenCode

| 项目 | Skill 格式 | 发现方式 |
|------|------------|----------|
| pi-mono | `SKILL.md` Markdown | 文件系统扫描 |
| OpenCode | `SKILL.md` + 远程 | 文件系统 + Git 拉取 |
| Codex CLI | MCP 服务器 | 配置声明 |

Codex 选择 MCP 作为技能标准，这是更现代但也更重量级的方法，每个技能需要完整的服务器进程。

---

## 5. Agent 会话隔离

Codex CLI 使用**文件系统级会话隔离**：

### 会话存储

- 每个会话对应独立的 `.codex/sessions/{session-id}.json` 文件
- JSON 格式存储完整消息历史
- 简单直接，便于版本控制和备份

### 分叉机制

- 创建新会话文件，复制父会话历史到起点
- 新会话独立写入，不修改父会话
- 手动管理，没有内置会话树 UI 导航

### 隔离特点

- **进程隔离**: SubAgent 通过 spawn 独立进程实现，完全隔离
- **文件隔离**: 每个会话独立文件，不会互相干扰
- **简洁设计**: 适合 CLI 交互，没有复杂数据库

---

## 总结

Codex 是 OpenAI 进入本地 Agent CLI 市场的产品：
- 设计理念: **简约**，相比 pi-mono 和 OpenCode 功能更少但更聚焦
- 优势: 深度集成最新 OpenAI 模型能力（o3/o4-mini 推理），原生 MCP 支持
- 定位: 开发者命令行助手，不如 OpenCode 功能丰富，但开箱即用
- 会话隔离: 进程+文件隔离，简单可靠
