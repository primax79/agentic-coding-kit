---
name: playwright
description: "Playwright MCP server integration for browser automation, web testing, and page scraping."
---

# Skill: playwright

## Purpose

Enables automated browser control, end-to-end testing, visual page inspection, and web scraping using the official Microsoft `@playwright/mcp` server.

## MCP Configuration

This skill includes `.mcp.json` running the Playwright MCP server via `npx`:

```json
{
  "playwright": {
    "command": "npx",
    "args": ["@playwright/mcp@latest"]
  }
}
```

## When to Use

- When building, debugging, or executing end-to-end (E2E) web application tests.
- When automating browser interactions, taking screenshots, or verifying UI states.
- When performing deep web scraping or testing dynamic web user interfaces.
