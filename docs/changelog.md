---
title: Changelog - AI DIAL General Purpose Agent
description: Notable changes, releases, and version history
version: 1.0.0
last_updated: 2025-12-31
related: [README.md, roadmap.md]
tags: [changelog, releases, history]
---

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Unit test coverage for memory store and tools
- System prompt optimization for consistent behavior
- Memory TTL (time-to-live) for automatic expiry
- Redis cache for cross-session memory sharing
- Performance benchmarks and optimization

See [Roadmap](./roadmap.md) for detailed future plans.

---

## [1.0.0] - 2025-12-31

Initial release as training/demonstration project.

### Added

#### Core Features
- **Long-Term Memory System**
  - Semantic storage with FAISS vector search
  - 384-dimensional embeddings (all-MiniLM-L6-v2)
  - User-specific bucket isolation
  - In-memory caching for performance
  
- **Memory Tools**
  - `store_memory`: Store user facts with importance and categories
  - `search_memory`: Semantic search with top-k results
  - `delete_all_memories`: Complete memory deletion

- **Deduplication**
  - Automatic merging of similar memories (>75% cosine similarity)
  - Runs when >10 memories and >24h since last run
  - Importance-based merge policy

#### Integration Tools

- **MCP Servers**
  - Python code interpreter with stateful Jupyter kernel (port 8050)
  - DuckDuckGo web search (port 8051)
  - Automatic tool discovery and schema conversion

- **File Processing**
  - PDF text extraction (pdfplumber)
  - CSV parsing and formatting
  - TXT file reading

- **RAG Search**
  - Document chunking (langchain)
  - Semantic search over uploaded files
  - LLM-powered synthesis

- **Image Generation**
  - DALL-E integration via DIAL Core
  - Size selection (256x256, 512x512, 1024x1024)

#### Infrastructure

- **DIAL Platform Integration**
  - Chat completion endpoint with streaming
  - User bucket isolation via API keys
  - Stage-based UI feedback
  - Message history management

- **Docker Compose Setup**
  - DIAL Core (Java backend)
  - Redis cache
  - Chat UI (Next.js)
  - Python interpreter MCP server
  - DuckDuckGo search MCP server

#### Documentation

- Comprehensive architecture documentation with Mermaid diagrams
- Setup guide with troubleshooting
- API reference for all tools
- Testing guide with manual workflows
- Glossary of terms and concepts
- Architecture Decision Records (ADRs):
  - ADR-001: Memory Storage Format
  - ADR-002: Embedding Model Selection
  - ADR-003: MCP vs Native Tools
  - ADR-004: Deduplication Strategy
- Roadmap with future enhancements

### Technical Details

- **Dependencies**
  - Python 3.12+
  - aidial-sdk 0.27.0
  - aidial-client 0.3.0
  - faiss-cpu 1.12.0
  - sentence-transformers 5.1.2
  - langchain 1.0.3

- **Memory Storage**
  - Single JSON file per user: `{bucket}/__long-memories/data.json`
  - Average size: ~6-8KB per memory
  - Scalable to ~10k memories per user

- **Performance**
  - Memory storage: ~100-200ms
  - Semantic search: ~50-100ms (1000 memories)
  - Deduplication: ~10-30s (1000 memories)
  - Embedding generation: ~50ms per text

### Known Issues

- System prompt inconsistency: LLM doesn't always store memories proactively (model-dependent)
- No unit tests: Relies on manual testing
- FAISS threading warnings in debug mode (mitigated with `OMP_NUM_THREADS=1`)
- Memory file not cached across agent restarts (by design)

### Security Notes

- ⚠️ **CRITICAL**: Remove API keys from `core/config.json` before committing
- User data isolated via DIAL buckets (API key-based)
- MCP servers run in isolated Docker containers
- No telemetry or external data sharing (except LLM API calls)

---

## Version History

### v1.0.0 (2025-12-31) - Initial Release
Training/demonstration project with core memory capabilities.

**Highlights:**
- Long-term memory with FAISS
- MCP integration (Python, search)
- File processing and RAG
- Comprehensive documentation

**Target Users:** Developers learning AI agent development, DIAL platform exploration

---

## Upgrade Guide

### From Pre-release to 1.0.0

**New Installation:**
Follow [Setup Guide](./setup.md) for fresh install.

**If migrating from development branch:**

1. **Backup memories:**
   ```bash
   # Download existing memories (if any)
   curl -H "Api-Key: dial_api_key" \
     http://localhost:8080/v1/files/user-bucket/__long-memories/data.json \
     > backup.json
   ```

2. **Update dependencies:**
   ```bash
   pip install -r requirements.txt --upgrade
   ```

3. **Restart services:**
   ```bash
   docker-compose down
   docker-compose pull
   docker-compose up -d
   ```

4. **Verify memory format:**
   Memories should have structure:
   ```json
   {
     "memories": [...],
     "updated_at": "...",
     "last_deduplicated_at": null
   }
   ```

---

## Breaking Changes

### None (Initial Release)

Future versions will document breaking changes here.

**Compatibility Promise:**
- Memory file format stability (v1.x series)
- Tool schema backward compatibility
- DIAL SDK API surface

**What May Change:**
- System prompt (for improved behavior)
- Deduplication algorithm parameters
- Caching strategy
- Internal tool implementations

---

## Contributors

This project is a training demonstration. See individual commits for detailed contributions.

**Maintainer:** TODO: Add maintainer info

**Contributors:**
- TODO: Add contributor list

---

## Related Resources

- **Project Repository:** TODO: Add GitHub URL
- **DIAL Platform:** [https://epam-rail.com/](https://epam-rail.com/)
- **Issue Tracker:** TODO: Add issues URL
- **Discussions:** TODO: Add discussions URL

---

## Acknowledgments

Built with:
- [AI DIAL SDK](https://github.com/epam/ai-dial-sdk) - Platform integration
- [FAISS](https://github.com/facebookresearch/faiss) - Vector similarity search
- [Sentence Transformers](https://www.sbert.net/) - Embedding generation
- [MCP](https://modelcontextprotocol.io/) - Tool integration protocol

---

**Next Release:** See [Roadmap](./roadmap.md) for planned features.
