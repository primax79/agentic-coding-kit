---
name: framework-skillset-generator
description: "Use when asked to generate a reference skillset for a framework or library from its source code, official docs, a formal spec (OpenAPI/JSON Schema/proto), and/or a real project that uses it - "build skills for X like we did for ADK", "turn this library's docs into skills", "point a skill-generator at this framework". Produces a set of grounded, citation-checked SKILL.md files plus a hub/index skill, staged for review before anything is written into a real repo. Not for writing one ad-hoc skill from a task description - that's kilo-customizer."
---

# Framework skillset generator

Turns "point me at a framework/library" into a set of grounded reference
skills, the same shape as adk-agentic-coding-kit's hand-made `adk-*`
skillset, but for any framework and without a human doing the extraction by
hand. Invoked via the `/generate-skillset` command, which sequences the
phases below with two confirmation gates.

## Inputs

Up to five, gather whichever apply (see `references/claim-grounding-rules.md`
for the priority order between them):

1. **Source code** - a git repo (URL/local checkout + ref) or an
   already-checked-out/installed local path.
2. **Official docs** - a URL or a local docs checkout.
3. **A formal spec** - OpenAPI, JSON Schema, proto, or similar.
4. **Official samples / community packages** - lower-priority evidence for
   idiom, never for whether an API exists.
5. **A real project that uses the framework** - not ground truth for the
   API surface, but authoritative for *what to cover and what realistic
   idioms look like*. See the exclusion rule in
   `claim-grounding-rules.md` before grepping one of these.

## Phase 1 - Gather sources

- Source code: `scripts/materialize_source.py --module-prefix <x> --dest <tree> [--local-path | --git-repo ... --ref ... | --package ... --version ...]`.
- Docs: fetch the relevant pages directly (WebFetch/Read) - not scripted,
  per the Deterministic Script Priority Rule: crawling arbitrary doc sites
  isn't reproducible enough to be worth a script, materializing a git tree
  is.
- Formal spec: read the file directly.
- Real-usage project: grep its actual source for call patterns of the
  target framework, excluding any prior analysis artifacts (see
  `claim-grounding-rules.md`). If its workspace has a live semantic/RAG
  index available, query it as a complementary lead-finding channel, then
  verify anything it surfaces by reading the real file:line before citing
  it. When this input is present, run the two-part analysis in
  `references/usage-analysis-format.md` before moving to Phase 2 - its
  output feeds the decomposition plan and gives drafters idioms to cite.

## Phase 2 - Catalogue, no judgement

Survey the framework's full surface area before deciding anything about
skill boundaries: what are the major subsystems/modules, what does each do,
where does it live. Pure extraction, no verdicts yet - verdicts (if a
real-usage project made Phase 1's analysis relevant) already happened in
that separate pass; this catalogue is about the framework itself, not about
any one consumer of it.

## Phase 3 - Decompose into a skill-per-task-family plan

One skill = one task family, not one module or one class. Split "everything
about X" into the per-task skills someone would actually reach for ("how do
I do function tools" vs "how do I do structured output" vs "how do I set up
auth" - not "everything in the `tools` module"). Produce a short plan: skill
names + one-line scope each, plus whether a companion upgrade-tracking
skill (the same role `adk-version-upgrade` plays for ADK) is warranted -
usually yes for anything with frequent breaking releases, worth naming as a
plan item even if drafting it is a follow-up, not part of this batch.

**Confirmation gate.** Surface this plan before drafting anything.

## Phase 4 - Dispatch `framework-topic-drafter` in parallel

One subagent call per planned skill, each given: its scoped topic, the
materialized source tree path, relevant docs/spec excerpts, any
real-usage-project findings that feed it, and `references/skill-shape-template.md`
to follow. Dispatch all of them in the same turn - this is exactly the
`adk-diff-auditor` pattern (one subagent per independent unit of work,
parallel, not sequential).

## Phase 5 - Citation check

```bash
scripts/check_citations.py --module-prefix <x> --old <tree> --new <tree> \
    --skills-dir <staging-dir> --strict
```

Same tree for `--old` and `--new` - this is a self-check of a freshly
drafted batch, not a version diff. Anything not `UNCHANGED`/`OK` goes back
to the relevant drafter for a fix-or-drop pass. Non-Python targets: no
mechanical check exists, fall back to manual grep-verification at the same
bar (see `claim-grounding-rules.md`).

## Phase 6 - Trigger-eval

Lightweight, mandatory. For each drafted skill, write a small eval set (3-5
should-trigger queries drawn from its own scope, 2-3 should-not-trigger
queries drawn from sibling topics in the same batch - cheap, since the
Phase 3 plan already states each skill's scope) as the JSON shape
`third-party/skills/skill-creator/scripts/run_eval.py` expects, then run:

```bash
python3 -m scripts.run_eval --eval-set <set.json> --skill-path <staging-dir>/<skill> \
    --num-workers 5
```

(invoked from inside `third-party/skills/skill-creator/`, its own sibling
location - not copied here, see that skill's own note on why). If a skill
under-triggers, run `run_loop.py` for the auto-improvement pass. A skill
still failing after that is flagged in the final report, not silently
shipped. **This phase requires the `claude` CLI specifically - there is no
Kilo-native path for it** (`skill-creator`'s own `SKILL.md` flags this
under "Description Optimization"); when running under Kilo alone, skip to
manual review of each description instead.

The heavier with-skill/without-skill benchmark (`grader`/`comparator`/`analyzer`,
real task runs, real cost) is deliberately not wired in here - see
"Deferred: quality benchmarking" below.

## Phase 7 - Write the hub/index skill

Cross-reference every generated skill by exact name, same role
`adk-conformance-review` plays for the `adk-*` family - one place that
indexes what the batch covers and points to each skill.

## Phase 8 - Second confirmation gate

Everything above only ever writes to a scratch/staging location. Surface
the finished batch (plus the trigger-eval results) and get explicit
sign-off before writing anything into a real repo.

## Phase 9 - Optional: compare against an existing skillset

If the user points at one:

```bash
scripts/compare_skillsets.py --generated <staging-dir> --existing <existing-skills-dir>
```

Produces a coverage/structural report - matched, missing, extra skills,
line counts, frontmatter completeness. **Report only, never auto-merge**:
whether/how to reconcile the two stays an explicit follow-up decision for
the user, matching this ecosystem's existing discipline
(`/adk-upgrade`'s "produces analysis and a spec; executing it is a separate
task"). Run `check_citations.py` against each side separately if citation
validity of the existing skillset itself is in question - this script does
not re-run that check.

## Deferred: quality benchmarking

Not built here, by explicit choice: a separate, opt-in "skill quality
benchmark" capability, likely dispatching the paid with-skill/without-skill
runs through the `kilo-mcp` orchestrator (`kilo_implement`) against a
specific execution platform instead of shelling out to `claude -p` inline -
so cost and parallelism go through the delegation/monitoring machinery
already built for that, rather than a second bespoke implementation here.

## Additional resources

- `references/claim-grounding-rules.md` - source priority order, citation
  format, the real-project-usage authority distinction, the analysis-artifact
  exclusion rule.
- `references/skill-shape-template.md` - the shape every drafted skill
  should follow.
- `references/usage-analysis-format.md` - the two-part format for the
  optional real-project-usage analysis (Phase 1).
- `scripts/materialize_source.py`, `scripts/check_citations.py`,
  `scripts/compare_skillsets.py` - see each script's own docstring.
