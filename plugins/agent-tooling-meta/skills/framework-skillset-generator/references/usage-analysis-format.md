# Real-project-usage analysis format

Used only when a real-usage-project input is given (input type 5, see
`claim-grounding-rules.md`). This produces a **scratch, intermediate**
artifact - it informs the decomposition plan and gives drafters real
idioms to cite, but it is not one of the shipped output skills and doesn't
need to survive past the run that produced it.

Two-part shape:

## Part 1 - catalogue, no judgement

A plain inventory of how the real project currently uses the target
framework: for each area of its own architecture that touches the
framework, how it's done today and where (`file:line`). No comparison, no
verdict yet - this part is pure extraction, safe to get wrong only by
missing something, not by mis-judging it.

## Part 2 - one question per candidate topic, verdict + evidence + recommendation

For each candidate topic identified from Part 1 (or from the framework's
own surface-area survey), a numbered section:

```markdown
## <N>. <a real, specific question about this project's use of the framework>

**Verdict: <a one-line judgement, stated plainly, not hedged>**

<Evidence: cite the project's own code (file:line) AND the framework's
sources (source/docs/samples, per the priority order) for whatever the
verdict rests on. If the framework has a documented idiomatic pattern for
this exact situation, name it and cite where it's documented/demonstrated.>

**Recommendation:** <concrete, actionable - not "consider reviewing this,"
but what to actually do, or, if it's a decision only the project's owners
can make, state it as an explicit either/or with the trade-off named.>
```

Close with a short synthesis: which findings feed which planned skill (an
idiom worth citing, a gap worth flagging as "the framework has no native
answer for this"), and which are project-specific enough that they don't
belong in a generic reference skill at all.

## Why this shape, not something simpler

A flat list of "things this project does" doesn't distinguish idiomatic
usage from a workaround the project needed because the framework genuinely
has no better answer - and that distinction is exactly what a generated
skill needs to get right (citing a workaround as if it were the recommended
pattern is a worse failure than not mentioning the topic at all). Forcing a
verdict, not just an observation, is what makes that distinction explicit
before it reaches the drafting phase.
