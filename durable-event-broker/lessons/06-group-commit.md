---
id: 06-group-commit
title: Batching and group commit
design_refs: [partition-ownership, group-commit, acknowledgement-contract]
validators: [go-build, go-test, go-test-race, manual-behaviour]
---

## Purpose

Use the partition owner to amortise synchronisation cost while preserving the durable
acknowledgement contract.

## Prerequisites

- Complete `05-partition-ownership` and retain the per-record sync measurements.

## Learning objectives

- Collect concurrent requests into a bounded batch.
- Balance batch size against maximum waiting time.
- Acknowledge a batch only after its write and sync succeed.
- Measure throughput, latency distribution, and actual batch sizes.

## Theory

Group commit trades a small amount of queueing delay for fewer synchronisation operations.
The first request starts a collection interval; capacity and a timer bound it. Correctness
depends on resolving all members consistently after write and sync outcomes, including
partial failure and shutdown.

## Concepts to teach

- Group commit
- Size and time batch thresholds
- Timer ownership and reuse
- Amortised I/O cost
- Tail latency
- Batch failure propagation

## Constraints

- Both maximum batch size and maximum collection delay are finite and configurable.
- Frames are written and assigned offsets in request order as observed by the owner.
- No request is acknowledged before the batch sync succeeds.
- A failed write or sync cannot yield success to only part of the same durability unit.
- Empty timers or busy loops must not consume CPU while idle.

## Suggested progression

Measure the existing owner, add a size-only batch, then add a time bound so sparse traffic
does not wait forever. Test threshold edges, storage failures, cancellation, and shutdown.
Repeat the earlier workload and compare distributions rather than quoting one best run.

## Completion conditions

- Tests cover size-triggered and time-triggered batches.
- A sync spy or equivalent evidence proves one sync may cover several acknowledgements.
- Failure and shutdown resolve every accepted request exactly once.
- Race-enabled tests pass.
- The learner records a comparable before/after measurement and explains the trade-off.

## On completion, persist

Record batch thresholds, timer semantics, durability unit, failure propagation, and measured
before/after results.

## Optional deeper paths

Explore adaptive batching as a design discussion; do not add it without a measurable goal.
