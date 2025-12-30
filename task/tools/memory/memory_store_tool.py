"""
Tool for storing new long-term memories about the user.

Execution flow:
1. LLM calls this tool when it detects important user information worth remembering
2. Tool parses JSON arguments (content, category, importance, topics)
3. Delegates to LongTermMemoryStore.add_memory() for persistence
4. Reports success/failure to the conversation stage

Side effects: Creates/updates memory file in user's DIAL bucket
"""

import json
from typing import Any

from task.tools.base import BaseTool
from task.tools.memory.memory_store import LongTermMemoryStore
from task.tools.models import ToolCallParams


class StoreMemoryTool(BaseTool):
    """
    Tool for storing long-term memories about the user.

    The orchestration LLM should extract important, novel facts about the user
    and store them using this tool. Examples:
    - User preferences (likes Python, prefers morning meetings)
    - Personal information (lives in Paris, works at Google)
    - Goals and plans (learning Spanish, traveling to Japan)
    - Important context (has a cat named Mittens)
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
        return "store_memory"

    @property
    def description(self) -> str:
        """
        Description guiding LLM on when/how to use this tool.
        
        Note: Must be <1024 chars. Emphasizes proactive storage of novel facts.
        """
        return (
            "Store important information about the user in long-term memory. "
            "Use this tool PROACTIVELY when the user shares: personal details (name, location, job), "
            "preferences (favorite language, tools, food), goals, plans, or any fact worth remembering. "
            "Do NOT ask permission - store automatically when you detect novel, useful information. "
            "Store ONE fact per call. Be specific and concise in content."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        """
        JSON Schema for tool arguments.
        
        Required: content, category
        Optional: importance (default 0.5), topics (default [])
        """
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The memory content to store. Should be a clear, concise fact about the user."
                },
                "category": {
                    "type": "string",
                    "description": "Category of the info (e.g., 'preferences', 'personal_info', 'goals', 'plans', 'context')",
                    "default": "general"
                },
                "importance": {
                    "type": "number",
                    "description": "Importance score between 0 and 1. Higher means more important to remember.",
                    "minimum": 0,
                    "maximum": 1,
                    "default": 0.5
                },
                "topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Related topics or tags for the memory",
                    "default": []
                }
            },
            "required": ["content", "category"]
        }

    async def _execute(self, tool_call_params: ToolCallParams) -> str:
        """
        Parse arguments and delegate to memory store.
        
        Args:
            tool_call_params: Contains tool_call.function.arguments (JSON string),
                              stage for UI feedback, api_key for DIAL auth
        
        Returns:
            Success/failure message
        """
        # Parse JSON arguments from LLM tool call
        args = json.loads(tool_call_params.tool_call.function.arguments)
        
        # Extract required and optional parameters
        content = args["content"]
        category = args.get("category", "general")
        importance = args.get("importance", 0.5)
        topics = args.get("topics", [])
        
        # Delegate to memory store backend
        result = await self.memory_store.add_memory(
            api_key=tool_call_params.api_key,
            content=content,
            importance=importance,
            category=category,
            topics=topics
        )
        
        # Update UI stage with result
        tool_call_params.stage.append_content(result)
        
        return result
