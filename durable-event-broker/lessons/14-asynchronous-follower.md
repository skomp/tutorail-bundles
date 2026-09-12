---
id: 14-asynchronous-follower
title: A restartable asynchronous follower
design_refs: [replication-boundary, offset-semantics, acknowledgement-contract, observability-contract]
validators: [go-build, go-test, go-test-race, manual-behaviour]
---

## Purpose

Add a deliberately incomplete replica that copies one leader partition, resumes after
interruption, and makes the gap between copying and distributed durability impossible to
ignore.

## Prerequisites

- Complete `13-observability-and-load`.

## Learning objectives

- Replicate from a follower's next local offset.
- Preserve leader-assigned record identity and order.
- Retry safely after follower or connection interruption.
- Measure replica lag.
- Demonstrate the durability and authority problems the design does not solve.

## Theory

An asynchronous follower is an internal consumer with stricter identity rules. It can
create another copy, but the leader acknowledges without waiting for it. Therefore the
copy is neither a quorum nor a failover protocol. Without authority and election rules,
the follower must remain read-only.

## Concepts to teach

- Log replication by offset
- Catch-up and steady-state following
- Idempotent resume
- Replica lag
- Asynchronous acknowledgement gap
- Authority, promotion, and split-brain boundaries
- Fault-injection reasoning

## Constraints

- Begin with one configured leader partition and one read-only follower.
- The follower preserves offsets, timestamps, keys, and payloads assigned by the leader.
- Resume does not duplicate or renumber records.
- The follower never accepts producer traffic or promotes itself.
- Leader acknowledgements do not wait for the follower in this course.
- The final documentation states that acknowledged records may be absent from the follower.

## Suggested progression

Reuse the internal fetch and append mechanics through a replication-specific boundary that
can preserve assigned metadata. Copy existing history, follow new records, interrupt and
restart the follower, and expose lag. Finally delay replication, acknowledge new leader
records, terminate the leader, and inspect which records the follower lacks.

## Completion conditions

- A follower catches up from empty and matches the leader's record identities.
- Restart resumes at the next offset without gaps or duplicates.
- Replica lag changes predictably while paused and while catching up.
- Race-enabled tests pass for interruption and shutdown paths.
- A controlled experiment demonstrates an acknowledged-but-unreplicated record.
- The learner explains why this system has neither quorum durability nor safe failover.

## On completion, persist

Record replication source, resume rule, metadata preservation, retry policy, lag definition,
and the demonstrated missing guarantees that define the distributed sequel.

## Optional deeper paths

Sketch the questions a distributed sequel must answer—placement, acknowledgements,
authority, leader failure, reassignment, and consumer coordination—without implementing
them here.
