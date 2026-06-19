# GBrain MCP Integration — Local Vault Search Engine

GBrain (github.com/garrytan/gbrain) provides hybrid search (keyword + vector) over markdown vaults. Connects to Hermes/OpenClaw via MCP protocol — zero code change, just config.yaml entry.

## Install

```bash
brew install oven-sh/bun/bun
git clone https://github.com/garrytan/gbrain.git ~/gbrain
cd ~/gbrain && bun install && bun link
```

## Initialize

```bash
gbrain init --pglite --no-embedding
# Creates ~/.gbrain/brain.pglite (PGLite embedded Postgres)
```

## Import Vault

```bash
gbrain sources add drewgent --path /Users/drew/.drewgent --name "Drewgent Vault"
gbrain import /Users/drew/.drewgent --source drewgent --no-embed
gbrain extract links --yes  # extract wikilinks
```

## MCP Server Config (config.yaml)

```yaml
mcp_servers:
  gbrain:
    command: /Users/drew/.bun/bin/gbrain
    args: ["serve"]
    timeout: 120
    description: "GBrain hybrid search over vault"
```

**Important**: `args` must be a YAML list (not JSON string). `env` must be a YAML dict (not JSON string). Wrong format causes `dictionary update sequence element #0 has length 1` error.

## Available MCP Tools (89 total)

Key tools for agent use:
- `search` — keyword FTS search (works without embeddings)
- `query` — hybrid search (vector + keyword, needs embeddings)
- `get_backlinks` — inbound links to a page
- `traverse_graph` — graph traversal from a page
- `get_page` — read a page by slug
- `get_stats` — brain statistics
- `think` — multi-hop synthesis across pages
- `find_orphans` — pages with no inbound links
- `sync_brain` — re-sync from git repo

## Embedding (Vector Search)

Requires OpenAI API key or local Ollama:

```bash
gbrain config set embedding_model openai:mxbai-embed-large
gbrain config set provider_base_urls '{"openai": "http://localhost:11434/v1"}'
```

**Caveat**: OpenAI client validates API key format — must start with `sk-`. Ollama ignores the key but the OpenAI library checks format first. Workaround: set `OPENAI_API_KEY=***` in MCP server env.

## Pitfalls

- **Key validation**: Even with `provider_base_urls` pointing at Ollama, OpenAI client library validates `OPENAI_API_KEY`. Ollama doesn't check keys, but the library rejects invalid formats before reaching Ollama.
- **First sync slow**: 5,000+ file vaults take 60-120s. Use `--no-embed` for initial import, add embeddings later.
- **MCP reconnect**: MCP tools discovered at session start. Adding GBrain mid-session requires gateway reload or next session.
- **Backlinks**: Run `gbrain extract links` separately after import — not automatic with `--no-embed`.
