#!/usr/bin/env python3
"""
preserve_rules.py - Preserves custom rules in .gitignore across regeneration.

Guarantees:
- Nothing is lost: Every line of the original file that is not part of a generated
  template block is preserved, wherever it sits (before, between or after generated blocks),
  and moved to the custom head in its original order.
- Comments stay attached to the rules that follow them.
- Blank-line grouping is kept.
- Duplicates of template lines are dropped only when identical.
- Detailed report: lines moved to the head, lines dropped as duplicates of template.
- Re-runs change nothing: Regenerating twice in a row produces the identical file.
"""

import os
import sys
import json
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "config", "templates.json"))


class PreservationReport:
    def __init__(self, lines_moved=None, lines_dropped=None):
        self.lines_moved = list(lines_moved) if lines_moved else []
        self.lines_dropped = list(lines_dropped) if lines_dropped else []

    def format_report(self):
        lines = [
            "--- .gitignore Regeneration Report ---",
            f"Lines moved to custom head ({len(self.lines_moved)}):",
        ]
        if self.lines_moved:
            for l in self.lines_moved:
                lines.append(f"  - {l}")
        else:
            lines.append("  (none)")

        lines.append(f"Lines dropped as duplicates of template ({len(self.lines_dropped)}):")
        if self.lines_dropped:
            for l in self.lines_dropped:
                lines.append(f"  - {l}")
        else:
            lines.append("  (none)")
        lines.append("--------------------------------------")
        return "\n".join(lines)

    def __repr__(self):
        return f"PreservationReport(lines_moved={self.lines_moved}, lines_dropped={self.lines_dropped})"


def load_template_config(config_path=None):
    """Load configuration from config/templates.json."""
    path = config_path or CONFIG_FILE
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config from {path}: {e}", file=sys.stderr)
    return {}


def find_generated_block_ranges(existing_lines, custom_templates=None, additional_rules=None):
    """
    Identifies all generated template block line index ranges [start_idx, end_idx] (inclusive).

    Recognizes:
    1. Toptal / gitignore.io blocks:
       Starts with `# Created by ...` (containing toptal.com or gitignore.io)
       Ends with `# End of ...` (or next block / EOF if omitted)
    2. Custom template blocks:
       Starts with `### <Title> ###` where Title matches a known custom template
       (e.g. Kilo Code, Claude Code, Roo Code, Cursor, GitHub Copilot, gCube Ecosystem,
       Local Environment Overrides, Additional Config Rules)
    """
    ranges = []
    n = len(existing_lines)

    # Build title -> set of rules
    custom_titles = {}
    if custom_templates:
        for k, v in custom_templates.items():
            if isinstance(v, dict) and "title" in v:
                custom_titles[v["title"]] = set(v.get("rules", []))
    if additional_rules:
        custom_titles["Additional Config Rules"] = set(additional_rules)
    elif "Additional Config Rules" not in custom_titles:
        custom_titles["Additional Config Rules"] = set()

    i = 0
    while i < n:
        line = existing_lines[i]
        stripped = line.strip()

        # 1. Toptal / gitignore.io block start
        if stripped.startswith("# Created by ") and ("toptal.com" in stripped or "gitignore.io" in stripped):
            start = i
            end = i
            j = i + 1
            found_end = False
            while j < n:
                j_line = existing_lines[j].strip()
                if j_line.startswith("# End of ") and ("toptal.com" in j_line or "gitignore.io" in j_line):
                    end = j
                    found_end = True
                    i = j + 1
                    break
                # If End of marker was missing, check if next block or custom head begins
                if j_line.startswith("# Created by ") and ("toptal.com" in j_line or "gitignore.io" in j_line):
                    end = j - 1
                    found_end = True
                    i = j
                    break
                if j_line.startswith("### ") and j_line.endswith(" ###"):
                    t_name = j_line[4:-4].strip()
                    if t_name in custom_titles:
                        end = j - 1
                        found_end = True
                        i = j
                        break
                j += 1
            if not found_end:
                end = n - 1
                i = n
            ranges.append((start, end))
            continue

        # 2. Custom template block start
        if stripped.startswith("### ") and stripped.endswith(" ###"):
            title = stripped[4:-4].strip()
            if title in custom_titles:
                start = i
                end = i
                expected = custom_titles[title]
                j = i + 1
                while j < n:
                    j_line = existing_lines[j]
                    j_strip = j_line.strip()
                    if not j_strip:
                        # Blank line: check if next non-blank line is still part of this template
                        k = j + 1
                        while k < n and not existing_lines[k].strip():
                            k += 1
                        if k < n and existing_lines[k].strip() in expected:
                            end = k
                            j = k + 1
                            continue
                        else:
                            break
                    if j_strip in expected or (j_strip.startswith("#") and "patch" in j_strip.lower()):
                        end = j
                        j += 1
                    else:
                        break
                ranges.append((start, end))
                i = max(end + 1, i + 1)
                continue

        i += 1

    if not ranges:
        return []

    # Sort and merge overlapping or adjacent ranges
    ranges.sort()
    merged = [ranges[0]]
    for cur_start, cur_end in ranges[1:]:
        last_start, last_end = merged[-1]
        if cur_start <= last_end + 1:
            merged[-1] = (last_start, max(last_end, cur_end))
        else:
            merged.append((cur_start, cur_end))
    return merged


