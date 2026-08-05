#!/usr/bin/env python3
"""Keep Kilo Code and Claude Code agent/skill definitions aligned.

See ../SKILL.md for the design rationale (why skills are symlinked but
agents are generated bidirectionally with per-side frontmatter preserved).
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import sys

FRONTMATTER_RE = re.compile(r'^---\n(.*?)\n---\n?(.*)$', re.DOTALL)

DEFAULT_CLAUDE_TOOLS = ['tools: Bash, Read, Edit, Write, Grep, Glob, WebFetch, WebSearch']
DEFAULT_KILO_META = ['mode: primary', 'model: google/gemini-3.5-flash', 'steps: 30']


def find_git_root(start):
    p = start.resolve()
    for parent in [p] + list(p.parents):
        if (parent / '.git').exists():
            return parent
    return None


# ---------- skills: single source of truth via symlink ----------

def add_missing_frontmatter(skills_dir):
    for skill_md in sorted(skills_dir.glob('*/SKILL.md')):
        text = skill_md.read_text()
        if text.lstrip().startswith('---'):
            continue
        name = skill_md.parent.name
        desc_lines, started = [], False
        for line in text.split('\n'):
            s = line.strip()
            if not s:
                if started:
                    break
                continue
            if s.startswith('#'):
                continue
            desc_lines.append(s)
            started = True
        description = ' '.join(desc_lines)[:300] or f'{name} skill'
        skill_md.write_text(f'---\nname: {name}\ndescription: {description}\n---\n\n{text}')
        print(f'[skills] added frontmatter to {skill_md}')


def ensure_skills_symlink(root):
    kilo_singular = root / '.kilo' / 'skill'
    kilo_dir = root / '.kilo' / 'skills'
    if kilo_singular.is_dir() and not kilo_singular.is_symlink() and not kilo_dir.exists():
        kilo_singular.rename(kilo_dir)
        print(f'[skills] renamed {kilo_singular} -> {kilo_dir}')

    claude_parent = root / '.claude'
    claude_dir = claude_parent / 'skills'

    if claude_dir.is_symlink():
        if claude_dir.resolve() == kilo_dir.resolve():
            add_missing_frontmatter(kilo_dir)
            return
        claude_dir.unlink()

    if claude_dir.is_dir():
        kilo_dir.mkdir(parents=True, exist_ok=True)
        for entry in list(claude_dir.iterdir()):
            if entry.is_symlink():
                entry.unlink()
                continue
            target = kilo_dir / entry.name
            if target.exists():
                print(f"[skills] WARNING: '{entry.name}' exists on both sides, keeping {target}, "
                      f"leaving {entry} in place for manual merge")
                continue
            entry.rename(target)
        remaining = list(claude_dir.iterdir())
        if remaining:
            print(f'[skills] WARNING: {claude_dir} not fully merged ({len(remaining)} conflicting '
                  f'entries left); symlink NOT created')
            return
        claude_dir.rmdir()

    if not kilo_dir.exists():
        return
    add_missing_frontmatter(kilo_dir)
    claude_parent.mkdir(parents=True, exist_ok=True)
    rel = os.path.relpath(kilo_dir, claude_parent)
    claude_dir.symlink_to(rel, target_is_directory=True)
    print(f'[skills] linked {claude_dir} -> {kilo_dir}')


# ---------- agents: bidirectional generation with hash-based drift detection ----------

def read_md(path):
    if not path or not path.exists():
        return None
    text = path.read_text()
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {'other_lines': [], 'body': text, 'description': ''}
    raw, body = m.group(1), m.group(2)
    description, other = '', []
    for line in raw.split('\n'):
        if not line.strip():
            continue
        key = line.split(':', 1)[0].strip().lower()
        if key == 'description':
            description = line.split(':', 1)[1].strip()
        elif key == 'name':
            continue  # regenerated from filename
        else:
            other.append(line)
    return {'other_lines': other, 'body': body, 'description': description}


def content_hash(parsed):
    return hashlib.sha256((parsed['description'] + '\x00' + parsed['body']).encode()).hexdigest()


def write_md(path, name_field, description, other_lines, body):
    fm = (['name: ' + name_field] if name_field else []) + [f'description: {description}'] + other_lines
    path.write_text('---\n' + '\n'.join(fm) + '\n---\n' + body)


def sync_agents(root):
    kilo_dir = root / '.kilo' / 'agent'
    claude_dir = root / '.claude' / 'agents'
    if not kilo_dir.exists() and not claude_dir.exists():
        return

    state_path = root / '.kilo-claude-sync-state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    dirty = False

    names = set()
    if kilo_dir.exists():
        names |= {p.stem for p in kilo_dir.glob('*.md')}
    if claude_dir.exists():
        names |= {p.stem for p in claude_dir.glob('*.md')}

    for name in sorted(names):
        kpath, cpath = kilo_dir / f'{name}.md', claude_dir / f'{name}.md'
        k, c = read_md(kpath), read_md(cpath)
        st = state.get(name, {})
        k_hash = content_hash(k) if k else None
        c_hash = content_hash(c) if c else None
        k_changed = k is not None and st.get('kilo_hash') != k_hash
        c_changed = c is not None and st.get('claude_hash') != c_hash

        if k and not c:
            claude_dir.mkdir(parents=True, exist_ok=True)
            write_md(cpath, name, k['description'], DEFAULT_CLAUDE_TOOLS, k['body'])
            print(f'[agents] created {cpath} from {kpath}')
        elif c and not k:
            kilo_dir.mkdir(parents=True, exist_ok=True)
            write_md(kpath, None, c['description'], DEFAULT_KILO_META, c['body'])
            print(f'[agents] created {kpath} from {cpath}')
        elif k_changed and c_changed:
            if k_hash != c_hash:
                print(f"[agents] CONFLICT: '{name}' edited on both sides since last sync — resolve "
                      f'manually, then re-run.')
                continue
            # identical content on both sides (e.g. installed by kilo-plugin-manager):
            # fall through to record state
        elif k_changed:
            write_md(cpath, name, k['description'], st.get('claude_only_lines') or DEFAULT_CLAUDE_TOOLS, k['body'])
            print(f"[agents] synced '{name}' kilo -> claude")
        elif c_changed:
            write_md(kpath, None, c['description'], st.get('kilo_only_lines') or DEFAULT_KILO_META, c['body'])
            print(f"[agents] synced '{name}' claude -> kilo")
        else:
            continue

        k, c = read_md(kpath), read_md(cpath)
        state[name] = {
            'kilo_hash': content_hash(k), 'claude_hash': content_hash(c),
            'kilo_only_lines': k['other_lines'], 'claude_only_lines': c['other_lines'],
        }
        dirty = True

    if dirty:
        state_path.write_text(json.dumps(state, indent=2) + '\n')


def main():
    ap = argparse.ArgumentParser(description='Sync agents/skills between Kilo Code and Claude Code')
    ap.add_argument('--scope', choices=['local', 'global', 'both'], default='both')
    ap.add_argument('--repo', default='.')
    args = ap.parse_args()

    roots = []
    if args.scope in ('local', 'both'):
        git_root = find_git_root(pathlib.Path(args.repo))
        if git_root:
            roots.append(('local', git_root))
        else:
            print('no git repo found for local scope, skipping', file=sys.stderr)
    if args.scope in ('global', 'both'):
        roots.append(('global', pathlib.Path.home()))

    for label, root in roots:
        print(f'== {label}: {root} ==')
        ensure_skills_symlink(root)
        sync_agents(root)


if __name__ == '__main__':
    main()
