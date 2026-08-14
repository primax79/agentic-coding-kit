# Reference skill shape

The recurring shape of a good generated reference skill (the *final*
output of this skill, one per planned topic - distinct from the
intermediate real-project-usage analysis format in
`usage-analysis-format.md`, which feeds this but isn't shipped itself).

## Frontmatter

```yaml
---
name: <framework>-<topic>
description: Use when <concrete trigger scenario 1>, <trigger scenario 2>,
  hitting "<a real error message or symptom>", or deciding between
  <option A> and <option B>. Written as a dense trigger clause, not a
  summary of the content.
---
```

Only `name` and `description` - no `tools`, no `metadata` block, unless the
target repo's own convention adds one (check what siblings in the same
plugin already do before adding fields that aren't there).

## Body

1. **Numbered findings.** Each one a self-contained technical fact, citing
   real source per `claim-grounding-rules.md`
   (`<repo-or-tree-label>: path/to/file.py::symbol`, or a docs/spec
   citation). A finding is one paragraph to a few, not a page - if it needs
   a page, it's probably two findings.
2. **Comparison table or checklist**, where the topic has a real either/or
   decision (e.g. "mechanism A vs mechanism B: when to use which" - a
   table with columns for the dimensions that actually differ, each cell
   citing the source that backs it).
3. **Code snippets**, quoted from real usage (a real sample, or a minimal
   illustrative snippet built from real, grepped signatures) - never
   invented signatures.
4. **Closing "Review checklist"** - a short checkbox list someone could run
   through when reviewing code that touches this topic.
5. **Closing "Related skills"** - cross-links by exact skill name to the
   other skills in the same generated batch, plus the hub/index skill.
   Get the names right; a broken cross-reference is worse than none.

## Length

Target 120–250 lines. Push detail that would blow past that into a
`references/*.md` file inside the skill's own folder, same as any other
skill - don't inflate SKILL.md just because the topic is rich. If a topic
genuinely doesn't need 120 lines, don't pad it; a short, dense skill beats
a long, thin one.

## What NOT to do

- Don't write a tutorial ("first, do X, then do Y") unless the topic is
  genuinely a linear procedure. Most reference-knowledge topics are a set
  of findings + a decision table, not a walkthrough.
- Don't restate the framework's own docs prose - cite it and add the part
  the docs don't say (a gotcha, a version-specific behavior, a comparison
  the docs don't draw explicitly).
- Don't invent a "Related skills" entry for a skill that doesn't exist in
  this batch. Check the actual list of drafted skill names before writing
  the cross-reference section.
