---
id: 04-durability-contract
title: What an acknowledgement promises
design_refs: [acknowledgement-contract, recovery-policy]
validators: [go-build, go-test, manual-behaviour]
---

## Purpose

Separate bytes accepted by a process from records covered by the broker's durability
promise, then measure the cost of making that promise for every append.

## Prerequisites

- Complete `03-recovery`.

## Learning objectives

- Explain the difference between a successful write and explicit file synchronisation.
- Place acknowledgement after the operation required by the durability contract.
- Measure per-record sync latency and throughput.
- State the limits of what the program can promise about physical storage.

## Theory

Operating systems normally buffer writes. Process termination, kernel failure, power loss,
and storage-controller behaviour are different failure boundaries. An explicit sync asks
the operating system to make prior writes durable, but honest documentation must not claim
knowledge of hardware guarantees the program cannot verify.

## Concepts to teach

- Page cache
- Flush versus sync
- Durability boundaries
- Acknowledgement ordering
- Latency distributions rather than averages alone
- Honest guarantees

## Constraints

- A durable append acknowledges only after its record is covered by a successful sync.
- Sync failures are returned to the caller.
- Benchmark or measurement code exercises the real append path.
- Do not optimise with batching yet; first capture the cost that motivates it.

## Suggested progression

Instrument the existing append path, establish its current acknowledgement point, then
move the point behind explicit synchronisation. Measure a repeatable sequence of durable
appends and capture latency and throughput. Discuss why different environments may produce
different numbers without invalidating the contract.

## Completion conditions

- Tests prove acknowledgement is not returned before the configured sync operation succeeds.
- A forced sync error reaches the caller where the platform permits deterministic injection.
- The learner records environment, workload, latency distribution, and throughput.
- The acknowledgement contract is written precisely and does not claim replication.
- Validators succeed.

## On completion, persist

Record the selected sync operation, acknowledgement point, measurement method, observed
baseline, and stated durability limits.

## Optional deeper paths

The authored optional lesson `page-cache-experiments` explores the operating-system
boundary further when the learner accepts it.
