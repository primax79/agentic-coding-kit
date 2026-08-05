#!/usr/bin/env python3
"""Verify SKILL.md citations against a real source tree of the target framework.

Forked from adk-agentic-coding-kit's ``adk-version-upgrade/scripts/check_citations.py``,
generalized from a hardcoded ``google.adk`` / ``google.adk_community`` package
pair to a single ``--module-prefix`` you pass at the CLI. Same AST-based
approach: extract every ``path::symbol`` / dotted-module / backtick /
fenced-code citation from a batch of SKILL.md files and classify each against
one or two materialized trees.

Two use modes:

1. **Self-check a freshly drafted batch** (this skill's own use case): pass
   the *same* tree as both ``--old`` and ``--new``. Every citation not
   ``UNCHANGED``/``OK`` is a hallucinated or mis-cited API — fix or drop it
   before the batch is considered done.
2. **Diff-check across two versions** (the original ADK use case, still
   supported): pass the old and new version's trees separately to see what a
   framework upgrade touches.

Trees are directories that contain ``<top-dir>/<rest of module path>`` (a
wheel/site-packages layout) or ``src/<top-dir>/...`` (a repo layout), where
``<top-dir>`` is the first dotted segment of ``--module-prefix``. Produce a
tree with this skill's own ``materialize_source.py``, or point at an
installed package::

    python3 -c "import <top_pkg>, pathlib; print(pathlib.Path(<top_pkg>.__file__).parents[<n>])"

Classification (the ``--old`` tree is what the skills were written against):

  files    UNCHANGED | CHANGED | MOVED_OR_DELETED | ADDED_AFTER | BROKEN | NO_TREE
  symbols  OK | MOVED | REMOVED | ADDED_AFTER | UNKNOWN

``BROKEN`` (cited path in neither tree) and ``UNKNOWN`` (identifier defined in
neither tree) are citation errors regardless of whether ``--old``/``--new``
differ — in self-check mode (same tree twice) these are the only two states
that can occur besides ``UNCHANGED``/``OK``. ``UNKNOWN`` also collects
ordinary English words and project-side identifiers, so it is reported only
with ``--strict``.

Known limitation, not attempted here: this is Python-AST-based, so it only
checks Python targets. A framework in another language needs its own
language-specific checker (a different AST/parser, same classification
shape) — fall back to manual grep-verification for those, same as the
baseline claim rule already requires regardless of tooling. Also unlike the
ADK original, this fork supports exactly one package family per run (no
``adk`` + ``adk_community`` pairing) — most single frameworks don't need
that; run the script twice with different ``--module-prefix``/``--skill``
selections if a framework genuinely spans two independent top-level packages.

Usage::

    check_citations.py --module-prefix requests --old /tmp/requests-2.31 --new /tmp/requests-2.31 \\
        --skills-dir /tmp/generated-batch
    check_citations.py --module-prefix google.adk --old /tmp/adk-2.1.0 --new /tmp/adk-2.6.1 \\
        --skills-dir plugins/adk-tools/skills --skill adk-function-tools --json
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path


def die(msg: str) -> "None":
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(1)


def build_patterns(module_prefix: str) -> tuple[re.Pattern, re.Pattern, str]:
    """Build the file/module citation regexes for one dotted module prefix.

    Returns (FILE_RE, MODULE_RE, top_dir) where ``top_dir`` is the first
    path segment on disk (e.g. ``google`` for ``google.adk``).
    """
    prefix_path = module_prefix.replace(".", "/")
    top_dir = prefix_path.split("/", 1)[0]
    file_re = re.compile(
        rf"(?:src/)?({re.escape(prefix_path)}(?:/[A-Za-z0-9_]+)*\.py)"
        r"(?:::([A-Za-z_][A-Za-z0-9_.]*))?"
    )
    module_re = re.compile(rf"\b{re.escape(module_prefix)}(?:\.[a-z_][a-z0-9_]*)+\b")
    return file_re, module_re, top_dir


BACKTICK_RE = re.compile(r"`([^`\n]{2,80})`")
FENCE_RE = re.compile(r"```[a-zA-Z]*\n(.*?)```", re.DOTALL)
IDENT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
DEF_RE = re.compile(
    r"^[ \t]*(?:async[ \t]+)?def[ \t]+(\w+)"
    r"|^[ \t]*class[ \t]+(\w+)"
    r"|^[ \t]*(\w+)[ \t]*(?::[^=\n]+)?=[^=]",
    re.MULTILINE,
)
# Identifiers that are too generic to carry signal even when the target framework defines them.
STOPWORDS = {
    "self", "cls", "args", "kwargs", "None", "True", "False", "return", "import",
    "from", "class", "def", "async", "await", "type", "id", "name", "value",
    "key", "data", "result", "error", "status", "message", "content", "text",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def defined_names(text: str) -> set[str]:
    """Every name a module makes available: classes, functions, assignment
    targets (including dataclass/Pydantic fields), function parameters and
    import aliases (``from .x import y as z`` — how most frameworks re-export)."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {m for groups in DEF_RE.findall(text) for m in groups if m}
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.arg):
            names.add(node.arg)
    return names


