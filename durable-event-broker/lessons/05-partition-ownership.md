---
id: 05-partition-ownership
title: One goroutine owns the append path
design_refs: [partition-ownership, acknowledgement-contract]
validators: [go-build, go-test, go-test-race]
---

## Purpose

Support concurrent append callers without losing offset order or scattering locks across
the storage engine. Channels are introduced because one execution context must own the
mutable partition state.

## Prerequisites

- Complete `04-durability-contract`.

## Learning objectives

- Identify the state that must change in one total order.
- Model append requests and per-request results over channels.
- Give one goroutine lifecycle ownership of a partition.
- Handle cancellation and shutdown without blocked senders or invented success.

## Theory

Channels do not make code correct by themselves. The useful invariant is that exactly one
goroutine assigns offsets, writes frames, and resolves append acknowledgements. Callers
submit work and wait for their own result. A bounded request channel also makes finite
capacity visible.

## Concepts to teach

- Goroutine ownership
- Request/reply channel patterns
- Happens-before relationships
- Bounded queues
- Context cancellation
- Channel closure and shutdown ownership
- Go race detector

## Constraints

- Only the partition owner mutates next offset and append state.
- Each accepted request receives exactly one success or failure result.
- Callers can abandon a wait through cancellation without blocking the owner.
- One component owns channel closure; callers never close the shared request channel.
- Keep durable per-record sync behaviour unchanged until group commit is introduced.

## Suggested progression

Identify all mutable append state, then wrap append submissions in request values carrying
a private result path. Start and stop the owner explicitly. Add concurrent tests for
offset uniqueness and ordering, followed by cancellation and shutdown cases under the race
detector.

## Completion conditions

- Concurrent appends receive unique contiguous offsets in persisted order.
- The race detector reports no race in the append, cancellation, or shutdown tests.
- Cancellation and shutdown cannot leave a caller blocked indefinitely.
- The owner reports storage errors to every affected request.
- The learner can state the ownership invariant and why a channel serves it.

## On completion, persist

Record owned state, request/result shape, channel capacity, closure owner, and shutdown order.

## Optional deeper paths

Compare the ownership design with a mutex-protected append method and identify where each
would be simpler or more difficult.
