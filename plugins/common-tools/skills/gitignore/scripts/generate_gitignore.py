#!/usr/bin/env python3
"""
gitignore script
Generates and applies .gitignore files using the gitignore.io (Toptal) API based on project detection.
"""

import os
import sys
import argparse
import urllib.request
import urllib.error
import json
import platform

API_BASE_URL = "https://www.toptal.com/developers/gitignore/api"

def get_available_templates():
    """Fetch all valid template names from the gitignore.io API."""
    url = f"{API_BASE_URL}/list?format=lines"
    req = urllib.request.Request(url, headers={"User-Agent": "gitignore/1.0"})
    try:
        with urllib.request.urlopen(req) as response:
            content = response.read().decode("utf-8")
            return set(line.strip().lower() for line in content.splitlines() if line.strip())
    except Exception as e:
        print(f"Warning: Could not fetch template list from API ({e}). Proceeding without validation.", file=sys.stderr)
        return None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "config", "templates.json"))

def load_config():
    """Load template configuration from config/templates.json without hardcoded fallbacks."""
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                base = set(data.get("mandatory_base_templates", []))
                custom = data.get("custom_templates", {})
                default_keys = set(data.get("default_custom_keys", []))
                standard_det = data.get("standard_templates_detection", {})
                global_additional = data.get("additional_rules", [])
                global_removed = data.get("removed_rules", [])
                return base, custom, default_keys, standard_det, global_additional, global_removed
        except Exception as e:
            print(f"Error: Failed to load config from {CONFIG_FILE} ({e}).", file=sys.stderr)
            sys.exit(1)
            
    print(f"Error: Configuration file not found at {CONFIG_FILE}.", file=sys.stderr)
    sys.exit(1)

MANDATORY_BASE_TEMPLATES, CUSTOM_TEMPLATES, DEFAULT_CUSTOM_KEYS, STANDARD_TEMPLATES_DETECTION, GLOBAL_ADDITIONAL_RULES, GLOBAL_REMOVED_RULES = load_config()

def detect_templates(project_dir, include_base=True, include_custom=True):
    """Detect appropriate gitignore templates for the project directory using declarative detection rules."""
    api_templates = set()
    custom_templates = set()
    
    # 1. Mandatory OS & IDE base templates
    if include_base:
        api_templates.update(MANDATORY_BASE_TEMPLATES)

    # 2. Local Custom Templates & AI Agents
    if include_custom:
        custom_templates.update(DEFAULT_CUSTOM_KEYS)
    else:
        # Declarative detection from custom_templates configuration
        for key, tpl_config in CUSTOM_TEMPLATES.items():
            detect_paths = tpl_config.get("detect_paths", [])
            for p in detect_paths:
                if os.path.exists(os.path.join(project_dir, p)):
                    custom_templates.add(key)
                    break

    # 3. Standard API Templates Declarative Detection
    # Walk directory once to collect existing relative paths and extensions
    existing_paths = set()
    existing_extensions = set()
    
    for root, dirs, files in os.walk(project_dir):
        rel_root = os.path.relpath(root, project_dir)
        rel_depth = rel_root.count(os.sep) if rel_root != "." else 0
        if rel_depth > 2:
            dirs.clear()
            continue
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "target", "dist", "build", "venv", ".venv")]
        
        for d in dirs:
            rel_dir = os.path.normpath(os.path.join(rel_root, d)) if rel_root != "." else d
            existing_paths.add(rel_dir)
            existing_paths.add(d.lower())
            
        for f in files:
            rel_file = os.path.normpath(os.path.join(rel_root, f)) if rel_root != "." else f
            existing_paths.add(rel_file)
            existing_paths.add(f.lower())
            ext = os.path.splitext(f)[1].lower()
            if ext:
                existing_extensions.add(ext)

    # Evaluate standard_templates_detection declaratively
    for tpl_name, det_rules in STANDARD_TEMPLATES_DETECTION.items():
        # Check detect_paths
        for p in det_rules.get("detect_paths", []):
            if p in existing_paths or p.lower() in existing_paths or os.path.exists(os.path.join(project_dir, p)):
                api_templates.add(tpl_name)
                break
        # Check detect_extensions
        if tpl_name not in api_templates:
            for ext in det_rules.get("detect_extensions", []):
                if ext.lower() in existing_extensions:
                    api_templates.add(tpl_name)
                    break

    return api_templates, custom_templates

