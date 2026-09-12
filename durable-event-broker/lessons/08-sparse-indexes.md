---
id: 08-sparse-indexes
title: Sparse indexes for offset lookup
design_refs: [sparse-index-contract, segment-layout, offset-semantics]
validators: [go-build, go-test, manual-behaviour]
---

## Purpose

Avoid scanning from the beginning of a large segment for every fetch while keeping the log
authoritative and the index rebuildable.

## Prerequisites

- Complete `07-segments`.

## Learning objectives

- Map selected logical offsets to physical file positions.
- Seek to a floor entry and scan forward to the requested offset.
- Choose an indexing interval and measure its trade-off.
- Rebuild an absent or invalid index from the log.

## Theory

A sparse index narrows a scan; it does not replace record validation. The useful lookup is
the greatest indexed offset not greater than the target. Density trades index size and
write work against scan length.

## Concepts to teach

- Sparse indexes
- Logical-to-physical mapping
- Floor lookup
- Binary search
- Rebuildable derived state
- Index density measurements

## Constraints

- Index entries identify offsets and byte positions within exactly one segment.
- The log remains the source of truth.
- Corrupt or stale indexes are rejected or rebuilt, never trusted over the log.
- Fetch returns records at or after the requested logical offset.
- Index updates must respect the append durability ordering documented by the learner.

## Suggested progression

Measure or count frames scanned by the existing fetch. Add periodic index entries, floor
lookup, and forward scan. Test exact hits, between-entry lookups, boundaries, missing
indexes, and corruption. Compare scan work at more than one interval.

## Completion conditions

- Correct fetch results are identical with and without the index.
- Tests cover exact, in-between, first, last, and cross-segment targets.
- Deleting an index and reopening rebuilds usable derived state.
- A damaged index cannot make damaged log data appear valid.
- The learner records index format, update ordering, density, and observed scan reduction.

## On completion, persist

Record index entry format, interval, floor-lookup rule, rebuild policy, and measurements.

## Optional deeper paths

Compare fixed-record-count and fixed-byte-distance indexing policies.
