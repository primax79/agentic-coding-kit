#!/usr/bin/env python3
"""Keep Kilo Code and Claude Code *agent* definitions aligned.

Agents are the only thing that genuinely needs this: each host demands its own
frontmatter shape (Kilo's `mode`/`model`/`steps`/`color`, Claude's `tools`), so
the shared description and body have to be regenerated on both sides.

Skills are deliberately no longer synced. Both hosts install them natively -
Claude Code through a marketplace plus `enabledPlugins`, Kilo through
`.kilo/skills` - and mirroring one directory into the other produced copies that
neither host's own tooling declared, so nothing updated them and nothing
reported them stale. `sync_skills()` below is kept only to migrate a repo away
from that arrangement; it is no longer called. See ../SKILL.md.
"""
import argparse
import hashlib
import json
import pathlib
import re
import shutil
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


# ---------- skills: bidirectional copy with tree-hash drift detection ----------
#
# Each <name>/ under .kilo/skills and .claude/skills can hold more than
# SKILL.md (scripts/, references/, assets/), so the unit of sync is the
# whole directory tree, hashed and copied wholesale — same conflict model
# as sync_agents(), generalized from one file to a tree.

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


def tree_hash(dir_path):
    if not dir_path.is_dir():
        return None
    h = hashlib.sha256()
    for f in sorted(p for p in dir_path.rglob('*') if p.is_file()):
        h.update(f.relative_to(dir_path).as_posix().encode() + b'\x00')
        h.update(f.read_bytes())
    return h.hexdigest()


def copy_tree(src, dst):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def migrate_legacy_symlink(dir_path):
    if dir_path.is_symlink():
        target = dir_path.resolve()
        dir_path.unlink()
        print(f'[skills] migrated legacy symlink {dir_path} (was -> {target}) to a real directory')


def sync_skills(root):
    kilo_singular = root / '.kilo' / 'skill'
    kilo_dir = root / '.kilo' / 'skills'
    if kilo_singular.is_dir() and not kilo_singular.is_symlink() and not kilo_dir.exists():
        kilo_singular.rename(kilo_dir)
        print(f'[skills] renamed {kilo_singular} -> {kilo_dir}')

    claude_dir = root / '.claude' / 'skills'
    migrate_legacy_symlink(claude_dir)
    migrate_legacy_symlink(kilo_dir)

    if not kilo_dir.exists() and not claude_dir.exists():
        return

    if kilo_dir.exists():
        add_missing_frontmatter(kilo_dir)
    if claude_dir.exists():
        add_missing_frontmatter(claude_dir)

    state_path = root / '.kilo-claude-sync-state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    skills_state = state.setdefault('skills', {})
    dirty = False

    names = set()
    if kilo_dir.exists():
        names |= {p.name for p in kilo_dir.iterdir() if p.is_dir()}
    if claude_dir.exists():
        names |= {p.name for p in claude_dir.iterdir() if p.is_dir()}

    for name in sorted(names):
        kpath, cpath = kilo_dir / name, claude_dir / name
        k_hash, c_hash = tree_hash(kpath), tree_hash(cpath)
        st = skills_state.get(name, {})
        k_changed = k_hash is not None and st.get('kilo_hash') != k_hash
        c_changed = c_hash is not None and st.get('claude_hash') != c_hash

        if k_hash is not None and c_hash is None:
            copy_tree(kpath, cpath)
            print(f"[skills] created '{name}' claude <- kilo")
        elif c_hash is not None and k_hash is None:
            copy_tree(cpath, kpath)
            print(f"[skills] created '{name}' kilo <- claude")
        elif k_changed and c_changed:
            if k_hash != c_hash:
                print(f"[skills] CONFLICT: '{name}' edited on both sides since last sync — resolve "
                      f'manually, then re-run.')
                continue
        elif k_changed:
            copy_tree(kpath, cpath)
            print(f"[skills] synced '{name}' kilo -> claude")
        elif c_changed:
            copy_tree(cpath, kpath)
            print(f"[skills] synced '{name}' claude -> kilo")
        else:
            continue

        skills_state[name] = {'kilo_hash': tree_hash(kpath), 'claude_hash': tree_hash(cpath)}
        dirty = True

    if dirty:
        state_path.write_text(json.dumps(state, indent=2) + '\n')


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
    # Ensure description is safely quoted for older Kilo YAML parser compatibility
    # Kilo 7.4.5 fails on block scalars and escaped double quotes
    desc_clean = description.strip()
    # Remove outer quotes if present
    if desc_clean.startswith('"') and desc_clean.endswith('"'):
        desc_clean = desc_clean[1:-1]
    if desc_clean.startswith("'") and desc_clean.endswith("'"):
        desc_clean = desc_clean[1:-1]
    
    # Replace any internal double quotes with backticks to avoid escaping `\"` which breaks Kilo
    desc_clean = desc_clean.replace('\\"', '`').replace('"', '`')
    
    # Force single line
    desc_clean = ' '.join(line.strip() for line in desc_clean.split('\n') if line.strip())
    
    fm = (['name: ' + name_field] if name_field else []) + [f'description: "{desc_clean}"'] + other_lines
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
        sync_agents(root)


if __name__ == '__main__':
    main()