def render_custom_templates(selected_keys):
    """Render generic local custom templates matching Toptal section format."""
    blocks = []
    keys = set(selected_keys)
    
    # Expand category shortcuts
    if "ai-agents" in keys or "ai" in keys or "ai-tools" in keys:
        for k, v in CUSTOM_TEMPLATES.items():
            if v.get("category") == "ai-agents":
                keys.add(k)
    if "custom" in keys or "all-custom" in keys:
        keys.update(CUSTOM_TEMPLATES.keys())

    for key in sorted(CUSTOM_TEMPLATES.keys()):
        if key in keys:
            tpl = CUSTOM_TEMPLATES[key]
            lines = [f"### {tpl['title']} ###"] + tpl["rules"]
            blocks.append("\n".join(lines))
            
    return "\n\n".join(blocks)

def fetch_gitignore(templates):
    """Fetch combined gitignore content for the given API templates."""
    if not templates:
        return ""
    
    sorted_templates = sorted(list(templates))
    target_str = ",".join(sorted_templates)
    url = f"{API_BASE_URL}/{target_str}"
    
    req = urllib.request.Request(url, headers={"User-Agent": "gitignore/1.0"})
    try:
        with urllib.request.urlopen(req) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"API HTTP Error {e.code}: {e.reason} for templates '{target_str}'")
    except Exception as e:
        raise RuntimeError(f"Failed to fetch gitignore from API: {e}")

def patch_api_content(api_content, selected_api_templates, selected_custom_templates):
    """Patch the fetched API content by removing rules in removed_rules and appending additional_rules."""
    removed_rules = set(GLOBAL_REMOVED_RULES)
    additional_rules = list(GLOBAL_ADDITIONAL_RULES)
    
    # Collect template-level patches
    for tpl in selected_api_templates:
        if tpl in STANDARD_TEMPLATES_DETECTION:
            removed_rules.update(STANDARD_TEMPLATES_DETECTION[tpl].get("removed_rules", []))
            additional_rules.extend(STANDARD_TEMPLATES_DETECTION[tpl].get("additional_rules", []))
            
    for tpl in selected_custom_templates:
        if tpl in CUSTOM_TEMPLATES:
            removed_rules.update(CUSTOM_TEMPLATES[tpl].get("removed_rules", []))
            additional_rules.extend(CUSTOM_TEMPLATES[tpl].get("additional_rules", []))

    if not api_content and not additional_rules:
        return ""

    # Filter out removed_rules
    if removed_rules and api_content:
        lines = api_content.splitlines()
        patched_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped in removed_rules or line in removed_rules:
                patched_lines.append(f"# [Removed by config patch]: {line}")
            else:
                patched_lines.append(line)
        api_content = "\n".join(patched_lines)

    # Append additional_rules
    if additional_rules:
        add_block = "\n".join(additional_rules)
        api_content = f"{api_content.rstrip()}\n\n### Additional Config Rules ###\n{add_block}"

    return api_content

def apply_gitignore(project_dir, new_content, force=False):
    """Write or update .gitignore in project_dir, placing custom existing rules at the top (head)."""
    gitignore_path = os.path.join(project_dir, ".gitignore")
    
    if os.path.exists(gitignore_path) and not force:
        with open(gitignore_path, "r", encoding="utf-8") as f:
            existing_content = f.read()
            
        # Extract custom user rules if the file already contained generated content
        api_marker = "# Created by https://www.toptal.com/developers/gitignore/api/"
        first_custom_marker = None
        for key, tpl in CUSTOM_TEMPLATES.items():
            marker = f"### {tpl['title']} ###"
            if marker in existing_content:
                idx = existing_content.find(marker)
                if first_custom_marker is None or idx < existing_content.find(first_custom_marker):
                    first_custom_marker = marker

        custom_rules = ""
        split_marker = None
        
        if first_custom_marker and existing_content.find(first_custom_marker) != -1:
            split_marker = first_custom_marker
        elif api_marker in existing_content:
            split_marker = api_marker
            
        if split_marker:
            parts = existing_content.split(split_marker, 1)
            custom_part = parts[0].strip()
            if custom_part.startswith("# Custom Project Rules"):
                lines = custom_part.splitlines()[1:]
                custom_part = "\n".join(lines).strip()
            custom_rules = custom_part
        else:
            custom_rules = existing_content.strip()

        if custom_rules:
            print("Preserving existing custom .gitignore entries at the head of the file...")
            final_content = f"# Custom Project Rules\n{custom_rules}\n\n{new_content.strip()}\n"
        else:
            final_content = new_content.strip() + "\n"
            
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write(final_content)
    else:
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write(new_content.strip() + "\n")
            
    print(f"Successfully saved .gitignore to {gitignore_path}")

