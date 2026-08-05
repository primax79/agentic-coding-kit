#!/usr/bin/env python3
"""Materialize a clean source tree of a target framework/library for citation-checking.

Generalized from adk-agentic-coding-kit's ``adk-version-upgrade/scripts/get_adk_tree.py``
(which hardcoded ``google-adk``/PyPI) to any Python package, parameterized by
``--module-prefix`` (must match the ``--module-prefix`` passed to this skill's
``check_citations.py``).

Three sources, in preference order:

1. ``--local-path`` — an already-checked-out or already-installed directory
   that contains ``<top-dir>/...`` (e.g. a monorepo dependency, or the
   project's own ``site-packages``). Just copied, no git/network involved —
   the cheapest and most trustworthy path when it's available.
2. ``--git-repo`` — a local checkout of the framework's own repo, plus
   ``--ref`` (a tag, branch, or commit). Uses ``git archive <ref> <path>``,
   which never touches the checkout's working tree or HEAD.
3. PyPI — ``pip download <package>==<version> --no-deps`` and unzip the
   wheel. Used automatically when neither of the above is given or fails.
   Covers "any pip-installable Python library" for free (the original
   ADK script's PyPI path was already generic, just parameterized on
   ``--package``) — kept for that reason, unlike npm/Maven/other-ecosystem
   registries, which are a deliberately out-of-scope gap for v1: this
   script only speaks git and PyPI. A non-Python target, or a Python one
   published only on a different index, needs its own fetch step; the
   skill's procedure falls back to whatever the input actually is (a docs
   URL, a formal spec file) rather than trying to force it through here.

All three paths normalize the output to the same layout::

    <dest>/<top-dir>/...

where ``<top-dir>`` is the first dotted segment of ``--module-prefix`` (e.g.
``google`` for ``google.adk``, or the package name itself for a flat
top-level package like ``requests``) — the same layout ``check_citations.py``
expects.

Examples::

    materialize_source.py --module-prefix google.adk --dest /tmp/adk-2.6.1 \\
        --git-repo ~/works/adk-python --ref v2.6.1
    materialize_source.py --module-prefix requests --dest /tmp/requests-2.31 \\
        --package requests --version 2.31.0
    materialize_source.py --module-prefix myapp --dest /tmp/myapp-src \\
        --local-path ~/works/myapp/src
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

PYPI_JSON = "https://pypi.org/pypi/{package}/json"


def die(msg: str) -> "None":
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(1)


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def latest_version(package: str, allow_pre: bool = False) -> str:
    """Latest version on PyPI. ``info.version`` is the latest stable release."""
    with urllib.request.urlopen(PYPI_JSON.format(package=package), timeout=30) as fh:
        data = json.load(fh)
    if not allow_pre:
        return data["info"]["version"]
    from packaging.version import Version  # type: ignore

    return str(max(Version(v) for v in data["releases"] if data["releases"][v]))


def resolve_ref(repo: Path, ref: str) -> str | None:
    for candidate in (ref, f"v{ref}"):
        if run(["git", "-C", str(repo), "rev-parse", "--verify", f"{candidate}^{{commit}}"]).returncode == 0:
            return candidate
    return None


def from_local_path(source: Path, top_dir: str, dest: Path) -> bool:
    if not source.is_dir():
        print(f"note: --local-path {source} is not a directory, skipping", file=sys.stderr)
        return False
    candidates = [source / top_dir, source / "src" / top_dir]
    src = next((c for c in candidates if c.is_dir()), None)
    if src is None:
        print(f"note: no {top_dir}/ found under {source} or {source / 'src'}, skipping", file=sys.stderr)
        return False
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest / top_dir, dirs_exist_ok=True)
    print(f"materialized from local path {source} -> {dest}")
    return True


def from_git(repo: Path, ref: str, top_dir: str, dest: Path, fetch: bool) -> bool:
    if not (repo / ".git").exists():
        print(f"note: {repo} is not a git checkout, falling back", file=sys.stderr)
        return False
    resolved = resolve_ref(repo, ref)
    if resolved is None and fetch:
        print(f"note: ref {ref} not present locally, running git fetch --tags", file=sys.stderr)
        run(["git", "-C", str(repo), "fetch", "--tags", "--quiet"])
        resolved = resolve_ref(repo, ref)
    if resolved is None:
        print(f"note: no ref {ref}/v{ref} in {repo}, falling back", file=sys.stderr)
        return False

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        archive = tmpdir / "src.tar"
        # Try both a src/ layout and a flat layout, same ambiguity get_adk_tree.py handled.
        for archive_path in (f"src/{top_dir}", top_dir):
            with archive.open("wb") as fh:
                proc = subprocess.run(
                    ["git", "-C", str(repo), "archive", resolved, archive_path],
                    stdout=fh, stderr=subprocess.PIPE, text=False,
                )
            if proc.returncode == 0:
                break
        else:
            print(f"note: git archive found neither src/{top_dir} nor {top_dir} at {resolved}, falling back", file=sys.stderr)
            return False

        shutil.unpack_archive(str(archive), str(tmpdir / "x"), format="tar")
        src = tmpdir / "x" / "src" / top_dir
        if not src.is_dir():
            src = tmpdir / "x" / top_dir
        if not src.is_dir():
            print("note: archive extraction produced no expected top-dir, falling back", file=sys.stderr)
            return False
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dest / top_dir, dirs_exist_ok=True)
    print(f"materialized from {repo}@{resolved} -> {dest}")
    return True


def from_pypi(package: str, version: str, top_dir: str, dest: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        proc = run(
            [sys.executable, "-m", "pip", "download", f"{package}=={version}",
             "--no-deps", "--only-binary", ":all:", "-d", str(tmpdir)]
        )
        if proc.returncode != 0:
            die(f"pip download failed:\n{proc.stdout}\n{proc.stderr}")
        wheels = sorted(tmpdir.glob("*.whl"))
        if not wheels:
            die(f"no wheel downloaded for {package}=={version}")
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(wheels[0]) as zf:
            for member in zf.namelist():
                if member.startswith(f"{top_dir}/") and not member.endswith("/"):
                    zf.extract(member, dest)
    print(f"materialized {package}=={version} from PyPI wheel -> {dest}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--module-prefix", required=True, help="dotted import path, e.g. google.adk or requests")
    ap.add_argument("--dest", required=True, type=Path)
    ap.add_argument("--local-path", type=Path, help="already-checked-out or already-installed directory to copy from")
    ap.add_argument("--git-repo", type=Path, help="local checkout of the framework's own repo")
    ap.add_argument("--ref", help="git tag/branch/commit to archive (required with --git-repo)")
    ap.add_argument("--no-fetch", action="store_true", help="do not run git fetch --tags when the ref is missing")
    ap.add_argument("--package", help="PyPI package name, if different from --module-prefix's top segment")
    ap.add_argument("--version", help="exact PyPI version, e.g. 2.31.0; omit with --latest")
    ap.add_argument("--latest", action="store_true", help="resolve the latest PyPI release")
    ap.add_argument("--force", action="store_true", help="overwrite a non-empty --dest")
    args = ap.parse_args()

    top_dir = args.module_prefix.split(".", 1)[0]
    dest: Path = args.dest.expanduser().resolve()
    if dest.exists() and any(dest.iterdir()):
        if not args.force:
            die(f"{dest} is not empty (use --force to overwrite)")
        shutil.rmtree(dest)

    ok = False
    if args.local_path:
        ok = from_local_path(args.local_path.expanduser(), top_dir, dest)
    if not ok and args.git_repo:
        if not args.ref:
            die("--ref is required with --git-repo")
        ok = from_git(args.git_repo.expanduser(), args.ref, top_dir, dest, fetch=not args.no_fetch)
    if not ok:
        package = args.package or top_dir
        if not (args.version or args.latest):
            die("no --local-path/--git-repo succeeded; pass --version X.Y.Z or --latest for the PyPI fallback")
        version = args.version or latest_version(package)
        from_pypi(package, version, top_dir, dest)

    marker = dest / top_dir
    if not marker.is_dir():
        die(f"expected {marker} after materialization")
    print(f"module_prefix={args.module_prefix} tree={dest}")


if __name__ == "__main__":
    main()
