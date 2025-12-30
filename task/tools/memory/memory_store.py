"""
Long-term memory storage backend for the General Purpose Agent.

Execution flow:
1. Memories are stored as JSON in a user-specific DIAL bucket file
2. Each memory has content, metadata, and a vector embedding for semantic search
3. On search, embeddings are compared using FAISS for fast nearest-neighbor lookup
4. Deduplication runs periodically (>24h) to merge similar memories (>75% similarity)
5. In-memory cache reduces DIAL API calls within the same session
6. All operations use the user's API key for authentication/authorization

External I/O: DIAL file storage API (upload/download/delete)
Side effects: Modifies user's memory file in DIAL bucket, updates in-memory cache
"""

import os
os.environ['OMP_NUM_THREADS'] = '1'  # Prevent FAISS threading issues in debug mode

import json
from datetime import datetime, UTC, timedelta
import numpy as np
import faiss
from aidial_client import AsyncDial
from sentence_transformers import SentenceTransformer

from task.tools.memory._models import Memory, MemoryData, MemoryCollection


class LongTermMemoryStore:
    """
    Manages long-term memory storage for users.

    Storage format: Single JSON file per user in DIAL bucket
    - File: {user_bucket}/__long-memories/data.json
    - Caching: In-memory dict keyed by file path (unique per user)
    - Deduplication: O(n log n) using FAISS batch cosine similarity search
    """

    # Minimum hours between deduplication runs to avoid frequent reprocessing
    DEDUP_INTERVAL_HOURS = 24
    # Cosine similarity threshold: memories above this are considered duplicates
    SIMILARITY_THRESHOLD = 0.75
    # Minimum collection size before deduplication is triggered
    MIN_MEMORIES_FOR_DEDUP = 10

    def __init__(self, endpoint: str):
        """
        Initialize the memory store with DIAL endpoint and embedding model.
        
        Args:
            endpoint: DIAL API base URL for file storage operations
        """
        self.endpoint = endpoint
        # all-MiniLM-L6-v2: lightweight model (80MB), 384-dim embeddings, good for semantic similarity
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        # Cache: file_path -> MemoryCollection (avoids repeated DIAL API calls)
        self._cache: dict[str, MemoryCollection] = {}
        # Single-threaded FAISS to prevent deadlocks in debug mode
        faiss.omp_set_num_threads(1)

    async def _get_memory_file_path(self, dial_client: AsyncDial) -> str:
        """
        Construct the DIAL bucket path for the user's memory file.
        
        The path uses the app's home bucket which is user-specific, ensuring
        memories are isolated per user and persist across conversations.
        
        Returns:
            Path in format: files/{bucket}/__long-memories/data.json
        """
        # DIAL provides a user-specific bucket via the app home path
        bucket = await dial_client.get_app_home_path()
        return f"files/{bucket}/__long-memories/data.json"

    async def _load_memories(self, api_key: str) -> MemoryCollection:
        """
        Load memories from DIAL bucket, using cache if available.
        
        Cache strategy: file path as key ensures user isolation and
        allows cross-conversation memory access within the same session.
        
        Args:
            api_key: User's DIAL API key for authentication
            
        Returns:
            MemoryCollection with existing memories or empty collection if none exist
        """
        # Create client with preview API version for latest features
        dial_client = AsyncDial(base_url=self.endpoint, api_key=api_key, api_version="2025-01-01-preview")
        file_path = await self._get_memory_file_path(dial_client)
        
        # Return cached collection if available (avoids redundant API calls)
        if file_path in self._cache:
            return self._cache[file_path]
        
        # Attempt to download existing memories from DIAL bucket
        try:
            response = await dial_client.files.download(file_path)
            content = response.content.decode('utf-8')
            data = json.loads(content)
            collection = MemoryCollection.model_validate(data)
        except Exception:
            # File doesn't exist or is corrupted - start with empty collection
            # This is expected for new users
            collection = MemoryCollection(memories=[], updated_at=datetime.now(UTC))
        
        # Populate cache for subsequent calls
        self._cache[file_path] = collection
        return collection

    async def _save_memories(self, api_key: str, memories: MemoryCollection):
        """
        Persist memories to DIAL bucket and update cache.
        
        Note: Uses compact JSON (no indentation) to minimize storage size.
        Each memory with embedding is ~6-8KB, so 1000 memories ≈ 6-8MB.
        
        Args:
            api_key: User's DIAL API key
            memories: Collection to save (will update its timestamp)
        """
        dial_client = AsyncDial(base_url=self.endpoint, api_key=api_key, api_version="2025-01-01-preview")
        file_path = await self._get_memory_file_path(dial_client)
        
        # Update timestamp to track last modification
        memories.updated_at = datetime.now(UTC)
        
        # Compact JSON to reduce file size (no indent, no extra whitespace)
        content = memories.model_dump_json()
        
        # Upload to DIAL bucket (PUT operation - creates or overwrites)
        await dial_client.files.upload(file_path, content.encode('utf-8'))
        
        # Update cache to reflect saved state
        self._cache[file_path] = memories

    async def add_memory(self, api_key: str, content: str, importance: float, category: str, topics: list[str]) -> str:
        """
        Add a new memory with computed embedding.
        
        Args:
            api_key: User's DIAL API key
            content: The memory text to store
            importance: Priority score 0-1 (higher = more likely to survive deduplication)
            category: Classification (e.g., 'preferences', 'personal_info')
            topics: Tags for additional context
            
        Returns:
            Confirmation message
        """
        collection = await self._load_memories(api_key)
        
        # Generate embedding vector for semantic search
        # encode() returns ndarray; convert to list for JSON serialization
        embedding = self.model.encode([content])[0].tolist()
        
        # Use UTC timestamp as unique ID (collision unlikely for human-paced input)
        memory_id = int(datetime.now(UTC).timestamp())
        
        memory = Memory(
            data=MemoryData(
                id=memory_id,
                content=content,
                importance=importance,
                category=category,
                topics=topics
            ),
            embedding=embedding
        )
        
        collection.memories.append(memory)
        await self._save_memories(api_key, collection)
        
        return f"Memory stored successfully: '{content}'"

    async def search_memories(self, api_key: str, query: str, top_k: int = 5) -> list[MemoryData]:
        """
        Search memories using semantic similarity via FAISS.
        
        Triggers deduplication if >24h since last run and >10 memories exist.
        
        Args:
            api_key: User's DIAL API key
            query: Natural language search query
            top_k: Maximum number of results to return
            
        Returns:
            List of MemoryData (content + metadata, no embeddings) sorted by relevance
        """
        collection = await self._load_memories(api_key)
        
        # Early return for empty collection
        if not collection.memories:
            return []
        
        # Run deduplication if needed (background maintenance)
        if self._needs_deduplication(collection):
            collection = await self._deduplicate_and_save(api_key, collection)
        
        # Build FAISS index for fast nearest-neighbor search
        embeddings = np.array([m.embedding for m in collection.memories], dtype=np.float32)
        
        # Normalize for cosine similarity (FAISS IndexFlatIP computes dot product)
        faiss.normalize_L2(embeddings)
        
        # IndexFlatIP: inner product (dot product) on normalized vectors = cosine similarity
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
        
        # Encode query and normalize for cosine similarity
        query_embedding = self.model.encode([query])[0].astype(np.float32)
        faiss.normalize_L2(query_embedding.reshape(1, -1))
        
        # Search for top_k nearest neighbors (limit to available memories)
        k = min(top_k, len(collection.memories))
        distances, indices = index.search(query_embedding.reshape(1, -1), k)
        
        # Return MemoryData (without embeddings) for matched memories
        return [collection.memories[i].data for i in indices[0]]

    def _needs_deduplication(self, collection: MemoryCollection) -> bool:
        """
        Check if deduplication should run based on collection size and time elapsed.
        
        Criteria: >10 memories AND (never deduplicated OR >24h since last dedup)
        """
        if len(collection.memories) <= self.MIN_MEMORIES_FOR_DEDUP:
            return False
        
        # Never deduplicated before
        if collection.last_deduplicated_at is None:
            return True
        
        # Check if enough time has passed since last deduplication
        time_since_dedup = datetime.now(UTC) - collection.last_deduplicated_at
        return time_since_dedup > timedelta(hours=self.DEDUP_INTERVAL_HOURS)

    async def _deduplicate_and_save(self, api_key: str, collection: MemoryCollection) -> MemoryCollection:
        """
        Run deduplication and persist the cleaned collection.
        
        Returns:
            Updated collection with duplicates removed
        """
        collection.memories = self._deduplicate_fast(collection.memories)
        collection.last_deduplicated_at = datetime.now(UTC)
        await self._save_memories(api_key, collection)
        return collection

    def _deduplicate_fast(self, memories: list[Memory]) -> list[Memory]:
        """
        Remove duplicate memories using FAISS batch cosine similarity search.
        
        Algorithm (O(n log n)):
        1. Build FAISS index from all memory embeddings
        2. Batch search to find k nearest neighbors for each memory
        3. For each pair with similarity > 0.75, mark lower-importance one as duplicate
        4. Return memories not marked as duplicates
        
        Strategy for choosing survivor:
        - Higher importance wins
        - On tie, earlier memory (lower index) wins
        """
        if len(memories) <= 1:
            return memories
        
        # Prepare embeddings matrix for FAISS
        embeddings = np.array([m.embedding for m in memories], dtype=np.float32)
        faiss.normalize_L2(embeddings)  # Normalize for cosine similarity
        
        # Build index using inner product (= cosine sim on normalized vectors)
        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings)
        
        # Search for k nearest neighbors (including self)
        # k=min(10, n) balances thoroughness vs performance
        k = min(10, len(memories))
        distances, indices = index.search(embeddings, k)
        
        # Track which memories to remove (by index)
        to_remove: set[int] = set()
        
        # Process each memory's neighbors to find duplicates
        for i in range(len(memories)):
            if i in to_remove:
                continue  # Already marked for removal
            
            # Check neighbors (skip self at index 0)
            for j_pos in range(1, k):
                j = indices[i][j_pos]
                similarity = distances[i][j_pos]
                
                # Skip if below threshold or already removed
                if similarity < self.SIMILARITY_THRESHOLD or j in to_remove:
                    continue
                
                # Decide which memory to keep based on importance
                importance_i = memories[i].data.importance
                importance_j = memories[j].data.importance
                
                # Keep the more important one; on tie, keep earlier (lower index)
                if importance_i >= importance_j:
                    to_remove.add(j)
                else:
                    to_remove.add(i)
                    break  # i is removed, stop checking its neighbors
        
        # Return memories not marked for removal
        return [m for idx, m in enumerate(memories) if idx not in to_remove]

    async def delete_all_memories(self, api_key: str) -> str:
        """
        Permanently delete all memories for the user.
        
        Warning: This operation cannot be undone. Removes the memory file
        from DIAL bucket and clears the local cache.
        
        Returns:
            Confirmation message
        """
        dial_client = AsyncDial(base_url=self.endpoint, api_key=api_key, api_version="2025-01-01-preview")
        file_path = await self._get_memory_file_path(dial_client)
        
        # Attempt to delete from DIAL bucket (may fail if file doesn't exist)
        try:
            await dial_client.files.delete(file_path)
        except Exception:
            pass  # File may not exist - that's fine
        
        # Clear cache entry
        if file_path in self._cache:
            del self._cache[file_path]
        
        return "All memories have been deleted successfully."
