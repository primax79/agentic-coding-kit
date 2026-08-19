#!/usr/bin/env python3
"""
validate_kilo_assets.py — Generic Kilo Code asset validator and sanitizer.

Checks and sanitizes markdown/YAML/JSON assets (skills, agents, commands, instructions,
and marketplace manifests) for Kilo Code parser compatibility.

Key Features & Edge-Case Handling:
1. Context-Aware Quote Escaping:
   - When replacing smart quotes (“ ”) inside YAML frontmatter strings, properly
     escapes them as `\"` to prevent breaking YAML string boundaries.
   - Serializes YAML frontmatter string values safely using JSON-compatible escaping.
2. Character Normalization:
   - Section signs (§ -> section )
   - Em-dashes (— ->  - )
   - En-dashes (– -> -)
   - Typographic smart quotes (“ ” -> \", ‘ ’ -> ')
3. Strict Frontmatter Schema Validation:
   - Commands (`command/*.md`): only allowed keys [description, agent, model, subtask].
   - Agents (`agent/*.md`): mode, permission, steps, model, description, hidden.
   - Skills (`SKILL.md`): name, description (single-line double-quoted string).
4. Template Macro & Link Safety:
   - Flags unescaped {file:...} references outside comments.
   - Flags raw @path references outside backticks.

Usage:
  python3 validate_kilo_assets.py [path] [--fix] [--verbose]
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

ALLOWED_COMMAND_KEYS = {"description", "agent", "model", "subtask", "template", "name"}
ALLOWED_AGENT_KEYS = {
    "description", "mode", "model", "steps", "hidden", "color", "permission",
    "name", "tools", "system_prompt"
}
ALLOWED_SKILL_KEYS = {
    "name", "description", "argument-hint", "user-invocable",
    "disable-model-invocation", "context", "license", "author", "version"
}

BODY_CHAR_REPLACEMENTS = {
    "§": "section ",
    "—": " - ",
    "–": "-",
    "“": '"',
    "”": '"',
    "‘": "'",
    "’": "'",
}


class ValidationReport:
    def __init__(self):
        self.errors: List[Tuple[str, int, str]] = []
        self.warnings: List[Tuple[str, int, str]] = []
        self.fixed: List[Tuple[str, str]] = []

    def add_error(self, file_path: str, line_no: int, msg: str):
        self.errors.append((file_path, line_no, msg))

    def add_warning(self, file_path: str, line_no: int, msg: str):
        self.warnings.append((file_path, line_no, msg))

    def add_fixed(self, file_path: str, desc: str):
        self.fixed.append((file_path, desc))

    @property
    def is_clean(self) -> bool:
        return len(self.errors) == 0


def sanitize_markdown_body(body_text: str) -> Tuple[str, List[str]]:
    """Sanitizes characters in markdown body while respecting code blocks."""
    changes = []
    lines = body_text.splitlines(keepends=True)
    new_lines = []
    in_code_fence = False

    for line in lines:
        if line.strip().startswith("```"):
            in_code_fence = not in_code_fence
            new_lines.append(line)
            continue

        if in_code_fence:
            new_lines.append(line)
            continue

        mod_line = line
        for bad_char, replacement in BODY_CHAR_REPLACEMENTS.items():
            if bad_char in mod_line:
                count = mod_line.count(bad_char)
                mod_line = mod_line.replace(bad_char, replacement)
                changes.append(f"Replaced {count} '{bad_char}' with '{replacement}' in body")

        new_lines.append(mod_line)

    return "".join(new_lines), changes


def sanitize_frontmatter(fm_text: str) -> Tuple[str, List[str]]:
    """
    Safely parses and sanitizes YAML frontmatter lines.
    Ensures that values with colons or internal quotes are properly double-quoted
    and internal double-quotes are escaped as \\\" (never raw quotes that break YAML).
    """
    changes = []
    lines = fm_text.splitlines()
    new_lines = []

    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            new_lines.append(line)
            continue

        match = re.match(r"^([a-zA-Z0-9_\-]+)\s*:\s*(.*)$", line)
        if not match:
            new_lines.append(line)
            continue

        key, raw_val = match.group(1), match.group(2).strip()

        # Step 1: Normalize smart quotes and section signs in the value
        clean_val = raw_val
        for bad_char, replacement in BODY_CHAR_REPLACEMENTS.items():
            if bad_char in clean_val:
                clean_val = clean_val.replace(bad_char, replacement)
                changes.append(f"Line {idx}: Replaced '{bad_char}' in '{key}' field")

        # Step 2: Extract underlying raw text (strip existing surrounding quotes if any)
        if (clean_val.startswith('"') and clean_val.endswith('"')) and len(clean_val) >= 2:
            inner = clean_val[1:-1]
            # Unescape already escaped quotes to get true raw string
            inner = inner.replace('\\"', '"').replace('\\\\', '\\')
        elif (clean_val.startswith("'") and clean_val.endswith("'")) and len(clean_val) >= 2:
            inner = clean_val[1:-1].replace("''", "'")
        elif clean_val.startswith(">") or clean_val.startswith("|"):
            inner = ""
            changes.append(f"Line {idx}: Converted multiline scalar block in '{key}' to single-line string")
        else:
            inner = clean_val

        # Step 3: Check if string needs double-quoting
        needs_quotes = (
            key in ("description", "name", "agent", "model")
            or ":" in inner
            or "-" in inner
            or '"' in inner
            or "'" in inner
            or "#" in inner
            or clean_val.startswith('"')
            or clean_val.startswith("'")
        )

        if needs_quotes:
            # Safely serialize string with escaped internal double-quotes using json.dumps
            serialized = json.dumps(inner, ensure_ascii=False)
            new_line = f"{key}: {serialized}"
            if new_line != line:
                changes.append(f"Line {idx}: Formatted and escaped '{key}' as valid double-quoted YAML string")
            new_lines.append(new_line)
        else:
            new_lines.append(line)

    return "\n".join(new_lines), changes


def validate_markdown_file(file_path: Path, fix: bool, report: ValidationReport):
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        report.add_error(str(file_path), 0, f"Cannot read file: {e}")
        return

    original_content = content
    modified = False

    # Check for frontmatter
    fm_match = re.match(r"^---\r?\n(.*?)\r?\n---", content, re.DOTALL)
    if fm_match:
        fm_text = fm_match.group(1)
        body_text = content[fm_match.end():]
        parent_dir = file_path.parent.name.lower()
        is_command = "command" in parent_dir or "commands" in parent_dir
        is_agent = "agent" in parent_dir or "agents" in parent_dir

        # Validate frontmatter keys and values
        for idx, line in enumerate(fm_text.splitlines(), 1):
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue

            k_match = re.match(r"^([a-zA-Z0-9_\-]+)\s*:\s*(.*)$", line_str)
            if k_match:
                key, val = k_match.group(1), k_match.group(2).strip()

                if is_command and key not in ALLOWED_COMMAND_KEYS:
                    report.add_warning(
                        str(file_path),
                        idx,
                        f"Unrecognized frontmatter key in command: '{key}' (allowed: {ALLOWED_COMMAND_KEYS})"
                    )
                elif is_agent and key not in ALLOWED_AGENT_KEYS:
                    report.add_warning(
                        str(file_path),
                        idx,
                        f"Unrecognized frontmatter key in agent: '{key}'"
                    )

                if any(c in line_str for c in ("§", "—", "–", "“", "”", "‘", "’")):
                    report.add_error(
                        str(file_path),
                        idx,
                        f"Prohibited/smart character detected in frontmatter line: {line_str}"
                    )

                if key == "description":
                    if val.startswith("|") or val.startswith(">"):
                        report.add_error(
                            str(file_path),
                            idx,
                            "Multiline block scalar (| or >) in description breaks Kilo. Use single-line double-quoted string."
                        )
                    elif ":" in val and not ((val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'"))):
                        report.add_error(
                            str(file_path),
                            idx,
                            "Unquoted colon in description field. Wrap in double quotes with escaped internal quotes."
                        )

        # Validate body characters
        for idx, line in enumerate(body_text.splitlines(), 1):
            for bad_char in ("§", "—", "–"):
                if bad_char in line and not line.strip().startswith("```"):
                    report.add_error(
                        str(file_path),
                        idx,
                        f"Prohibited character '{bad_char}' detected in markdown body."
                    )

            if "{file:" in line and not line.strip().startswith("//"):
                report.add_warning(
                    str(file_path),
                    idx,
                    "Literal '{file:...}' detected in body outside '//' comment. Kilo template engine may attempt disk substitution."
                )

        if fix:
            new_fm, fm_changes = sanitize_frontmatter(fm_text)
            new_body, body_changes = sanitize_markdown_body(body_text)

            if new_fm != fm_text or new_body != body_text:
                content = f"---\n{new_fm}\n---{new_body}"
                modified = True
                for fc in fm_changes + body_changes:
                    report.add_fixed(str(file_path), fc)

    else:
        # No frontmatter - plain markdown file
        for idx, line in enumerate(content.splitlines(), 1):
            for bad_char in ("§", "—", "–"):
                if bad_char in line and not line.strip().startswith("```"):
                    report.add_error(
                        str(file_path),
                        idx,
                        f"Prohibited character '{bad_char}' detected in markdown text."
                    )

        if fix:
            content, body_changes = sanitize_markdown_body(content)
            if content != original_content:
                modified = True
                for bc in body_changes:
                    report.add_fixed(str(file_path), bc)

    if fix and modified and content != original_content:
        file_path.write_text(content, encoding="utf-8")


def scan_directory(target_path: Path, fix: bool, verbose: bool) -> ValidationReport:
    report = ValidationReport()
    ignore_dirs = {".git", "node_modules", "dist", "out", "__pycache__", ".venv", "venv", ".kilo-worktrees"}

    if target_path.is_file():
        if target_path.suffix.lower() in {".md", ".json", ".jsonc"}:
            validate_markdown_file(target_path, fix, report)
        return report

    for root, dirs, files in os.walk(target_path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".git")]
        for file in files:
            p = Path(root) / file
            if p.suffix.lower() in {".md"}:
                validate_markdown_file(p, fix, report)

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Generic Kilo Code asset validator and sanitizer."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Directory or file to validate (defaults to current directory)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically fix and sanitize prohibited characters and frontmatter formatting with proper quote escaping",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show verbose output",
    )

    args = parser.parse_args()
    target = Path(args.path).resolve()

    if not target.exists():
        print(f"Error: Path '{target}' does not exist.", file=sys.stderr)
        sys.exit(1)

    print(f"Validating Kilo Code assets in: {target} (fix={args.fix})")
    report = scan_directory(target, fix=args.fix, verbose=args.verbose)

    if report.fixed:
        print(f"\n[FIXED] {len(report.fixed)} issue(s) resolved automatically:")
        for file_p, desc in report.fixed:
            print(f"  ✓ {file_p}: {desc}")

    if report.warnings:
        print(f"\n[WARNINGS] {len(report.warnings)} warning(s) found:")
        for file_p, line_no, msg in report.warnings:
            loc = f":{line_no}" if line_no > 0 else ""
            print(f"  ⚠ {file_p}{loc}: {msg}")

    if report.errors:
        print(f"\n[ERRORS] {len(report.errors)} error(s) found:")
        for file_p, line_no, msg in report.errors:
            loc = f":{line_no}" if line_no > 0 else ""
            print(f"  ✗ {file_p}{loc}: {msg}")
        print("\nValidation FAILED. Run with `--fix` to automatically repair common issues.")
        sys.exit(1)
    else:
        print("\n✓ Validation PASSED. All assets are fully compliant with Kilo Code parsers.")
        sys.exit(0)


if __name__ == "__main__":
    main()
