# ADR-002: Embedding Model Selection

## Status
**Accepted** - 2025-12-31

## Context

Semantic memory search requires converting text to vector embeddings. The model must:
- Generate high-quality embeddings for short facts (10-100 words)
- Run efficiently on CPU (no GPU dependency)
- Have small download size for fast startup
- Support batch encoding for deduplication

### Options Considered

| Model | Dimensions | Size | Performance | Accuracy |
|-------|------------|------|-------------|----------|
| all-MiniLM-L6-v2 | 384 | 80MB | ⭐⭐⭐ Fast | ⭐⭐⭐ Good |
| all-mpnet-base-v2 | 768 | 420MB | ⭐⭐ Medium | ⭐⭐⭐⭐ Best |
| paraphrase-MiniLM-L3-v2 | 384 | 60MB | ⭐⭐⭐⭐ Fastest | ⭐⭐ Moderate |
| text-embedding-ada-002 (OpenAI) | 1536 | API | ⭐ Slow (network) | ⭐⭐⭐⭐ Excellent |

## Decision

Use **all-MiniLM-L6-v2** from Sentence Transformers.

### Model Specifications
- **Dimensions**: 384
- **Download Size**: ~80MB
- **Inference Time**: ~50ms per encoding on CPU
- **Training Data**: 1B+ sentence pairs
- **Score on STS Benchmark**: 0.84 (Spearman correlation)

### Rationale

1. **Size/Performance Balance**: 80MB model downloads in ~10s on typical connection
2. **CPU Efficiency**: Optimized for CPU inference, no GPU required
3. **Quality**: Sufficient accuracy for short-text similarity (user facts)
4. **Ecosystem**: Part of `sentence-transformers`, well-maintained
5. **Cost**: Free, no API calls required

### Benchmark Comparison

```python
# Memory search quality test (10 stored memories)
Query: "where does user live"
Ground truth: "User lives in Paris, France"

all-MiniLM-L6-v2:  Score: 0.87 (Rank: 1) ✅
paraphrase-MiniLM: Score: 0.81 (Rank: 1) ✅
all-mpnet-base:    Score: 0.91 (Rank: 1) ✅ (slower)
```

All models retrieve correct memory, but all-MiniLM-L6-v2 offers best speed/accuracy trade-off.

## Consequences

### Positive
- ✅ Fast startup (<10s model download on first run)
- ✅ Low memory footprint (~200MB with model loaded)
- ✅ No external API dependency (offline capable)
- ✅ Batch encoding supports efficient deduplication
- ✅ Deterministic results (same input → same embedding)

### Negative
- ❌ Lower accuracy than larger models (acceptable for training)
- ❌ 384 dimensions less expressive than 768 (still sufficient)
- ❌ Not fine-tuned for very short text (<5 words)

### Neutral
- Embedding generation: ~50-100ms per memory (acceptable)
- FAISS index build: O(n log n) for 384-dim vectors
- Storage overhead: ~1.5KB per embedding (384 floats × 4 bytes)

## Implementation Notes

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

# Generate embedding
embedding = model.encode("User lives in Paris", convert_to_numpy=True)
assert embedding.shape == (384,)

# Batch encoding (for deduplication)
embeddings = model.encode(["fact 1", "fact 2"], batch_size=32)
```

### Model Caching

Model downloads to `~/.cache/torch/sentence_transformers/` on first run. Subsequent runs use cached version.

## Alternatives for Production

If accuracy becomes critical:

1. **all-mpnet-base-v2**: Higher accuracy (768 dims), slower but still CPU-friendly
2. **OpenAI text-embedding-ada-002**: Best quality, requires API calls ($0.0001/1K tokens)
3. **Custom Fine-tuning**: Train on domain-specific memory examples
4. **Multilingual Models**: If supporting non-English users (e.g., paraphrase-multilingual-MiniLM)

## Upgrade Path

Embeddings are versioned implicitly via model. To upgrade:

1. Store model name in `MemoryCollection`: `"embedding_model": "all-MiniLM-L6-v2"`
2. On load, check model version
3. If mismatched, regenerate all embeddings (one-time migration)
4. Update `embedding_model` field

## Related

- [Architecture - Memory System](../architecture.md#long-term-memory-system)
- [API Reference - Memory Tools](../api.md#memory-tools)
- ADR-001: Memory Storage Format
- ADR-004: Deduplication Strategy
