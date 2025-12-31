---
title: API Reference - AI DIAL General Purpose Agent
description: Detailed tool schemas, agent interfaces, and integration patterns
version: 1.0.0
last_updated: 2025-12-31
related: [architecture.md, setup.md]
tags: [api, tools, schemas, integration]
---

# API Reference

## Table of Contents
- [Agent Interface](#agent-interface)
- [Memory Tools](#memory-tools)
- [MCP Tools](#mcp-tools)
- [File Tools](#file-tools)
- [RAG Tool](#rag-tool)
- [Image Generation Tool](#image-generation-tool)
- [Tool Base Classes](#tool-base-classes)
- [Data Models](#data-models)

## Agent Interface

### GeneralPurposeAgent

**Module**: `task.agent`

Main orchestration class that handles chat completions with tool calling.

#### Constructor

```python
GeneralPurposeAgent(
    endpoint: str,
    system_prompt: str,
    tools: list[BaseTool]
)
```

**Parameters:**
- `endpoint` (str): DIAL Core URL (e.g., `http://localhost:8080`)
- `system_prompt` (str): Instructions for LLM behavior
- `tools` (list[BaseTool]): List of available tools

#### Methods

##### `handle_request`

```python
async def handle_request(
    deployment_name: str,
    choice: Choice,
    request: Request,
    response: Response
) -> Message
```

Processes a chat completion request with tool calling.

**Parameters:**
- `deployment_name` (str): LLM deployment (e.g., `gpt-4o`, `claude-sonnet-3-7`)
- `choice` (Choice): DIAL SDK choice object for streaming
- `request` (Request): Incoming chat completion request
- `response` (Response): DIAL SDK response object

**Returns:** Final assistant message

**Flow:**
1. Unpacks message history + system prompt
2. Streams from DIAL Core with tool schemas
3. If tool calls: executes tools → appends results → recurses
4. If no tool calls: streams content to user

**Example:**
```python
agent = GeneralPurposeAgent(
    endpoint="http://localhost:8080",
    system_prompt=SYSTEM_PROMPT,
    tools=[store_tool, search_tool]
)

await agent.handle_request(
    deployment_name="gpt-4o",
    choice=choice,
    request=request,
    response=response
)
```

---

## Memory Tools

### StoreMemoryTool

**Module**: `task.tools.memory.memory_store_tool`

Stores new long-term memories about the user.

#### Schema

```json
{
  "name": "store_memory",
  "description": "Store important information about the user in long-term memory...",
  "parameters": {
    "type": "object",
    "properties": {
      "content": {
        "type": "string",
        "description": "The memory content to store. Should be a clear, concise fact."
      },
      "category": {
        "type": "string",
        "description": "Category: 'preferences', 'personal_info', 'goals', 'plans', 'context'",
        "default": "general"
      },
      "importance": {
        "type": "number",
        "description": "Priority 0-1. Higher = more likely to survive deduplication.",
        "minimum": 0,
        "maximum": 1,
        "default": 0.5
      },
      "topics": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Tags for classification (e.g., ['programming', 'languages'])",
        "default": []
      }
    },
    "required": ["content"]
  }
}
```

#### Usage Examples

**Store user's name:**
```json
{
  "content": "User's name is Alice",
  "category": "personal_info",
  "importance": 0.9,
  "topics": ["identity"]
}
```

**Store preference:**
```json
{
  "content": "Prefers Python over JavaScript",
  "category": "preferences",
  "importance": 0.7,
  "topics": ["programming", "languages"]
}
```

**Store location:**
```json
{
  "content": "Lives in Paris, France",
  "category": "personal_info",
  "importance": 0.9,
  "topics": ["location", "geography"]
}
```

#### Constructor

```python
StoreMemoryTool(memory_store: LongTermMemoryStore)
```

**Parameters:**
- `memory_store`: Shared backend instance for consistent caching

#### Implementation Notes

- Generates 384-dim embedding using `all-MiniLM-L6-v2`
- Triggers deduplication if >10 memories and >24h since last run
- Saves to `{user_bucket}/__long-memories/data.json`
- Updates in-memory cache for fast subsequent access

---

### SearchMemoryTool

**Module**: `task.tools.memory.memory_search_tool`

Searches stored memories using semantic similarity.

#### Schema

```json
{
  "name": "search_memory",
  "description": "Search long-term memory for information about the user...",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query. Use natural language (e.g., 'where does user live?')"
      },
      "top_k": {
        "type": "integer",
        "description": "Number of results to return",
        "minimum": 1,
        "maximum": 20,
        "default": 5
      }
    },
    "required": ["query"]
  }
}
```

#### Usage Examples

**Find user's location:**
```json
{
  "query": "where does the user live",
  "top_k": 3
}
```

**Response:**
```markdown
Found 3 memories:

1. **Category:** personal_info | **Importance:** 0.9 | **Similarity:** 0.92
   Content: Lives in Paris, France
   Topics: location, geography

2. **Category:** context | **Importance:** 0.6 | **Similarity:** 0.78
   Content: Enjoys visiting local cafes in Le Marais district
   Topics: lifestyle, preferences
```

**Find programming preferences:**
```json
{
  "query": "programming languages user likes"
}
```

#### Constructor

```python
SearchMemoryTool(memory_store: LongTermMemoryStore)
```

#### Implementation Notes

- Uses FAISS cosine similarity search
- Returns memories sorted by similarity score (descending)
- Empty result if no memories stored
- Query embedding generated with same model as storage

---

### DeleteMemoryTool

**Module**: `task.tools.memory.memory_delete_tool`

Deletes all stored memories for the user.

#### Schema

```json
{
  "name": "delete_all_memories",
  "description": "Delete ALL stored memories. Use only when user explicitly requests.",
  "parameters": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
```

#### Usage Example

**User says:** "Forget everything about me" or "Delete my data"

**Tool call:**
```json
{}
```

**Response:**
```
Successfully deleted all memories. The memory file has been removed.
```

#### Constructor

```python
DeleteMemoryTool(memory_store: LongTermMemoryStore)
```

#### Implementation Notes

- Deletes `{user_bucket}/__long-memories/data.json`
- Clears in-memory cache
- **Irreversible** - no backup created
- Returns error if no memories exist

---

## MCP Tools

MCP (Model Context Protocol) tools are dynamically discovered from external servers.

### MCPTool Adapter

**Module**: `task.tools.mcp.mcp_tool`

Wraps MCP server tools to match `BaseTool` interface.

#### Constructor

```python
MCPTool(
    client: MCPClient,
    mcp_tool_model: MCPToolModel
)
```

**Parameters:**
- `client`: MCP client connected to server
- `mcp_tool_model`: Tool schema from server's `tools/list` response

### Python Code Interpreter

**MCP Server**: `python-interpreter` at `localhost:8050`

#### Schema

```json
{
  "name": "execute_code",
  "description": "Execute Python code in a stateful Jupyter kernel",
  "parameters": {
    "type": "object",
    "properties": {
      "code": {
        "type": "string",
        "description": "Python code to execute"
      }
    },
    "required": ["code"]
  }
}
```

#### Usage Examples

**Calculate factorial:**
```json
{
  "code": "import math\nresult = math.factorial(10)\nprint(result)"
}
```

**Response:**
```
3628800
```

**Data analysis:**
```json
{
  "code": "import pandas as pd\ndf = pd.DataFrame({'x': [1,2,3], 'y': [4,5,6]})\nprint(df.describe())"
}
```

**Stateful execution:**
```python
# First call
{"code": "x = 42"}

# Second call (x persists)
{"code": "print(x * 2)"}  # Output: 84
```

#### Implementation Notes

- Runs in isolated Docker container
- Jupyter kernel state persists across calls within conversation
- Output includes stdout, stderr, and display data (images, plots)
- Timeout: 30 seconds per execution

---

### DuckDuckGo Search

**MCP Server**: `ddg-search` at `localhost:8051`

#### Schema

```json
{
  "name": "ddg_search",
  "description": "Search the web using DuckDuckGo",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query"
      },
      "max_results": {
        "type": "integer",
        "description": "Maximum number of results",
        "default": 5
      }
    },
    "required": ["query"]
  }
}
```

#### Usage Example

**Search for weather:**
```json
{
  "query": "weather Paris France today",
  "max_results": 3
}
```

**Response:**
```markdown
1. **Weather in Paris** - https://weather.com/paris
   Current temperature: 15°C, partly cloudy...

2. **Paris Weather Forecast** - https://forecast.com
   Today's conditions: Mild with chance of rain...
```

---

## File Tools

### FileContentExtractionTool

**Module**: `task.tools.files.file_content_extraction_tool`

Extracts text content from uploaded files.

#### Schema

```json
{
  "name": "extract_file_content",
  "description": "Extract text content from uploaded file (PDF, TXT, CSV, DOCX)",
  "parameters": {
    "type": "object",
    "properties": {
      "file_url": {
        "type": "string",
        "description": "DIAL file URL (files/{bucket}/{path})"
      },
      "page_number": {
        "type": "integer",
        "description": "Page number for PDFs (1-indexed)",
        "default": 1
      }
    },
    "required": ["file_url"]
  }
}
```

#### Usage Example

**Extract PDF page:**
```json
{
  "file_url": "files/user123/documents/report.pdf",
  "page_number": 3
}
```

**Response:**
```
=== Page 3 ===

Quarterly Results Summary
...
```

#### Supported Formats

- **PDF**: `pdfplumber` for text + table extraction
- **TXT**: Direct text read
- **CSV**: Pandas DataFrame formatted as table
- **DOCX**: TODO (not implemented)

---

## RAG Tool

### RagTool

**Module**: `task.tools.rag.rag_tool`

Semantic search over uploaded documents using embeddings + LLM retrieval.

#### Schema

```json
{
  "name": "rag_search",
  "description": "Search through uploaded documents semantically",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query or question about documents"
      },
      "file_urls": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Optional: specific files to search (default: all uploaded)"
      }
    },
    "required": ["query"]
  }
}
```

#### Usage Example

**Search across all documents:**
```json
{
  "query": "What are the key findings about climate change?"
}
```

**Response:**
```markdown
Found 3 relevant passages:

**From: research_paper.pdf (Page 2)**
> Global temperatures have risen 1.5°C since pre-industrial times...

**From: summary.txt**
> Key finding: Arctic ice melting accelerating...
```

#### Implementation Notes

- Uses `langchain` for document chunking (500 tokens, 50 overlap)
- Generates embeddings for chunks on first query
- Caches processed documents in `DocumentCache`
- Sends top-k chunks to LLM for synthesis
- Cache cleared when conversation ends

---

## Image Generation Tool

### ImageGenerationTool

**Module**: `task.tools.deployment.image_generation_tool`

Generates images using DALL-E via DIAL Core.

#### Schema

```json
{
  "name": "generate_image",
  "description": "Generate an image from a text prompt using DALL-E",
  "parameters": {
    "type": "object",
    "properties": {
      "prompt": {
        "type": "string",
        "description": "Detailed description of the image to generate"
      },
      "size": {
        "type": "string",
        "enum": ["256x256", "512x512", "1024x1024"],
        "default": "1024x1024"
      }
    },
    "required": ["prompt"]
  }
}
```

#### Usage Example

**Generate image:**
```json
{
  "prompt": "A serene mountain landscape at sunset with a lake in the foreground",
  "size": "1024x1024"
}
```

**Response:**
Returns DIAL attachment with image URL.

---

## Tool Base Classes

### BaseTool

**Module**: `task.tools.base`

Abstract base class for all tools.

#### Interface

```python
class BaseTool(ABC):
    @abstractmethod
    async def _execute(self, params: ToolCallParams) -> str | Message:
        """Implement tool logic. Return string or Message object."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier used by LLM."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Description for LLM (max 1024 chars)."""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """JSON Schema for tool arguments."""
        pass
    
    @property
    def schema(self) -> dict[str, Any]:
        """OpenAI-compatible function schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
    
    @property
    def create_tool_stage(self) -> bool:
        """Whether to create UI stage for this tool."""
        return True
    
    @property
    def show_in_stage(self) -> bool:
        """Whether to show arguments/response in stage."""
        return True
```

#### Creating Custom Tools

```python
from task.tools.base import BaseTool
from task.tools.models import ToolCallParams
import json

class MyCustomTool(BaseTool):
    @property
    def name(self) -> str:
        return "my_tool"
    
    @property
    def description(self) -> str:
        return "Does something useful"
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "input": {"type": "string"}
            },
            "required": ["input"]
        }
    
    async def _execute(self, params: ToolCallParams) -> str:
        args = json.loads(params.tool_call.function.arguments)
        input_text = args["input"]
        
        # Update stage with progress
        params.stage.append_content(f"Processing: {input_text}\n")
        
        # Perform logic
        result = self._do_work(input_text)
        
        return f"Result: {result}"
```

---

## Data Models

### Memory Models

**Module**: `task.tools.memory._models`

#### MemoryData

```python
class MemoryData(BaseModel):
    id: int              # Unix timestamp
    content: str         # Memory text
    importance: float    # 0-1 priority score
    category: str        # Classification
    topics: list[str]    # Tags
```

#### Memory

```python
class Memory(BaseModel):
    data: MemoryData         # Metadata
    embedding: list[float]   # 384-dim vector
```

#### MemoryCollection

```python
class MemoryCollection(BaseModel):
    memories: list[Memory]
    updated_at: datetime
    last_deduplicated_at: datetime | None
```

### Tool Parameters

**Module**: `task.tools.models`

#### ToolCallParams

```python
class ToolCallParams(BaseModel):
    tool_call: ToolCall          # OpenAI function call
    stage: StageProcessor        # UI feedback
    choice: Choice               # DIAL SDK choice
    api_key: str                 # User's API key
    conversation_id: str         # Conversation ID
```

### MCP Models

**Module**: `task.tools.mcp.mcp_tool_model`

#### MCPToolModel

```python
class MCPToolModel(BaseModel):
    name: str                    # Tool identifier
    description: str             # Usage guide
    inputSchema: dict[str, Any]  # JSON Schema
```

---

## Integration Examples

### Adding Memory Tools to Agent

```python
from task.tools.memory.memory_store import LongTermMemoryStore
from task.tools.memory.memory_store_tool import StoreMemoryTool
from task.tools.memory.memory_search_tool import SearchMemoryTool
from task.tools.memory.memory_delete_tool import DeleteMemoryTool

# Create shared backend (CRITICAL: single instance for all tools)
memory_store = LongTermMemoryStore(endpoint="http://localhost:8080")

# Create tools
tools = [
    StoreMemoryTool(memory_store=memory_store),
    SearchMemoryTool(memory_store=memory_store),
    DeleteMemoryTool(memory_store=memory_store),
]

# Initialize agent
agent = GeneralPurposeAgent(
    endpoint="http://localhost:8080",
    system_prompt=SYSTEM_PROMPT,
    tools=tools
)
```

### Loading MCP Tools

```python
from task.tools.mcp.mcp_client import MCPClient
from task.tools.mcp.mcp_tool import MCPTool

async def load_mcp_tools(url: str) -> list[BaseTool]:
    tools = []
    client = await MCPClient.create(url)
    
    for mcp_tool_model in await client.get_tools():
        tools.append(
            MCPTool(
                client=client,
                mcp_tool_model=mcp_tool_model
            )
        )
    
    return tools

# Usage
python_tools = await load_mcp_tools("http://localhost:8050/mcp")
search_tools = await load_mcp_tools("http://localhost:8051/mcp")
```

### Testing Tools Directly

```python
from task.tools.memory.memory_store_tool import StoreMemoryTool
from task.tools.models import ToolCallParams
from aidial_client.types.chat.legacy.chat_completion import ToolCall, FunctionCall

# Mock tool call
tool_call = ToolCall(
    id="call_123",
    type="function",
    function=FunctionCall(
        name="store_memory",
        arguments='{"content": "Test memory", "category": "test"}'
    )
)

# Mock parameters
params = ToolCallParams(
    tool_call=tool_call,
    stage=mock_stage,
    choice=mock_choice,
    api_key="test_key",
    conversation_id="test_conv"
)

# Execute tool
tool = StoreMemoryTool(memory_store)
result = await tool.execute(params)
print(result.content)
```

---

**Related Documents:**
- [Architecture](./architecture.md) - System design and data flows
- [Setup Guide](./setup.md) - Environment configuration
- [Testing Guide](./testing.md) - Tool validation strategies
