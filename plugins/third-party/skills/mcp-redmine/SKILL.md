---
name: mcp-redmine
description: "Redmine MCP server integration for managing issues, tracking bugs, and interacting with Redmine ticket workflows via the Model Context Protocol."
---

# Skill: mcp-redmine

## Purpose

Enables automated interaction with a Redmine issue tracking system. It allows the agent to fetch, read, update, and manage Redmine issues natively using the `mcp-redmine` MCP server.

## MCP Configuration

This skill includes an `.mcp.json` running the `mcp-redmine` MCP server via `uvx`. It requires the `REDMINE_URL` and `REDMINE_API_KEY` environment variables to be set in your host environment.

```json
{
  "redmine": {
    "command": "uvx",
    "args": [
      "--from",
      "mcp-redmine==2026.01.13.152335",
      "--refresh-package",
      "mcp-redmine",
      "mcp-redmine"
    ],
    "env": {
      "REDMINE_URL": "https://support.example.com",
      "REDMINE_API_KEY": "${env.REDMINE_API_KEY}"
    }
  }
}
```

## When to Use

- When querying, searching, or filtering bug reports or tasks.
- When you need to read ticket details, history, or attachments to understand a problem.
- When creating new issues or updating existing tickets with comments or status changes during the development workflow.
