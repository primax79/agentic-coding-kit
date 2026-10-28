#!/usr/bin/env python3
"""Migrate a Kilo RAG index to a new collection key after a workspace move/rename.

Kilo keys each workspace's Qdrant collection as `ws-<sha256(workspace_path)[:16]>`
and its file-hash cache as `~/.local/state/kilo/indexing/roo-index-cache-<sha256(workspace_path)>.json`.
The hash is computed over the *exact* workspace path string Kilo was given (no normalization) -
so moving or renaming a project's directory changes the hash, and Kilo starts
"unindexed" from scratch even though nothing about the code changed.

This script:
1. Copies every point (vectors + payload, including the fixed-UUID metadata point
   that carries the embedding profile / schema-complete markers) from the old
   Qdrant collection into the new one, and creates Kilo's keyword payload indexes
   (`type`, `pathSegments.0`..`pathSegments.4`).
2. Migrates `~/.local/state/kilo/indexing/roo-index-cache-<old_sha256>.json` to
   `roo-index-cache-<new_sha256>.json`, rewriting the absolute file path keys from
   `old_path` to `new_path` so Kilo's incremental scanner skips all unchanged files
   instead of re-embedding the entire workspace.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Optional

DEFAULT_QDRANT_URL = "http://localhost:16333"
SCROLL_BATCH_SIZE = 200
DEFAULT_CACHE_DIR = os.path.expanduser("~/.local/state/kilo/indexing")

# Mirrors QdrantVectorStore.createCollection() in kilo-indexing's qdrant-client.ts
HNSW_CONFIG = {"m": 64, "ef_construct": 512, "on_disk": True}
PAYLOAD_INDEX_FIELDS = ["type", "pathSegments.0", "pathSegments.1", "pathSegments.2", "pathSegments.3", "pathSegments.4"]


def workspace_sha256(workspace_path: str) -> str:
    return hashlib.sha256(workspace_path.encode("utf-8")).hexdigest()


def collection_name(workspace_path: str) -> str:
    return f"ws-{workspace_sha256(workspace_path)[:16]}"


def cache_file_path(workspace_path: str, cache_dir: str = DEFAULT_CACHE_DIR) -> str:
    return os.path.join(cache_dir, f"roo-index-cache-{workspace_sha256(workspace_path)}.json")


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


def create_payload_indexes(base_url: str, name: str, api_key: Optional[str]) -> None:
    for field in PAYLOAD_INDEX_FIELDS:
        try:
            _request(
                "PUT",
                base_url,
                f"/collections/{name}/index?wait=true",
                api_key,
                {"field_name": field, "field_schema": "keyword"},
            )
        except RuntimeError as e:
            print(f"WARNING: failed to create payload index '{field}' on '{name}': {e}", file=sys.stderr)


def migrate_cache_file(
    old_path: str,
    new_path: str,
    cache_dir: str = DEFAULT_CACHE_DIR,
    delete_old: bool = False,
) -> tuple[bool, int]:
    old_cache = cache_file_path(old_path, cache_dir)
    new_cache = cache_file_path(new_path, cache_dir)
    if not os.path.isfile(old_cache):
        return False, 0

    with open(old_cache, "r", encoding="utf-8") as fp:
        raw_hashes: dict[str, str] = json.load(fp)

    old_prefix = old_path.rstrip("/\\")
    new_prefix = new_path.rstrip("/\\")
    rewritten: dict[str, str] = {}
    for file_key, file_hash in raw_hashes.items():
        if file_key == old_prefix:
            rewritten[new_prefix] = file_hash
        elif file_key.startswith(old_prefix + "/"):
            rewritten[new_prefix + file_key[len(old_prefix) :]] = file_hash
        elif file_key.startswith(old_prefix + "\\"):
            rewritten[new_prefix + file_key[len(old_prefix) :]] = file_hash
        else:
            rewritten[file_key] = file_hash

    os.makedirs(cache_dir, exist_ok=True)
    tmp_cache = f"{new_cache}.tmp"
    with open(tmp_cache, "w", encoding="utf-8") as fp:
        json.dump(rewritten, fp)
    os.replace(tmp_cache, new_cache)

    if delete_old and os.path.isfile(old_cache):
        os.remove(old_cache)

    return True, len(rewritten)


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
        create_payload_indexes(args.qdrant_url, new_name, args.api_key)

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

    if args.old_path and args.new_path:
        migrated_cache, entries = migrate_cache_file(
            args.old_path,
            args.new_path,
            args.cache_dir,
            delete_old=bool(args.delete_old and args.yes),
        )
        if migrated_cache:
            print(f"Migrated cache file ({entries} file hashes rewritten from '{args.old_path}' to '{args.new_path}').")
        else:
            print(f"Note: no local cache file found for '{args.old_path}' in {args.cache_dir}.")

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
        print(
            f"Source collection '{old_name}' left untouched. "
            f"Delete it manually once you've verified Kilo picks up '{new_name}' correctly."
        )


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

    p_migrate = sub.add_parser("migrate", help="copy all points and cache hashes from the old workspace to the new one")
    p_migrate.add_argument("--qdrant-url", default=DEFAULT_QDRANT_URL)
    p_migrate.add_argument("--api-key", default=None)
    p_migrate.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR, help="Kilo indexing cache directory")
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