def resolve_tree(path: Path, top_dir: str) -> Path:
    """Return the directory that directly contains ``<top_dir>/``."""
    path = path.expanduser().resolve()
    for candidate in (path, path / "src"):
        if (candidate / top_dir).is_dir():
            return candidate
    if path.name == top_dir:
        return path.parent
    raise SystemExit(f"error: {path} contains no {top_dir}/ (looked in {path} and {path / 'src'})")


class Tree:
    def __init__(self, roots: list[Path], label: str, top_dir: str):
        self.top_dir = top_dir
        self.roots = [resolve_tree(r, top_dir) for r in roots]
        self.label = label
        self.files: dict[str, str] = {}
        self.defs: set[str] = set()
        self.tokens: set[str] = set()
        self.defs_by_file: dict[str, set[str]] = {}
        self.has_package = False
        for root in self.roots:
            self._index(root)

    def _index(self, root: Path) -> None:
        if (root / self.top_dir).is_dir():
            self.has_package = True
        for py in sorted((root / self.top_dir).rglob("*.py")):
            rel = py.relative_to(root).as_posix()
            self.files[rel] = sha(py)
            text = py.read_text(encoding="utf-8", errors="replace")
            names = defined_names(text)
            self.defs_by_file[rel] = names
            self.defs |= names
            self.tokens |= set(IDENT_RE.findall(text))

    def covers(self) -> bool:
        return self.has_package

    def basenames(self, name: str) -> list[str]:
        return [rel for rel in self.files if rel.rsplit("/", 1)[-1] == name]

    def module_targets(self, dotted: str) -> list[str]:
        """Candidate on-disk targets for a dotted module path."""
        rel = dotted.replace(".", "/")
        out = [f"{rel}.py", f"{rel}/__init__.py"]
        return [p for p in out if p in self.files]


def extract(skill_md: Path, file_re: re.Pattern, module_re: re.Pattern) -> dict:
    text = skill_md.read_text(encoding="utf-8")
    files: dict[str, set[str]] = {}
    for path, symbol in file_re.findall(text):
        files.setdefault(path, set())
        if symbol:
            files[path].add(symbol.split(".")[-1])
    modules = set(module_re.findall(text))

    idents: set[str] = set()
    for raw in BACKTICK_RE.findall(text):
        token = raw.strip().rstrip("()")
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token):
            idents.add(token)
        elif re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", token):
            idents.add(token.rsplit(".", 1)[-1])
    for fence in FENCE_RE.findall(text):
        idents |= set(IDENT_RE.findall(fence))

    idents = {
        i for i in idents
        if i not in STOPWORDS
        and len(i) >= 4
        and ("_" in i or (i[:1].isupper() and any(c.islower() for c in i)))
    }
    return {"files": files, "modules": modules, "idents": idents}


