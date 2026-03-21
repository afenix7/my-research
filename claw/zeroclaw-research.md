# ZeroClaw Technical Analysis: Gateway, Sub-agent, Context Trimming, Isolation, and Memory Mechanisms

## Project Overview

ZeroClaw is a Rust-first autonomous agent runtime optimized for performance, efficiency, stability, extensibility, sustainability, and security. It's part of the Claw ecosystem of AI agent frameworks, focusing heavily on security through multiple layers of sandboxing and isolation.

**Official Resources:**
- GitHub Repository: [https://github.com/zeroclaw-labs/zeroclaw](https://github.com/zeroclaw-labs/zeroclaw)

---

## 1. Gateway Mechanism

### Architecture / Implementation

ZeroClaw uses an **Axum-based HTTP gateway with comprehensive security hardening. The gateway is the primary entry point for webhooks, REST API, and WebSocket connections. It supports multiple messaging channels (Telegram, Discord, Slack, etc.) through webhook integration.

**Source Location:** `src/gateway/mod.rs, `src/gateway/api.rs`

### Key Code Snippet

```rust
// From: src/gateway/mod.rs:L51-L67
// Maximum request body size (64KB) — prevents memory exhaustion.
pub const MAX_BODY_SIZE: usize = 65_536;
/// Default request timeout (30s) — prevents slow-loris attacks.
pub const REQUEST_TIMEOUT_SECS: u64 = 30;

/// Read gateway request timeout from `ZEROCLAW_GATEWAY_TIMEOUT_SECS` env var
/// at runtime, falling back to [`REQUEST_TIMEOUT_SECS`].
///
/// Agentic workloads with tool use (web search, MCP tools, sub-agent
/// delegation) regularly exceed 30 seconds. This allows operators to
/// increase the timeout without recompiling.
pub fn gateway_request_timeout_secs() -> u64 {
    std::env::var("ZEROCLAW_GATEWAY_TIMEOUT_SECS")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(REQUEST_TIMEOUT_SECS)
}
```

### Key Characteristics / Design Choices

1. **Security-First Design**:
   - 64KB maximum request body size to prevent memory exhaustion attacks
   - 30-second default request timeout to prevent slow-loris attacks
   - Configurable timeout via environment variable for agentic workloads that need longer
   - Header sanitization handled by axum/hyper out of the box
   - Rate limiting with configurable sliding window

2. **Multiple Endpoint Types**:
   - REST JSON API for machine-to-machine communication
   - Webhook endpoints for messaging channel callbacks (Telegram, Discord, etc.)
   - WebSocket for real-time streaming
   - Server-Sent Events (SSE) for progress updates
   - Static file serving for web UI

3. **Pairing Security**: Public endpoint pairing for secure authentication between clients and the gateway

3. **Architecture**: Stateless shared state with Arc/Mutex for thread-safe concurrent access

---

## 2. Sub-agent Mechanism (Identity/Soul Design)

### Architecture / Implementation

ZeroClaw implements a **delegate tool-based sub-agent system** where specialized sub-agents can be configured declaratively and invoked via tool calls from a primary agent. Each agent has an identity configuration that supports both the default "openclaw" format and external AIEOS identity JSON format.

**Source Location:**
- Sub-agent delegation tool: `src/tools/delegate.rs`
- Identity config schema: `src/config/schema.rs:L1354-L1378`

### Key Code Snippet

```rust
// From: src/config/schema.rs:L1354-L1378
pub struct IdentityConfig {
    /// Identity format: "openclaw" (default) or "aieos"
    #[serde(default = "default_identity_format")]
    pub format: String,
    /// Path to AIEOS JSON file (relative to workspace)
    #[serde(default)]
    pub aieos_path: Option<String>,
    /// Inline AIEOS JSON (alternative to file path)
    #[serde(default)]
    pub aieos_inline: Option<String>,
}

fn default_identity_format() -> String {
    "openclaw".into()
}

impl Default for IdentityConfig {
    fn default() -> Self {
        Self {
            format: default_identity_format(),
            aieos_path: None,
            aieos_inline: None,
        }
    }
}
```

```rust
// From: src/tools/delegate.rs:L15-L34
/// Tool that delegates a subtask to a named agent with a different
/// provider/model configuration. Enables multi-agent workflows where
/// a primary agent can hand off specialized work (research, coding,
/// summarization) to purpose-built sub-agents.
pub struct DelegateTool {
    agents: Arc<HashMap<String, DelegateAgentConfig>>,
    security: Arc<SecurityPolicy>,
    /// Global credential fallback (from config.api_key)
    fallback_credential: Option<String>,
    /// Provider runtime options inherited from root config.
    provider_runtime_options: providers::ProviderRuntimeOptions,
    /// Depth at which this tool instance lives in the delegation chain.
    depth: u32,
    /// Parent tool registry for agentic sub-agents.
    parent_tools: Arc<RwLock<Vec<Arc<dyn Tool>>>>,
    /// Inherited multimodal handling config for sub-agent loops.
    multimodal_config: crate::config::MultimodalConfig,
    /// Global delegate tool config providing default timeout values.
    delegate_config: DelegateToolConfig,
}
```

### Key Characteristics / Design Choices

1. **Declarative Sub-agent Configuration**: Each sub-agent is pre-configured in the main configuration file with:
   - Custom model/provider settings
   - Optional system prompt
   - Tool allowlist
   - Timeout configuration
   - Agentic mode toggle (multi-turn tool calling vs single-turn completion)

2. **Depth Tracking**: Delegation depth is tracked and incremented for nested sub-agent calls, preventing infinite recursion

3. **Tool Allowlist**: The primary agent can restrict which tools are available to the sub-agent for security containment

4. **Two Identity Formats:
   - **OpenClaw format: Default identity built into the OpenClaw/ZeroClaw ecosystem
   - **AIEOS format: External identity/persona format loaded from JSON file or inline

5. **Hybrid Modes**: Supports both:
   - **Single-turn**: Delegate task to sub-agent, get completion, return result to main conversation
   - **Agentic**: Full multi-turn tool-calling loop for the sub-agent to complete the task autonomously

---

## 3. Context Trimming Strategy (Compaction)

### Architecture / Implementation

ZeroClaw implements a **hybrid two-stage context trimming strategy that combines:
1. **LLM-based auto-compaction when token or message thresholds are exceeded
2. **Deterministic hard trimming** as a fallback when compaction fails

**Source Location:** `src/agent/loop_.rs`

### Key Code Snippet

```rust
// From: src/agent/loop_.rs:L226-L250
/// Default trigger for auto-compaction when non-system message count exceeds this threshold.
const DEFAULT_MAX_HISTORY_MESSAGES: usize = 50;

/// Keep this many most-recent non-system messages after compaction.
const COMPACTION_KEEP_RECENT_MESSAGES: usize = 20;

/// Safety cap for compaction source transcript passed to the summarizer.
const COMPACTION_MAX_SOURCE_CHARS: usize = 12_000;

/// Max characters retained in stored compaction summary.
const COMPACTION_MAX_SUMMARY_CHARS: usize = 2_000;

/// Estimate token count for a message history using ~4 chars/token heuristic.
/// Includes a small overhead per message for role/framing tokens.
fn estimate_history_tokens(history: &[ChatMessage]) -> usize {
    history
        .iter()
        .map(|m| {
            // ~4 chars per token + ~4 framing tokens per message (role, delimiters)
            m.content.len().div_ceil(4) + 4
        })
        .sum()
}
```

```rust
// From: src/agent/loop_.rs:L349-L409
async fn auto_compact_history(
    history: &mut Vec<ChatMessage>,
    provider: &dyn Provider,
    model: &str,
    max_history: usize,
    max_context_tokens: usize,
) -> Result<bool> {
    let has_system = history.first().map_or(false, |m| m.role == "system");
    let non_system_count = if has_system {
        history.len().saturating_sub(1)
    } else {
        history.len()
    };

    let estimated_tokens = estimate_history_tokens(history);

    // Trigger compaction when either token budget OR message count is exceeded.
    if estimated_tokens <= max_context_tokens && non_system_count <= max_history {
        return Ok(false);
    }

    let start = if has_system { 1 } else { 0 };
    let keep_recent = COMPACTION_KEEP_RECENT_MESSAGES.min(non_system_count);
    let compact_count = non_system_count.saturating_sub(keep_recent);
    if compact_count == 0 {
        return Ok(false);
    }

    let mut compact_end = start + compact_count;

    // Snap compact_end to a user-turn boundary so we don't split mid-conversation.
    while compact_end > start && history.get(compact_end).map_or(false, |m| m.role != "user") {
        compact_end -= 1;
    }
    if compact_end <= start {
        return Ok(false);
    }

    let to_compact: Vec<ChatMessage> = history[start..compact_end].to_vec();
    let transcript = build_compaction_transcript(&to_compact);

    let summarizer_system = "You are a conversation compaction engine. Summarize older chat history into concise context for future turns. Preserve: user preferences, commitments, decisions, unresolved tasks, key facts. Omit: filler, repeated chit-chat, verbose tool logs. Output plain text bullet points only.";

    let summary_raw = provider
        .chat_with_system(Some(summarizer_system), &transcript, model, 0.2)
        .await
        .unwrap_or_else(|_| {
            // Fallback to deterministic local truncation when summarization fails.
            truncate_with_ellipsis(&transcript, COMPACTION_MAX_SUMMARY_CHARS)
        });

    let summary = truncate_with_ellipsis(&summary_raw, COMPACTION_MAX_SUMMARY_CHARS);
    apply_compaction_summary(history, start, compact_end, &summary);

    Ok(true)
}
```

```rust
// From: src/agent/loop_.rs:L305-L323
/// Trim conversation history to prevent unbounded growth.
/// Preserves the system prompt (first message if role=system) and the most recent messages.
fn trim_history(history: &mut Vec<ChatMessage>, max_history: usize) {
    // Nothing to trim if within limit
    let has_system = history.first().map_or(false, |m| m.role == "system");
    let non_system_count = if has_system {
        history.len() - 1
    } else {
        history.len()
    };

    if non_system_count <= max_history {
        return;
    }

    let start = if has_system { 1 } else { 0 };
    let to_remove = non_system_count - max_history;
    history.drain(start..start + to_remove);
}
```

### Key Characteristics / Design Choices

1. **Dual Trigger**: Compaction is triggered when **either** token budget OR message count threshold is exceeded

2. **User-turn Alignment**: Compaction always snaps to a user-turn boundary to avoid splitting conversations

3. **Incremental Compaction**: Only the oldest messages (before the most recent 20) are compacted, keeping the recent conversation intact

4. **Hard Character Caps**:
   - 12,000 chars max for source transcript to avoid overwhelming the summarizer
   - 2,000 chars max for the resulting summary to keep the compacted context bounded

5. **Graceful Fallback: If LLM summarization fails, falls back to deterministic truncation instead of failing

6. **4 chars/token Heuristic**: Simple but effective token estimation with small overhead per message for role/framing

7. **System Prompt Preservation**: The system prompt is always preserved during trimming, never removed

8. **Two-Stage Process**: Auto-compaction runs first to preserve context via summarization, then hard trimming to guarantee fit if still over budget

---

## 4. Context Isolation Mechanism

### Architecture / Implementation

ZeroClaw provides **multi-layered context and file-system isolation** at multiple levels:
1. **Workspace-level isolation** for multi-tenant deployments
2. **Per-session memory isolation**
3. **OS-level sandboxing** for tool execution
4. **Docker-level network isolation** optional

**Source Location:**
- Workspace config: `src/config/workspace.rs`, `src/config/schema.rs:L332-L416
- Security boundary: `src/security/workspace_boundary.rs`
- Sandbox trait: `src/security/traits.rs`
- Implementations: `src/security/docker.rs`, `src/security/bubblewrap.rs`, `src/security/firejail.rs`

### Key Code Snippet

```rust
// From: src/config/schema.rs:L378-L396
/// Multi-client workspace isolation configuration.
/// When enabled, each client engagement gets an isolated workspace with
/// isolated memory, audit, and secrets.
pub struct WorkspaceConfig {
    /// Enable workspace isolation. Default: false.
    #[serde(default)]
    pub enabled: bool,
    /// Enable memory namespace prefix for isolation.
    pub name: String,
    /// Memory isolation: prefixes all memory keys with the workspace namespace,
    /// so cross-workspace memory recall is not possible unless explicitly enabled.
    pub isolate_memory: bool,
    /// Isolate secrets: secrets from this workspace can't be accessed by other workspaces.
    pub isolate_secrets: bool,
    /// Audit logs isolated to this workspace.
    pub isolate_audit: bool,
```

### Key Characteristics / Design Choices

1. **Configurable Isolation Levels**: Each workspace can independently isolate:
   - Memory (namespaced so cross-workspace recall is disabled by default
   - Secrets (API keys are not shared between workspaces
   - Audit logs (separate logging per workspace)

2. **Filesystem Boundary Enforcement**: All file tool operations are checked against the workspace boundary to prevent path traversal attacks

3. **Multiple Sandbox Backends for Tool Execution:
   - **Bubblewrap** (Linux/macOS): User-namespace isolation via unshare
   - **Firejail** (Linux): Additional DAC and seccomp-bpf security
   - **Docker**: Full container isolation with optional network isolation
   - **None**: No additional isolation for trusted environments

4. **Per-thread Isolation in Channels**: In channels like Discord/Slack, each thread gets its own isolated session context

5. **Session Isolation in Memory Backends**: SQLite backend enforces session boundaries so memories from different sessions can't leak

6. **Landlock LSM Support** on Linux: Kernel-level filesystem sandboxing for additional security

---

## 5. Memory Mechanism Design

### Architecture / Implementation

ZeroClaw uses a **pluggable trait-based memory system** with multiple backend implementations. Memory is categorized into core (long-term facts, daily session notes, conversation context, and custom categories. All backends support optional session scoping for isolation.

**Source Location:**
- Trait definition: `src/memory/traits.rs`
- SQLite backend: `src/memory/sqlite.rs`
- Multiple backends: markdown, sqlite, postgres, qdrant, mem0, lucid

### Key Code Snippet

```rust
// From: src/memory/traits.rs:L85-L136
pub trait Memory: Send + Sync {
    /// Backend name
    fn name(&self) -> &str;

    /// Store a memory entry, optionally scoped to a session
    async fn store(
        &self,
        key: &str,
        content: &str,
        category: MemoryCategory,
        session_id: Option<&str>,
    ) -> anyhow::Result<()>;

    /// Recall memories matching a query (keyword search), optionally scoped to a session
    async fn recall(
        &self,
        query: &str,
        limit: usize,
        session_id: Option<&str>,
    ) -> anyhow::Result<Vec<MemoryEntry>>;

    /// Get a specific memory by key
    async fn get(&self, key: &str) -> anyhow::Result<Option<MemoryEntry>>;

    /// List all memory keys, optionally filtered by category and/or session
    async fn list(
        &self,
        category: Option<&MemoryCategory>,
        session_id: Option<&str>,
    ) -> anyhow::Result<Vec<MemoryEntry>>;

    /// Remove a memory by key
    async fn forget(&self, key: &str) -> anyhow::Result<bool>;

    /// Count total memories
    async fn count(&self) -> anyhow::Result<usize>;

    /// Health check
    async fn health_check(&self) -> bool;

    /// Store a conversation trace as procedural memory.
    ///
    /// Backends that support procedural storage (e.g. mem0) override this
    /// to extract "how to" patterns from tool-calling turns.  The default
    /// implementation is a no-op.
    async fn store_procedural(
        &self,
        _messages: &[ProceduralMessage],
        _session_id: Option<&str>,
    ) -> anyhow::Result<()> {
        Ok(())
    }
}
```

```rust
// From: src/memory/traits.rs:L16-L26
/// A single memory entry
#[derive(Clone, Serialize, Deserialize)]
pub struct MemoryEntry {
    pub id: String,
    pub key: String,
    pub content: String,
    pub category: MemoryCategory,
    pub timestamp: String,
    pub session_id: Option<String>,
    pub score: Option<f64>,
}
```

### Key Characteristics / Design Choices

1. **Trait-based Pluggable Architecture**: Any backend can be swapped without changing core agent code

2. **Memory Categorization System**:
   - **Core**: Long-term facts, preferences, decisions (permanent storage
   - **Daily**: Daily session logs and temporary notes
   - **Conversation**: Conversation history context
   - **Custom**: User-defined categories with string names

3. **Optional Session Scoping**: Every memory operations can be scoped to a session_id, providing isolation between concurrent conversations

4. **Multiple Backend Options:
   - **SQLite**: Default embedded database with optional vector search support
   - **markdown**: Flat-file markdown-based memory for simple deployments
   - **PostgreSQL**: Client-server PostgreSQL with vector extensions
   - **Qdrant**: Dedicated vector database for semantic search
   - **mem0**: Procedural memory for learning from conversation patterns
   - **Lucid**: Hybrid ranking combining vector + BM25

5. **Procedural Memory Support**: Special support for storing conversation traces to learn "how-to" patterns from past tool use, supported by mem0 backend

6. **Hybrid Search**: Vector + keyword search supported by many backends for better recall

7. **Workspace Namespacing**: When workspace isolation is enabled, all memory keys are prefixed with the workspace namespace to prevent leakage

---

## Architecture Summary

| Feature | Implementation | Source Location | Advantages |
|---------|-----------------|-----------------|------------|
| Gateway Mechanism | Axum-based HTTP with security hardening | `src/gateway/ | Slow-loris protection, 64KB max body, configurable timeouts |
| Sub-agent/Identity | Declarative config with delegate tool | `src/tools/delegate.rs`, `src/config/schema.rs` | Multi-agent specialization, depth tracking, configurable personas |
| Context Trimming | Hybrid auto-compaction + hard trimming | `src/agent/loop_.rs | Preserves context via LLM summarization, guarantees fit |
| Context Isolation | Multi-layer: workspace + session + OS sandbox | `src/config/workspace.rs`, `src/security/` | Defense in depth, configurable, prevents cross-talk |
| Memory Mechanism | Pluggable trait with multiple backends | `src/memory/traits.rs`, `src/memory/*.rs` | Flexible deployment options, session isolation, supports semantic search |

## Summary

ZeroClaw is a security-first Rust-based autonomous agent framework that:

1. Takes an **Axum-based hardened HTTP gateway** with proper security boundaries against common attacks like slow-loris and memory exhaustion.

2. Implements **declarative sub-agent delegation** where any agent can invoke pre-configured specialized sub-agents with different model settings, with depth tracking to prevent infinite recursion.

3. Uses a **hybrid context compaction strategy** combining LLM-based summarization of older messages with deterministic hard trimming as a fallback, always preserving the system prompt and most recent conversation.

4. Provides **defense-in-depth context isolation** with workspace-level memory/secrets/audit isolation, per-session scoping, and multiple OS-level sandbox backends (Bubblewrap, Firejail, Docker).

5. Features a **pluggable memory architecture** with trait abstraction enabling multiple storage backends from simple markdown to PostgreSQL+Qdrant for semantic search, with categorization and optional session/workspace isolation.

The project demonstrates a strong focus on security and performance with a modular, extensible architecture suitable for production multi-tenant deployments.

## References

[^1]: GitHub Repository - https://github.com/zeroclaw-labs/zeroclaw
