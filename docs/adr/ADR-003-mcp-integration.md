# ADR-003: MCP vs Native Tools

## Status
**Accepted** - 2025-12-31

## Context

The agent needs capabilities beyond memory (web search, code execution, file processing, image generation). Two integration patterns:

1. **Native Tools**: Implement directly in agent code
2. **MCP (Model Context Protocol)**: Delegate to external servers

### Requirements

- **Isolation**: Code execution must be sandboxed
- **Reusability**: Tools should work across different agents
- **Maintenance**: Minimize agent code complexity
- **Flexibility**: Easy to add/remove capabilities

## Decision

Use **hybrid approach**:

| Capability | Pattern | Rationale |
|------------|---------|-----------|
| **Memory Tools** | Native | Requires agent-specific caching, bucket access |
| **Python Execution** | MCP Server | Needs isolation, stateful kernel |
| **Web Search** | MCP Server | Reusable, no custom logic needed |
| **File Extraction** | Native | Uses DIAL bucket API directly |
| **Image Generation** | Native | Simple DIAL Core API call |
| **RAG Search** | Native | Requires document cache, embedding |

### MCP Servers Used

1. **Python Code Interpreter** (port 8050)
   - Stateful Jupyter kernel
   - Sandboxed execution
   - Timeout protection

2. **DuckDuckGo Search** (port 8051)
   - Web search + content fetching
   - Rate limiting built-in
   - No API key required

## Rationale

### Why MCP for Code Execution

✅ **Security**: Isolated Docker container prevents malicious code from affecting agent
✅ **Statefulness**: Jupyter kernel maintains variables across calls (required for multi-step coding)
✅ **Resource Limits**: Container can enforce CPU/memory limits
✅ **Language Agnostic**: Could add Node.js, Java interpreters without agent changes

### Why MCP for Web Search

✅ **Simplicity**: No need to implement HTTP client, parsing, rate limiting
✅ **Reusability**: Same server used by other DIAL agents
✅ **Maintenance**: Search provider changes don't require agent updates

### Why Native for Memory Tools

✅ **Cache Consistency**: All tools share single `LongTermMemoryStore` instance
✅ **Bucket Access**: Direct DIAL API usage (no HTTP overhead)
✅ **User Isolation**: API keys flow naturally through agent
✅ **Debugging**: Easier to trace memory operations

### Why Native for File Extraction

✅ **DIAL Integration**: Files already in bucket, no need to send via HTTP
✅ **Performance**: Direct bucket access faster than MCP round-trip
✅ **Custom Logic**: Pagination specific to agent needs

## Consequences

### Positive

- ✅ Best tool for the job (native vs. external based on requirements)
- ✅ Security through isolation (code execution)
- ✅ Reusability of MCP servers across projects
- ✅ Flexible: easy to convert native → MCP or vice versa

### Negative

- ❌ Mixed patterns increase conceptual complexity
- ❌ MCP servers add deployment dependencies
- ❌ Network latency for MCP calls (~50-100ms overhead)

### Neutral

- Agent code: ~500 lines native tools, ~100 lines MCP integration
- Startup time: +2s for MCP client connection verification
- Failure modes: MCP server down = capability unavailable (graceful degradation)

## MCP Integration Pattern

```python
# Discovery and wrapping
mcp_client = await MCPClient.create("http://localhost:8050/mcp")
mcp_tools = await mcp_client.get_tools()

for mcp_tool_model in mcp_tools:
    tools.append(
        MCPTool(
            client=mcp_client,
            mcp_tool_model=mcp_tool_model
        )
    )
```

**Advantages**:
- Automatic schema conversion (MCP → OpenAI function calling)
- Single `MCPTool` adapter for all MCP servers
- Lazy loading: tools discovered at runtime

## Alternative Considered: All-Native

**Rejected because**:
- ❌ Code execution requires complex sandboxing (Docker, VMs)
- ❌ Web scraping logic duplicated across agents
- ❌ Security risk (code execution in agent process)
- ❌ Higher maintenance burden

## Alternative Considered: All-MCP

**Rejected because**:
- ❌ Memory tools need shared cache (impossible via HTTP)
- ❌ Every DIAL bucket access becomes HTTP round-trip
- ❌ Increased latency for simple operations
- ❌ Overengineering for training project

## Future Extensions

### Potential MCP Additions

1. **Database Query Server**: SQL execution with safe query parsing
2. **Chart Generation Server**: Data visualization (matplotlib, plotly)
3. **Email/Calendar Server**: Integration with productivity tools

### Converting Native → MCP

If file extraction becomes complex:

```python
# MCP Server: file-processor
# Tools: extract_pdf, extract_csv, extract_docx

mcp_client = await MCPClient.create("http://localhost:8052/mcp")
```

**Trigger**: If file extraction logic exceeds ~200 lines

## Related

- [Architecture - MCP Integration](../architecture.md#mcp-integration)
- [API Reference - MCP Tools](../api.md#mcp-tools)
- [Setup Guide - MCP Configuration](../setup.md#docker-compose-configuration)
