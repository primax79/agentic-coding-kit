---
description: Format Markdown files automatically delegating entirely to markdownlint.
agent: general
---
Format the project's Markdown files by calling the `markdown-formatter` skill.

This command will:
1. Load the `markdown-formatter` skill.
2. Delegate 100% of the formatting tasks to David Anson's `markdownlint` CLI with the `--fix` option.
3. Validate that the files have been formatted cleanly.
