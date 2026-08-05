#!/usr/bin/env python3
"""Generate a marketplace feed of this repo's skills, in the shape Kilo's
official marketplace API serves per skill (id, description, category,
githubUrl, content|files) - as JSON, since the client's parseResponse()
tries JSON.parse() first and only falls back to YAML (see kilocode's
packages/kilo-vscode/src/services/marketplace/api.ts).

Ported from Kilo-Org/kilo-marketplace's bin/generate-skill-marketplace.ts,
adapted for this family of repos' `plugins/<plugin>/skills/<skill>/` layout
(the official repo has a flat `skills/` root; these are multi-plugin).

Two output modes, matching the two install paths Kilo's installer.ts
supports for a skill item (see its installSkill()):

- `--mode tarball` (default): `content` = a GitHub Release asset URL. Does
  NOT exist until package_and_publish_skills.py (in this same directory)
  has actually published it - run that after generating, or the URLs 404.
- `--mode files`: `files` = a flat list of paths relative to each skill's
  directory, fetched individually from raw.githubusercontent.com by
  installer.ts's downloadSkillFiles(). No packaging/release step at all -
  the files just need to exist wherever githubUrl points once this JSON is
  pushed. Simpler to author, no `gh` dependency, but N small requests per
  install instead of one compressed download.

Usage: python3 generate_skill_marketplace.py <repo-root> [--output PATH] [--mode tarball|files] [--tag skills-latest]
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from plugin_manager import parse_fm  # noqa: E402 - reuse the existing frontmatter parser

DEFAULT_TAG = "skills-latest"
EXCLUDE_NAMES = {"__pycache__", ".DS_Store"}


def die(msg):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def git_remote_owner_repo(repo_root):
    result = subprocess.run(
        ["git", "-C", str(repo_root), "remote", "get-url", "origin"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        die(f"could not read git remote 'origin' in {repo_root}: {result.stderr.strip()}")
    url = result.stdout.strip()
    # Matches both git@github.com:owner/repo.git and https://github.com/owner/repo.git
    m = re.search(r"github\.com[:/]([^/]+)/([^/.]+?)(?:\.git)?$", url)
    if not m:
        die(f"could not parse GitHub owner/repo from remote URL: {url}")
    return m.group(1), m.group(2)


def find_skills(repo_root):
    return sorted(repo_root.glob("plugins/*/skills/*/SKILL.md"))


def dequote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def list_skill_files(skill_dir):
    files = []
    for path in sorted(skill_dir.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(skill_dir)
        if any(part in EXCLUDE_NAMES or part.startswith(".") for part in rel.parts):
            continue
        files.append(rel.as_posix())
    return files


def build_items(repo_root, owner, repo, mode, tag):
    items = []
    seen = {}
    for skill_md in find_skills(repo_root):
        skill_dir = skill_md.parent
        plugin_dir = skill_dir.parent.parent
        skill_id = skill_dir.name
        category = plugin_dir.name

        fields, _ = parse_fm(skill_md.read_text())
        name = dequote(fields.get("name", ""))
        description = dequote(fields.get("description", ""))

        if name != skill_id:
            die(f"{skill_md}: frontmatter name '{name}' must match directory name '{skill_id}'")
        if not description:
            die(f"{skill_md}: missing description")
        if skill_id in seen:
            die(f"duplicate skill id '{skill_id}': {seen[skill_id]} and {skill_md}")
        seen[skill_id] = skill_md

        rel = skill_dir.relative_to(repo_root).as_posix()
        item = {
            "id": skill_id,
            "description": description,
            "category": category,
            "githubUrl": f"https://github.com/{owner}/{repo}/tree/main/{rel}",
        }
        if mode == "files":
            item["files"] = list_skill_files(skill_dir)
        else:
            item["content"] = f"https://github.com/{owner}/{repo}/releases/download/{tag}/{skill_id}.tar.gz"
        items.append(item)

    items.sort(key=lambda i: (i["category"], i["id"]))
    return items


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("repo_root", type=Path)
    parser.add_argument("--output", type=Path, default=None, help="default: <repo-root>/marketplace-skills.json")
    parser.add_argument("--mode", choices=["tarball", "files"], default="tarball")
    parser.add_argument("--tag", default=DEFAULT_TAG, help="release tag the 'content' URLs point at (--mode tarball only)")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    if not repo_root.is_dir():
        die(f"not a directory: {repo_root}")

    owner, repo = git_remote_owner_repo(repo_root)
    items = build_items(repo_root, owner, repo, args.mode, args.tag)

    output = args.output or (repo_root / "marketplace-skills.json")
    output.write_text(json.dumps({"items": items}, indent=2) + "\n")
    categories = {i["category"] for i in items}
    print(f"Generated {output} with {len(items)} skills across {len(categories)} categories")


if __name__ == "__main__":
    main()