def main():
    parser = argparse.ArgumentParser(description="Generate and apply .gitignore using gitignore.io API and generic local custom templates")
    parser.add_argument("--dir", default=".", help="Project directory (default: current directory)")
    parser.add_argument("--templates", help="Comma-separated list of templates to include (e.g. java,python,kilo,claude,gcube,local-env)")
    parser.add_argument("--no-base", action="store_true", help="Do not automatically include mandatory base OS/IDE templates")
    parser.add_argument("--no-custom", action="store_true", help="Do not automatically include default custom templates (AI agents, local-env)")
    parser.add_argument("--suggest", action="store_true", help="Auxiliary helper: inspect workspace and output suggested template tags as JSON")
    parser.add_argument("--dry-run", action="store_true", help="Print generated content without writing to .gitignore")
    parser.add_argument("--force", action="store_true", help="Overwrite existing .gitignore completely")
    
    args = parser.parse_args()
    project_dir = os.path.abspath(args.dir)
    
    if not os.path.isdir(project_dir):
        print(f"Error: Directory '{project_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    if args.suggest:
        api_detected, custom_detected = detect_templates(project_dir, include_base=not args.no_base, include_custom=not args.no_custom)
        res = {
            "base_templates": sorted(list(MANDATORY_BASE_TEMPLATES)),
            "custom_templates": sorted(list(custom_detected)),
            "api_templates": sorted(list(api_detected - MANDATORY_BASE_TEMPLATES)),
            "all_suggested": sorted(list(api_detected | custom_detected))
        }
        print(json.dumps(res, indent=2))
        sys.exit(0)

    print(f"Analyzing project directory: {project_dir}")
    api_detected, custom_detected = detect_templates(project_dir, include_base=not args.no_base, include_custom=not args.no_custom)
    
    if args.templates:
        explicit = [t.strip().lower() for t in args.templates.split(",") if t.strip()]
        for t in explicit:
            if t in CUSTOM_TEMPLATES or t in ("ai", "ai-agents", "ai-tools", "custom", "all-custom"):
                custom_detected.add(t)
            else:
                api_detected.add(t)
        
    available = get_available_templates()
    if available:
        valid_api = {t for t in api_detected if t in available}
        invalid_api = api_detected - valid_api
        if invalid_api:
            print(f"Warning: The following requested API templates were not recognized: {', '.join(invalid_api)}", file=sys.stderr)
        api_detected = valid_api

    custom_labels = [CUSTOM_TEMPLATES[k]["title"] for k in sorted(custom_detected) if k in CUSTOM_TEMPLATES]
    all_selected_labels = custom_labels + sorted(list(api_detected))
    print(f"Selected templates: {', '.join(all_selected_labels)}")
    
    custom_content = render_custom_templates(custom_detected)
    
    try:
        api_content = fetch_gitignore(api_detected) if api_detected else ""
        api_content = patch_api_content(api_content, api_detected, custom_detected)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if custom_content and api_content:
        new_content = f"{custom_content}\n\n{api_content.strip()}"
    elif custom_content:
        new_content = custom_content
    else:
        new_content = api_content.strip()

    if args.dry_run:
        print("\n--- Generated .gitignore Content (Dry Run) ---\n")
        print(new_content)
    else:
        apply_gitignore(project_dir, new_content, force=args.force)
        print("\nTo apply changes and re-index cached files in git, you can run:")
        print("  git rm --cached -r .")
        print("  git add .")
        print('  git commit -m "chore(git): generate .gitignore and re-index repository"')

if __name__ == "__main__":
    main()
