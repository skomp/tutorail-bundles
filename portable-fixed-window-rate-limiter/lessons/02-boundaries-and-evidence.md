---
id: 02-boundaries-and-evidence
title: Attack the boundaries
design_refs: [behavioural-contract, window-semantics, state-model]
validators: [project-runs, tests-pass]
---

## Purpose

Turn a plausible implementation into a defensible one by testing semantic boundaries,
reviewing its public contract, and explaining the algorithm's deliberate limitations.

## Prerequisites

Lesson `01-windowed-counting` is complete and its deterministic happy-path tests pass.

## Learning objectives

- Select tests that establish semantics rather than inflate coverage
- Recognise the burst characteristic at adjacent fixed-window boundaries
- Review an implementation against its stated contract
- Communicate scope and limitations precisely

## Theory

Fixed windows permit a burst of up to twice the nominal limit around a boundary: one
budget can be consumed just before it and another immediately after it. That is not an
implementation bug; it is a property of the algorithm. Bugs still cluster around the
same point, especially off-by-one comparisons and assigning the boundary timestamp to
the old window.

State for inactive keys can also grow without bound. Cleanup is a production concern,
but implementing it is outside this short course; the limitation should be named.

## Concepts to teach

- semantic boundary testing
- off-by-one reasoning
- burst behaviour
- state-retention trade-offs
- evidence-based completion

## Constraints

- Tests must cover the last allowed and first rejected requests.
- Tests must cover the instant immediately before a boundary and the exact boundary.
- Tests must demonstrate isolation between at least two client keys.
- Do not add persistence, networking, or an alternative rate-limiting algorithm.
- Treat inactive-key cleanup as a documented limitation, not required implementation.

## Suggested progression

- Ask the learner to predict the boundary behaviour before running it.
- Add or sharpen the smallest set of tests that distinguishes correct semantics.
- Review names and public API clarity in the selected language.
- Run the complete test suite and a small demonstration.
- Have the learner explain the boundary burst and retained-state limitation.

Before the first task, make the authored optional lesson offer from the manifest. A
learner who declines it must still be able to complete this lesson and the course.

## Completion conditions

- All contract, rollover, boundary, and client-isolation tests pass.
- The project runs through its documented commands without unexplained failures.
- The learner can explain the `2N` boundary burst and why it follows from fixed windows.
- The learner can identify at least fixed-window burstiness and inactive-key retention
  as limitations without claiming the implementation solves them.

## On completion, persist

Record the verified behavioural contract, exact test command, and explicitly accepted
limitations in the instance state. Append any durable API refinements to `DESIGN.md`.

## Optional deeper paths

If the learner asks where to go afterward, discuss—but do not implement—cleanup,
distributed coordination, observability, or alternative algorithms.
