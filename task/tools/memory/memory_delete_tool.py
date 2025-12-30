"""
Tool for deleting all stored long-term memories.

Execution flow:
1. LLM calls this tool when user explicitly requests memory deletion
2. Delegates to LongTermMemoryStore.delete_all_memories()
3. Memory file is removed from DIAL bucket, cache is cleared
4. Reports success to conversation stage

Side effects: Permanently removes user's memory file from DIAL bucket
Warning: This action cannot be undone
"""

from typing import Any

from task.tools.base import BaseTool
from task.tools.memory.memory_store import LongTermMemoryStore
from task.tools.models import ToolCallParams


class DeleteMemoryTool(BaseTool):
    """
    Tool for deleting all long-term memories about the user.

    This permanently removes all stored memories from the system.
    Use with caution - this action cannot be undone.
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
        return "delete_all_memories"

    @property
    def description(self) -> str:
        """
        Description guiding LLM on when/how to use this tool.
        
        Note: Emphasizes this is destructive and requires explicit user request.
        """
        return (
            "PERMANENTLY delete ALL stored memories about the user. "
            "This action CANNOT be undone. Only use when the user EXPLICITLY asks to: "
            "'delete my memories', 'forget everything about me', 'clear my data', etc. "
            "ALWAYS confirm with the user before calling this tool."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        """
        JSON Schema for tool arguments.
        
        No parameters required - deletes all memories unconditionally.
        """
        return {
            "type": "object",
            "properties": {}
        }

    async def _execute(self, tool_call_params: ToolCallParams) -> str:
        """
        Delete all memories and report result.
        
        Args:
            tool_call_params: Contains api_key for DIAL auth, stage for UI feedback
        
        Returns:
            Confirmation message
        """
        # Delegate to memory store backend - removes file and clears cache
        result = await self.memory_store.delete_all_memories(
            api_key=tool_call_params.api_key
        )
        
        # Update UI stage with deletion confirmation
        tool_call_params.stage.append_content(result)
        
        return result