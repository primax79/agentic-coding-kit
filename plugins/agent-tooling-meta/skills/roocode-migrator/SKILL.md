---
name: roocode-migrator
description: "Migrates skills and mode rules from roocode (.roo) to kilocode (.kilo / ~/.config/kilo) configuration, converting XML rules to Markdown agents."
---

# When to use
Use this skill when transitioning from roocode to kilocode. It automates the migration of:
- Project-local skills (`.roo/skills/` -> `.kilo/skills/`)
- Global skills (`~/.roo/skills/` -> `~/.config/kilo/skills/`)
- Roocode custom mode rules (e.g. `rules-<mode>/*.xml` -> converted into a Markdown prompt for kilocode agents in `.kilo/agent/` or `~/.config/kilo/agent/`)

# Workflow

### 1. Run Migration Script
Execute the custom JavaScript migration utility to handle both local and global, skill and mode translation.

**Command:**
```bash
node ./.kilo/skills/roocode-migrator/scripts/migrate.js
```

### 2. Verification
List the migrated agents and skills to ensure successful migration and structure.

**Local agents & skills:**
```bash
ls -la .kilo/agent/ .kilo/skills/
```

**Global agents & skills:**
```bash
ls -la ~/.config/kilo/agent/ ~/.config/kilo/skills/
```
