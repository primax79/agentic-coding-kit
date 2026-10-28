#!/usr/bin/env python3
"""Cleanup orphaned, empty, or deleted workspace indexes in Qdrant, LanceDB, and Kilo's hash cache.

Kilo keys each workspace's index resources by `sha256(workspace_path)`:
- Qdrant collection: `ws-<sha256(workspace_path)[:16]>`
- Hash cache file:   `~/.local/state/kilo/indexing/roo-index-cache-<sha256(workspace_path)>.json`
- LanceDB table dir: `~/.cache/kilo/lancedb/<basename>-<sha256(workspace_path)[:16]>`

Because each `roo-index-cache-<sha256>.json` file stores absolute file paths as keys,
this script can reconstruct the exact original `workspace_path` for any cached index by
hashing the ancestor prefixes of its keys and matching against `<sha256>` — even when
the workspace folder was deleted months ago or created in `/tmp` or `.kilo/worktrees`.

Usage:
    # 1. Audit / dry-run across Qdrant, cache files, and LanceDB (safe, read-only):
    python3 clean-qdrant-collections.py --qdrant-url http://localhost:16333

    # 2. Delete all confirmed orphans (missing workspace paths, temp/worktree runs, empty):
    python3 clean-qdrant-collections.py --qdrant-url http://localhost:16333 --delete-all-orphans --yes

    # 3. Delete index (Qdrant + cache + LanceDB) for a specific workspace path or collection:
    python3 clean-qdrant-collections.py --workspace "/path/to/deleted/project" --yes
    python3 clean-qdrant-collections.py --collection ws-0123456789abcdef --yes
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Set, Tuple

DEFAULT_QDRANT_URL = "http://localhost:16333"
DEFAULT_CACHE_DIR = os.path.expanduser("~/.local/state/kilo/indexing")
DEFAULT_LANCEDB_DIR = os.path.expanduser("~/.cache/kilo/lancedb")
METADATA_POINT_ID = "f946a536-9af4-4f1f-9f95-7d6efb4647d5"

TEMP_PATH_MARKERS = (
    "/private/var/folders/",
    "/var/folders/",
    "/tmp/",
    "/private/tmp/",
    "/.kilo/worktrees/",
    "/worktree-pool/",
    "/pytest-of-",
)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def qdrant_hash(workspace_path: str) -> str:
    return f"ws-{sha256_hex(workspace_path)[:16]}"


def is_temp_workspace_path(ws_path: str) -> bool:
    normalized = ws_path.replace("\\", "/")
    return any(marker in normalized for marker in TEMP_PATH_MARKERS)


def infer_workspace_from_cache_keys(full_hash: str, keys: List[str]) -> Optional[str]:
    """Reconstruct the exact workspace_path whose sha256 equals full_hash by testing ancestor prefixes."""
    if not keys:
        return None
    sample_Paths = [keys[0]]
    if len(keys) > 1:
        sample_Paths.append(os.path.commonpath(keys[: min(len(keys), 20)]))

    tested: Set[str] = set()
    for sample in sample_Paths:
        current = sample
        while current and current not in tested:
            tested.add(current)
            if sha256_hex(current) == full_hash:
                return current
            if current.startswith("/private/"):
                alt = current[len("/private") :]
                if sha256_hex(alt) == full_hash:
                    return alt
            elif current.startswith("/var/") or current.startswith("/tmp/"):
                alt = "/private" + current
                if sha256_hex(alt) == full_hash:
                    return alt
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
    return None


def scan_cache_files(cache_dir: str = DEFAULT_CACHE_DIR) -> Dict[str, dict]:
    """Scan all roo-index-cache-<hash64>.json files and resolve their workspace paths."""
    by_short_hash: Dict[str, dict] = {}
    if not os.path.isdir(cache_dir):
        return by_short_hash

    for entry in os.listdir(cache_dir):
        if not (entry.startswith("roo-index-cache-") and entry.endswith(".json")):
            continue
        full_hash = entry[len("roo-index-cache-") : -len(".json")]
        if len(full_hash) != 64:
            continue
        short_hash = full_hash[:16]
        coll_name = f"ws-{short_hash}"
        full_path = os.path.join(cache_dir, entry)
        ws_path = None
        key_count = 0
        try:
            with open(full_path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            if isinstance(data, dict):
                keys = list(data.keys())
                key_count = len(keys)
                ws_path = infer_workspace_from_cache_keys(full_hash, keys)
        except Exception:
            pass

        by_short_hash[coll_name] = {
            "full_hash": full_hash,
            "cache_file": full_path,
            "workspace_path": ws_path,
            "cached_files": key_count,
        }
    return by_short_hash


def scan_lancedb_dirs(lancedb_dir: str = DEFAULT_LANCEDB_DIR) -> Dict[str, List[str]]:
    """Map ws-<hash16> -> list of LanceDB directories matching -<hash16>."""
    by_coll: Dict[str, List[str]] = {}
    if not os.path.isdir(lancedb_dir):
        return by_coll
    for entry in os.listdir(lancedb_dir):
        full = os.path.join(lancedb_dir, entry)
        if not os.path.isdir(full) or "-" not in entry:
            continue
        suffix = entry.rsplit("-", 1)[-1]
        if len(suffix) == 16:
            coll_name = f"ws-{suffix}"
            by_coll.setdefault(coll_name, []).append(full)
    return by_coll


def request_json(
    method: str,
    base_url: str,
    path: str,
    body: Optional[dict] = None,
    api_key: Optional[str] = None,
) -> dict[str, Any]:
    url = base_url.rstrip("/") + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["api-key"] = api_key
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"{method} {path} -> connection error: {e.reason}") from e


def get_all_collections(base_url: str, api_key: Optional[str] = None) -> List[str]:
    res = request_json("GET", base_url, "/collections", api_key=api_key)
    colls = res.get("result", {}).get("collections", [])
    return [c["name"] for c in colls if c.get("name", "").startswith("ws-")]


def get_collection_info(base_url: str, name: str, api_key: Optional[str] = None) -> dict:
    try:
        res = request_json("GET", base_url, f"/collections/{name}", api_key=api_key)
        return res.get("result", {})
    except RuntimeError:
        return {}


def delete_collection(base_url: str, name: str, api_key: Optional[str] = None) -> bool:
    try:
        request_json("DELETE", base_url, f"/collections/{name}", api_key=api_key)
        return True
    except RuntimeError as e:
        print(f"Failed to delete {name}: {e}", file=sys.stderr)
        return False


def discover_known_workspaces(
    cache_map: Dict[str, dict],
    extra_roots: Optional[List[str]] = None,
) -> Dict[str, str]:
    """Build a mapping of collection_name -> workspace_path from cache files, VS Code storage, and disk roots."""
    coll_to_path: Dict[str, str] = {}

    # 1. Exact reconstruction from roo-index-cache-<sha256>.json keys (most authoritative)
    for coll_name, meta in cache_map.items():
        if meta.get("workspace_path"):
            coll_to_path[coll_name] = meta["workspace_path"]

    # 2. VS Code workspaceStorage
    ws_pattern = os.path.expanduser("~/Library/Application Support/Code/User/workspaceStorage/*/workspace.json")
    for f in glob.glob(ws_pattern):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                d = json.load(fp)
                folder = d.get("folder")
                if folder and folder.startswith("file://"):
                    p = urllib.parse.unquote(folder[7:])
                    coll_to_path.setdefault(qdrant_hash(p), p)
        except Exception:
            pass

    # 3. Discovered Git repos in scan roots (e.g. ~/works, ~/devel)
    roots = [os.path.expanduser("~/works"), os.path.expanduser("~/devel")]
    if extra_roots:
        roots.extend([os.path.expanduser(r) for r in extra_roots])

    skip_dirs = {
        "node_modules", "target", ".venv", "venv", ".git", "dist",
        "build", ".cache", "site-packages", ".tox", "vendor", "bin", "obj",
    }

    for root_dir in roots:
        if not os.path.isdir(root_dir):
            continue
        root_depth = root_dir.rstrip(os.sep).count(os.sep)
        for current_root, dirs, files in os.walk(root_dir):
            depth = current_root.count(os.sep) - root_depth
            if depth >= 3:
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
            if ".git" in files or os.path.isdir(os.path.join(current_root, ".git")):
                coll_to_path.setdefault(qdrant_hash(current_root), current_root)

    return coll_to_path


def inspect_collection_sample(base_url: str, name: str, api_key: Optional[str] = None) -> List[str]:
    """Return a few sample relative filePaths from the collection."""
    body = {"limit": 5, "with_payload": True, "with_vector": False}
    try:
        res = request_json("POST", base_url, f"/collections/{name}/points/scroll", body=body, api_key=api_key)
        points = res.get("result", {}).get("points", [])
    except Exception:
        return []

    file_paths = []
    for p in points:
        payload = p.get("payload") or {}
        fp = payload.get("filePath")
        if fp:
            file_paths.append(fp)
    return file_paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--qdrant-url", default=DEFAULT_QDRANT_URL, help=f"Qdrant REST URL (default: {DEFAULT_QDRANT_URL})")
    parser.add_argument("--api-key", default=None, help="Optional Qdrant API key")
    parser.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR, help="Kilo indexing cache directory")
    parser.add_argument("--lancedb-dir", default=DEFAULT_LANCEDB_DIR, help="Kilo LanceDB directory")
    parser.add_argument("--scan-root", action="append", default=[], help="Additional directories to search for existing git repos")
    parser.add_argument("--delete-empty", action="store_true", help="Delete collections with <= 1 point (empty or only metadata)")
    parser.add_argument("--delete-missing", action="store_true", help="Delete indexes whose workspace path no longer exists on disk")
    parser.add_argument("--delete-temp", action="store_true", help="Delete indexes created for temporary/test/worktree paths")
    parser.add_argument("--delete-all-orphans", action="store_true", help="Delete all empty, temp, and missing-path indexes (Qdrant + cache + LanceDB)")
    parser.add_argument("--collection", help="Target a specific collection name (ws-...) directly")
    parser.add_argument("--workspace", help="Target a specific workspace path directly (even if already deleted on disk)")
    parser.add_argument("--yes", action="store_true", help="Confirm deletion (required for any delete operation)")
    args = parser.parse_args()

    cache_map = scan_cache_files(args.cache_dir)
    lancedb_map = scan_lancedb_dirs(args.lancedb_dir)

    qdrant_reachable = True
    all_colls: List[str] = []
    try:
        all_colls = get_all_collections(args.qdrant_url, args.api_key)
    except Exception as e:
        qdrant_reachable = False
        print(f"WARNING: Qdrant not reachable at {args.qdrant_url} ({e}); auditing local cache/LanceDB only.", file=sys.stderr)

    target_coll = args.collection or (qdrant_hash(args.workspace) if args.workspace else None)
    if target_coll:
        ws_path = args.workspace or cache_map.get(target_coll, {}).get("workspace_path")
        has_qdrant = target_coll in all_colls
        cache_entry = cache_map.get(target_coll)
        lance_dirs = lancedb_map.get(target_coll, [])
        print(f"Target index: {target_coll}")
        print(f"  Workspace path: {ws_path or '(unknown)'} (exists={bool(ws_path and os.path.exists(ws_path))})")
        print(f"  Qdrant collection present: {has_qdrant}")
        print(f"  Cache file present: {bool(cache_entry)} ({cache_entry.get('cached_files', 0) if cache_entry else 0} files)")
        print(f"  LanceDB dirs present: {len(lance_dirs)}")
        if not args.yes:
            print("\nPass --yes to delete this index across Qdrant, cache, and LanceDB.")
            return
        if has_qdrant:
            delete_collection(args.qdrant_url, target_coll, args.api_key)
            print(f"Deleted Qdrant collection {target_coll}.")
        if cache_entry and os.path.isfile(cache_entry["cache_file"]):
            os.remove(cache_entry["cache_file"])
            print(f"Deleted cache file {cache_entry['cache_file']}.")
        for d in lance_dirs:
            shutil.rmtree(d, ignore_errors=True)
            print(f"Deleted LanceDB dir {d}.")
        return

    known_paths = discover_known_workspaces(cache_map, args.scan_root)
    all_keys = sorted(set(all_colls) | set(cache_map.keys()) | set(lancedb_map.keys()))
    print(
        f"Found {len(all_colls)} Qdrant collections, {len(cache_map)} cache files, "
        f"{len(lancedb_map)} LanceDB dirs ({len(all_keys)} unique index keys)."
    )

    active_items: List[Tuple[str, str, int]] = []
    missing_items: List[Tuple[str, str, int]] = []
    temp_items: List[Tuple[str, str, int]] = []
    empty_items: List[Tuple[str, int]] = []
    unknown_items: List[Tuple[str, int, List[str]]] = []

    qdrant_set = set(all_colls)
    for idx, c in enumerate(all_keys, 1):
        points_count = -1
        if c in qdrant_set:
            info = get_collection_info(args.qdrant_url, c, args.api_key)
            points_count = info.get("points_count", 0)

        ws_path = known_paths.get(c)
        cached_files = cache_map.get(c, {}).get("cached_files", 0)

        if ws_path and is_temp_workspace_path(ws_path):
            temp_items.append((c, ws_path, points_count))
            continue

        if ws_path:
            if os.path.exists(ws_path):
                if c in qdrant_set and points_count <= 1 and cached_files == 0:
                    empty_items.append((c, points_count))
                else:
                    active_items.append((c, ws_path, points_count))
            else:
                missing_items.append((c, ws_path, points_count))
            continue

        if (c in qdrant_set and points_count <= 1) or (c not in qdrant_set and cached_files == 0):
            empty_items.append((c, max(points_count, 0)))
            continue

        sample_files = inspect_collection_sample(args.qdrant_url, c, args.api_key) if c in qdrant_set else []
        unknown_items.append((c, points_count, sample_files))

    print("\n" + "=" * 64)
    print("INDEX AUDIT SUMMARY (Qdrant + Cache + LanceDB):")
    print(f"  [ACTIVE]       Existing workspace on disk:   {len(active_items)}")
    print(f"  [MISSING]      Deleted/moved workspace path: {len(missing_items)}")
    print(f"  [TEMP/TEST]    Temp/pytest/worktree paths:   {len(temp_items)}")
    print(f"  [EMPTY]        Empty or metadata-only:       {len(empty_items)}")
    print(f"  [UNKNOWN]      Unresolved path (in Qdrant):  {len(unknown_items)}")
    print("=" * 64 + "\n")

    if missing_items:
        print("Sample deleted/moved workspaces:")
        for c, p, pts in missing_items[:8]:
            pts_label = f"{pts} pts" if pts >= 0 else "cache-only"
            print(f"  {c} ({pts_label}) -> {p}")
        if len(missing_items) > 8:
            print(f"  ... and {len(missing_items) - 8} more.")
        print()

    if temp_items:
        print("Sample temp/worktree workspaces:")
        for c, p, pts in temp_items[:5]:
            pts_label = f"{pts} pts" if pts >= 0 else "cache-only"
            print(f"  {c} ({pts_label}) -> {p}")
        if len(temp_items) > 5:
            print(f"  ... and {len(temp_items) - 5} more.")
        print()

    if args.delete_all_orphans:
        args.delete_empty = True
        args.delete_missing = True
        args.delete_temp = True

    to_delete: Set[str] = set()
    if args.delete_empty:
        to_delete.update(c for c, _ in empty_items)
    if args.delete_missing:
        to_delete.update(c for c, _, _ in missing_items)
    if args.delete_temp:
        to_delete.update(c for c, _, _ in temp_items)

    if not to_delete:
        print("No deletions requested. Run with:")
        print("  --delete-missing      to delete indexes whose workspace folder was deleted")
        print("  --delete-temp         to delete temp/pytest/worktree indexes")
        print("  --delete-empty        to delete empty and metadata-only indexes")
        print("  --delete-all-orphans  to delete all missing + temp + empty indexes")
        print("  --workspace <path>    to delete the index of a specific workspace")
        print("Remember to include --yes to confirm.")
        return

    print(f"Targeted for deletion: {len(to_delete)} index keys.")
    if not args.yes:
        print("\nABORTED: Refusing to delete without --yes flag (dry-run mode).")
        return

    del_qdrant = 0
    del_cache = 0
    del_lance = 0
    for c in sorted(to_delete):
        if qdrant_reachable and c in qdrant_set:
            if delete_collection(args.qdrant_url, c, args.api_key):
                del_qdrant += 1
        cache_entry = cache_map.get(c)
        if cache_entry and os.path.isfile(cache_entry["cache_file"]):
            try:
                os.remove(cache_entry["cache_file"])
                del_cache += 1
            except OSError:
                pass
        for d in lancedb_map.get(c, []):
            shutil.rmtree(d, ignore_errors=True)
            del_lance += 1

    print(
        f"\nCleanup complete: deleted {del_qdrant} Qdrant collections, "
        f"{del_cache} cache files, and {del_lance} LanceDB directories."
    )


if __name__ == "__main__":
    main()
