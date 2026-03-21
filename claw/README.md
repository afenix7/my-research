# Claw Ecosystem Technical Research

This repository contains a comprehensive technical research of four major projects in the Claw ecosystem of AI agent frameworks:

- **nanobot** - Standalone MCP (Model Context Protocol) host by Jay Rylance: Go backend + Svelte 5 frontend
- **openclaw** - TypeScript VSCode extension-based autonomous agent by clawdbot: Successor to Claude Dev
- **zeroclaw** - Rust-first performance-focused autonomous agent runtime by zeroclaw-labs: Security-first with sandboxing
- **happyclaw** - Multi-user self-hosted IM (Feishu/Telegram/QQ) AI agent by riba2534: Self-hosted collaborative agents

All research focuses on five core architectural mechanisms:

1. **Gateway mechanism** - How the system accepts requests and routes to agents
2. **Sub-agent mechanism** - How sub-agents are implemented, including identity/soul/persona design
3. **Context trimming strategy** - How the system manages context window limits through compaction/trimming
4. **Context isolation mechanism** - How concurrent sessions/agents are isolated from each other
5. **Memory mechanism design** - How long-term memory and conversation history is managed

## Research Documents

| Project | Language | Primary Use Case | Research Document |
|---------|----------|------------------|-------------------|
| [nanobot](https://github.com/jayrilance/nanobot) | Go (backend) + Svelte (frontend) | Standalone MCP host combining MCP servers with LLMs | [nanobot-research.md](./nanobot-research.md) |
| [openclaw](https://github.com/clawdbot/openclaw) | TypeScript | VSCode extension autonomous coding agent | [openclaw-research.md](./openclaw-research.md) |
| [zeroclaw](https://github.com/zeroclaw-labs/zeroclaw) | Rust | Security-first autonomous agent runtime with sandboxing | [zeroclaw-research.md](./zeroclaw-research.md) |
| [happyclaw](https://github.com/riba2534/happyclaw) | TypeScript (Node.js backend) + React (frontend) | Multi-user self-hosted IM AI agent | [happyclaw-research.md](./happyclaw-research.md) |

## Architectural Comparison

### Gateway Mechanism

| Project | Gateway Implementation | Key Features |
|---------|------------------------|--------------|
| **nanobot** | Go HTTP server (Chi router) + MCP-UI endpoint | Unified MCP gateway, session management, proxy to UI dev server |
| **openclaw** | VSCode extension commands + Node.js runtime | IDE-native gateway, streaming to VSCode webview |
| **zeroclaw** | Axum (Rust) HTTP | Security-hardened with 64KB max body, 30s timeout, rate limiting |
| **happyclaw** | Hono (Node.js) HTTP + WebSocket | Multi-channel IM webhooks, real-time streaming to web UI, REST API |

### Sub-agent / Identity (Soul) Mechanism

| Project | Sub-agent Implementation | Identity Design |
|---------|--------------------------|-----------------|
| **nanobot** | Declarative config agents, MCP tool exposure | Each agent defined in config with name, model, instructions |
| **openclaw** | Declarative config with hierarchical fallback | Identity (soul) config with emoji, prefix, description; hierarchical resolution channel→account→global→agent |
| **zeroclaw** | Delegate tool with pre-configured sub-agents, depth tracking | Configurable identity: openclaw native or AIEOS JSON format from file/inline |
| **happyclaw** | Claude Agent SDK native sub-agents | Predefined code-reviewer/web-researcher, user can create custom per-group |

### Context Trimming / Compaction

| Project | Strategy | Key Algorithm |
|---------|----------|---------------|
| **nanobot** | Incremental compaction - only compact messages after last compaction | Token counting with 83.5% threshold trigger, large tool output truncation to disk with references kept in context |
| **openclaw** | Multi-stage chunked LLM summarization with progressive fallback | Safety margin 1.2× token budgeting, adaptive chunking, identifier preservation, fallback when oversized, pruning with tool-use pairing repair |
| **zeroclaw** | Hybrid: LLM compaction + deterministic hard trimming | Dual trigger (token count OR message count), snaps to user-turn boundary, keeps 20 most recent messages |
| **happyclaw** | Delegated to Claude Agent SDK | Built-in SDK compaction, full history archived to disk before compaction |

### Context Isolation

| Project | Isolation Strategy | Key Mechanisms |
|---------|--------------------|----------------|
| **nanobot** | Session-tree with parent-child attribute inheritance | Session struct with attributes, lock-per-session, parent attribute lookup fallback |
| **openclaw** | Per-agent workspace directory isolation | Each agent gets isolated workspace directory, configurable per-agent, default for default agent |
| **zeroclaw** | Multi-layer defense: workspace + session + OS-level sandbox | Workspace namespacing for memory/secrets/audit, multiple sandbox backends (Bubblewrap, Firejail, Docker), per-thread session in channels |
| **happyclaw** | Per-group directory + per-user home container + Docker isolation by default | Isolated working directory per group, each user gets isolated home container, mount whitelisting blocks sensitive paths, non-admin Docker by default |

### Memory Mechanism

| Project | Memory Architecture | Backends / Features |
|---------|---------------------|----------------------|
| **nanobot** | Database-backed session storage with MCP built-in servers | SQLite/MySQL/PostgreSQL, session management, built-in resource MCP server for persistent resources |
| **openclaw** | Hybrid vector + FTS (full-text search) with SQLite | SQLite with extension support, hybrid ranking combining vector similarity + BM25, pluggable backends |
| **zeroclaw** | Trait-based pluggable architecture | Multiple backends: markdown, SQLite, PostgreSQL, Qdrant, mem0, lucid; categorized memory (core/daily/conversation/custom); procedural memory support |
| **happyclaw** | Hybrid agent-autonomous markdown + SQLite | Agent maintains `CLAUDE.md` memory at workspace and user-global levels, MCP tools for append/search/get, SQLite stores full message history |

## Summary of Design Philosophies

| Project | Design Philosophy | Main Target |
|---------|------------------|-------------|
| **nanobot** | Modular MCP-first standalone host | Deployable MCP-UI server for creating agent experiences through any interface |
| **openclaw** | IDE-integrated autonomous coding | VSCode-based AI coding assistant with sophisticated context management |
| **zeroclaw** | Security-first performance-oriented Rust | Production deployment with strong sandboxing and isolation |
| **happyclaw** | Multi-user IM collaboration | Self-hosted AI assistant for team collaboration via Feishu/Telegram/QQ |

## License

This research document is licensed under the MIT License, same as the original projects.
