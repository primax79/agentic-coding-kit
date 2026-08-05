---
name: terraform
description: HashiCorp Terraform MCP server integration for authoring, validating, and managing Infrastructure as Code (IaC) configurations.
---

# Skill: terraform

## Purpose

Provides Model Context Protocol (MCP) tooling and best practices for HashiCorp Terraform, allowing AI assistants to query Terraform schemas, validate `.tf` configuration files, and assist in managing Infrastructure as Code deployments.

## MCP Configuration

This skill includes `.mcp.json` running the official HashiCorp Docker MCP server (`hashicorp/terraform-mcp-server:0.4.0`):

```json
{
  "terraform": {
    "command": "docker",
    "args": [
      "run",
      "-i",
      "--rm",
      "-e", "TFE_TOKEN=${TFE_TOKEN}",
      "hashicorp/terraform-mcp-server:0.4.0"
    ]
  }
}
```

## When to Use

- When writing, refactoring, or auditing Terraform HCL code (`.tf`).
- When planning, validating, or troubleshooting infrastructure deployments.
- When generating Terraform modules or checking provider specifications.
