# 04 — Installing and Configuring Kilo Code Itself

`docs/02`/`03` assume Kilo Code is already installed and working. This doc
covers getting there: installing Kilo, picking/authenticating an LLM
provider, wiring always-on instruction files, and (optional) enabling
semantic codebase search backed by a local Qdrant.

## Table of Contents

- [Install](#install)
- [LLM / Model Configuration](#llm--model-configuration)
- [Always-on Instruction Files](#always-on-instruction-files)
- [Codebase Semantic Indexing (RAG) with Qdrant](#codebase-semantic-indexing-rag-with-qdrant)

---

## Install

Official guide: [kilo.ai/install](https://kilo.ai/install) (VS Code
extension + optional CLI). Config lives at `~/.config/kilo/kilo.jsonc`
(global) and, per-project, `.kilo/kilo.jsonc` — same Global-vs-Local
distinction as everywhere else in Kilo (see
[`docs/03`](03-compatibility-and-distribution.md#bootstrap-kilo-plugin-manager-itself)
for the gotcha where the Settings UI's graphical fields write Global Config
but some things are only honored from Local).

## LLM / Model Configuration

Top-level `model` (and optional `small_model` for cheap/fast sub-tasks) in
`kilo.jsonc`:

```jsonc
{
  "model": "google/gemini-3.6-flash",
  "small_model": "google/gemini-3.5-flash-lite"
}
```

Per-agent overrides live under `"agent": { "<agent-name>": { "model": "..." } }`
— e.g. pin a different/stronger model just for implementation work without
changing the global default. `kilo auth status` (or the `kilo_auth_status`
MCP tool, if driving Kilo via `kilo-mcp`) shows which providers have valid
credentials. Run `kilo auth login <provider>` (e.g. `google`) to
authenticate a new one — API keys are stored under
`~/.local/share/kilo/auth.json`, never in `kilo.jsonc` itself for the
providers that support the login flow.

**Model choice matters more than it looks** — a cheap/fast model is
noticeably more prone to inventing plausible-but-wrong library API calls
than a stronger one. See
[`adk-agentic-coding-kit/instructions/`](https://github.com/primax79/adk-agentic-coding-kit/tree/main/instructions)
for the anti-hallucination rule this project ended up writing after hitting
that in practice, and the next section for how to wire it in.

## Always-on Instruction Files

Skills load on demand; **instruction files load into every session
unconditionally** — the mechanism for standing rules (git safety,
API-verification discipline, scope discipline) that should apply no matter
what task is running. Configured via the `instructions` array in
`kilo.jsonc`:

```jsonc
{
  "instructions": [
    "./AGENTS.md",                        // project-relative — whatever repo Kilo is running in
    "~/.config/kilo/INSTRUCTIONS.md"      // global, every project on the machine
  ]
}
```

The actual content — and the reasoning behind it — is maintained in
[`adk-agentic-coding-kit/instructions/`](https://github.com/primax79/adk-agentic-coding-kit/tree/main/instructions),
not duplicated here; that doc also covers wiring the equivalent mechanism
into Claude Code (`CLAUDE.md`). *(Open question, not yet decided: since
that content is fully generic — not ADK-specific — it may belong here in
`agentic-coding-kit` instead, long-term. Flagging rather than moving it
unilaterally.)*

## Codebase Semantic Indexing (RAG) with Qdrant

Separate from everything above: Kilo's own **codebase search** feature
(semantic search over *this* repo's source, used internally by Kilo's
`explore` agent and similar) — not related to any application-level RAG a
project you're working on might have. Needs a vector store; Qdrant running
locally via Docker is the straightforward option.

### Qdrant via Docker

Minimal `compose.yml` (verified working setup):

```yaml
services:
  qdrant_vector_memory:
    image: qdrant/qdrant:latest
    container_name: qdrant_vector_memory
    expose:
      - 6333
    ports:
      - 16333:6333
    volumes:
      - ./mnt/long_term_memory/vector:/qdrant/storage
    restart: unless-stopped
```

```bash
docker compose up -d
```

Port `16333` on the host (mapped to Qdrant's default `6333` in-container)
to avoid colliding with any other local Qdrant instance a project you're
working on might run for its own application RAG — genuinely two different
Qdrant deployments, don't point Kilo's indexing at a project's own RAG
instance.

### Wiring it into `kilo.jsonc`

```jsonc
{
  "experimental": {
    "semantic_indexing": true,
    "codebase_search": true
  },
  "indexing": {
    "enabled": true,
    "provider": "gemini",
    "gemini": {
      "apiKey": "<your-gemini-api-key>"
    },
    "qdrant": {
      "url": "http://localhost:16333/"
    },
    "vectorStore": "qdrant"
  }
}
```

`indexing.gemini.apiKey` is used specifically for generating the
embeddings used by the index — separate from whichever provider/key is
authenticated for the model doing the actual coding (previous section).

<!-- TODO(screenshots): docs/screenshots/kilo_rag_config.png (Settings UI,
     indexing panel showing the fields above) and
     docs/screenshots/kilo_rag_status.png (indexing status/progress
     indicator once enabled) — see PR/commit that added this comment for
     who's providing them. -->

---

Screenshots for this section go in `docs/screenshots/` (same convention as
`kilo_skill_config.png` in `gcube-ai-toolkit`) — reference them here as
`![...](screenshots/<filename>.png)` once added.