def audit(skill_md: Path, old: Tree, new: Tree, file_re: re.Pattern, module_re: re.Pattern) -> dict:
    cited = extract(skill_md, file_re, module_re)
    report: dict = {
        "skill": skill_md.parent.name,
        "files": [],
        "modules": [],
        "symbols": [],
        "unknown": [],
    }

    if not (old.covers() and new.covers()):
        report["files"].append({
            "path": "(module prefix)", "state": "NO_TREE",
            "hint": "the given trees do not contain the module prefix at all — check --module-prefix and the tree paths",
        })
        return report

    for path, symbols in sorted(cited["files"].items()):
        in_old, in_new = path in old.files, path in new.files
        if in_old and in_new:
            state = "UNCHANGED" if old.files[path] == new.files[path] else "CHANGED"
            hint = ""
        elif in_old and not in_new:
            moved = new.basenames(path.rsplit("/", 1)[-1])
            state = "MOVED_OR_DELETED"
            hint = f"same basename now at: {', '.join(moved)}" if moved else "no file with that basename in the new tree"
        elif not in_old and in_new:
            state = "ADDED_AFTER"
            hint = "path exists only in the new tree — the citation predates it or was written against another version"
        else:
            state = "BROKEN"
            hint = "path in neither tree — bad citation, likely hallucinated"
        report["files"].append({"path": path, "state": state, "hint": hint})

        for sym in sorted(symbols):
            report["symbols"].append(classify_symbol(sym, path, old, new))

    for dotted in sorted(cited["modules"]):
        leaf = dotted.rsplit(".", 1)[-1]
        if leaf.startswith("__") and leaf.endswith("__"):
            continue  # `<prefix>.__file__` and friends are snippets, not modules
        o, n = old.module_targets(dotted), new.module_targets(dotted)
        if not o and not n:
            # Not a module: most likely a symbol re-exported from the parent package.
            parent = dotted.rsplit(".", 1)[0]
            entry = classify_symbol(leaf, None, old, new)
            entry["hint"] = f"resolved as a symbol re-exported from {parent}; {entry['hint']}".strip("; ")
            report["symbols"].append(entry)
            continue
        if o and n:
            changed = any(old.files[p] != new.files[p] for p in n if p in old.files)
            state = "CHANGED" if changed else "UNCHANGED"
        elif o and not n:
            state = "MOVED_OR_DELETED"
        else:
            state = "ADDED_AFTER"
        report["modules"].append({"module": dotted, "state": state, "targets": n or o})

    cited_syms = {s["symbol"] for s in report["symbols"]}
    unknown: list[str] = []
    for ident in sorted(cited["idents"]):
        if ident in cited_syms:
            continue
        entry = classify_symbol(ident, None, old, new)
        if entry["state"] == "UNKNOWN":
            unknown.append(ident)
        else:
            report["symbols"].append(entry)
    report["unknown"] = unknown
    report["symbols"].sort(key=lambda s: (s["state"], s["symbol"]))
    return report


def classify_symbol(sym: str, path: str | None, old: Tree, new: Tree) -> dict:
    in_old, in_new = sym in old.defs, sym in new.defs
    if not in_old and not in_new:
        return {"symbol": sym, "path": path, "state": "UNKNOWN",
                "hint": "not defined in either tree — not a framework symbol, or a bad citation"}
    if not in_old and in_new:
        return {"symbol": sym, "path": path, "state": "ADDED_AFTER",
                "hint": "new in the target version"}
    if in_old and not in_new:
        state = "REMOVED" if sym not in new.tokens else "MOVED"
        hint = ("no definition and no textual occurrence left in the new tree"
                if state == "REMOVED" else "definition gone but the name still occurs — renamed, re-exported or now imported")
        return {"symbol": sym, "path": path, "state": state, "hint": hint}
    if path and path in new.files and path in old.files:
        if sym in old.defs_by_file.get(path, set()) and sym not in new.defs_by_file.get(path, set()):
            where = [p for p, names in new.defs_by_file.items() if sym in names]
            return {"symbol": sym, "path": path, "state": "MOVED",
                    "hint": f"no longer defined in the cited file; now in: {', '.join(where[:5]) or 'unknown'}"}
    return {"symbol": sym, "path": path, "state": "OK", "hint": ""}


