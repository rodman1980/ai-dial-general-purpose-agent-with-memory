---
title: Setup Guide - AI DIAL General Purpose Agent
description: Complete environment setup, installation, configuration, and deployment instructions
version: 1.0.0
last_updated: 2025-12-31
related: [README.md, architecture.md]
tags: [setup, installation, configuration, docker]
---

# Setup Guide

## Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Installation](#detailed-installation)
- [Configuration](#configuration)
- [Running the Agent](#running-the-agent)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Development Setup](#development-setup)

## Prerequisites

### System Requirements

- **OS**: macOS, Linux, or Windows with WSL2
- **Python**: 3.12 or higher
- **Docker**: 20.10+ with Docker Compose V2
- **Memory**: 4GB minimum, 8GB recommended
- **Disk**: 5GB free space for Docker images

### Software Dependencies

```bash
# Verify installations
python3 --version  # Should be 3.12+
docker --version   # Should be 20.10+
docker compose version  # Should be v2.0+
```

### API Keys (Required)

You'll need API keys for:
- **OpenAI** (GPT-4o): [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- **Anthropic** (Claude, optional): [https://console.anthropic.com/](https://console.anthropic.com/)

## Quick Start

For impatient developers:

```bash
# 1. Clone and navigate
cd ai-dial-general-purpose-agent-with-memory

# 2. Activate virtual environment
source dial_agent_with_memory/bin/activate

# 3. Start DIAL infrastructure
docker-compose up -d

# 4. Configure API keys (see Configuration section)
# Edit core/config.json with your keys

# 5. Run agent
python -m task.app

# 6. Open Chat UI
open http://localhost:3000
```

**⚠️ Security Reminder**: Remove API keys from `core/config.json` before committing.

## Detailed Installation

### Step 1: Clone Repository

```bash
git clone <repository-url> ai-dial-general-purpose-agent-with-memory
cd ai-dial-general-purpose-agent-with-memory
```

### Step 2: Virtual Environment

The repository includes a pre-configured virtual environment:

```bash
# Activate existing environment
source dial_agent_with_memory/bin/activate

# Verify Python version
python --version  # Should show Python 3.12.x

# Verify dependencies installed
pip list | grep -E "aidial|faiss|sentence-transformers"
```

**Expected output:**
```
aidial-client         0.3.0
aidial-sdk            0.27.0
faiss-cpu             1.12.0
sentence-transformers 5.1.2
```

### Step 3: Install Dependencies (if not pre-installed)

If you need to recreate the environment:

```bash
# Create new virtual environment
python3.12 -m venv dial_agent_with_memory

# Activate
source dial_agent_with_memory/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Dependencies breakdown:**
```
aidial-sdk==0.27.0              # DIAL platform SDK
aidial-client==0.3.0            # DIAL API client
mcp==1.20.0                     # Model Context Protocol
faiss-cpu==1.12.0               # Vector similarity search
sentence-transformers==5.1.2    # Embedding generation
beautifulsoup4==4.14.2          # HTML parsing
pdfplumber==0.11.7              # PDF extraction
numpy==2.3.4                    # Numerical computing
pandas==2.3.3                   # Data manipulation
langchain==1.0.3                # Document chunking
```

### Step 4: Start DIAL Infrastructure

```bash
docker-compose up -d
```

This starts 7 services:

| Service | Port | Description |
|---------|------|-------------|
| `chat` | 3000 | DIAL Chat UI (Next.js frontend) |
| `core` | 8080 | DIAL Core (Java backend) |
| `redis` | 6379 | Redis cache for DIAL Core |
| `themes` | 3001 | Theme server for Chat UI |
| `adapter-dial` | - | DIAL protocol adapter |
| `python-interpreter` | 8050 | Python code execution MCP server |
| `ddg-search` | 8051 | DuckDuckGo search MCP server |

**Verify services:**
```bash
docker-compose ps
```

**Expected output:**
```
NAME                 STATUS    PORTS
chat                 running   0.0.0.0:3000->3000/tcp
core                 running   0.0.0.0:8080->8080/tcp
redis                running   0.0.0.0:6379->6379/tcp
python-interpreter   running   0.0.0.0:8050->8000/tcp
ddg-search           running   0.0.0.0:8051->8000/tcp
...
```

### Step 5: Configure API Keys

Edit `core/config.json` and add your API keys:

```json
{
  "keys": {
    "dial_api_key": "secret",
    "openai-key": "sk-proj-...",
    "anthropic-key": "sk-ant-..."
  },
  "models": [
    {
      "name": "gpt-4o",
      "type": "chat",
      "endpoint": "https://api.openai.com/v1/chat/completions",
      "upstreams": [
        {"endpoint": "https://api.openai.com/v1", "key": "openai-key"}
      ]
    }
  ]
}
```

**⚠️ Critical**: This file is `.gitignore`d, but double-check before committing.

## Configuration

### DIAL Core Configuration (`core/config.json`)

Full configuration structure:

```json
{
  "keys": {
    "dial_api_key": "secret",
    "openai-key": "YOUR_OPENAI_KEY",
    "anthropic-key": "YOUR_ANTHROPIC_KEY"
  },
  "models": [
    {
      "name": "gpt-4o",
      "type": "chat",
      "endpoint": "https://api.openai.com/v1/chat/completions",
      "upstreams": [
        {
          "endpoint": "https://api.openai.com/v1",
          "key": "openai-key"
        }
      ]
    },
    {
      "name": "claude-sonnet-3-7",
      "type": "chat",
      "endpoint": "https://api.anthropic.com/v1/messages",
      "upstreams": [
        {
          "endpoint": "https://api.anthropic.com",
          "key": "anthropic-key"
        }
      ]
    },
    {
      "name": "dall-e-3",
      "type": "image",
      "endpoint": "https://api.openai.com/v1/images/generations",
      "upstreams": [
        {
          "endpoint": "https://api.openai.com/v1",
          "key": "openai-key"
        }
      ]
    }
  ],
  "applications": [
    {
      "name": "general-purpose-agent",
      "displayName": "General Purpose Agent with Memory",
      "endpoint": "http://host.docker.internal:5030",
      "description": "AI agent with long-term memory, web search, code execution"
    }
  ]
}
```

### Agent Configuration (`task/app.py`)

Configure deployment settings via environment variables:

```bash
# Set LLM model (default: gpt-4o)
export DEPLOYMENT_NAME="claude-sonnet-3-7"

# Set DIAL Core endpoint (default: http://localhost:8080)
export DIAL_ENDPOINT="http://localhost:8080"
```

Or modify directly in `task/app.py`:

```python
DIAL_ENDPOINT = os.getenv('DIAL_ENDPOINT', "http://localhost:8080")
DEPLOYMENT_NAME = os.getenv('DEPLOYMENT_NAME', 'gpt-4o')
```

### Docker Compose Configuration

Customize services in `docker-compose.yml`:

```yaml
services:
  python-interpreter:
    image: khshanovskyi/python-code-interpreter-mcp-server:latest
    ports:
      - "8050:8000"
    environment:
      LOG_LEVEL: "INFO"
    mem_limit: 2G  # Adjust memory limit
    cpus: 2.0      # Adjust CPU allocation
```

**Common customizations:**
- Change ports if conflicts exist
- Adjust memory limits for MCP servers
- Configure Redis maxmemory policy
- Enable/disable chat UI features

## Running the Agent

### Development Mode

```bash
# Ensure virtual environment is active
source dial_agent_with_memory/bin/activate

# Start agent with auto-reload
python -m task.app
```

**Expected output:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:5030
```

### Production Mode

```bash
# Run with Gunicorn + Uvicorn workers
gunicorn task.app:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:5030
```

### Background Mode

```bash
# Run as daemon
nohup python -m task.app > agent.log 2>&1 &

# Check logs
tail -f agent.log

# Stop
pkill -f "python -m task.app"
```

## Verification

### 1. Check DIAL Core Health

```bash
curl http://localhost:8080/health
```

**Expected:** `{"status": "ok"}`

### 2. Verify Agent Registration

```bash
curl -X POST http://localhost:8080/openai/deployments/general-purpose-agent/chat/completions \
  -H "Content-Type: application/json" \
  -H "Api-Key: dial_api_key" \
  -d '{
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'
```

**Expected:** JSON response with assistant message

### 3. Test Memory Tool

Open Chat UI at [http://localhost:3000](http://localhost:3000):

```
User: My name is Alice and I live in Paris.
Agent: Got it, I'll remember that!

[New conversation]
User: What's the weather where I live?
Agent: [searches memories] Let me check the weather in Paris...
```

### 4. Verify MCP Servers

```bash
# Python interpreter
curl http://localhost:8050/health
# Expected: 200 OK

# DuckDuckGo search
curl http://localhost:8051/health
# Expected: 200 OK
```

### 5. Check Logs

```bash
# Agent logs
python -m task.app  # Watch console output

# DIAL Core logs
docker-compose logs -f core

# MCP server logs
docker-compose logs -f python-interpreter
docker-compose logs -f ddg-search
```

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

**Error:** `Error starting userland proxy: bind: address already in use`

**Solution:**
```bash
# Find process using port
lsof -i :8080  # or :3000, :5030, etc.

# Kill process
kill -9 <PID>

# Or change port in docker-compose.yml
```

#### 2. FAISS Threading Issues

**Error:** `OMP: Error #15: Initializing libiomp5.dylib, but found libiomp5.dylib already initialized`

**Solution:** Already handled in `memory_store.py`:
```python
os.environ['OMP_NUM_THREADS'] = '1'
```

If still occurring:
```bash
export OMP_NUM_THREADS=1
python -m task.app
```

#### 3. DIAL Core Cannot Reach Agent

**Error:** `Connection refused to http://host.docker.internal:5030`

**Solution (macOS/Windows):**
```yaml
# In core/config.json, use host.docker.internal:
"endpoint": "http://host.docker.internal:5030"
```

**Solution (Linux):**
```yaml
# In docker-compose.yml, add to core service:
extra_hosts:
  - "host.docker.internal:host-gateway"
```

#### 4. Missing API Keys

**Error:** `Authentication failed` or `Invalid API key`

**Solution:**
1. Verify keys are set in `core/config.json`
2. Check key format (no extra spaces/quotes)
3. Restart DIAL Core: `docker-compose restart core`

#### 5. Memory File Not Found

**Error:** `File not found: files/.../__long-memories/data.json`

**This is expected** for new users. Memory file is created on first `store_memory` call.

#### 6. Sentence Transformers Download

**First run** downloads the embedding model (~80MB). If slow:

```bash
# Pre-download model
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

### Debug Mode

Enable verbose logging:

```python
# In task/app.py, add:
import logging
logging.basicConfig(level=logging.DEBUG)
```

View all messages sent to LLM:

```python
# Already present in agent.py
print("\nHistory:")
for msg in unpacked_messages:
    print(f"     {json.dumps(msg)}")
```

### Health Check Script

Create `scripts/health_check.sh`:

```bash
#!/bin/bash

echo "Checking DIAL infrastructure..."

# DIAL Core
curl -s http://localhost:8080/health > /dev/null && echo "✅ DIAL Core" || echo "❌ DIAL Core"

# Chat UI
curl -s http://localhost:3000 > /dev/null && echo "✅ Chat UI" || echo "❌ Chat UI"

# Agent
curl -s http://localhost:5030/health > /dev/null && echo "✅ Agent" || echo "❌ Agent"

# Python Interpreter
curl -s http://localhost:8050/health > /dev/null && echo "✅ Python MCP" || echo "❌ Python MCP"

# DuckDuckGo Search
curl -s http://localhost:8051/health > /dev/null && echo "✅ DuckDuckGo MCP" || echo "❌ DuckDuckGo MCP"
```

Run: `bash scripts/health_check.sh`

## Development Setup

### IDE Configuration

**VS Code:**

`.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/dial_agent_with_memory/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false
}
```

**PyCharm:**
1. Settings → Project → Python Interpreter
2. Add existing interpreter: `dial_agent_with_memory/bin/python`
3. Mark `task/` as Sources Root

### Hot Reload

Use `uvicorn` auto-reload:

```bash
uvicorn task.app:app --reload --host 0.0.0.0 --port 5030
```

Changes to `task/` directory trigger automatic restart.

### Testing Environment

```bash
# Run tests (if implemented)
pytest tests/

# Run with coverage
pytest --cov=task --cov-report=html tests/

# View coverage
open htmlcov/index.html
```

### Linting and Formatting

```bash
# Format code
black task/

# Lint code
pylint task/

# Type checking
mypy task/
```

## Deployment

### Docker Deployment

Create `Dockerfile` for agent:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY task/ ./task/

CMD ["python", "-m", "task.app"]
```

Build and run:

```bash
docker build -t dial-agent:latest .
docker run -p 5030:5030 -e DIAL_ENDPOINT=http://core:8080 dial-agent:latest
```

### Production Checklist

- [ ] Remove API keys from `core/config.json`
- [ ] Use environment variables for secrets
- [ ] Enable HTTPS for DIAL Core
- [ ] Configure rate limiting
- [ ] Set up monitoring (Prometheus, Grafana)
- [ ] Configure log aggregation (ELK, Splunk)
- [ ] Implement backup strategy for DIAL buckets
- [ ] Set resource limits for MCP servers
- [ ] Enable CORS for Chat UI
- [ ] Configure authentication (OAuth, SAML)

## Next Steps

1. **Read Architecture**: Understand system design → [architecture.md](./architecture.md)
2. **Explore API**: Learn tool schemas → [api.md](./api.md)
3. **Test Memory**: Validate storage/search/deletion → [testing.md](./testing.md)
4. **Customize Prompt**: Improve LLM behavior → [prompts.py](../task/prompts.py)

---

**Having Issues?** Check [Troubleshooting](#troubleshooting) or review logs with `docker-compose logs -f`.
