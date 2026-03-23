# HappyClaw - Multi-user AI Agent System Architecture Analysis

This research analyzes **HappyClaw** - a self-hosted multi-user AI Agent system built on Claude Agent SDK, focusing on how it implements gateway, container isolation, sub-agent execution, and persistent memory mechanisms.

## Research Scope

For each core module, we examined:
1.  **Architecture Overview** - How the module fits into the overall system
2.  **Data Structures and Storage** - Key types, database schema, filesystem layout
3.  **Complete Operation Flow** - Step-by-step process for key operations
4.  **Code Maps** - Key source files with line numbers and core algorithm snippets
5.  **Design Choices & Tradeoffs** - Why it was built this way

## Core Modules Researched

| Module | Architecture | Main Approach | Report |
|--------|--------------|---------------|--------|
| [HappyClaw Gateway](codemap/gateway-codemap.md) | Hono HTTP + WebSocket | Multi-channel IM gateway with WebSocket real-time streaming, includes pairing mechanism analysis | [codemap/gateway-codemap.md](codemap/gateway-codemap.md) |
| [Database Schema](codemap/database-codemap.md) | SQLite with WAL mode | Persistent storage for messages, users, groups, tasks, sub-agents | [codemap/database-codemap.md](codemap/database-codemap.md) |
| [Container Runner](codemap/container-runner-codemap.md) | Docker + Host dual execution | Multi-layer isolation (per-group directory, Docker container, per-user home) | [codemap/container-runner-codemap.md](codemap/container-runner-codemap.md) |
| [Sub-agent System](codemap/subagent-codemap.md) | Claude SDK native | Predefined + user-configurable sub-agents with prompt-based identity | [codemap/subagent-codemap.md](codemap/subagent-codemap.md) |
| [Memory Mechanism](codemap/memory-codemap.md) | Hybrid agent-autonomous | Agent-maintained markdown + SQLite metadata + MCP full-text search | [codemap/memory-codemap.md](codemap/memory-codemap.md) |

## Summary Table - Key Characteristics

| Module | Storage Approach | Isolation | Authentication | Key Feature |
|--------|------------------|-----------|----------------|------------|
| **Gateway** | In-memory connection pool | Per-user IM connections | HMAC-signed cookies, bcrypt | Multi-channel (Feishu/Telegram/QQ/Web), real-time streaming |
| **Database** | SQLite WAL | - | - | Full message history, incremental migrations |
| **Container Runner** | Filesystem per group | Directory + Docker (optional) | Mount whitelist/blocklist | Dual-mode (container/host), permission hierarchy |
| **Sub-agent** | Database + filesystem | Per-group isolation | Inherited from group | Claude SDK native, tool allowlist |
| **Memory** | Markdown files + SQLite | Per-user/per-group | Inherited from group | Agent-autonomous, two-level (workspace + user-global) |

## Overview: Architecture Summary

HappyClaw is a **multi-user self-hosted AI Agent system** that:

1.  **Multi-channel Input**: Accepts messages from Feishu, Telegram, QQ instant messaging platforms plus a React web UI
2.  **Isolated Execution**: Runs Claude Agents in either Docker containers (default for non-admins) or directly on the host (for admins), with per-user/per-group filesystem isolation
3.  **Real-time Streaming**: Streams agent output (text deltas, tool use, thinking) via WebSocket to the web UI in real-time
4.  **Sub-agent Support**: Supports predefined specialized sub-agents (code-reviewer, web-researcher) and allows users to create custom sub-agents per workspace
5.  **Hybrid Persistent Memory**: Combines agent-autonomous markdown memory (`CLAUDE.md`) with SQLite persistence for full message history and metadata

### High-level Architecture Diagram

```mermaid
classDiagram
    class Gateway {
        +Hono HTTP router
        +WebSocket connection manager
        +IM connection pool (per-user)
        +Route modules (auth/groups/memory/tasks/agents)
        +handleWebhook()
        +broadcastToWeb()
    }
    class Database {
        +SQLite WAL mode
        +messages: full history
        +users: accounts
        +groups: workspaces
        +tasks: scheduled tasks
        +agents: sub-agent definitions
    }
    class ContainerRunner {
        +runContainerAgent()
        +runHostAgent()
        +buildVolumeMounts()
        +isolation: per-group folder
        +security: mount allowlist
    }
    class AgentRunner {
        +Claude Agent SDK query()
        +MCP tools (12 tools)
        +IPC file communication
        +streaming output via stdout
        +PreCompact hook archives conversation
    }
    class MemorySystem {
        +workspace: groups/{folder}/CLAUDE.md
        +user-global: user-global/{userId}/CLAUDE.md
        +MCP: memory_append/search/get
        +full-text search via backend
    }
    class PairingManager {
        +generatePairingCode(userId)
        +verifyPairingCode(code)
        +6-digit, 5-min TTL, single-use
        +binds QQ chats to user accounts
    }

    Gateway --> Database : stores messages/users
    Gateway --> ContainerRunner : enqueues message
    ContainerRunner --> AgentRunner : spawns process/container
    AgentRunner --> MemorySystem : reads/writes memory
    Gateway --> PairingManager : handles /pair command
```

## Directory Structure

```
~/my-research/claw/happyclaw/
├── README.md                 # This file - overview and comparison
├── codemap/                  # Detailed codemap for each core module
│   ├── gateway-codemap.md    # Gateway architecture + pairing mechanism
│   ├── database-codemap.md   # Database schema and migrations
│   ├── container-runner-codemap.md  # Container execution and isolation
│   ├── subagent-codemap.md   # Sub-agent system design
│   └── memory-codemap.md     # Hybrid memory mechanism
└── docs/                     # Additional documentation
```

## Reading the Reports

Each codemap file follows the same structure:
1.  Module overview and official links
2.  Architecture diagrams (class and data flow)
3.  Complete storage/layout description
4.  Step-by-step operation flow for key operations
5.  Key source files with line numbers
6.  Core code snippets showing key algorithms
7.  Summary of design choices and tradeoffs
