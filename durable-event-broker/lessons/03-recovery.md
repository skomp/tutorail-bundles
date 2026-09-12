---
id: 03-recovery
title: Persistent append and crash recovery
design_refs: [record-framing, recovery-policy, offset-semantics]
validators: [go-build, go-test, manual-behaviour]
---

## Purpose

Replace the in-memory history with an append-only file and make restart behaviour an
explicit part of correctness.

## Prerequisites

- Complete `02-record-framing` with a bounded defensive decoder.

## Learning objectives

- Append framed records to a file without rewriting prior records.
- Scan the file on startup and reconstruct the next logical offset.
- Recover the longest valid prefix after a torn tail write.
- Refuse silent recovery from corruption inside the valid prefix.

## Theory

Append-only layout simplifies recovery because valid history is a prefix. End-of-file at
a frame boundary is clean; end-of-file inside the final frame is a torn tail. A checksum
failure in the middle is different: skipping it would break offset continuity and conceal
data loss.

## Concepts to teach

- Append-only file access
- Short writes and exact-write loops
- Startup scanning
- Torn-tail recovery
- Tail damage versus interior corruption
- Resource lifetime and error wrapping

## Constraints

- The file is the source of truth; do not maintain a second durable representation.
- Recovery truncates only an invalid final frame.
- Interior corruption prevents normal startup and reports its position.
- Closing and reopening the log preserves records and next-offset assignment.
- Ordinary write success is not yet claimed as durable; that contract comes next.

## Suggested progression

Open or create the log, append encoded frames, and rebuild in-memory metadata on reopen.
Create deterministic tests that cut a valid file at several tail positions and another
that corrupts an interior frame. Add a manual kill/restart experiment after the tests.

## Completion conditions

- Restart preserves all complete records and resumes at the correct next offset.
- Every tested torn-tail cut recovers exactly the valid prefix and truncates the bad tail.
- Interior corruption is reported rather than skipped or truncated as though it were a tail.
- File descriptors close on success and error paths.
- Validators succeed and the learner reports the kill/restart observation.

## On completion, persist

Record file-open mode, exact-write strategy, startup scan outputs, and the boundary between
recoverable tail damage and fatal interior corruption.

## Optional deeper paths

Explore offline inspection or repair tooling, while keeping automatic recovery conservative.
