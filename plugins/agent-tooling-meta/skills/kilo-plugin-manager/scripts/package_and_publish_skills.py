#!/usr/bin/env python3
"""Package this repo's skills as .tar.gz and publish them to a GitHub
Release via `gh`, so the URLs generate_skill_marketplace.py (in this same
directory) computed actually resolve.

Ported from Kilo-Org/kilo-marketplace's .github/workflows/package-skills.yml,
adapted to run locally on demand instead of in CI. Same dual-tag scheme:

- `skills-<UTC timestamp>-<short sha>`: immutable snapshot, kept forever -
  real version history, browsable/restorable on GitHub, even though no
  per-item version field exists in the feed (see kilo-plugin-manager's
  SKILL.md for why that field would currently be inert - the official
  installer has no update-in-place logic to read it).
- `skills-latest`: rolling tag, overwritten (`--clobber`) every run - this
  is the one the generated marketplace feed's `content` URLs point at.

Requires `gh` authenticated with push access to the repo (`gh auth status`).

Usage: python3 package_and_publish_skills.py <repo-root> [--dry-run]
"""
import argparse
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

EXCLUDE_NAMES = {"__pycache__", ".DS_Store"}


def die(msg):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def find_skills(repo_root):
    return sorted(repo_root.glob("plugins/*/skills/*/SKILL.md"))


def run(cmd, cwd=None, check=True):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        die(f"{' '.join(cmd)} failed:\n{result.stderr.strip()}")
    return result


def git_head_sha(repo_root, short=False):
    args = ["git", "-C", str(repo_root), "rev-parse"] + (["--short"] if short else []) + ["HEAD"]
    return run(args).stdout.strip()


def skip_junk(tarinfo):
    if any(part in EXCLUDE_NAMES or part.startswith(".") for part in Path(tarinfo.name).parts):
        return None
    return tarinfo


def package(repo_root, dist_dir):
    dist_dir.mkdir(parents=True, exist_ok=True)
    tarballs = []
    for skill_md in find_skills(repo_root):
        skill_dir = skill_md.parent
        skill_id = skill_dir.name
        tarball = dist_dir / f"{skill_id}.tar.gz"
        with tarfile.open(tarball, "w:gz") as tar:
            tar.add(skill_dir, arcname=skill_id, filter=skip_junk)
        tarballs.append(tarball)
        print(f"Packaged: {tarball.name} ({tarball.stat().st_size} bytes)")
    return tarballs


def gh_release_publish(repo_root, tag, tarballs, title, notes, dry_run):
    upload_cmd = ["gh", "release", "upload", tag, *(str(t) for t in tarballs), "--clobber"]
    create_cmd = ["gh", "release", "create", tag, *(str(t) for t in tarballs), "--title", title, "--notes", notes]

    if dry_run:
        print(f"[dry-run] {' '.join(upload_cmd)}")
        print(f"[dry-run]   (falls back to: {' '.join(create_cmd)} if tag doesn't exist yet)")
        return

    upload = run(upload_cmd, cwd=repo_root, check=False)
    if upload.returncode != 0:
        run(create_cmd, cwd=repo_root)
    print(f"Published tag '{tag}'.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("repo_root", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="package locally, print gh commands, publish nothing")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    if not repo_root.is_dir():
        die(f"not a directory: {repo_root}")

    dist_dir = repo_root / "dist" / "skills"
    tarballs = package(repo_root, dist_dir)
    if not tarballs:
        print("No skills found under plugins/*/skills/ - nothing to publish.")
        shutil.rmtree(dist_dir, ignore_errors=True)
        return

    sha = git_head_sha(repo_root)
    sha_short = git_head_sha(repo_root, short=True)
    date = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    dated_tag = f"skills-{date}-{sha_short}"

    gh_release_publish(
        repo_root, dated_tag, tarballs,
        title=f"Skills Release {date}",
        notes=f"Automated skills release from commit {sha}",
        dry_run=args.dry_run,
    )
    gh_release_publish(
        repo_root, "skills-latest", tarballs,
        title="Latest Skills",
        notes="Latest packaged skills. Updated automatically.",
        dry_run=args.dry_run,
    )

    shutil.rmtree(dist_dir, ignore_errors=True)
    if not args.dry_run:
        print(f"Published {len(tarballs)} skills to '{dated_tag}' and 'skills-latest'.")


if __name__ == "__main__":
    main()
