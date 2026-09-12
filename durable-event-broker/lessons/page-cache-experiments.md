---
id: page-cache-experiments
title: Page-cache and durability experiments
optional: true
design_refs: [acknowledgement-contract, recovery-policy]
validators: [manual-behaviour]
---

## Purpose

Make the storage boundary behind the durability contract observable without changing the
contract into claims the operating system or device cannot guarantee.

## Prerequisites

- The learner has a persistent append path and has reached `04-durability-contract`.

## Learning objectives

- Distinguish user-space buffering, kernel page cache, filesystem state, and stable storage.
- Compare buffered writes, explicit file sync, and close under controlled runs.
- Inspect relevant system calls with a platform-appropriate tracing tool when available.
- Report environment-specific results without generalising them into universal guarantees.

## Theory

A write can complete after copying data into kernel memory. Closing a file and terminating
a process are not equivalent to power failure. Filesystems and devices differ in how they
honour flushes, and metadata durability may require separate reasoning from data durability.
The broker contract should state which operating-system primitive it waits for and the
failure boundary it intends to cover.

## Concepts to teach

- User-space buffers
- Operating-system page cache
- Data and metadata durability
- Sync-related system calls
- Process crash versus machine failure
- Measurement limits

## Constraints

- Experiments use a disposable broker data directory.
- No experiment requires privileged destructive actions or unsafe power interruption.
- Platform-specific tooling is optional; observable broker timing remains sufficient.
- Results include operating system, filesystem when known, storage context, and limitations.
- Do not weaken the main durability acknowledgement to obtain a better number.

## Suggested progression

Diagram the layers a record crosses, measure append and sync separately, and inspect the
system calls on a supported platform. Compare ordinary process termination and abrupt
process kill, then state what neither experiment can prove about sudden machine power loss.

## Completion conditions

- The learner can identify the layer at which each measured operation completes.
- Measurements compare at least buffered write and explicit sync paths.
- Any tracing evidence corresponds to the real broker append path.
- The written conclusion separates observation, inference, and untested failure boundaries.

## On completion, persist

Record environment, tools, operations observed, results, limitations, and any clarification
made to the acknowledgement contract.

## Optional deeper paths

Investigate directory synchronisation after creating or renaming segment files as a focused
design discussion before changing recovery behaviour.
