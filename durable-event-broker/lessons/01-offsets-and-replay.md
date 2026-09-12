---
id: 01-offsets-and-replay
title: Logical offsets and replay
design_refs: [record-model, offset-semantics]
validators: [go-build, go-test]
---

## Purpose

Turn insertion order into an explicit, addressable log. Consumers must be able to resume
from a logical position and replay old records without destructive dequeue semantics.

## Prerequisites

- Complete `00-running-broker`.

## Learning objectives

- Assign monotonically increasing logical offsets.
- Fetch a bounded number of records starting at an offset.
- Define behaviour at the beginning, middle, and current end of a log.
- Distinguish a log cursor from a byte position or queue acknowledgement.

## Theory

An offset names a record's position within one ordered partition. It is stable even when
the physical representation later changes. Fetching from the current end is a successful
empty read, while fetching from an offset that no longer exists after retention will later
need a distinct result.

## Concepts to teach

- Partition-local logical offsets
- Inclusive fetch-from semantics
- Bounded batches
- Replay and independent consumers
- Empty-at-end behaviour

## Constraints

- The first appended record uses a documented initial offset.
- Fetch accepts a start offset and maximum record count.
- Two consumers may replay the same records independently.
- Do not expose slice indexes as the public offset contract.

## Suggested progression

Add broker-assigned metadata to stored records. Extend append to return the assigned
offset, then implement bounded fetch. Test boundary cases before changing the executable
to demonstrate two independent replay positions.

## Completion conditions

- Assigned offsets are monotonic and contiguous in the single in-memory log.
- Fetch from a known offset returns that record first and respects the requested limit.
- Fetch at the current end returns no records without an error.
- Independent replay positions do not mutate broker state.
- All validators pass without accepted new warnings.

## On completion, persist

Record the initial offset, inclusive fetch rule, and empty-at-end behaviour.

## Optional deeper paths

Compare logical offsets with sequence numbers, file positions, and queue acknowledgements.
