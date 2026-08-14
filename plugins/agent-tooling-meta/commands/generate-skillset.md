---
description: Generate a reference skillset for a framework/library from its source, docs, a formal spec, and/or a real project that uses it
---

Run the framework-skillset generation procedure.

Target framework/library, and whichever inputs are available (source repo
path/URL, docs URL or checkout, spec file, real-usage-project path,
existing skillset to compare against at the end): $ARGUMENTS

Load the `framework-skillset-generator` skill and follow it. It owns the
phases, the scripts and the claim-grounding bar; this command only fixes
the order of work and the confirmation gates.

## Steps

1. **Gather sources** (skill Phase 1). Materialize the source tree with
   `scripts/materialize_source.py`; fetch docs directly; read any spec
   file directly; if a real-usage-project path was given, run the
   catalogue + verdict/recommendation analysis from
   `references/usage-analysis-format.md`, excluding any prior
   analysis-artifact paths per `references/claim-grounding-rules.md`.

2. **Catalogue the framework itself** (skill Phase 2), no judgement yet.

3. **Propose the decomposition plan** (skill Phase 3): skill names + one-line
   scope each, plus whether a companion upgrade-tracking skill is warranted.

4. **Confirm the plan with me** before drafting anything. Wait for my
   go-ahead.

5. **Dispatch `framework-topic-drafter` in parallel** (skill Phase 4), one
   per planned skill, all at once, each with its scoped topic, the
   relevant materialized sources, and any real-usage-project findings that
   feed it.

6. **Citation-check the batch** (skill Phase 5):
   `scripts/check_citations.py --module-prefix <x> --old <tree> --new <tree>
   --skills-dir <staging-dir> --strict`. Send anything not clean back to the
   relevant drafter.

7. **Trigger-eval the batch** (skill Phase 6) via `skill-creator`'s
   `run_eval.py`/`run_loop.py`, if running under Claude Code - skip to
   manual description review if the `claude` CLI isn't reachable (e.g.
   under Kilo alone).

8. **Write the hub/index skill** (skill Phase 7) cross-referencing the
   batch.

9. **Report to me before writing into a real repo**: the drafted batch,
   citation-check results, trigger-eval results, and any topic-boundary
   notes the drafters reported. Wait for my go-ahead.

10. **If an existing skillset was given to compare against** (skill
    Phase 9): run `scripts/compare_skillsets.py` and present the report.
    Report only - do not merge or overwrite the existing skillset as part
    of this command.

## Rules

- **IMPORTANTE:** MAI USARE IL CARATTERE `-`. In Kilo rompe il parsing anche nel corpo in md.
- Everything through step 9 writes only to a scratch/staging location, never
  into a real repo.
- No claim about the framework without a `path::symbol` (or doc/spec
  citation) actually read in this run.
- State negative results explicitly ("checked, no better native pattern
  exists") - padding a finding with speculation costs the next reader a
  re-verification.
