# Drewgent Agent - Architecture & Implementation Guide

**Version**: 1.1
**Last Updated**: 2026-05-12  
**Maintainer**: Drewgent (Chief Agent Commander @ HUMANERD)

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Docker Deployment](#docker-deployment)
4. [Brain System & Feedback Loop](#brain-system--feedback-loop)
5. [Module Connections](#module-connections)
6. [Monitoring & Observability](#monitoring--observability)
7. [Optimization Decisions](#optimization-decisions)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)
10. [Lessons Learned](#lessons-learned)

---

## Overview

Drewgent is a personal AI agent system built on the HUMANERD architecture. It combines multiple specialized modules (VerificationEngine, GrowthEngine, RevisionLoop, AutoLearner) into a unified agent that runs as a Docker-based service.

### Key Design Principles

1. **Feedback Loop Architecture**: Every action is verified, and verification results feed back into the knowledge base to improve future decisions
2. **Docker-First Deployment**: All components run in Docker containers for consistency across machines
3. **Local-First Monitoring**: No external monitoring services; all metrics are collected locally and pushed to Discord
4. **Minimal External Dependencies**: Reduces attack surface and failure points

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Drewgent Agent                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Gateway   │  │   Agent     │  │    Brain System       │ │
│  │  (Message   │──│  (Core AI)  │──│  ┌─────────────────┐    │ │
│  │   Router)   │  │             │  │  │ AutoLearner    │    │ │
│  └─────────────┘  └─────────────┘  │  │ (wiki-based)   │    │ │
│         │                │         │  └─────────────────┘    │ │
│         │                │         └─────────────────────────┘ │
│         │                │                    │                │
│         ▼                ▼                    ▼                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              Monitor (Discord Alerts)                    │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Core Components

| Component | Purpose | Key File |
|----------|---------|----------|
| **Gateway** | Message routing, platform adapters (Discord, Telegram, etc.) | `gateway/run.py` |
| **Agent** | Core AI processing, tool orchestration | `run_agent.py` |
| **AutoLearner** | Passive + active learning, wiki-based knowledge base | `agent/auto_learn.py` |
| **Brain Tools** | Agent's active access to its own knowledge | `tools/brain_tool.py` |
| **VerificationEngine** | Response validation, quality gates | `modules/verification_engine.py` |
| **GrowthEngine** | Pattern discovery, learning | `modules/growth_engine.py` |
| **RevisionLoop** | LLM re-calling for revisions | `modules/revision_loop.py` |
| **Monitor** | Local metrics collection, Discord notifications | `scripts/drewgent_monitor.py` |

---

## Docker Deployment

### Image Registry

```
humanerdkr/drewgent:latest        # Gateway + Agent
humanerdkr/drewgent-monitor:latest # Monitor only
```

### Docker Compose Configuration

```yaml
services:
  drewgent-gateway:
    image: humanerdkr/drewgent:latest
    container_name: drewgent-gateway
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./data:/opt/data
      - ~/.drewgent:/root/.drewgent:rw
      - /Volumes/drewgent_storage:/nas:ro
    env_file:
      - ~/.drewgent/.env
    environment:
      - HERMES_HOME=/opt/data
      - PYTHONPATH=/opt/drewgent
    entrypoint: ["bash", "-c", "cd /opt/drewgent && mkdir -p /opt/data/{cron,sessions,logs,hooks,memories,skills} && exec python3 -m drewgent_cli.main gateway run"]

  drewgent-agent:
    image: humanerdkr/drewgent:latest
    container_name: drewgent-agent
    restart: unless-stopped
    network_mode: host
    entrypoint: ["bash", "-c", "cd /opt/drewgent && mkdir -p /opt/data && exec python3 cli.py agent run"]
    volumes:
      - ./data:/opt/data
      - ~/.drewgent:/root/.drewgent:rw
      - /Volumes/drewgent_storage:/nas:ro
    depends_on:
      - drewgent-gateway

  monitor:
    image: humanerdkr/drewgent-monitor:latest
    container_name: drewgent-monitor
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./data:/opt/data
    environment:
      - GATEWAY_URL=http://localhost:8642
      - DREW_DISCORD_WEBHOOK=${DISCORD_WEBHOOK_URL}
    entrypoint: ["python3", "/usr/local/bin/drewgent_monitor.py"]
```

### Key Docker Decisions

1. **`network_mode: host`**: Avoids Docker's DNS issues, simplifies localhost access
2. **Volume Mounts**: 
   - `./data:/opt/data` - Persistent state
   - `~/.drewgent:/root/.drewgent:rw` - Config and credentials
3. **`restart: unless-stopped`**: Ensures recovery after system reboot

### Building & Pushing Images

```bash
# Build and push Drewgent
docker build -t humanerdkr/drewgent:latest .
docker push humanerdkr/drewgent:latest

# Build and push Monitor
docker build -f Dockerfile.simple -t humanerdkr/drewgent-monitor:latest .
docker push humanerdkr/drewgent-monitor:latest
```

---

## Brain System & Feedback Loop

### The Feedback Loop Concept

```
┌──────────────────────────────────────────────────────────────┐
│                    FEEDBACK LOOP                             │
│                                                              │
│  Action → Verification → Brain → Better Action         │
│                                                              │
│  1. User message arrives                                    │
│  2. Agent generates response                                │
│  3. VerificationEngine checks quality                      │
│  4. AutoLearner extracts patterns from turn               │
│  5. Future queries use brain_query + wiki context         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Brain System Structure

The brain system consists of two layers:

**1. AutoLearner (`agent/auto_learn.py`)** — passive + active learning
- Passive: `learn_from_turn()` extracts patterns after each conversation turn
- Active: `save_insight()` records explicit agent decisions
- Output: Obsidian wiki at `~/.drewgent/memories/` (entities/, concepts/, insights/)
- Semantic: embeddings stored for similarity search when text match is insufficient

**2. Brain Tools (`tools/brain_tool.py`)** — agent's active access
- `brain_query`: agent queries wiki during reasoning for relevant context
- `brain_record`: agent explicitly saves knowledge worth remembering
- Both are regular registry tools (not agent-level interceptors)

**Injection pipeline** (in `run_agent.py`):
```
user message → brain_query → <brain_context> tag injected into user message
turn ends → AutoLearner.learn_from_turn() → wiki updated
```

```python
# agent/auto_learn.py
class AutoLearner:
    def learn_from_turn(self, user_text, assistant_text) -> (int, int):
        """Passive extraction from conversation. Returns (user_insights, memory_insights)."""

    def save_insight(self, insight: Insight) -> bool:
        """Explicit save from brain_record tool."""

    def query_wiki(self, query, context, max_results, max_chars) -> str:
        """Active query used by brain_query tool."""
```

### Knowledge Types (Brain System)

| Type | Source | Description |
|------|--------|-------------|
| `preference` | AutoLearner pattern extraction | User likes/dislikes expressed in conversation |
| `correction` | AutoLearner pattern extraction | User corrections or negative feedback |
| `tool` | AutoLearner + brain_record | Tool usage patterns, commands that worked |
| `project` | brain_record | Project-specific context saved by agent |
| `anti_preference` | AutoLearner | Negative patterns (avoid this approach) |

> Note: The old `KnowledgeBus` singleton (v1.0, 2026-04-15) is deprecated.
> The current brain system uses the Obsidian wiki at `~/.drewgent/memories/` with
> `AutoLearner` as the core engine.

### Brain Filesystem — NeuronFS (.neuron files)

The brain filesystem at `~/.drewgent/brain/Drewgent-brain/` organizes governance rules
in a 7-layer subsumption hierarchy (P0-brainstem through P6-prefrontal). Each rule is a
`.neuron` file containing a micro-opcode pattern with `禁` (forbidden) tokens and `vorq`
(value-or-lookup) / `enforce` mechanisms.

**Key brain files (2026-05-12 upgrade):**

| File | Purpose |
|------|---------|
| `P0-brainstem/禁karpathy_coding_principles.neuron` | P0 enforcement of Karpathy's 4 coding principles |
| `~/.drewgent/SOUL.md` | Primary identity — links to P0-brainstem |
| `~/.drewgent/AGENTS.md` | Project context — links to SOUL.md and P0-brainstem |

**Organic reference chain (2026-05-12):**
```
SOUL.md ↔ P0-brainstem ↔ AGENTS.md
  (cross-referential brain system — all three files reference each other)
```

System prompt layers that load brain components:
- Layer 1: `load_soul_md()` → `~/.drewgent/SOUL.md`
- Layer 3: `brain_load()` → `~/.drewgent/brain/Drewgent-brain/` (P0-brainstem neurons)
- Layer 7: `build_context_files_prompt()` → `~/.drewgent/AGENTS.md`

See `CHANGELOG.md` for the complete upgrade history.

### Wiki Maintenance (Autonomous)

Session-end maintenance keeps the wiki healthy without user intervention:

```python
# AutoLearner.run_maintenance() — called automatically at session end
# 1. retire_stale_entries() — files untouched 90+ days → retired/
# 2. deduplicate_wiki() — duplicate daily log entries merged
# 3. detect_knowledge_gaps() — topics tracked but lacking wiki coverage
```

### Verification Engine Integration

```python
# Verification happens after every LLM response
def verify_and_process_response(user_message, response, context):
    """
    1. Run verification checks
    2. AutoLearner extracts patterns from turn
    3. Return verification result
    """
    result = VerificationEngine.verify(response, context)
    # AutoLearner extracts patterns from the turn passively
    AutoLearner.learn_from_turn(user_message, assistant_text)
    return result
```

---

## Module Connections

### API Endpoints (Gateway)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/v1/metrics` | GET | Verification statistics |
| `/v1/knowledge` | GET | Brain wiki query (AutoLearner) |

### Module Dependency Chain

```
AutoLearner (wiki-based knowledge, no external dependencies)
    ↑
Agent (uses AutoLearner for brain_query + learn_from_turn)
    ↑
VerificationEngine (standalone verification)
GrowthEngine (standalone pattern discovery)
RevisionLoop (standalone revision)
    ↑
Gateway (routes messages to Agent)
```

### Key Implementation Details

#### 1. Streaming Verification with Chunk Injection

When streaming responses, revision chunks are injected after all LLM output:

```python
# SSE stream structure:
[chunk1][chunk2][chunk3]...  ← LLM output
[finish_chunk]                 ← usage stats
[revision_chunk]               ← ⚠️ revision request (if needed)
[DONE]
```

**Important**: Injection order matters:
1. All LLM chunks first
2. finish_chunk with usage
3. **revision_chunk** (after finish, before DONE)
4. [DONE]

#### 2. Non-Streaming Verification

```python
verification_result = verify_and_process_response(
    user_message=user_message,
    response=final_response,
    context={"platform": "api_server", ...}
)
# Handle: append revision_notes or block response
```

---

## Monitoring & Observability

### Drewgent Monitor Script

Located at `scripts/drewgent_monitor.py`, this script:

1. **Collects** metrics every hour
2. **Sends** Discord notifications
3. **Excludes** night hours (midnight to 8 AM)
4. **Provides** morning summary at 8 AM

### Monitor Features

```python
# Metrics collected
- Gateway Health (/health)
- Verification Statistics (/v1/metrics)
  - total/approved/revision/rejected counts
  - pass rate percentage
  - average score
  - P0 blocks (hallucination, safety)
- Knowledge Brain (wiki entries)
  - total entries
  - by category (entities, concepts, insights)
  - recent entries
  - by insight type
- Models (/v1/models)
```

### Discord Notification Schedule

| Time | Notification |
|------|--------------|
| Every hour (on the hour) | Full metrics report |
| Midnight - 8 AM | Data collection only (no notifications) |
| 8 AM | Night summary (midnight to 8 AM data) |

### Log Files

| File | Location | Description |
|------|----------|-------------|
| Monitor log | `data/drewgent_monitor.log` | Monitor script output |
| Gateway logs | `data/logs/` | Gateway activity |
| Knowledge dump | `data/drewgent_knowledge.json` | All knowledge entries |
| Metrics snapshot | `data/drewgent_metrics_snapshot.json` | Latest metrics |

---

## Optimization Decisions

### 1. Docker Volume Mounts for Development

**Problem**: Rebuilding Docker images during development is slow.

**Solution**: Mount source directories as read-only volumes:

```yaml
volumes:
  - ./agent:/opt/drewgent/agent:ro
  - ./gateway:/opt/drewgent/gateway:ro
  - ./modules:/opt/drewgent/modules:ro
```

**Trade-off**: Image contains code, but volumes override at runtime. Changes reflect immediately without rebuild.

### 2. Colima Timeout Workaround

**Problem**: Docker build on Colima (macOS VM) times out at 120 seconds.

**Solution**: Use pre-built images from Docker Hub. Local builds only when absolutely necessary.

### 3. Network Mode: host

**Problem**: Docker's internal DNS can cause issues with localhost services.

**Solution**: Use `network_mode: host` to:
- Simplify service discovery
- Avoid DNS resolution problems
- Direct port access

### 4. Brain System: Wiki-Based Knowledge

**Design**: The brain uses Obsidian wiki files at `~/.drewgent/memories/` instead of
a singleton in-memory store. This provides persistence, human readability, and
bidirectional sync with Obsidian itself.

```python
# AutoLearner writes to wiki files
wiki_path = get_drewgent_home() / "memories"  # entities/, concepts/, insights/
AutoLearner(wiki_path=wiki_path, enabled=True)

# Brain tools give the agent active access
# brain_query → searches wiki, returns relevant entries
# brain_record → writes new insight to wiki
```

### 5. RevisionLoop Model Selection

**Problem**: OpenAI models caused API key errors.

**Solution**: Switched to MiniMax M2.7 for RevisionLoop:

```python
# Before (caused errors)
model = "gpt-4o-mini"
base_url = "https://api.openai.com/v1"

# After (worked)
model = "MiniMax-M2.7"
base_url = "https://api.minimax.chat/v1"
```

**Key Fix**: The API logic had a bug where `OPENAI_API_KEY` being set caused it to use OpenAI URL even when `base_url` was explicitly set.

---

## Best Practices

### 1. Configuration Management

```python
# Always use environment variables for secrets
DISCORD_WEBHOOK = os.environ.get("DREW_DISCORD_WEBHOOK", "")

# Never hardcode credentials in code
# Never commit .env files to version control
```

### 2. Error Handling

```python
def get_gateway(endpoint: str) -> Optional[Dict[str, Any]]:
    """Always handle connection errors gracefully"""
    try:
        resp = requests.get(f"{GATEWAY_URL}{endpoint}", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return None  # Caller handles None case
```

### 3. State Persistence

```python
# Use JSON files for knowledge persistence
STATE_FILE = "/tmp/drewgent_monitor_state.json"

def save_state(state: dict) -> None:
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)
```

### 4. Clean Architecture

```
# Good: Single responsibility
def verify_and_process_response(user_message, response, context):
    result = VerificationEngine.verify(response, context)
    AutoLearner.learn_from_turn(user_message, response)
    return result

# Bad: Mixing concerns
def process_message(msg):
    # verification + storage + logging + response formatting all in one
```

### 5. Docker Image Optimization

```dockerfile
# Use specific Python version
FROM python:3.11-slim

# Install only necessary dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git ripgrep \
    && rm -rf /var/lib/apt/lists/*

# Copy files in order of change frequency (caching optimization)
COPY requirements.txt pyproject.toml ./
COPY drewgent_cli ./drewgent_cli
COPY agent ./agent
# ... less frequently changed files last
```

---

## Troubleshooting

### Gateway Unreachable

```bash
# Check if container is running
docker ps

# Check logs
docker logs drewgent-gateway

# Test health endpoint
curl http://localhost:8642/health
```

### Monitor Not Sending Notifications

```bash
# Check monitor logs
docker logs drewgent-monitor

# Test webhook manually
curl -X POST -H "Content-Type: application/json" \
  -d '{"content":"test"}' \
  https://discord.com/api/webhooks/YOUR_WEBHOOK_URL
```

### Brain Wiki Empty

```bash
# Check wiki directory
ls -la ~/.drewgent/memories/

# Check wiki entries
ls ~/.drewgent/memories/entities/
ls ~/.drewgent/memories/insights/

# Query brain via API
curl http://localhost:8642/v1/knowledge
```

### Docker Build Timeout (Colima)

```bash
# Use pre-built images instead of building locally
docker pull humanerdkr/drewgent:latest
```

---

## Lessons Learned

### 1. Cloudflare Tunnel Account Management

**Problem**: Tunnels were created in the wrong Cloudflare account.

**Lesson**: Always verify the correct account is selected in Dashboard before creating tunnels. CLI doesn't always respect account selection.

**Solution**: 
- Create tunnels via Dashboard with correct account selected
- Use API tokens with minimal required permissions
- Document which account owns which resource

### 2. DNS Resolution Issues with Tailscale

**Problem**: Mac's DNS was being intercepted by Tailscale, returning IPv6 addresses that couldn't connect.

**Lesson**: VPN clients can intercept DNS even for domains they don't own.

**Solutions**:
1. Add domain to VPN's DNS exception list
2. Use `/etc/hosts` for local overrides
3. Test from external network/device

### 3. API Token Permissions

**Problem**: API token lacked sufficient permissions, causing "Authentication error" on tunnel listing.

**Lesson**: Cloudflare API tokens are granular - "DNS:edit" doesn't mean "Tunnel:manage".

**Solution**: Create tokens with minimum required permissions for the task.

### 4. Streaming Chunk Injection Order

**Problem**: Revision chunks were being injected in wrong order, causing malformed SSE streams.

**Lesson**: In streaming responses, order matters critically.

**Solution**: 
1. All LLM chunks first
2. finish_chunk (usage stats)
3. revision_chunk (if revision needed)
4. [DONE]

### 5. Docker Volume Mounts vs Built Images

**Problem**: Choosing between development speed (volume mounts) and portability (built images).

**Lesson**: The choice depends on deployment context.

**Solution**: 
- Development: Use volume mounts for immediate code updates
- Production/Deployment: Use pre-built images for consistency

### 6. Model Provider API Quirks

**Problem**: RevisionLoop failed with OpenAI because environment variable checking logic was flawed.

**Lesson**: Provider APIs have different requirements - always test with actual provider.

**Solution**:
- Don't assume OpenAI-compatible APIs work identically
- Check API key presence vs explicit configuration
- Test with fallback providers

---

## Deployment Checklist

### New Machine Setup

```bash
# 1. Install Docker
brew install docker docker-compose

# 2. Create necessary directories
mkdir -p data

# 3. Copy .env file with credentials
cp ~/.drewgent/.env.example ~/.drewgent/.env
# Edit with actual API keys

# 4. Start services
docker-compose up -d

# 5. Verify
curl http://localhost:8642/health
docker ps
```

### Updating Images

```bash
# Pull latest
docker pull humanerdkr/drewgent:latest
docker pull humanerdkr/drewgent-monitor:latest

# Restart services
docker-compose restart
```

---

## Contact & Support

- **Documentation**: `/docs/`
- **Logs**: `/data/logs/`
- **Knowledge Base**: `/data/drewgent_knowledge.json`
- **Metrics**: `/data/drewgent_metrics_snapshot.json`

---

*This document is maintained by Drewgent Agent. For updates, see CHANGELOG.md*
