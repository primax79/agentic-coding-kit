---
name: kilo-rag-index-manager
description: Administers Kilo's own semantic codebase index (Qdrant collections, embedding config) independently of any orchestrator - primarily migrating the index across a workspace move/rename without a full re-embed. Use when a Kilo-indexed project directory is moved/renamed and the index needs to follow it, or when inspecting/cleaning up Qdrant collections created by Kilo's indexing feature.
---

# Skill: kilo-rag-index-manager

Kilo's own semantic indexing feature (Settings > Indexing) keys each workspace's
Qdrant collection as `ws-<sha256(workspace_path)[:16]>` (see kilo-indexing's
`qdrant-client.ts`, `QdrantVectorStore` constructor). The hash is taken over the
*exact* workspace path string Kilo was given, unnormalized — so moving or renaming
a project directory changes the hash, and Kilo reports the new path as
"unindexed" from scratch even though nothing about the code changed. There's no
Kilo-side migration for this; the old collection is simply orphaned in Qdrant.

This is independent of `kilo-mcp`/orchestration — it applies any time a project
that Kilo indexes gets moved, regardless of whether an orchestrating AI is
involved at all.

## Usage

```bash
# 1. Sanity-check what collection name a path hashes to, and see what's actually
#    on the Qdrant instance, before touching anything:
python3 scripts/migrate-qdrant-collection.py hash "/old/path/to/project"
python3 scripts/migrate-qdrant-collection.py list --qdrant-url http://localhost:16333

# 2. Copy the index across (source collection is left untouched by default):
python3 scripts/migrate-qdrant-collection.py migrate \
    --old-path "/old/path/to/project" \
    --new-path "/new/path/to/project" \
    --qdrant-url http://localhost:16333

# 3. Once Kilo confirms the new path shows "IDX Complete" in Settings > Indexing,
#    delete the old collection explicitly (not automatic - shared resource):
python3 scripts/migrate-qdrant-collection.py migrate --old-collection ws-XXXX \
    --delete-old --qdrant-url http://localhost:16333 --yes
```

If the collection names are already known (e.g. from `list`), pass
`--old-collection`/`--new-collection` instead of `--old-path`/`--new-path` to skip
re-deriving the hash — safer when there's any doubt about the exact path string
Kilo originally used (trailing slash, symlink vs real path, etc.).

## How it works

Talks to Qdrant's REST API directly (stdlib-only, no `qdrant-client` dependency):
creates the destination collection with the same vector size/distance/HNSW config
Kilo itself would use, then scrolls every point (vectors + payload) from the
source collection and upserts it into the destination — including the
fixed-UUID metadata point that carries the embedding profile and
schema-complete markers, so Kilo's own compatibility check
(`openExisting`/`initialize` in `qdrant-client.ts`) accepts the destination as
already indexed. No re-embedding, no Kilo CLI/extension involved in the copy
itself.

## Gotchas

- **The hash is exact-string, not normalized.** If in doubt about trailing
  slashes or symlink resolution, verify with `hash`/`list` before migrating
  rather than assuming the path you have in hand matches what Kilo hashed.
- **Vector dimension in Kilo's Settings UI does not truncate Gemini's output.**
  `GeminiEmbedder` never forwards a `dimensions` override to the embedding API
  (unlike Ollama/OpenRouter, which do) — leave "Vector dimension" on Auto for
  the Gemini provider, or the created collection's expected size won't match
  what Gemini actually returns.
- **Deletion is opt-in and gated.** `--delete-old` requires `--yes`; without it
  the source collection is left in place so you can verify the destination in
  Kilo's UI first.
