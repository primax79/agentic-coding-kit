# Claim-grounding rules

Every technical claim a generated skill makes must be traceable to something
actually read, not inferred or remembered. This is the single biggest lever
on whether a generated skill is trustworthy - an unverified claim about an
API that doesn't exist (a hallucinated class, a renamed parameter, a method
that was removed two versions ago) is worse than no skill at all, because it
reads as confident and gets acted on.

## Ground-truth priority order

When sources disagree, prefer in this order:

1. **Installed package / source checkout** - what actually runs. Always
   wins for "does this symbol exist, what's its real signature."
2. **Official docs** - wins for *intent*: why a feature exists, when to use
   it over an alternative, migration guidance the source code itself won't
   state.
3. **Official samples** - real, runnable usage of the API, useful for
   idiom and composition patterns docs often don't show.
4. **Community packages / plugins** - lowest priority; useful for "is there
   a well-known extension for X," never as evidence for what the core
   framework itself does.

**Code wins for behavior, docs win for intent.** If the docs say a parameter
defaults to `False` and the source says `True`, the source is right about
what happens at runtime - but the docs may still be right about what the
parameter is *for*. State both when they disagree rather than silently
picking one.

## Citation format

Every claim cites where it came from, in a format someone can re-grep:

- Source code: `path/to/file.py::symbol_name` (or just the path for a
  file-level claim).
- Official docs: `doc-url#section` or `docs/relative/path.md:line-range`
  for a local docs checkout.
- A formal spec (OpenAPI, JSON Schema, proto): the field/operation path as
  it appears in the spec (e.g. `paths./users/{id}.get.parameters`).

**Never assert an API you have not personally grepped or read in the
current run.** "I recall this class having a `timeout` parameter" is not
grounding - grep it, or don't claim it. If a symbol *might* exist but
wasn't found in the time available, say so explicitly ("not verified -
grep `X` before relying on this") rather than stating it as fact.

## Real-project-usage input: a different kind of authority

A real project that uses the target framework (the fifth input type, beyond
source/docs/samples/community) is **not** ground truth for whether an API
exists - treat anything it does as no more authoritative than a community
sample for that question. Its actual value is answering a different
question: **what does this skillset need to cover, and what do realistic
idioms actually look like here** - the same role the originating project
played for every hand-made reference skillset that grew out of a real
upgrade or conformance pass rather than being written in the abstract.

Concretely, when a real-usage-project path is given:

- Grep it for actual call patterns of the target framework's APIs - this
  tells you which parts of the surface area are load-bearing enough to
  deserve a skill, versus corners nobody touches.
- If the workspace has a live semantic index available (e.g. via a RAG
  search tool pointed at that project's path), query it for "how is X
  used here" - but treat anything it surfaces as a lead to verify by
  reading the actual file:line, not as a citation-grade claim on its own.
- Where the project diverges from the framework's own idiom, that
  divergence is itself signal - it usually means either the project found
  a genuine gap (the framework has no native answer, so custom code is
  legitimate) or the project is doing something the framework already
  has a better answer for. Which one it is takes actually comparing the
  project's approach against the framework's docs/samples for the same
  concern - don't assume either direction by default.

**Exclusion rule - do not grep prior analysis artifacts as if they were
source code.** A real-usage project may already contain notes, reports, or
a prior validation pass about its own use of the target framework (a
task/analysis folder, a "state of progress" doc, a previously-generated
skillset for the same framework). Exclude those from this gathering step -
grep the actual application source, not documents that already contain
someone else's conclusions about it. Reading those would silently import a
prior analysis's answers into a supposedly independent pass, which defeats
the point whenever this skill's own output is later going to be compared
against exactly that prior analysis's result.

## When claim-grounding isn't mechanically checkable

`check_citations.py` (this skill's own script) is AST-based and therefore
only validates Python targets. For a framework in another language, there
is no bundled equivalent checker - fall back to manual grep-verification of
every citation, holding the same bar (nothing asserted without being read),
just without the mechanical safety net.
