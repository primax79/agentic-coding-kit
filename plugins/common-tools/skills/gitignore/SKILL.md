---
name: gitignore
description: "Creates or updates a project's .gitignore file using the gitignore.io (Toptal) API and local custom templates (AI agents, gCube, local env), preserving custom rules at the head of the file and optionally re-indexing git cache."
---

# Skill: gitignore

## Purpose

Automatically generate or update a project's `.gitignore` file using the official [gitignore.io / Toptal API](https://www.toptal.com/developers/gitignore/api) combined with an extensible registry of local custom templates (AI Coding Agents like Kilo Code and Claude Code, gCube Ecosystem rules, local environment overrides).

## Division of Responsibilities

- **Skill (LLM Decision Authority):** Decides which tags/templates to pass to the generator based on project context, user instructions, and workspace inspection.
- **Script (Auxiliary Helper & Determinisic Generator):**
  - Implements auxiliary helper methods (`--suggest`) that scan workspace files and return candidate tags (base, custom, API) to assist the Skill.
  - Generates the `.gitignore` content deterministically, fetching API templates, applying custom local sections, and preserving existing custom user rules at the HEAD.

## Workflow

### 1. Consult Script Auxiliary Helper (Optional Hint)

To inspect candidate templates detected by the script, run:

```bash
python3 /Users/Alfredo/works/gcube-ai-toolkit/skills/gitignore/scripts/generate_gitignore.py --dir . --suggest
```

The script returns a JSON payload with candidate tags (`base_templates`, `custom_templates`, `api_templates`).

### 2. Skill Decision & Tag Selection

The AI agent executing this skill evaluates the suggested tags alongside project context:

- **gCube Check:** Verify if `gcube-app.xml`, `gcube/` folder, or `org.gcube` POM dependencies exist -> include `gcube`.
- **Stack Verification:** Confirm or refine detected language and framework tags (e.g. `java`, `python`, `angular`, `node`, `go`, `rust`, `csharp`).
- **Base & Custom Tags:** Ensure mandatory base OS/IDE templates (`visualstudiocode`, `emacs`, `macos`, `windows`, `linux`) and AI agent templates (`kilo`, `claude`, `roocode`, `cursor`) are included.

### 3. Execute Generation with Selected Tags

Run the script passing the final comma-separated list of tags chosen by the Skill:

```bash
python3 /Users/Alfredo/works/gcube-ai-toolkit/skills/gitignore/scripts/generate_gitignore.py --dir . --templates "visualstudiocode,emacs,macos,windows,linux,kilo,claude,gcube,java,maven"
```

### 4. Extensible Configuration (`config/templates.json`)

All base templates, custom templates, and default custom keys are defined in a clean JSON configuration file located at `config/templates.json`:

- **AI Agents & Tooling (`category: "ai-agents"`):**
  - `kilo`: `.kilo/worktrees/`, `agent-manager.json`
  - `claude`: `.claude/worktrees/`, `.claude/settings.local.json`
  - `roocode`: `.roo/tasks/`, `.roo/db/`
  - `cursor`: `.cursor/rules/*.local`
  - `copilot`: `.copilot/`
- **gCube Ecosystem (`category: "gcube"`):**
  - `gcube`: `token.properties`, `local-config.properties`, `gcube/extra-resources/local*`, `*.war.failed`
- **Local Environment Overrides (`category: "environment"`):**
  - `local-env`: `*.local`, `.env.local`, `.env.*.local`

To add or edit custom template definitions or default base tags, simply edit `skills/gitignore/config/templates.json` without modifying any Python code.

### 5. Custom User Rule Preservation

If `.gitignore` already exists:

- Existing custom entries are preserved at the **HEAD** (top) of `.gitignore` under `# Custom Project Rules`.
- Local custom templates (`CUSTOM_TEMPLATES`) follow below the head custom rules.
- Toptal API-generated rules are appended at the bottom.

### 6. API References & Template Listing

The script interacts with the Toptal gitignore.io API:

- **API Template List (JSON):** `https://www.toptal.com/developers/gitignore/api/list?format=json`
- **API Template List (Plain lines):** `https://www.toptal.com/developers/gitignore/api/list?format=lines`
- **API Combined Generator:** `https://www.toptal.com/developers/gitignore/api/<template_1>,<template_2>,...`

### 7. Git Cache Cleanup & Re-indexing (Optional Prompt)

After creating or updating `.gitignore`, check if git tracking cleanup is needed (e.g. if files now ignored were previously tracked).

Ask the user via the `question` tool or prompt whether to execute the re-indexing sequence:

```bash
git rm --cached -r .
git add .
git commit -m "chore(git): generate .gitignore and re-index repository"
```

> **Note on syntax:** `git rm --cached -r .` removes cached index entries without deleting physical local files.
