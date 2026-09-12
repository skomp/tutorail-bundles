---
id: 07-segments
title: Rolling the log into segments
design_refs: [segment-layout, record-framing, recovery-policy]
validators: [go-build, go-test]
---

## Purpose

Replace the indefinitely growing file with a sequence of manageable segment files while
preserving one logical partition log.

## Prerequisites

- Complete `06-group-commit`.

## Learning objectives

- Name and order segments by base logical offset.
- Roll before appending a batch that would exceed the configured target.
- Keep only the active segment mutable.
- Recover segment ordering and validate continuity on startup.

## Theory

Segmentation creates units for retention, indexing, replication, and inspection. Segment
size is a policy target rather than a promise that no frame ever crosses it: a single valid
frame may be larger than the target but still below the maximum record size.

## Concepts to teach

- Base offsets
- Active versus closed segments
- Segment discovery and ordering
- Rollover boundaries
- Cross-segment offset continuity
- Atomic creation and close behaviour

## Constraints

- Segment filenames sort or parse deterministically by base offset.
- Existing closed segments are never reopened for append.
- Startup rejects overlapping, duplicated, or discontinuous segment histories.
- A batch is not split in a way that violates its durability acknowledgement.
- Tests use small configured thresholds rather than writing large fixtures.

## Suggested progression

Introduce a segment type around the existing single-file mechanics, then make a partition
manage an ordered collection. Add rollover with tiny deterministic limits, reopen tests,
and invalid-directory-layout tests.

## Completion conditions

- Appending across rollover produces multiple correctly named segments.
- Fetch and recovery preserve one continuous logical sequence across them.
- Restart selects only the final segment as active.
- Invalid overlap, duplicate base offset, and gap cases are reported.
- Validators pass.

## On completion, persist

Record naming, target-size semantics, rollover timing, active-segment rule, and startup
continuity checks.

## Optional deeper paths

Discuss preallocation and filesystem allocation without making either part of correctness.
