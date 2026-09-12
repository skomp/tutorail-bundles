---
id: 10-topics-and-partitions
title: Topics and independent partitions
design_refs: [topic-partition-model, offset-semantics, partition-ownership]
validators: [go-build, go-test, go-test-race]
---

## Purpose

Generalise one log into a broker containing named topics and independently ordered
partitions without inventing a global order.

## Prerequisites

- Complete `09-retention`.

## Learning objectives

- Manage lifecycle and lookup for multiple topic-partitions.
- Keep offsets, append owners, segments, and retention local to each partition.
- Select keyed partitions deterministically.
- Define an explicit distribution strategy for unkeyed records.

## Theory

Partitioning provides parallelism by weakening ordering scope. Records within one
partition are ordered; records in different partitions have no broker-defined relative
order. Stable key routing preserves per-key order only while the partition count and hash
rule remain compatible.

## Concepts to teach

- Topic and partition namespaces
- Per-partition ordering
- Stable hashing
- Key affinity
- Unkeyed distribution
- Partition-count change consequences
- Concurrent partition lifecycles

## Constraints

- Offsets are scoped to one topic-partition.
- Topic and partition names are validated before they become filesystem paths.
- Keyed routing uses a documented stable algorithm, not a process-random hash.
- Tests must not assert a global order across partitions.
- No consumer-group or broker-managed cursor state is introduced.

## Suggested progression

Wrap the existing partition behind broker lookup, create a topic with a fixed count, and
address appends explicitly first. Add keyed selection and then a documented unkeyed
strategy. Exercise independent owners under the race detector and restart the whole broker.

## Completion conditions

- Multiple topics and partitions persist and recover independently.
- Identical keys select the same partition for a fixed topic configuration.
- Invalid names cannot escape the broker data directory.
- Tests demonstrate per-partition ordering without claiming cross-partition order.
- Race-enabled tests pass.

## On completion, persist

Record namespace validation, directory layout, routing algorithms, ordering scope, and the
consequence of changing partition count.

## Optional deeper paths

Compare modulo hashing with consistent hashing as preparation for a distributed sequel;
do not add cluster placement here.
