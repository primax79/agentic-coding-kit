#!/usr/bin/env python3
"""Move (or copy) a Kilo customization item — skill, agent, or command/workflow —
between global and project-local scope.

Locations per kind:
  kind     | local (project)             | global (primary)              | other global (warn if twin found)
  ---------+-----------------------------+-------------------------------+----------------------------------
  skill    | <repo>/.kilo/skills/<n>/    | ~/.kilo/skills/<n>/           | ~/.config/kilo/skills/<n>/
  agent    | <repo>/.kilo/agent/<n>.md   | ~/.config/kilo/agent/<n>.md   | ~/.kilo/agent/<n>.md
  command  | <repo>/.kilo/command/<n>.md | ~/.config/kilo/command/<n>.md | ~/.kilo/command/<n>.md

Usage:
  move_item.py <skill|agent|command> to-local  <name> [--repo PATH] [--copy] [--force]
  move_item.py <skill|agent|command> to-global <name> [--repo PATH] [--copy] [--force]

Notes:
- Default is MOVE; --copy leaves the source in place. A local item shadows a
  global one with the same name (Kilo precedence: project wins).
- Refuses to overwrite an existing destination unless --force.
- After any change: /reload in Kilo; if agents/commands changed, re-run
  kilo-claude-sync (agents are mirrored to .claude/agents, commands to
  .claude/commands).
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HOME = Path.home()

KINDS = {
    "skill": {
        "local": lambda repo: repo / ".kilo" / "skills",
        "global": HOME / ".kilo" / "skills",
        "other_globals": [HOME / ".config" / "kilo" / "skills"],
        "is_dir": True,
    },
    "agent": {
        "local": lambda repo: repo / ".kilo" / "agent",
        "global": HOME / ".config" / "kilo" / "agent",
        "other_globals": [HOME / ".kilo" / "agent"],
        "is_dir": False,
    },
    "command": {
        "local": lambda repo: repo / ".kilo" / "command",
        "global": HOME / ".config" / "kilo" / "command",
        "other_globals": [HOME / ".kilo" / "command"],
        "is_dir": False,
    },
}


def repo_root(path: Path) -> Path:
    try:
        out = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return Path(out)
    except subprocess.CalledProcessError:
        return path.resolve()


def item_path(base: Path, name: str, is_dir: bool) -> Path:
    return base / name if is_dir else base / f"{name}.md"


def validate(kind: str, path: Path, is_dir: bool) -> None:
    md = path / "SKILL.md" if is_dir else path
    if not md.is_file():
        sys.exit(f"ERROR: {path} is not a valid {kind} ({'no SKILL.md' if is_dir else 'file missing'})")
    head = md.read_text(encoding="utf-8", errors="replace").splitlines()[:12]
    if kind == "skill" and not any(l.startswith("name:") for l in head):
        print(f"WARNING: {md} has no 'name:' frontmatter (required for skill discovery)")
    if kind in ("agent", "command") and not any(l.startswith("description:") for l in head):
        print(f"WARNING: {md} has no 'description:' frontmatter")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("kind", choices=sorted(KINDS))
    ap.add_argument("direction", choices=["to-local", "to-global"])
    ap.add_argument("name", help="item name (skill dir name, or agent/command filename without .md)")
    ap.add_argument("--repo", default=".", help="project path (default: cwd; resolved to git root)")
    ap.add_argument("--copy", action="store_true", help="copy instead of move")
    ap.add_argument("--force", action="store_true", help="overwrite destination if it exists")
    args = ap.parse_args()

    cfg = KINDS[args.kind]
    repo = repo_root(Path(args.repo))
    local_base, global_base = cfg["local"](repo), cfg["global"]
    src_base, dst_base = (global_base, local_base) if args.direction == "to-local" else (local_base, global_base)
    src = item_path(src_base, args.name, cfg["is_dir"])
    dst = item_path(dst_base, args.name, cfg["is_dir"])

    if not (src.is_dir() if cfg["is_dir"] else src.is_file()):
        sys.exit(f"ERROR: source {args.kind} not found: {src}")
    validate(args.kind, src, cfg["is_dir"])

    if dst.exists():
        if not args.force:
            sys.exit(f"ERROR: destination already exists: {dst} (use --force to overwrite)")
        shutil.rmtree(dst) if dst.is_dir() else dst.unlink()

    dst.parent.mkdir(parents=True, exist_ok=True)
    if args.copy:
        shutil.copytree(src, dst, symlinks=True) if cfg["is_dir"] else shutil.copy2(src, dst)
        action = "copied"
    else:
        shutil.move(str(src), str(dst))
        action = "moved"
    print(f"OK: {action} {src} -> {dst}")

    if args.copy and args.direction == "to-local":
        print("NOTE: the local copy shadows the global item with the same name (Kilo precedence).")
    for og in cfg["other_globals"]:
        twin = item_path(og, args.name, cfg["is_dir"])
        if twin.exists():
            print(f"WARNING: another copy exists at {twin} — check which one your Kilo version loads "
                  "and remove the stale twin.")

    if args.kind == "skill":
        # Nothing to mirror: this moved a skill inside Kilo's own directories.
        # Claude Code installs skills through its marketplace plus enabledPlugins,
        # so it is unaffected — and the two must not be bridged.
        for side, claude_dir in [("global", HOME / ".claude" / "skills"),
                                 ("local", repo / ".claude" / "skills")]:
            if claude_dir.is_symlink():
                print(f"WARNING: {side} {claude_dir} is a symlink into Kilo's skills — a leftover "
                      "from the old bridge between the two hosts. Remove it, and declare the "
                      "plugin in .claude/settings.json under enabledPlugins instead.")
    else:
        print("NOTE: agents/commands are mirrored to .claude/ — run the kilo-claude-sync skill "
              "for the affected scope(s).")
    print("Run /reload in Kilo to pick up the change in the current session.")


if __name__ == "__main__":
    main()
