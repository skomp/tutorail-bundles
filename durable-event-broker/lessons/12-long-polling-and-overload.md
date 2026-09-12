---
id: 12-long-polling-and-overload
title: Long polling, cancellation, and overload
design_refs: [backpressure-contract, transport-boundary, partition-ownership]
validators: [go-build, go-test, go-test-race, manual-behaviour]
---

## Purpose

Let consumers wait efficiently at the log end and ensure finite broker capacity produces
explicit behaviour rather than goroutine or memory growth.

## Prerequisites

- Complete `11-http-api`.

## Learning objectives

- Wait for new records without polling in a busy loop.
- Wake relevant waiters after a durable append becomes visible.
- Propagate HTTP cancellation and deadlines into broker operations.
- Return explicit overload when bounded append capacity is exhausted.

## Theory

Pull-based consumption separates a slow consumer from producer storage, but waiting
requests still consume resources. Notifications are hints to recheck the log condition;
they are not records and may be coalesced. Correct wait loops always re-evaluate the
predicate after wake-up.

## Concepts to teach

- Long polling
- Condition rechecking
- Notification coalescing
- Context propagation
- Bounded queues
- Overload signalling
- Goroutine leak detection

## Constraints

- Fetch returns immediately when data is already available.
- Waiting has a caller-controlled deadline or cancellation path.
- Notification cannot be lost in a way that leaves available data waiting indefinitely.
- Append admission is bounded and overload is distinguishable from storage failure.
- Slow or disconnected clients do not create unbounded goroutines.

## Suggested progression

Add a wait-capable internal fetch operation, then expose it through HTTP. Test data already
present, append-after-wait, timeout, client cancellation, shutdown, and several waiters.
Saturate a deliberately tiny append queue and confirm overload behaviour under the race
detector.

## Completion conditions

- Long-poll fetch wakes and returns the correct offset range after append.
- Timeout and cancellation return promptly without leaking waiters.
- Queue saturation yields the documented overload response.
- Shutdown releases all waiting producers and consumers deterministically.
- Race-enabled tests and a manual concurrent run succeed.

## On completion, persist

Record wait predicate, notification mechanism, deadline behaviour, capacities, overload
contract, and shutdown handling.

## Optional deeper paths

Compare long polling with server-sent events without adding a second main-path transport.
