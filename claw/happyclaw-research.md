# HappyClaw Technical Analysis: Gateway, Sub-agent, Context Trimming, Isolation, and Memory Mechanisms

## Project Overview

HappyClaw is a self-hosted multi-user AI Agent system for Instant Messaging platforms (Feishu/Lark, Telegram, QQ) with a web UI. It runs Claude AI agents in isolated Docker containers or on the host machine, with each user getting their own independent workspace. It's part of the Claw ecosystem, focusing on multi-user collaboration and persistent memory.

**Official Resources:**
- GitHub Repository: [https://github.com/riba2534/happyclaw](https://github.com/riba2534/happyclaw)

---

## 1. Gateway Mechanism

### Architecture / Implementation

HappyClaw uses a **Hono-based HTTP gateway with WebSocket support for real-time streaming**. The gateway accepts webhooks from IM platforms (Feishu, Telegram, QQ) and serves the web UI frontend. It also handles REST API for the web UI and WebSocket for streaming agent output.

**Source Location:**
- Main gateway setup: `src/web.ts`
- Routes: `src/routes/` (auth, groups, memory, tasks, agents, admin, etc.)
- WebSocket protocol: `shared/stream-event.ts`

### Key Characteristics / Design Choices

1. **Multi-Channel Input**: Supports:
   - Feishu/Lark via WebSocket long-lived connection
   - Telegram via long polling
   - QQ via WebSocket connection
   - Web UI via HTTP + WebSocket

2. **Security Features**:
   - CORS configuration with configurable allowed origins
   - HMAC-signed cookies for session authentication
   - bcrypt password hashing
   - AES-256-GCM encryption for stored secrets
   - Rate limiting on login attempts (5 failures → 15 minute lockout)

3. **Real-time Streaming**: All agent output (text deltas, thinking, tool use) is streamed via WebSocket to the web UI in real-time using the `StreamEvent` protocol

4. **Separation of Concerns**: Gateway (main process) handles HTTP API and message routing, while agent execution happens in separate container/host processes via IPC files

5. **Atomic IPC**: File-based IPC with atomic writes (`.tmp` then rename) to avoid partial reads

---

## 2. Sub-agent Mechanism (Identity/Soul Design)

### Architecture / Implementation

HappyClaw implements **two-level sub-agent system**:
1. **Predefined Sub-agents**: Built-in specialized agents (code-reviewer, web-researcher) that can be invoked via the MCP `send_message` tool
2. **User-configured Sub-agents**: Users can create custom sub-agents per-group through the web UI, each with their own system prompt and status tracking

**Source Location:**
- Predefined definitions: `container/agent-runner/src/agent-definitions.ts`
- API routes: `src/routes/agents.ts`
- Database table: `agents` (id, status, kind, prompt, group_id)

### Key Code Snippet

```typescript
// From: container/agent-runner/src/agent-definitions.ts:L10-L27
// Predefined sub-agents built into the agent runner
export const PREDEFINED_AGENTS: Record<string, AgentDefinition> = {
  'code-reviewer': {
    description: 'Code review agent that analyzes code quality, best practices, and potential issues',
    prompt:
      'You are a strict code reviewer. Focus on correctness, security, performance, and maintainability. ' +
      'Point out specific issues with file:line references. Be concise and actionable.',
    tools: ['Read', 'Glob', 'Grep'],
    maxTurns: 15,
  },
  'web-researcher': {
    description: 'Web research agent that searches and extracts information from web pages',
    prompt:
      'You are an efficient web researcher. Search for information, extract key facts, and summarize findings. ' +
      'Always cite sources with URLs. Prefer authoritative sources.',
    tools: ['WebSearch', 'WebFetch', 'Read', 'Write'],
    maxTurns: 20,
  },
};
```

### Key Characteristics / Design Choices

1. **Claude Agent SDK Integration**: Leverages the official Claude Agent SDK's native sub-agent support where any agent can invoke specialized sub-agents with different prompts and tool allowlists

2. **Per-Group Sub-agents**: Sub-agents are scoped to a specific group/workspace, so different workspaces can have their own custom agents

3. **Identity via Prompt**: Sub-agent "soul" (persona) is defined entirely by the system prompt - different prompts create different agent behaviors

4. **Tool Allowlist**: Each sub-agent can have its own allowed tool list, restricting what operations the sub-agent can perform for security containment

5. **Max Turns Control**: Each sub-agent has a configurable maximum turn count to prevent infinite loops

6. **Status Tracking**: The gateway tracks sub-agent status (idle/running/completed/error) and broadcasts status updates via WebSocket to the web UI

7. **Per-user AI Appearance**: Users can customize AI name, avatar emoji, and avatar color - this is the user-facing "soul" identity

---

## 3. Context Trimming Strategy (Compaction)

### Architecture / Implementation

HappyClaw **delegates context trimming and compaction to the Claude Agent SDK**, which provides built-in context management. The HappyClaw gateway stores full message history in SQLite and the agent runner uses the SDK's built-in session management.

There's also a **PreCompact hook** that archives full conversations to the `conversations/` directory before compaction occurs, providing a full audit trail.

**Source Location:**
- SDK: `@anthropic-ai/claude-agent-sdk` (transitive dependency)
- Archiving hook: Mentioned in `container/agent-runner/`

### Key Characteristics / Design Choices

1. **SDK-Managed Context**: Relies on Claude Agent SDK's built-in context window management which automatically trims older messages when context is exhausted

2. **Conversation Archiving**: Before compaction, the full conversation is archived to disk in `conversations/` for future reference

3. **Full History Persistence**: Gateway maintains complete message history in SQLite for display in the web UI even after compaction

4. **Session Persistence**: Claude session state is persisted in `data/sessions/{folder}/.claude/` isolated per session

5. **/clear Command**: Users can manually clear context with the `/clear` command via IM interface

---

## 4. Context Isolation Mechanism

### Architecture / Implementation

HappyClaw provides **strong isolation at multiple levels**:
1. **Per-group/workspace directory isolation** - each group has its own working directory
2. **Per-user home container isolation** - each user gets an isolated home container
3. **Docker container isolation** - default for non-admin users, everything runs in a container
4. **Database-level isolation** - sessions, memory, and messages are scoped to groups/users
5. **IPC namespacing** - each group has its own IPC directory

**Source Location:**
- Types: `src/types.ts` (context_mode: 'group' | 'isolated' for scheduled tasks)
- Container mounting: `src/container-runner.ts`
- Security: `src/mount-security.ts`

### Key Characteristics / Design Choices

1. **Filesystem Isolation**:
   - Each registered group has its own folder `data/groups/{folder}/` that only it can access
   - Claude sessions are stored in `data/sessions/{folder}/.claude/` per-session isolation
   - IPC communication uses `data/ipc/{folder}/` with separate input/messages/tasks directories

2. **Docker Isolation by Default**:
   - Non-admin users default to Docker container execution mode
   - Only specifically allowed directories can be mounted into containers
   - Blocked paths: `.ssh`, `.gnupg`, and other sensitive directories are never mounted
   - Non-admin containers get read-only access to whitelisted mounts by default

3. **User Isolation**:
   - Each user gets an automatic `is_home=true` main container on registration
   - Admin: `folder=main` runs in host mode with broader access
   - Member: `folder=home-{userId}` runs in container mode with isolation
   - Users cannot access each other's workspaces or memory without explicit sharing

4. **Multiple Modes**:
   - `container`: Full Docker container isolation (default for non-admins)
   - `host`: Runs directly on host for admin/debugging

5. **Scheduled Task Isolation**: Scheduled tasks can run in either `group` context (sharing the group session) or `isolated` context (fresh session each run)

6. **Mount Security**:
   - Whitelist-based mount allowlist
   - Blocked patterns prevent mounting sensitive directories
   - Non-main groups always get read-only access unless explicitly configured otherwise

---

## 5. Memory Mechanism Design

### Architecture / Implementation

HappyClaw uses a **hybrid memory system combining**:
1. **CLAUDE.md automatic maintenance**: Agent autonomously maintains a markdown-based memory file in the workspace
2. **Database memory**: SQLite stores messages, scheduled tasks, users, groups, and sub-agents
3. **User-global memory**: Each user has a global `CLAUDE.md` for user-level preferences and facts
4. **Full-text search**: Memory files support full-text search via MCP tools

**Source Location:**
- Database: `src/db.ts` (SQLite with WAL mode)
- Memory API routes: `src/routes/memory.ts`
- MCP tools: `container/agent-runner/src/mcp-tools.ts` (`memory_append`, `memory_search`, `memory_get`)

### Key Code Snippet

**Database Schema** (from `src/db.ts`):

```
- `chats`: Group metadata
- `messages`: Full message history (all messages preserved)
- `scheduled_tasks`: Scheduled task configuration
- `task_run_logs`: Task execution history
- `registered_groups`: Workspace registration with isolation settings
- `sessions`: (group_folder, agent_id) → Claude session_id mapping for persistence
- `users`: User accounts with password hash, role, permissions, and AI appearance settings
- `user_sessions`: Login sessions
- `invite_codes`: Registration invitation codes
- `auth_audit_log`: Authentication audit trail
- `group_members`: Many-to-many mapping of users to shared workspaces
- `agents`: Sub-agent definitions (per-group)
- `usage_records`: Token usage per request
- `usage_daily_summary`: Pre-aggregated daily usage statistics
```

### Key Characteristics / Design Choices

1. **Agent-Autonomous Memory**: The agent itself maintains `CLAUDE.md` memory files - it can append, search, and recall facts using MCP tools

2. **Two-Level Memory**:
   - **Workspace memory**: `CLAUDE.md` in the group workspace folder for project-specific knowledge
   - **User-global memory**: `data/groups/user-global/{userId}/CLAUDE.md` for user preferences and personal facts that travel across workspaces

3. **SQLite Persistence**:
   - WAL mode for concurrent reads and writes
   - Schema migrations from v1 to v24 with automatic upgrade
   - All messages are persisted indefinitely - compaction only affects the active agent context, not the stored history

4. **MCP Tools for Memory Access**:
   - `memory_append`: Append a new fact to memory
   - `memory_search`: Full-text search across memory files
   - `memory_get`: Retrieve a specific memory file content

5. **Daily Summary**: Automatic daily summary runs at 2-3 AM that writes a HEARTBEAT.md with daily activity recap

6. **Full-text Search**: Backend supports full-text search across all memory files returned to the agent for recall

7. **Sharing**: Multiple users can be added as members to a shared workspace, allowing collaboration on the same workspace with shared memory

---

## Architecture Summary

| Feature | Implementation | Source Location | Advantages |
|---------|-----------------|-----------------|------------|
| Gateway Mechanism | Hono HTTP + WebSocket, multi-channel IM webhooks | `src/web.ts`, `src/routes/` | Real-time streaming, supports multiple IM platforms |
| Sub-agent/Identity | Claude SDK native sub-agents + user-configurable per group | `container/agent-runner/src/agent-definitions.ts`, `src/routes/agents.ts` | Specialization, configurable personas, tool isolation |
| Context Trimming | Delegated to Claude Agent SDK with pre-compaction archiving | SDK built-in + hook archiving to `conversations/` | Leverages official SDK battle-tested implementation |
| Context Isolation | Multi-layer: per-group directory, Docker container, per-user home | `src/container-runner.ts`, `src/mount-security.ts` | Defense in depth, multi-user safe |
| Memory Mechanism | Hybrid: Agent-maintained markdown `CLAUDE.md` + SQLite + MCP tools | `src/routes/memory.ts`, `container/agent-runner/src/mcp-tools.ts` | Agent-autonomous, persistent, searchable, supports both workspace and user-global |

## Summary

HappyClaw is a multi-user self-hosted AI agent system that:

1. Uses **Hono for the HTTP/WebSocket gateway** with built-in security features (authentication, rate limiting, CORS) and supports multiple IM platforms (Feishu, Telegram, QQ) plus web UI.

2. Implements **sub-agents via Claude Agent SDK native support** with predefined specialized agents (code-reviewer, web-researcher) and allows users to create custom sub-agents per group, each with their own prompt identity and tool allowlist.

3. **Delegates context trimming to the Claude Agent SDK** while archiving full conversation history before compaction for auditing.

4. Provides **defense-in-depth context isolation** through directory per-workspace isolation, Docker container isolation by default for non-admins, per-user home containers, and mount whitelisting that blocks sensitive paths.

5. Features **hybrid agent-autonomous memory** where the agent maintains markdown memory files (workspace-level and user-global) with full-text search via MCP tools, backed by SQLite for metadata and message history.

The project focuses on multi-user collaboration with proper isolation between users and workspaces, making it suitable for self-hosted team deployment with persistent memory across conversations.

## References

[^1]: GitHub Repository - https://github.com/riba2534/happyclaw
