---
name: macroplan-authoring
description: "Deprecated: replaced by task-pipeline (ai-orchestration, plugin architect-side). Only redirects there; do not use it to create or edit tasks."
---

# macroplan-authoring (deprecated)

This skill has been superseded by **`task-pipeline`**, shipped by the `ai-orchestration` marketplace (plugin `architect-side`, <https://github.com/primax79/ai-orchestration>). The two used to be installed side by side with the same description, and agents loading this older copy wrote plans the engine cannot read (tasks as bullets or table rows, `T<n>` ids inside plans).

Do not create or edit tasks from this skill. Instead:

1. Load `task-pipeline` (`/plugin install architect-side@ai-orchestration` if it is missing).
2. Follow its "Format is not optional" rule: plan tasks are `### NN.T - <title>` blocks with a Status line, emergent tasks are created with `ai-orch tasks new`, and `ai-orch tasks validate` is clean after every change.
3. For a project already written in the old format, follow its "Normalizing existing tasks" section.