def extract_template_rules(template_content):
    """
    Extracts all rule patterns from the template content.
    Comments and section headers are ignored.
    """
    rules = set()
    for line in template_content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            rules.add(stripped)
    return rules


def preserve_custom_rules(existing_content, new_template_content, custom_templates_config=None):
    """
    Preserves custom rules from existing_content and places them at the head of new_template_content.

    Returns:
        (final_content, PreservationReport)
    """
    if not existing_content:
        return (new_template_content.strip() + "\n", PreservationReport([], []))

    # Load configuration if not provided
    if custom_templates_config is None:
        cfg = load_template_config()
        custom_templates = cfg.get("custom_templates", {})
        additional_rules = cfg.get("additional_rules", [])
    else:
        custom_templates = custom_templates_config.get("custom_templates", {})
        additional_rules = custom_templates_config.get("additional_rules", [])

    existing_lines = existing_content.splitlines()
    template_rules = extract_template_rules(new_template_content)

    block_ranges = find_generated_block_ranges(existing_lines, custom_templates, additional_rules)
    generated_line_indices = set()
    for start, end in block_ranges:
        for idx in range(start, end + 1):
            generated_line_indices.add(idx)

    has_blocks = len(block_ranges) > 0
    first_block_start = block_ranges[0][0] if has_blocks else None
    last_block_end = block_ranges[-1][1] if has_blocks else None

    # Partition non-template lines into paragraphs
    paragraphs = []
    current_para = []
    prev_custom_idx = None

    for i, line in enumerate(existing_lines):
        if i in generated_line_indices or line.strip() == "# Custom Project Rules":
            if current_para:
                paragraphs.append(current_para)
                current_para = []
            continue

        if not line.strip():
            if current_para:
                paragraphs.append(current_para)
                current_para = []
            continue

        if prev_custom_idx is not None and i > prev_custom_idx + 1:
            if current_para:
                paragraphs.append(current_para)
                current_para = []

        if not has_blocks or i < first_block_start:
            loc = "head"
        elif i > last_block_end:
            loc = "after"
        else:
            loc = "between"

        current_para.append((line, loc))
        prev_custom_idx = i

    if current_para:
        paragraphs.append(current_para)

    # Process paragraphs: comment attachment, duplicate checking, moves tracking
    lines_moved = []
    lines_dropped = []
    preserved_paragraphs = []

    for para in paragraphs:
        kept_items = []
        pending_comments = []
        pending_comments_orphaned = False

        for line, loc in para:
            stripped = line.strip()
            if stripped.startswith("#"):
                if pending_comments_orphaned:
                    pending_comments = []
                    pending_comments_orphaned = False
                pending_comments.append((line, loc))
            else:
                # Rule line
                if stripped in template_rules:
                    # Identical duplicate of template line
                    lines_dropped.append(stripped)
                    pending_comments_orphaned = True
                else:
                    # Non-duplicate rule kept
                    for c_line, c_loc in pending_comments:
                        kept_items.append((c_line, c_loc))
                    pending_comments = []
                    pending_comments_orphaned = False
                    kept_items.append((line, loc))

        if pending_comments and not pending_comments_orphaned:
            for c_line, c_loc in pending_comments:
                kept_items.append((c_line, c_loc))

        if kept_items:
            preserved_paragraphs.append(kept_items)
            for item_line, item_loc in kept_items:
                if item_loc in ("between", "after"):
                    lines_moved.append(item_line)

    para_strings = []
    for para in preserved_paragraphs:
        para_strings.append("\n".join(line for line, loc in para))
    custom_rules_str = "\n\n".join(para_strings).strip()

    if custom_rules_str:
        final_content = f"# Custom Project Rules\n{custom_rules_str}\n\n{new_template_content.strip()}\n"
    else:
        final_content = new_template_content.strip() + "\n"

    report = PreservationReport(lines_moved=lines_moved, lines_dropped=lines_dropped)
    return final_content, report


def main():
    parser = argparse.ArgumentParser(description="Preserve custom rules in .gitignore and deduplicate against template")
    parser.add_argument("--existing", required=True, help="Path to existing .gitignore file")
    parser.add_argument("--template", required=True, help="Path to template file (or file containing new template content)")
    parser.add_argument("--output", help="Path to output file (defaults to stdout or in-place update if requested)")
    parser.add_argument("--dry-run", action="store_true", help="Print report and result without modifying files")

    args = parser.parse_args()

    if not os.path.isfile(args.existing):
        print(f"Error: Existing file '{args.existing}' not found.", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(args.template):
        print(f"Error: Template file '{args.template}' not found.", file=sys.stderr)
        sys.exit(1)

    with open(args.existing, "r", encoding="utf-8") as f:
        existing_content = f.read()
    with open(args.template, "r", encoding="utf-8") as f:
        template_content = f.read()

    final_content, report = preserve_custom_rules(existing_content, template_content)

    if args.dry_run:
        print("\n--- Resulting .gitignore Content (Dry Run) ---\n")
        print(final_content)
        print(report.format_report())
        sys.exit(0)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(final_content)
        print(f"Saved preserved .gitignore to {args.output}")
    else:
        print(final_content)

    print("\n" + report.format_report())


if __name__ == "__main__":
    main()
