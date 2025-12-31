# ADR-004: Deduplication Strategy

## Status
**Accepted** - 2025-12-31

## Context

Users may share similar information multiple times:
- "I live in Paris" vs. "My home is in Paris, France"
- "I prefer Python" vs. "Python is my favorite language"
- "I work at Google" vs. "I'm a software engineer at Google"

Without deduplication:
- ❌ Storage bloat (10x growth over time)
- ❌ Redundant search results
- ❌ Slower FAISS search (linear in collection size)

### Requirements

- Merge semantically similar memories (not exact duplicates)
- Preserve higher-importance memories
- Run automatically without user intervention
- Avoid frequent reprocessing (expensive)

## Decision

Implement **periodic deduplication** with the following strategy:

### Trigger Conditions

Deduplication runs when **ALL** conditions met:
1. Memory count > 10 (avoid overhead for small collections)
2. Time since last dedup > 24 hours (avoid frequent runs)

### Similarity Threshold

**75% cosine similarity** marks memories as duplicates.

**Rationale:**
- 0.90+: Only exact paraphrases (too strict)
- 0.75-0.90: Semantically equivalent (sweet spot)
- 0.50-0.75: Related but distinct (too lenient)

### Merge Policy

For each duplicate pair:

1. **Keep higher importance**: If `importance_a > importance_b`, keep A
2. **Merge content**: If importance equal, concatenate: `"A. B"`
3. **Combine topics**: Union of both topic lists
4. **Update timestamp**: Use most recent `id`

### Algorithm

```
1. Build FAISS index from all embeddings
2. For each memory, find top-5 similar (excluding self)
3. Filter pairs where similarity > 0.75
4. Sort pairs by average importance (descending)
5. Mark lower-importance memories for deletion
6. Merge content from marked memories
7. Remove marked memories from collection
8. Update last_deduplicated_at timestamp
```

**Complexity:** O(n log n) due to FAISS batch search

## Rationale

### Why 75% Threshold

Empirical testing with sample memories:

| Memory A | Memory B | Similarity | Duplicate? |
|----------|----------|------------|------------|
| "Lives in Paris" | "Home in Paris, France" | 0.87 | ✅ Yes |
| "Prefers Python" | "Python is favorite" | 0.81 | ✅ Yes |
| "Works at Google" | "Software engineer at Google" | 0.72 | ❌ No (different aspects) |
| "Likes coffee" | "Enjoys croissants" | 0.68 | ❌ No (different topics) |

**Conclusion:** 0.75 captures paraphrases without merging distinct facts.

### Why 24-Hour Delay

- User might add related memories intentionally (e.g., updating location)
- Immediate dedup could delete new memory before user sees it stored
- 24h ensures user has seen both memories in search results
- Reduces computation frequency (dedup is O(n²) similarity checks)

### Why Importance-Based

- Core identity facts (name, location) should survive merges
- Low-importance context can be aggregated
- User implicitly signals value via importance parameter

## Consequences

### Positive

- ✅ Storage grows linearly, not exponentially
- ✅ Search results less redundant
- ✅ FAISS performance maintained (fewer vectors)
- ✅ Automatic - no user intervention needed

### Negative

- ❌ Deduplication takes ~5-30s for 100-1000 memories
- ❌ Could merge distinct facts if embeddings too similar
- ❌ No way to "unmerge" - operation irreversible

### Neutral

- Frequency: ~1 dedup per day per active user
- Overhead: Acceptable for <10k memories

## Implementation Details

```python
async def _deduplicate_memories(self, api_key: str, collection: MemoryCollection):
    # Check conditions
    if len(collection.memories) <= self.MIN_MEMORIES_FOR_DEDUP:
        return
    
    if collection.last_deduplicated_at:
        hours_since = (datetime.now(UTC) - collection.last_deduplicated_at).total_seconds() / 3600
        if hours_since < self.DEDUP_INTERVAL_HOURS:
            return
    
    # Build FAISS index
    embeddings = np.array([m.embedding for m in collection.memories])
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    
    # Find similar pairs
    similarities, indices = index.search(embeddings, k=5)
    
    # Merge logic
    to_remove = set()
    for i, (sims, idxs) in enumerate(zip(similarities, indices)):
        for j, (sim, idx) in enumerate(zip(sims, idxs)):
            if idx == i:
                continue
            if sim > self.SIMILARITY_THRESHOLD:
                # Keep higher importance
                if collection.memories[i].data.importance > collection.memories[idx].data.importance:
                    to_remove.add(idx)
                else:
                    to_remove.add(i)
    
    # Remove duplicates
    collection.memories = [m for i, m in enumerate(collection.memories) if i not in to_remove]
    collection.last_deduplicated_at = datetime.now(UTC)
```

## Monitoring

Track deduplication effectiveness:

```python
metrics = {
    "memories_before": len_before,
    "memories_after": len_after,
    "removed_count": len_before - len_after,
    "removal_rate": (len_before - len_after) / len_before,
    "duration_ms": duration
}
```

**Healthy Range:**
- Removal rate: 5-20% (indicates effective dedup)
- Duration: <30s for 1000 memories

**Alert If:**
- Removal rate > 50% (threshold too aggressive)
- Duration > 60s (consider batching or indexing)

## Alternatives Considered

### 1. No Deduplication

**Rejected:** Storage grows unbounded, search quality degrades

### 2. Exact Match Only

**Rejected:** Misses paraphrases, doesn't solve storage issue

### 3. Cluster-Based Merging

**Idea:** Group similar memories into clusters, keep centroid

**Rejected:** Loses specific details, overly aggressive merging

### 4. User Confirmation

**Idea:** Show duplicate pairs, ask user to merge

**Rejected:** Adds friction, doesn't scale (100+ memories)

## Future Enhancements

### Smart Merging

Instead of concatenation, use LLM to synthesize:

```
Memory A: "Lives in Paris"
Memory B: "Home in Paris, France"

LLM Merge: "Lives in Paris, France"
```

**Trade-off:** Adds LLM cost and latency

### Importance Decay

Automatically reduce importance of old memories:

```python
age_days = (now - memory.created_at).days
importance *= 0.95 ** (age_days / 30)  # 5% decay per month
```

**Use Case:** Old preferences become less relevant

## Related

- [Architecture - Deduplication](../architecture.md#deduplication-algorithm)
- [API Reference - Memory Store](../api.md#memory-tools)
- ADR-001: Memory Storage Format
- ADR-002: Embedding Model Selection
