---
id: 01-windowed-counting
title: Count requests in deterministic windows
design_refs: [behavioural-contract, window-semantics, state-model, time-source]
validators: [project-runs, tests-pass]
---

## Purpose

Implement the smallest complete vertical slice: independent counters per client,
fixed-window rollover, and tests that control time without sleeping.

## Prerequisites

Lesson `00-contract-and-language` is complete and the selected toolchain can run the
project and its tests.

## Learning objectives

- Derive a stable fixed-window identifier from time
- Maintain independent state per client key
- Inject nondeterminism at a narrow boundary
- Test time-dependent behaviour deterministically

## Theory

A fixed-window counter maps a timestamp to one non-overlapping interval. Integer
division of elapsed time by the window duration `W` is one common representation, but
the course specifies semantics rather than a formula. Moving to a new interval resets
the effective count for that key.

Wall-clock sleeps make tests slow and flaky. The limiter should depend on a time source
whose production form reads real time and whose test form returns values selected by
the test.

## Concepts to teach

- fixed windows
- half-open intervals and exact boundaries
- maps or dictionaries keyed by client identity
- injected clocks, functions, or interfaces
- deterministic tests

## Constraints

- A decision must be constant-time on average with respect to previously seen requests.
- Client keys must not share counters.
- A request at the exact window boundary belongs to the new window.
- Tests must advance fake time directly; they must not sleep.
- Keep the implementation in memory and single-process.

## Suggested progression

- Introduce the replaceable time source and prove the test controls it.
- Represent one client's current window and count.
- Generalise the state to multiple client keys.
- Make the existing budget example pass.
- Add a test that advances into a new window and observes a fresh budget.

## Completion conditions

- The first `N` requests for a key in one window are allowed and `N + 1` is rejected.
- A request at the exact start of the following window is allowed.
- Two distinct keys receive independent budgets.
- The relevant test suite passes without real-time waiting.
- The learner can describe the stored state and the average cost of one decision.

## On completion, persist

Record the time-source design and internal state representation in `DESIGN.md`. Record
the test command and demonstrated behaviours in the instance state.

## Optional deeper paths

If asked, compare fixed windows with sliding logs, sliding counters, and token buckets.
Keep those comparisons conceptual rather than replacing the project algorithm.
