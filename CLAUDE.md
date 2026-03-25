# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with codebase in this repository.

## Project Overview

This is a **technical research repository** containing in-depth deep-dive analysis and documentation of various open-source AI agent frameworks and game engine systems. It does NOT contain actual source code from the projects - it contains codemaps, architectural analysis, and comparative research created by reading and analyzing external open-source repositories.

## Principles

- Always use the `deep-wiki` skill to investigate GitHub projects when doing research
- Use appropriate specialized subagents for investigation tasks
- This repository is for knowledge accumulation, not for shipping production code

## Repository Structure

```
/root/my-research/
├── agents/                      # AI Agent Implementation Comparison
│   ├── pi-mono-research.md      # badlogic/pi-mono analysis
│   ├── opencode-research.md     # anomalyco/opencode analysis
│   ├── codex-research.md        # openai/codex analysis
│   ├── claude-code-research.md  # anthropic/claude-code analysis
│   ├── pi-mono/                 # Detailed codemap by architectural component
│   └── opencode/                 # Detailed codemap by architectural component
├── claw/                        # Claw Ecosystem Technical Research
│   ├── README.md                # Overall ecosystem comparison (4 projects)
│   ├── nanobot-research.md      # nanobot-ai/nanobot analysis
│   ├── openclaw-research.md     # clawdbot/openclaw analysis
│   ├── zeroclaw-research.md     # zeroclaw-labs/zeroclaw analysis
│   ├── happyclaw-research.md    # riba2534/happyclaw analysis
│   ├── nanobot/                 # Detailed codemap substructure
│   ├── happyclaw/               # Detailed codemap substructure
│   └── zeroclaw/                # Detailed codemap substructure
├── ecs/                         # ECS Frameworks - Component Storage & CRUD Comparison
│   ├── README.md                # Overview of 6 frameworks
│   ├── findings.md              # Key observations and patterns
│   └── codemap/                 # Detailed per-framework codemaps
├── render-graph/                # Render Graph Implementation Analysis (Game Engine)
│   ├── README.md                # Adria vs SakuraEngine comparison
│   ├── adria-analysis.md        # mateeeeeee/Adria (DirectX 12) analysis
│   └── sakura-analysis.md       # SakuraEngine/SakuraEngine analysis
├── notes/                       # Additional technical notes and articles
│   ├── agents/                  # 7 Markdown articles on AI agent topics
│   └── game-engine/             # GAMES104/GAMES202 course lecture notes
└── transcripts/                 # Research transcripts (placeholder)
```

## Common Development Commands

This repository contains **only Markdown documentation** - there are no buildable artifacts, no dependencies to install, and no tests to run. All content is human-readable technical analysis.

When adding new research:

1. Create a new research file following the existing codemap pattern
2. Include GitHub links to the original project being analyzed
3. Break down analysis by architectural component
4. Reference key source files from the external repository
5. Add comparative summary tables where appropriate

## Key Research Focus Areas

### AI Agents
- Gateway mechanism - how requests are accepted and routed
- Sub-agent mechanism - how child agents are implemented
- Context trimming - how context window limits are managed
- Context isolation - how concurrent sessions are isolated
- Memory mechanism - long-term memory and conversation history storage
- Agent React pattern - core loop implementation
- Skills - reusable instructions/capabilities
- Session isolation - forking/branching experimentation

### ECS (Entity Component System)
- Memory storage architecture (SoA vs AoS, sparse vs dense, chunks vs pages)
- Complete CRUD operation flows
- Cache locality optimization strategies
- Framework comparisons across 6 different implementations

### Render Graphs (Game Engine)
- Render graph compilation process
- Barrier handling strategies
- Synchronization point management
- Async compute implementation
- RHI (Render Hardware Interface) abstraction

## Top-Level Research Summary

### AI Agent Comparison (agents/)

| Feature | pi-mono | OpenCode | Codex CLI | Claude Code |
|---------|---------|----------|-----------|------------|
| Agent React | Event-driven double loop | ACP + event bus | Simple ReAct | ReAct + hierarchical Team Lead/Member |
| Context Compression | LLM structured summary + keep recent | Pruning + LLM compression (2-level) | Sliding window + summary | Auto-compaction with circuit breaker |
| SubAgent | Markdown discovery | Config + dynamic generation | Process-level spawn | Built-in `spawn_sub_agent` + Agent Teams |
| Skill Format | `SKILL.md` Markdown | `SKILL.md` + remote Git | MCP server config | `SKILL.md` + native MCP |
| Session Isolation | Tree structured file (LDJSON) | SQL + parent_id reference | File-level isolation | git worktree + branching |
| Agent Teams | ❌ | ❌ | ❌ | ✅ Native parallel collaboration |

### Claw Ecosystem Comparison (claw/)

| Project | Language | Gateway | Sub-agent | Context Trimming | Isolation | Memory |
|---------|----------|---------|-----------|------------------|-----------|--------|
| **nanobot** | Go + Svelte | Chi HTTP | Declarative config | Incremental compaction @ 83.5% | Session-tree | SQLite/MySQL/PostgreSQL |
| **openclaw** | TypeScript | VSCode extension | Declarative config | Multi-stage chunked summarization | Per-agent directory | Hybrid SQLite vector + FTS |
| **zeroclaw** | Rust | Axum HTTP | Delegate tool config | Hybrid LLM + hard trim | Multi-layer sandbox | Pluggable (markdown/SQLite/Qdrant) |
| **happyclaw** | TypeScript | Hono HTTP+WebSocket | Claude SDK native | Delegated to SDK | Docker + per-group | Agent-autonomous CLAUDE.md + SQLite |

## Guidance

When adding new research to this repository:
- Follow the existing codemap format established in previous research
- Categorize findings by architectural component
- Include direct references to source files in the external GitHub repository
- Focus on *how* the implementation works, not just *what* it does
- Add comparative tables when comparing multiple implementations
