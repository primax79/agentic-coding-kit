#!/usr/bin/env python3
"""Migrate a Kilo RAG index to a new collection key after a workspace move/rename.

Kilo keys each workspace's Qdrant collection as `ws-<sha256(workspace_path)[:16]>`
(see kilo-indexing's qdrant-client.ts, QdrantVectorStore constructor). The hash is
computed over the *exact* workspace path string Kilo was given (no normalization) -
so moving or renaming a project's directory changes the hash, and Kilo starts
"unindexed" from scratch even though nothing about the code changed.

This script copies every point (vectors + payload, including the fixed-UUID
metadata point that carries the embedding profile / schema-complete markers) from
the collection keyed by the OLD path straight into a new collection keyed by the
NEW path, via Qdrant's REST API. No re-embedding, no Kilo CLI/extension involved -
it only talks to Qdrant, so it works regardless of which tool (Kilo IDE extension,
`kilo run`, an orchestrating AI) originally built the index.

Usage:
    # 1. Sanity-check what collection name a path hashes to, and see what's
    #    actually on the Qdrant instance, before touching anything:
    migrate-qdrant-collection.py hash "/old/path/to/project"
    migrate-qdrant-collection.py list --qdrant-url http://localhost:16333

    # 2. Copy the index across (old collection is left untouched by default):
    migrate-qdrant-collection.py migrate \\
        --old-path "/old/path/to/project" \\
        --new-path "/new/path/to/project" \\
        --qdrant-url http://localhost:16333

    # 3. Once Kilo confirms the new path shows "IDX Complete", delete the old
    #    collection explicitly (not automatic - it's a shared resource):
    migrate-qdrant-collection.py migrate --old-collection ws-XXXX --delete-old \\
        --qdrant-url http://localhost:16333 --yes

If you already know the collection names (e.g. from `list`), pass --old-collection/
--new-collection instead of --old-path/--new-path to skip re-deriving the hash.

Depends on nothing outside the Python 3 standard library.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from typing import Any, Optional

DEFAULT_QDRANT_URL = "http://localhost:6333"
SCROLL_BATCH_SIZE = 200

# Mirrors QdrantVectorStore.createCollection() in kilo-indexing's qdrant-client.ts -
# any collection this script creates must match what Kilo itself would create, or
# Kilo's own compatibility check (openExisting / initialize) will reject it.
HNSW_CONFIG = {"m": 64, "ef_construct": 512, "on_disk": True}


def collection_name(workspace_path: str) -> str:
    digest = hashlib.sha256(workspace_path.encode("utf-8")).hexdigest()
    return f"ws-{digest[:16]}"


def _request(
    method: str,
    base_url: str,
    path: str,
    api_key: Optional[str] = None,
    body: Optional[dict] = None,
) -> dict[str, Any]:
    url = base_url.rstrip("/") + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["api-key"] = api_key
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"{method} {path} -> could not reach {base_url}: {e.reason}") from e


def get_collection(base_url: str, name: str, api_key: Optional[str]) -> Optional[dict]:
    try:
        return _request("GET", base_url, f"/collections/{name}", api_key)["result"]
    except RuntimeError as e:
        if "HTTP 404" in str(e):
            return None
        raise


def cmd_hash(args: argparse.Namespace) -> None:
    print(collection_name(args.path))


def cmd_list(args: argparse.Namespace) -> None:
    result = _request("GET", args.qdrant_url, "/collections", args.api_key)["result"]
    collections = result.get("collections", [])
    if not collections:
        print("No collections found.")
        return
    for c in collections:
        name = c["name"]
        info = get_collection(args.qdrant_url, name, args.api_key) or {}
        points = info.get("points_count", "?")
        vectors = info.get("config", {}).get("params", {}).get("vectors", {})
        size = vectors.get("size") if isinstance(vectors, dict) else vectors
        print(f"{name}\tpoints={points}\tdim={size}")


def _scroll_all_points(base_url: str, name: str, api_key: Optional[str]):
    offset = None
    total = 0
    while True:
        body = {
            "limit": SCROLL_BATCH_SIZE,
            "with_payload": True,
            "with_vector": True,
        }
        if offset is not None:
            body["offset"] = offset
        result = _request("POST", base_url, f"/collections/{name}/points/scroll", api_key, body)["result"]
        points = result.get("points", [])
        total += len(points)
        if points:
            yield points, total
        offset = result.get("next_page_offset")
        if offset is None or not points:
            break


def cmd_migrate(args: argparse.Namespace) -> None:
    old_name = args.old_collection or collection_name(args.old_path)
    new_name = args.new_collection or collection_name(args.new_path)

    if old_name == new_name:
        print(f"Old and new collection names are identical ({old_name}) - nothing to do.", file=sys.stderr)
        sys.exit(1)

    old_info = get_collection(args.qdrant_url, old_name, args.api_key)
    if old_info is None:
        print(f"Source collection '{old_name}' does not exist on {args.qdrant_url}.", file=sys.stderr)
        print("Run the 'list' command to see what's actually there.", file=sys.stderr)
        sys.exit(1)

    old_points_count = old_info.get("points_count", 0)
    vectors_config = old_info.get("config", {}).get("params", {}).get("vectors", {})
    print(f"Source: {old_name} ({old_points_count} points, vectors={vectors_config})")

    new_info = get_collection(args.qdrant_url, new_name, args.api_key)
    if new_info is not None:
        if not args.force:
            print(
                f"Destination collection '{new_name}' already exists "
                f"({new_info.get('points_count', 0)} points). Pass --force to overwrite by "
                "upserting into it anyway (points are keyed by id, so this merges/replaces, "
                "it does not wipe first).",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"Destination '{new_name}' already exists - merging into it (--force).")
    else:
        print(f"Creating destination collection '{new_name}'...")
        if isinstance(vectors_config, dict):
            create_vectors = {**vectors_config, "on_disk": True}
        else:
            create_vectors = {"size": vectors_config, "distance": "Cosine", "on_disk": True}
        _request(
            "PUT",
            args.qdrant_url,
            f"/collections/{new_name}",
            args.api_key,
            {"vectors": create_vectors, "hnsw_config": HNSW_CONFIG},
        )

    copied = 0
    for batch, total in _scroll_all_points(args.qdrant_url, old_name, args.api_key):
        upsert_points = [{"id": p["id"], "vector": p["vector"], "payload": p.get("payload") or {}} for p in batch]
        _request(
            "PUT",
            args.qdrant_url,
            f"/collections/{new_name}/points?wait=true",
            args.api_key,
            {"points": upsert_points},
        )
        copied = total
        print(f"  copied {copied}/{old_points_count} points...", end="\r")

    print(f"\nDone: {copied} points copied from '{old_name}' to '{new_name}'.")

    new_final = get_collection(args.qdrant_url, new_name, args.api_key) or {}
    final_count = new_final.get("points_count", 0)
    if final_count != old_points_count and not args.force:
        print(
            f"WARNING: destination has {final_count} points, source had {old_points_count}. "
            "Verify before deleting anything.",
            file=sys.stderr,
        )

    if args.delete_old:
        if not args.yes:
            print(f"Refusing to delete '{old_name}' without --yes (this is destructive).", file=sys.stderr)
            sys.exit(1)
        _request("DELETE", args.qdrant_url, f"/collections/{old_name}", args.api_key)
        print(f"Deleted source collection '{old_name}'.")
    else:
        print(f"Source collection '{old_name}' left untouched. Delete it manually once you've verified Kilo picks up '{new_name}' correctly.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_hash = sub.add_parser("hash", help="print the Qdrant collection name Kilo derives for a workspace path")
    p_hash.add_argument("path", help="workspace path exactly as Kilo/VS Code would report it (no trailing slash)")
    p_hash.set_defaults(func=cmd_hash)

    p_list = sub.add_parser("list", help="list collections on the Qdrant instance with point counts and dimensions")
    p_list.add_argument("--qdrant-url", default=DEFAULT_QDRANT_URL)
    p_list.add_argument("--api-key", default=None)
    p_list.set_defaults(func=cmd_list)

    p_migrate = sub.add_parser("migrate", help="copy all points from the old workspace's collection to the new one")
    p_migrate.add_argument("--qdrant-url", default=DEFAULT_QDRANT_URL)
    p_migrate.add_argument("--api-key", default=None)
    p_migrate.add_argument("--old-path", help="old workspace path (mutually exclusive with --old-collection)")
    p_migrate.add_argument("--new-path", help="new workspace path (mutually exclusive with --new-collection)")
    p_migrate.add_argument("--old-collection", help="old collection name, if already known")
    p_migrate.add_argument("--new-collection", help="new collection name, if already known")
    p_migrate.add_argument("--force", action="store_true", help="merge into an already-existing destination collection")
    p_migrate.add_argument("--delete-old", action="store_true", help="delete the source collection after copying")
    p_migrate.add_argument("--yes", action="store_true", help="required together with --delete-old to confirm deletion")
    p_migrate.set_defaults(func=cmd_migrate)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "migrate":
        if bool(args.old_path) == bool(args.old_collection):
            parser.error("pass exactly one of --old-path or --old-collection")
        if bool(args.new_path) == bool(args.new_collection):
            parser.error("pass exactly one of --new-path or --new-collection")

    try:
        args.func(args)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
