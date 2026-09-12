---
id: concurrent-callers
title: Make one decision atomic
design_refs: [behavioural-contract, state-model, concurrency-boundary]
validators: [tests-pass]
optional: true
---

## Purpose

Extend the sequential limiter so concurrent callers cannot observe the same remaining
capacity and collectively exceed the configured limit.

## Prerequisites

Lesson `01-windowed-counting` is complete. The selected language or runtime has a
meaningful concurrency model the learner can exercise locally.

## Learning objectives

- Identify the read-modify-write critical section
- Choose synchronisation appropriate to the selected language
- Distinguish memory safety from behavioural atomicity
- Design a concurrency test that can reveal over-admission

## Theory

One limiter decision reads a client's window and count, decides, and sometimes writes
new state. If those actions interleave, multiple callers may all observe capacity that
only one of them should consume. Thread-safe containers alone do not necessarily make
the multi-step decision atomic.

The appropriate mechanism may be a lock, actor, atomic update, serial executor, or
another runtime idiom. Teach the selected ecosystem rather than translating a mutex
recipe mechanically.

## Concepts to teach

- race conditions
- read-modify-write atomicity
- critical sections
- ecosystem-specific synchronisation
- concurrency test limitations

## Constraints

- Preserve the public behavioural contract.
- Protect the whole decision, not merely individual map operations.
- Avoid a complex lock hierarchy; this is one in-memory component.
- The test must assert that concurrent attempts admit no more than `N` requests.
- Explain honestly when the language runtime makes a test probabilistic.

## Suggested progression

- Inspect the existing decision path and mark its critical section.
- Choose the smallest idiomatic synchronisation mechanism.
- Launch more than `N` concurrent attempts against one key and collect decisions.
- Confirm exactly `N` successes, then rerun the sequential suite.
- Discuss contention and possible finer-grained designs without requiring them.

## Completion conditions

- Concurrent attempts against one key never produce more than `N` allowed decisions in
  the exercised test.
- The sequential contract and boundary tests still pass.
- The learner can explain why the original implementation could race and what now makes
  a decision atomic.

## On completion, persist

Record the synchronisation choice, its protected critical section, and the concurrency
test evidence in the instance state and `DESIGN.md`.

## Optional deeper paths

Discuss per-key locking, sharding, actors, lock-free approaches, or race detectors only
when they are relevant to the chosen language and requested by the learner.
