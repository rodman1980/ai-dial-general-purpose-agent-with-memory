"""
Tool for semantic search over stored long-term memories.

Execution flow:
1. LLM calls this tool to recall relevant user information before answering
2. Tool parses query and top_k from JSON arguments
3. Delegates to LongTermMemoryStore.search_memories() for FAISS vector search
4. Formats results as markdown and reports to conversation stage

External I/O: Reads from user's DIAL bucket via memory store
"""

import json
from typing import Any

from task.tools.base import BaseTool
from task.tools.memory._models import MemoryData
from task.tools.memory.memory_store import LongTermMemoryStore
from task.tools.models import ToolCallParams


class SearchMemoryTool(BaseTool):
    """
    Tool for searching long-term memories about the user.

    Performs semantic search over stored memories to find relevant information.
    Uses FAISS vector similarity on sentence embeddings.
    """

    def __init__(self, memory_store: LongTermMemoryStore):
        """
        Args:
            memory_store: Shared backend instance for memory operations
        """
        self.memory_store = memory_store

    @property
    def name(self) -> str:
        """Unique identifier used by LLM to invoke this tool."""
        return "search_memory"

    @property
    def description(self) -> str:
        """
        Description guiding LLM on when/how to use this tool.
        
        Note: Emphasizes searching BEFORE answering personal questions.
        """
        return (
            "Search long-term memory for information about the user. "
            "Use this tool BEFORE answering questions that might relate to stored user info: "
            "their name, location, job, preferences, goals, or any personal context. "
            "Also use when the user asks 'do you remember...', 'what do you know about me', etc. "
            "The search is semantic - use natural language queries."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        """
        JSON Schema for tool arguments.
        
        Required: query
        Optional: top_k (default 5, range 1-20)
        """
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query. Can be a question or keywords to find relevant memories."
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of most relevant memories to return.",
                    "minimum": 1,
                    "maximum": 20,
                    "default": 5
                }
            },
            "required": ["query"]
        }

    async def _execute(self, tool_call_params: ToolCallParams) -> str:
        """
        Execute semantic search and format results as markdown.
        
        Args:
            tool_call_params: Contains tool_call.function.arguments (JSON string),
                              stage for UI feedback, api_key for DIAL auth
        
        Returns:
            Markdown-formatted list of matching memories or "No memories found."
        """
        # Parse JSON arguments from LLM tool call
        args = json.loads(tool_call_params.tool_call.function.arguments)
        
        query = args["query"]
        top_k = args.get("top_k", 5)
        
        # Perform semantic search via FAISS vector similarity
        results: list[MemoryData] = await self.memory_store.search_memories(
            api_key=tool_call_params.api_key,
            query=query,
            top_k=top_k
        )
        
        # Format results for LLM consumption
        if not results:
            final_result = "No memories found."
        else:
            # Build markdown list with content, category, and topics
            lines = ["**Found memories:**\n"]
            for i, memory in enumerate(results, 1):
                lines.append(f"{i}. **{memory.content}**")
                lines.append(f"   - Category: {memory.category}")
                if memory.topics:
                    lines.append(f"   - Topics: {', '.join(memory.topics)}")
                lines.append("")  # Blank line between entries
            final_result = "\n".join(lines)
        
        # Update UI stage with search results
        tool_call_params.stage.append_content(final_result)
        
        return final_result
