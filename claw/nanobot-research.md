# Nanobot Technical Analysis: Gateway, Sub-agent, Context and Memory Mechanisms

## Project Overview

Nanobot is a standalone open-source MCP (Model Context Protocol) host that enables building agents with MCP and MCP-UI. Unlike built-in MCP hosts in applications like VSCode, Claude, or ChatGPT, Nanobot is designed to be an open-source, deployable solution that combines MCP servers with LLMs to create agent experiences through various interfaces (chat, voice, SMS, etc.).

**Official Resources:**
- GitHub Repository: [https://github.com/nanobot-ai/nanobot](https://github.com/nanobot-ai/nanobot)
- **Language:** Go (backend), Svelte 5 + TypeScript (frontend)

---

## 1. Gateway Mechanism

### Architecture / Implementation

Nanobot itself acts as an MCP gateway that exposes aggregated tools from multiple MCP servers through a single MCP endpoint. The HTTP gateway is implemented in the `pkg/server/server.go` which handles all MCP protocol requests.

**Source Location:** `pkg/server/server.go` [nanobot-ai/nanobot → pkg/server/server.go]

Key gateway responsibilities:
- Handles MCP protocol initialization and session management
- Aggregates tools from all configured MCP servers and agents
- Routes tool calls to the appropriate backend MCP server
- Provides a unified interface for clients to access all capabilities

### Key Code Snippet

```go
// OnMessage handles incoming MCP messages and routes them to the appropriate handler
func (s *Server) OnMessage(ctx context.Context, msg mcp.Message) {
	if msg.ID != nil {
		ctx = mcp.WithRequestID(ctx, msg.ID)
	}

	msg.Session.Run(ctx, msg, func(ctx context.Context, m mcp.Message) {
		s.onMessage(ctx, m)
	})
}

func (s *Server) onMessage(ctx context.Context, msg mcp.Message) {
	if err := s.data.Sync(ctx, s.config); err != nil {
		msg.SendError(ctx, err)
		return
	}

	mcp.SessionFromContext(ctx).Set(session.ManagerSessionKey, s.manager)

	for _, h := range s.handlers {
		ok, err := h(ctx, msg)
		if err != nil {
			if cancelErr, ok := errors.AsType[*mcp.RequestCancelledError](context.Cause(mcp.UserContext(ctx))); ok {
				msg.SendError(ctx, mcp.ErrRPCRequestCancelled.WithMessage("%s", cancelErr.Reason))
			} else {
				msg.SendError(ctx, err)
			}
			return
		} else if ok {
			return
		}
	}

	msg.SendError(ctx, mcp.ErrRPCMethodNotFound.WithMessage("%s", msg.Method))
}
```

**Tool Call Routing:**
```go
func (s *Server) handleCallTool(ctx context.Context, msg mcp.Message, payload mcp.CallToolRequest) error {
	// ...
	toolMapping, ok := toolMappings[payload.Name]
	if !ok {
		// ... error handling
	}

	result, err := s.runtime.Call(ctx, toolMapping.MCPServer, toolMapping.TargetName, payload.Arguments, tools.CallOptions{
		ProgressToken: msg.ProgressToken(),
		LogData: map[string]any{
			"mcpToolName": payload.Name,
		},
		Meta: msg.Meta(),
	})
	// ...
}
```

### Key Characteristics / Design Choices

- **Protocol-native:** Nanobot gateway natively implements the MCP protocol, so any MCP-compatible client can connect directly
- **Aggregation:** Combines multiple MCP servers and agents into a single exposed endpoint
- **Session-based:** Each connection gets its own isolated session with independent state
- **Hook system:** Supports request/response hooks that can modify messages before/after routing

**Reference Sources:**
- [Nanobot CLAUDE.md Documentation](https://github.com/nanobot-ai/nanobot/blob/main/CLAUDE.md) [^1]

---

## 2. Sub-agent Mechanism

### Architecture / Implementation

Nanobot implements sub-agents by treating agents as callable tools through the MCP protocol system. Any agent can be invoked as a tool by another agent, enabling hierarchical sub-agent composition.

**Source Location:**
- `pkg/agents/run.go` - Main agent execution loop
- `pkg/tools/service.go` - Tool and agent registry and mapping
- `pkg/servers/agent/server.go` - Agent MCP server exposition

### Key Code Snippet

**Agent Registration as Tool:**
```go
// In tools/service.go: When building tool mappings, agents are treated as tools
for _, agentName := range opt.Servers {
	agent, ok := config.Agents[agentName]
	if !ok {
		continue
	}

	tools := filterTools(&mcp.ListToolsResult{
		Tools: []mcp.Tool{
			{
				Name:        types.AgentTool + agentName,
				Description: agent.Description,
				InputSchema: types.ChatInputSchema,
			},
		},
	}, opt.Tools)
	// ... add to result
}
```

**Agent Execution Loop with Sub-agent Support:**
```go
// In pkg/agents/run.go: The main agent execution loop
func (a *Agents) Complete(ctx context.Context, req types.CompletionRequest, opts ...types.CompletionOptions) (_ *types.CompletionResponse, err error) {
	// ... session management
	for {
		config, err := a.configHook(ctx, baseConfig, currentRun.Request.GetAgent())
		if err != nil {
			return nil, err
		}

		ctx := types.WithConfig(ctx, config)

		if err := a.run(ctx, config, currentRun, previousRun, opts); err != nil {
			return nil, err
		}

		if currentRun.Done {
			// ... return final response
		}

		previousRun = currentRun
		currentRun = &types.Execution{
			Request: req.Reset(),
		}
	}
}
```

**Config Hook for Sub-agents:**
```go
// Sub-agents can have config hooks that modify their configuration before execution
func (a *Agents) configHook(ctx context.Context, baseConfig types.Config, agentName string) (types.Config, error) {
	session := mcp.SessionFromContext(ctx).Root()
	var sessionInit types.SessionInitHook
	session.Get(types.SessionInitSessionKey, &sessionInit)

	agent := baseConfig.Agents[agentName]
	if !slices.ContainsFunc(agent.Hooks, func(hook mcp.HookMapping) bool {
		return hook.Name == "config" && slices.Contains(hook.Targets, "nanobot.system/config")
	}) {
		agent.Hooks = append(agent.Hooks, mcp.HookMapping{Name: "config", Targets: []string{"nanobot.system/config"}})
	}
	hookResult, err := mcp.InvokeHooks(ctx, a.registry, agent.Hooks, &types.AgentConfigHook{
		Agent:     &agent.HookAgent,
		Meta:      sessionInit.Meta,
		SessionID: session.ID(),
	}, "config", nil)
	// ... apply modifications
	return baseConfig, nil
}
```

### Key Characteristics / Design Choices

- **MCP-based composition:** Sub-agents are just MCP servers that expose a chat capability
- **Configuration-driven:** Agents are defined in YAML configuration with their own model, tools, and instructions
- **Hierarchical:** Any agent can invoke any other agent as a sub-agent
- **No fixed "soul/identity" design:** Identity comes from the agent's instructions and configuration, no separate identity object model

---

## 3. Context Trimming Strategy

### Architecture / Implementation

Nanobot uses a two-level context management strategy: **incremental summarization compaction** for conversation history and **size-based truncation** for large tool outputs.

**Source Location:**
- `pkg/agents/compact.go` - Conversation compaction by summarization
- `pkg/agents/truncate.go` - Tool output truncation
- `pkg/agents/run.go:577-599` - Compaction triggering check

### Key Code Snippet

**Compaction Trigger:**
```go
const compactionThreshold = 0.835
const defaultContextWindow = 200_000

// shouldCompact returns true if estimated tokens > 83.5% of context window
func shouldCompact(req types.CompletionRequest, contextWindowSize int) bool {
	if contextWindowSize <= 0 {
		return false
	}

	estimated := estimateTokens(req.Input, req.SystemPrompt, req.Tools)
	threshold := int(float64(contextWindowSize) * compactionThreshold)
	return estimated > threshold
}
```

**Incremental Compaction Algorithm:**
```go
// compact performs conversation compaction by summarizing history messages
// into a condensed summary, allowing the conversation to continue within
// the context window limits.
//
// On re-compaction, only the messages since the previous summary are summarized
// (with the previous summary included as context). This keeps the summarization
// input bounded rather than growing with the full conversation.
func (a *Agents) compact(ctx context.Context, req types.CompletionRequest, currentRequestInput []types.Message, previousCompacted []types.Message) (*compactResult, error) {
	history, newInput := splitHistoryAndNewInput(req.Input, currentRequestInput)

	// Split history: find last compaction summary, only summarize what came after
	var previousSummaryText string
	var sinceLastSummary []types.Message
	lastSummaryIdx := -1
	for i, msg := range history {
		if IsCompactionSummary(msg) {
			lastSummaryIdx = i
			if len(msg.Items) > 0 && msg.Items[0].Content != nil {
				previousSummaryText = msg.Items[0].Content.Text
			}
		}
	}
	if lastSummaryIdx >= 0 {
		sinceLastSummary = history[lastSummaryIdx+1:]
	} else {
		sinceLastSummary = history
	}

	// Get summary from LLM using structured prompt
	summaryReq := types.CompletionRequest{
		Model: req.Model,
		Input: []types.Message{
			// prompt with transcript goes here
		},
	}

	resp, err := a.completer.Complete(ctx, summaryReq)
	// ... extract summary and create compacted input

	// Build the result: summary + new messages since compaction
	compactedInput := []types.Message{summaryMessage}
	compactedInput = append(compactedInput, newInput...)

	// Keep all archived messages for potential recovery
	archivedMessages := make([]types.Message, 0, len(previousCompacted)+len(history))
	archivedMessages = append(archivedMessages, previousCompacted...)
	archivedMessages = append(archivedMessages, history...)

	return &compactResult{
		compactedInput:   compactedInput,
		archivedMessages: archivedMessages,
	}, nil
}
```

**Tool Output Truncation:**
```go
const maxToolResultSize = 50 * 1025 // 50 KiB

// truncateToolResult truncates large tool outputs and stores the full content
// to a file on disk with a note in the context
func truncateToolResult(ctx context.Context, toolName, callID string, msg *types.Message) *types.Message {
	// ... check size
	if size <= maxToolResultSize {
		return msg
	}

	// Store full output to disk: sessions/<sessionID>/truncated-outputs/...
	filePath := filepath.Join(sessionsDir, sessionID, "truncated-outputs", fileName)
	writeFullResult(content, filePath)
	truncated := buildTruncatedContent(content, maxToolResultSize, filePath)

	// Return truncated message with reference to full file
	return &types.Message{
		ID:   msg.ID,
		Role: msg.Role,
		Items: []types.CompletionItem{
			{
				ID: msg.Items[0].ID,
				ToolCallResult: &types.ToolCallResult{
					CallID: result.CallID,
					Output: newOutput,
				},
			},
		},
	}
}
```

### Key Characteristics / Design Choices

- **Incremental summarization:** Only summarizes messages since last compaction, keeping the summarization prompt bounded
- **Structured summary template:** Uses fixed template with sections (Goal, What Happened, Current State, Next Steps, etc.) for consistent summaries
- **Archived messages preserved:** Original full messages are kept in memory for potential recovery
- **Offline truncation:** Large tool outputs are moved to disk instead of being discarded entirely
- **Token-based threshold:** Compaction triggers when estimated token count exceeds 83.5% of configured context window
- **Model-agnostic:** Uses the same LLM model configured for the agent to do the summarization

---

## 4. Context Isolation Mechanism

### Architecture / Implementation

Nanobot uses **session-based context isolation** where each MCP connection gets its own independent session with isolated state. Sessions form a tree with parent-child relationships for sub-agent invocations.

**Source Location:**
- `pkg/mcp/session.go` - Session implementation with attributes storage
- `pkg/session/` - Session manager

### Key Code Snippet

**Session Structure:**
```go
type Session struct {
	ctx               context.Context
	cancel            context.CancelCauseFunc
	wire              Wire
	handler           MessageHandler
	pendingRequest    PendingRequests
	InitializeResult  InitializeResult
	InitializeRequest InitializeRequest
	Parent            *Session  // Parent session for sub-agents
	HookRunner        HookRunner
	attributes        map[string]any  // Isolated attributes storage
	lock              sync.Mutex
	// ... other fields
}
```

**Attribute Isolation:**
```go
// Get retrieves a value from session attributes, falling back to parent session
func (s *Session) Get(key string, out any) (ret bool) {
	if s == nil {
		return false
	}
	defer func() {
		if !ret && s != nil && s.Parent != nil {
			ret = s.Parent.Get(key, out)
		}
	}()

	s.lock.Lock()
	defer s.lock.Unlock()
	v, ok := s.attributes[key]
	if !ok {
		return false
	}
	// ... copy into output
	return true
}

// Set stores a value in this session's attributes
func (s *Session) Set(key string, value any) {
	if s == nil {
		return
	}
	s.lock.Lock()
	defer s.lock.Unlock()
	if s.attributes == nil {
		s.attributes = make(map[string]any)
	}
	s.attributes[key] = value
}
```

**Root Session Access:**
```go
// Root returns the root session by following parent links
func (s *Session) Root() *Session {
	if s == nil {
		return nil
	}
	if s.Parent == nil {
		return s
	}
	return s.Parent.Root()
}
```

**Environment Inheritance:**
```go
func (s *Session) GetEnvMap() map[string]string {
	result := make(map[string]string)
	s.lock.Lock()
	env, _ := s.attributes[SessionEnvMapKey].(map[string]string)
	maps.Copy(result, env)
	s.lock.Unlock()

	if s.Parent != nil {
		parentEnv := s.Parent.GetEnvMap()
		for k, v := range parentEnv {
			if _, exists := env[k]; !exists {
				result[k] = v
			}
		}
	}

	return result
}
```

### Key Characteristics / Design Choices

- **Per-connection isolation:** Each client connection gets its own session with isolated state
- **Parent-child hierarchy:** Sub-agents inherit environment from parent but can override values
- **Thread-safe:** All session attribute access is protected by mutex for concurrent access
- **Cancellation propagation:** Context cancellation propagates through the session tree
- **MCP sandboxing:** MCP servers can be run in Docker containers for additional process-level isolation (in `pkg/mcp/sandbox/`)

---

## 5. Memory Mechanism

### Architecture / Implementation

Nanobot does not have a built-in long-term persistent memory system like vector storage. Memory is primarily:
1. **In-session memory:** Conversation history kept in the session object (with compaction)
2. **Archived compacted messages:** Original messages preserved after compaction in memory
3. **File-based overflow:** Truncated tool outputs stored on disk in session directory
4. **MCP resource system:** Custom resources can be stored via MCP resource API

**Source Location:**
- `pkg/resources/` - Built-in resource management
- `pkg/agents/compact.go` - Compaction with archival

### Key Characteristics

- **Transient in-memory:** Memory is tied to the session lifecycle, not persistent across restarts by default
- **Compaction instead of trimming:** Rather than dropping old messages, Nanobot summarizes them to preserve context
- **Extensible via MCP:** Long-term memory can be added via an external MCP server that provides memory capabilities
- **No built-in vector storage:** Relies on external tools for semantic memory/search

---

## Architecture Summary

| Feature | Implementation | Source Location | Advantages |
|---------|----------------|-----------------|------------|
| **Gateway** | MCP protocol aggregation HTTP server | `pkg/server/server.go` | Unified access to multiple MCP servers, standard protocol |
| **Sub-agent** | MCP-based tool composition, agents as callable tools | `pkg/tools/service.go`, `pkg/agents/run.go` | Flexible hierarchical composition, configuration-driven |
| **Context Trimming** | Incremental LLM summarization + disk overflow for tools | `pkg/agents/compact.go`, `pkg/agents/truncate.go` | Preserves context while staying within window, doesn't discard information entirely |
| **Context Isolation** | Session tree with attribute inheritance, mutex protection | `pkg/mcp/session.go` | Isolated per connection, sub-agent hierarchy supported, thread-safe |
| **Memory** | In-session with compaction, no built-in long-term | `pkg/agents/` | Simple, relies on LLM summarization, extensible via MCP |

## Summary

Nanobot is a clean, modular MCP host implementation that focuses on enabling composition of agents and tools through the standard MCP protocol. Key design insights:

1. **Protocol-first design:** Everything is MCP - agents are MCP servers, tools come from MCP servers, the gateway speaks MCP
2. **Incremental compaction is better than brute-force trimming:** By only summarizing new messages since last compaction, Nanobot keeps compaction costs bounded while preserving long-term context
3. **Session tree for isolation:** Sub-agents get their own session state but can inherit from parent, balancing isolation and information sharing
4. **Externalizes long-term memory:** Doesn't attempt to build its own vector DB - lets external MCP servers provide that capability

## References

[^1]: Nanobot CLAUDE.md - https://github.com/nanobot-ai/nanobot/blob/main/CLAUDE.md
