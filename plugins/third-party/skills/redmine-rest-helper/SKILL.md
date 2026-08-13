---
name: redmine-rest-helper
description: "Generic fallback skill for interacting with a Redmine issue tracker via its REST API and curl when an MCP server is not available. Provides instructions on how to fetch, read, and comment on Redmine tickets using HTTP requests."
---

# Skill: redmine-rest-helper

## Purpose

This skill provides generic, automated procedures for interacting with any Redmine ticketing and issue-tracking system using REST APIs and personal API Keys. It is meant to be used as a fallback when the native `mcp-redmine` server is not installed or available.

## When to Use

- When you need to read or analyze a Redmine ticket but no Redmine MCP server is configured.
- When you need to update, comment on, or change the status of an issue using curl/REST directly.

## Workflow

### 1. Setup & API Key

To interact with Redmine, you need the base URL and a valid API Key.

- The URL and Key must be provided by the user or retrieved from local environment variables or configuration files.

### 2. Fetching Issue Details (GET)

To read a Redmine ticket, invoke a secure cURL/WebFetch query targeting the JSON endpoint:

- **Endpoint**: `<REDMINE_URL>/issues/{issue_id}.json?include=children,journals`
- **Request Header**: `X-Redmine-API-Key: <API_KEY>`

**Bash Example:**

```bash
curl -s -H "X-Redmine-API-Key: $REDMINE_API_KEY" "$REDMINE_URL/issues/12345.json?include=children,journals"
```

### 3. Adding a Journal/Comment (PUT)

To add a comment or update an issue:

- **Endpoint**: `<REDMINE_URL>/issues/{issue_id}.json`
- **Request Header**: `X-Redmine-API-Key: <API_KEY>`, `Content-Type: application/json`
- **JSON Payload Shape**:

  ```json
  {
    "issue": {
      "notes": "Comment text to append..."
    }
  }
  ```

**Bash Example:**

```bash
curl -X PUT -H "X-Redmine-API-Key: $REDMINE_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"issue": {"notes": "Updated successfully."}}' \
     "$REDMINE_URL/issues/12345.json"
```

## Self-Verification
- Always parse the JSON response received from Redmine to ensure the status code is `200 OK` (for reads) or `200 OK` / `204 No Content` (for updates).
- Format the retrieved ticket's details into a clean markdown representation for the user.
