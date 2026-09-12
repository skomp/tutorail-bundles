---
id: 09-retention
title: Retention and expired offsets
design_refs: [retention-semantics, segment-layout, offset-semantics]
validators: [go-build, go-test]
---

## Purpose

Bound disk use by deleting closed segments and make history loss visible to consumers.

## Prerequisites

- Complete `08-sparse-indexes`.

## Learning objectives

- Apply age- and size-based retention at segment granularity.
- Protect the active segment from deletion.
- Define deterministic ordering when several segments qualify.
- Distinguish an expired requested offset from an empty read at the log end.

## Theory

Retention changes the earliest available logical offset but does not renumber surviving
records. Deleting whole immutable segments avoids rewriting active history. A lagging
consumer needs an explicit out-of-range result containing the earliest available offset so
it can choose recovery policy.

## Concepts to teach

- Retention horizon
- Segment-granular deletion
- Earliest available offset
- Offset-out-of-range errors
- Injectable clocks for deterministic tests
- Open-file and deletion considerations across platforms

## Constraints

- Never delete the active segment.
- Never renumber offsets after deletion.
- Size policy removes oldest eligible segments first.
- Age tests use a controllable clock or metadata seam, not sleeps.
- Index files are removed consistently with their segments.

## Suggested progression

Expose earliest available offset, implement size retention, then age retention with a
deterministic clock. Test all-history-fits, several deletions, active-only history, restart,
and fetches below, at, and above the retained boundary.

## Completion conditions

- Size and age retention delete only eligible closed segments.
- Active data remains writable and readable after retention.
- Fetch below the retained boundary returns an explicit error and earliest offset.
- Fetch at the current end remains a successful empty result.
- Validators pass without time-dependent flakes.

## On completion, persist

Record retention evaluation order, time source, deletion rules, and expired-offset API.

## Optional deeper paths

Discuss legal retention, tombstones, and compaction only to distinguish them from this
course's deletion policy.
