---
name: kilo-rag-index-manager
description: "Administers Kilo's own semantic codebase index (Qdrant collections, LanceDB dirs, ~/.local/state/kilo/indexing cache files) independently of any orchestrator - migrating indexes across workspace moves/renames without re-embedding, and auditing/cleaning up orphaned indexes of deleted or temporary workspaces."
---

# Skill: kilo-rag-index-manager

Kilo's semantic indexing feature keys each workspace's index resources by `sha256(workspace_path)`:
- **Qdrant collection**: `ws-<sha256(workspace_path)[:16]>`
- **File-hash cache**: `~/.local/state/kilo/indexing/roo-index-cache-<sha256(workspace_path)>.json`
- **LanceDB directory**: `~/.cache/kilo/lancedb/<basename>-<sha256(workspace_path)[:16]>`

Moving or renaming a project directory changes `sha256(workspace_path)`, leaving both the Qdrant collection and the hash cache orphaned. Deleting a project or running temporary worktrees/tests leaves stale collections and cache files behind.

## Usage

```bash
# 1. Sanity-check what collection name a path hashes to, and list collections:
python3 scripts/migrate-qdrant-collection.py hash "/old/path/to/project"
python3 scripts/migrate-qdrant-collection.py list --qdrant-url http://localhost:16333

# 2. Migrate Qdrant points + payload indexes + rewrite roo-index-cache-<hash>.json paths:
python3 scripts/migrate-qdrant-collection.py migrate \
    --old-path "/old/path/to/project" \
    --new-path "/new/path/to/project" \
    --qdrant-url http://localhost:16333

# 3. Once verified, delete the old collection and old cache file:
python3 scripts/migrate-qdrant-collection.py migrate \
    --old-path "/old/path/to/project" \
    --new-path "/new/path/to/project" \
    --delete-old --qdrant-url http://localhost:16333 --yes

# 4. Audit all indexes (Qdrant + cache files + LanceDB) and reconstruct workspace paths:
python3 scripts/clean-qdrant-collections.py --qdrant-url http://localhost:16333

# 5. Delete all confirmed orphans (deleted folders, temp/worktree paths, empty indexes):
python3 scripts/clean-qdrant-collections.py --qdrant-url http://localhost:16333 --delete-all-orphans --yes

# 6. Delete the index of one specific workspace (even if already deleted on disk):
python3 scripts/clean-qdrant-collections.py --workspace "/path/to/deleted/project" --yes
```

## How it works

1. **Migration (`migrate-qdrant-collection.py`)**:
   - Creates the destination Qdrant collection with Kilo's exact HNSW config (`m=64, ef_construct=512, on_disk=True`) and keyword payload indexes (`type`, `pathSegments.0`..`pathSegments.4`).
   - Scrolls all points (including the fixed-UUID metadata point `f946a536-9af4-4f1f-9f95-7d6efb4647d5`) into the new collection.
   - Rewrites `~/.local/state/kilo/indexing/roo-index-cache-<old_sha256>.json` into `roo-index-cache-<new_sha256>.json`, replacing the `old_path` prefix on every cached file key with `new_path` so Kilo's incremental scanner skips all unchanged files instead of re-embedding.
2. **Orphan Audit & Cleanup (`clean-qdrant-collections.py`)**:
   - Reads the absolute file keys inside each `roo-index-cache-<sha256>.json` and hashes their ancestor prefixes to mathematically reconstruct the exact `workspace_path` that generated `<sha256>`, even if the folder was deleted months ago.
   - Classifies every index into `ACTIVE`, `MISSING` (deleted workspace), `TEMP/TEST` (`/tmp`, `/var/folders`, `.kilo/worktrees`, `pytest-`), or `EMPTY`, and cleans Qdrant collections, cache files, and LanceDB directories together.
