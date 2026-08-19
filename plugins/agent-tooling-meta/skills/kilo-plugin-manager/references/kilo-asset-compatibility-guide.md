# Kilo Code Asset Compatibility and Parser Specification

This document details the parsing behavior, schema constraints, and compatibility rules of **Kilo Code** (CLI and VS Code Extension) when loading Markdown commands, agents, skills, rules, and configuration files.

---

## 1. Root-Cause Analysis of Parser Failures

Kilo Code processes Markdown assets via a pipeline combining:
1. **Gray-Matter Frontmatter Extraction**: Splits YAML headers from the Markdown body.
2. **Fallback Sanitization (`pl1`)**: Regex-based auto-corrector attempting to recover unquoted YAML values.
3. **Template Macro Substitution (`CqA.substitute`)**: Resolves `{file:...}`, `{env:...}`, and `@path` references.
4. **Effect-TS / StandardSchema Decoders**: Validates frontmatter objects against strict TypeScript `V.Struct` definitions.

Any asset violating these stages causes `Failed to parse command`, `Failed to parse YAML frontmatter`, or runtime session aborts.

---

## 2. Strict Formatting Rules

### A. Special and Non-ASCII Characters

| Prohibited Token | Code Point | Issue in Kilo | Required Replacement |
| :--- | :--- | :--- | :--- |
| **`§`** (Section Sign) | `U+00A7` | Breaks tokenizer in command/skill parsers and fallback sanitizer. | `section ` or `` `§` `` in code blocks |
| **`—`** (Em-dash) | `U+2014` | Corrupts YAML frontmatter and list parsing. | ` - ` or `-` |
| **`–`** (En-dash) | `U+2013` | Corrupts YAML frontmatter. | `-` |
| **`“` `”` `‘` `’`** (Smart Quotes) | Typographic | Causes YAML `SyntaxError` in string literals. | Standard ASCII `"` and `'` |

---

### B. Frontmatter YAML Constraints

1. **Description Field (`description`)**:
   - **Must be a single-line string.**
   - **Must be double-quoted** (`"..."`) whenever it contains colons (`:`), commas, dashes, or quotes.
   - Internal double-quotes must be escaped as `\"`.
   - **Never use multiline scalar block indicators (`|` or `>`)** in descriptions; Kilo expects a single scalar string.

   *Example (Correct):*
   ```yaml
   ---
   name: my-skill
   description: "Validates assets: checks for compliance, schemas, and encoding."
   ---
   ```

2. **Schema Field Restrictions by Item Kind**:

   * **Commands (`command/*.md` or `commands/*.md`)**:
     * Strict schema (`E77 = V.Struct(...)`). Unrecognized keys are **rejected** with `ConfigInvalidError`.
     * **Allowed Keys:** `description` (string), `agent` (string), `model` (string), `subtask` (boolean).
     * *Do NOT add:* `name`, `version`, `tools`, `permissions`.

   * **Agents (`agent/*.md` or `agents/*.md`)**:
     * **Allowed Keys:** `description`, `mode` (`primary` | `subagent` | `all`), `model`, `steps`, `hidden`, `color`, `permission`.
     * Permission blocks map tool names to actions (`allow`, `ask`, `deny`).

   * **Skills (`skills/<name>/SKILL.md`)**:
     * **Allowed Keys:** `name` (required), `description` (required), `argument-hint`, `user-invocable`, `disable-model-invocation`, `context`.

---

### C. Template Macro and Reference Safety

1. **`{file:...}` Macro:**
   - Kilo matches `\{file:[^}]+\}` globally in Markdown bodies and attempts to read the target file from the filesystem.
   - If writing illustrative examples in documentation, prefix the line with `//` or enclose in code fences to avoid runtime file lookup failures.

2. **`@path` Inclusion Syntax:**
   - Unquoted `@word` or `@path` outside backticks is interpreted as a file inclusion token.
   - Any user handles or ticket references (e.g. `@user`, `@issue-123`) must be enclosed in backticks: `` `@username` ``.

3. **Shell Macro `` !`cmd` ``:**
   - Commands prefixed with `!` inside backticks execute shell commands at command load time. Avoid arbitrary exclamation marks directly attached to backticks.

---

## 3. Automated Validation Tool (`validate_kilo_assets.py`)

A generic, path-agnostic validation script is provided in `scripts/validate_kilo_assets.py`.

### Features
- **Path Independent**: Accepts any target directory or file.
- **Zero External Dependencies**: Pure Python standard library (`os`, `re`, `sys`, `pathlib`, `argparse`).
- **Comprehensive Linting**: Checks non-ASCII chars, YAML syntax, unknown frontmatter fields, and template macro safety.
- **Auto-Remediation (`--fix`)**: Automatically converts section signs, em-dashes, typographic quotes, and formats descriptions into properly quoted single-line strings.

### Usage
```bash
# Check current directory / marketplace
python3 scripts/validate_kilo_assets.py .

# Check specific repository or directory with verbose output
python3 scripts/validate_kilo_assets.py /path/to/repo --verbose

# Automatically repair and sanitize all assets
python3 scripts/validate_kilo_assets.py /path/to/repo --fix
```
