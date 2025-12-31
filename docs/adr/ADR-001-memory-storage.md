# ADR-001: Memory Storage Format

## Status
**Accepted** - 2025-12-31

## Context

The agent requires persistent storage of user-specific memories across conversations. Key requirements:
- Per-user isolation (multi-tenant)
- Fast read/write access
- Support for semantic search via embeddings
- Deduplication of similar memories
- Consistent view across multiple tools

### Options Considered

1. **SQL Database** (PostgreSQL with pgvector)
   - ✅ Structured queries, ACID guarantees
   - ❌ Requires external infrastructure
   - ❌ Overhead for small collections

2. **NoSQL Database** (MongoDB, DynamoDB)
   - ✅ Flexible schema, scalable
   - ❌ Additional service dependency
   - ❌ Complexity for training project

3. **Single JSON File per User**
   - ✅ Simple, no external dependencies
   - ✅ Uses existing DIAL bucket infrastructure
   - ✅ Easy to inspect and debug
   - ❌ Less efficient for very large collections

4. **Multiple Files (one per memory)**
   - ✅ Granular updates
   - ❌ Complex synchronization
   - ❌ Higher API call overhead

## Decision

Use **single JSON file per user** stored in DIAL bucket at `{user_bucket}/__long-memories/data.json`.

### File Structure
```json
{
  "memories": [
    {
      "data": {...},
      "embedding": [...]
    }
  ],
  "updated_at": "2025-12-31T12:00:00Z",
  "last_deduplicated_at": null
}
```

### Rationale

1. **Simplicity**: Leverages DIAL's existing bucket system, no additional infrastructure
2. **Atomic Updates**: Single file write ensures consistency
3. **User Isolation**: Bucket paths automatically scoped to users
4. **Debugging**: Easy to inspect with `dial_client.files.download()`
5. **Training Focus**: Appropriate complexity for demonstration project

### Implementation Details

- **Storage Location**: `files/{user_bucket}/__long-memories/data.json`
- **Locking**: None needed - DIAL handles concurrent writes
- **Caching**: In-memory cache keyed by file path
- **Format**: Compact JSON (no indentation to reduce size)

## Consequences

### Positive
- ✅ Zero infrastructure overhead beyond DIAL
- ✅ Automatic user isolation via bucket paths
- ✅ Simple backup/restore (copy file)
- ✅ Easy debugging and inspection

### Negative
- ❌ Full file rewrite on every update (acceptable for <1000 memories)
- ❌ No built-in concurrent write protection (mitigated by single-agent architecture)
- ❌ Limited to ~10k memories before performance degrades (acceptable for training)

### Neutral
- File size: ~6-8KB per memory → 6-8MB for 1000 memories (reasonable)
- Read latency: ~50-200ms from DIAL bucket (cached after first load)
- Write latency: ~100-300ms (acceptable for async storage)

## Alternatives for Production

If scaling beyond 1000 memories per user:

1. **Sharded JSON Files**: Split into multiple files (e.g., by date range)
2. **Vector Database**: Qdrant, Pinecone, or Weaviate for millions of memories
3. **SQL with pgvector**: Better query capabilities, ACID guarantees
4. **Hybrid**: Metadata in SQL, embeddings in vector DB

## Related

- [Architecture - Memory System](../architecture.md#long-term-memory-system)
- [API Reference - Memory Tools](../api.md#memory-tools)
- ADR-002: Embedding Model Selection
