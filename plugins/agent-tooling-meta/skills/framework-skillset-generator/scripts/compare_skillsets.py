#!/usr/bin/env python3
"""Compare a freshly generated skillset against an existing/ground-truth one.

New script, not present in adk-agentic-coding-kit — that repo never needed
this because it only ever went one direction (hand-write once). This is the
piece framework-skillset-generator's validation runs need: given two
skill-directory paths, produce a coverage table (skill names + one-line
scope, flagged matched/missing/extra on each side) and structural stats
(line counts, frontmatter completeness). No semantic content diffing — a
script can't judge whether two differently-named skills cover the same
concept, or whether one's technical content is actually better; that's left
to the human/LLM reading this report side by side with both batches.

Citation validity is deliberately NOT run from here: run
``check_citations.py`` separately against each batch with its own
``--module-prefix`` and tree — this script only orients the reader, it
doesn't re-implement that check.

Usage::

    compare_skillsets.py --generated /tmp/generated-batch \\
        --existing adk-agentic-coding-kit/plugins/adk-tools/skills
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def parse_frontmatter(skill_md: Path) -> dict:
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    out = {"name": None, "description": None, "has_metadata": False, "line_count": len(text.splitlines())}
    if not text.startswith("---"):
        return out
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return out
    fm = match.group(1)
    name_match = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
    if name_match:
        out["name"] = name_match.group(1).strip()
    desc_match = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
    if desc_match:
        out["description"] = desc_match.group(1).strip()
    out["has_metadata"] = "metadata:" in fm
    return out


def scan_skills(root: Path) -> dict[str, dict]:
    skills = {}
    for skill_md in sorted(root.rglob("SKILL.md")):
        info = parse_frontmatter(skill_md)
        name = info["name"] or skill_md.parent.name
        skills[name] = {**info, "path": str(skill_md.parent.relative_to(root))}
    return skills


def one_line(description: str | None, width: int = 100) -> str:
    if not description:
        return "(no description)"
    description = " ".join(description.split())
    return description[:width] + ("…" if len(description) > width else "")


def render(generated: dict[str, dict], existing: dict[str, dict]) -> str:
    all_names = sorted(set(generated) | set(existing))
    out = ["# Skillset comparison", ""]
    out.append(f"Generated: {len(generated)} skills. Existing (ground truth): {len(existing)} skills.")
    out.append("")
    out.append("## Coverage")
    out.append("")
    out.append("| skill | in generated | in existing | scope (whichever side has it; generated wins if both) |")
    out.append("|---|---|---|---|")
    matched = missing = extra = 0
    for name in all_names:
        g, e = generated.get(name), existing.get(name)
        if g and e:
            matched += 1
            flag_g, flag_e = "yes", "yes"
        elif e and not g:
            missing += 1
            flag_g, flag_e = "**missing**", "yes"
        else:
            extra += 1
            flag_g, flag_e = "yes", "**extra**"
        scope = one_line((g or e)["description"])
        out.append(f"| `{name}` | {flag_g} | {flag_e} | {scope} |")
    out.append("")
    out.append(f"**{matched} matched, {missing} missing from generated (present only in existing), "
                f"{extra} extra in generated (not in existing).**")
    out.append("")

    out.append("## Structural stats")
    out.append("")
    out.append("| skill | source | lines | has name | has description | has metadata |")
    out.append("|---|---|---|---|---|---|")
    for name in all_names:
        for label, batch in (("generated", generated), ("existing", existing)):
            info = batch.get(name)
            if not info:
                continue
            out.append(
                f"| `{name}` | {label} | {info['line_count']} | "
                f"{'yes' if info['name'] else 'no'} | {'yes' if info['description'] else 'no'} | "
                f"{'yes' if info['has_metadata'] else 'no'} |"
            )
    out.append("")
    out.append(
        "Reminder: run `check_citations.py` separately against each batch's own "
        "materialized tree to check citation validity — this report only orients, "
        "it does not re-verify claims."
    )
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--generated", required=True, type=Path, help="directory holding the freshly generated skill folders")
    ap.add_argument("--existing", required=True, type=Path, help="directory holding the existing/ground-truth skill folders")
    args = ap.parse_args()

    generated_root = args.generated.expanduser().resolve()
    existing_root = args.existing.expanduser().resolve()
    if not generated_root.is_dir():
        sys.exit(f"error: {generated_root} is not a directory")
    if not existing_root.is_dir():
        sys.exit(f"error: {existing_root} is not a directory")

    generated = scan_skills(generated_root)
    existing = scan_skills(existing_root)
    if not generated:
        print(f"warning: no SKILL.md found under {generated_root}", file=sys.stderr)
    if not existing:
        print(f"warning: no SKILL.md found under {existing_root}", file=sys.stderr)

    print(render(generated, existing))


if __name__ == "__main__":
    main()