def render(reports: list[dict], old: Tree, new: Tree, strict: bool) -> str:
    out: list[str] = [f"# Citation audit — {old.label} -> {new.label}", ""]
    interesting_files: set[str] = set()
    problems = 0

    for rep in reports:
        rows_f = [f for f in rep["files"] if f["state"] not in {"UNCHANGED"}]
        rows_m = [m for m in rep["modules"] if m["state"] != "UNCHANGED"]
        rows_s = [s for s in rep["symbols"] if s["state"] != "OK"]
        clean = not rows_f and not rows_m and not rows_s and not (strict and rep["unknown"])
        out.append(f"## {rep['skill']} — {'clean' if clean else 'needs review'}")
        out.append("")
        if clean:
            out.append(f"{len(rep['files'])} cited files, {len(rep['symbols'])} checked symbols: no change.")
            out.append("")
            continue
        if rows_f:
            out.append("| cited file | state | note |")
            out.append("|---|---|---|")
            for f in rows_f:
                out.append(f"| `{f['path']}` | {f['state']} | {f['hint']} |")
                if f["state"] == "CHANGED":
                    interesting_files.add(f["path"])
                elif f["state"] != "NO_TREE":
                    problems += 1
            out.append("")
        if rows_m:
            out.append("| cited module | state | resolves to |")
            out.append("|---|---|---|")
            for m in rows_m:
                out.append(f"| `{m['module']}` | {m['state']} | {', '.join(m['targets']) or '-'} |")
                interesting_files.update(m["targets"])
                if m["state"] not in {"CHANGED", "NO_TREE"}:
                    problems += 1
            out.append("")
        if rows_s:
            out.append("| symbol | cited in | state | note |")
            out.append("|---|---|---|---|")
            for s in rows_s:
                out.append(f"| `{s['symbol']}` | {s['path'] or '-'} | {s['state']} | {s['hint']} |")
                problems += 1
            out.append("")
        if strict and rep["unknown"]:
            out.append(f"Unverifiable identifiers (not defined in either tree): {', '.join('`%s`' % u for u in rep['unknown'])}")
            out.append("")

    out.append("## Diffs to read")
    out.append("")
    if interesting_files:
        out.append("Cited files whose content changed — read these diffs before trusting the skills:")
        out.append("")
        for path in sorted(interesting_files):
            out.append(f"- `{path}`")
    else:
        out.append("No cited file changed between the two trees.")
    out.append("")
    out.append(f"**{problems} finding(s) beyond plain content changes; {len(interesting_files)} changed cited file(s).**")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--module-prefix", required=True,
                     help="dotted import path of the framework's top package, e.g. google.adk or requests")
    ap.add_argument("--old", required=True, type=Path, action="append",
                     help="tree of the version the skills were written against (repeatable); "
                          "pass the same path as --new for a self-check of a freshly drafted batch")
    ap.add_argument("--new", required=True, type=Path, action="append",
                     help="tree of the target version (repeatable)")
    ap.add_argument("--skills-dir", required=True, type=Path,
                     help="directory holding the skill folders to audit")
    ap.add_argument("--skill", action="append", default=[], help="restrict to these skill names (repeatable)")
    ap.add_argument("--pattern", default="*", help="glob for skill folders under --skills-dir (default: *)")
    ap.add_argument("--strict", action="store_true", help="also list identifiers not defined in either tree")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    args = ap.parse_args()

    file_re, module_re, top_dir = build_patterns(args.module_prefix)
    old = Tree(args.old, ", ".join(p.name for p in args.old), top_dir)
    new = Tree(args.new, ", ".join(p.name for p in args.new), top_dir)

    skills_dir = args.skills_dir.expanduser().resolve()
    folders = sorted(p for p in skills_dir.glob(args.pattern) if (p / "SKILL.md").is_file())
    if args.skill:
        wanted = set(args.skill)
        folders = [p for p in folders if p.name in wanted]
    if not folders:
        raise SystemExit(f"error: no SKILL.md found under {skills_dir}/{args.pattern}")

    reports = [audit(p / "SKILL.md", old, new, file_re, module_re) for p in folders]
    if args.json:
        json.dump(
            {"old": [str(r) for r in old.roots], "new": [str(r) for r in new.roots], "reports": reports},
            sys.stdout, indent=2,
        )
        print()
    else:
        print(render(reports, old, new, args.strict))


if __name__ == "__main__":
    main()
