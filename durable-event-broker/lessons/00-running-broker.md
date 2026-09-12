---
id: 00-running-broker
title: A running broker with an in-memory log
design_refs: [record-model]
validators: [go-build, go-test, go-vet]
---

## Purpose

Establish the shortest vertical path through the project: a running Go process can append
an opaque record and fetch it again. The first implementation stays in memory so the
learner can define useful broker operations before storage mechanics arrive.

## Prerequisites

- A working Go toolchain.
- Comfort with structs, methods, slices, errors, and tests in some language.

## Learning objectives

- Create a small Go module and executable without speculative package structure.
- Represent an optional key and opaque payload without treating them as text or JSON.
- Separate the executable entry point from a directly testable in-process broker API.

## Theory

An event broker stores records for later replay; it is not merely a live notification
channel. Even the in-memory version therefore exposes append and bounded fetch operations.
The payload remains bytes so application formats stay outside the broker.

Introduce Go packages only when both executable and tests need the code. Explain slice
aliasing at the API boundary: retaining caller-owned byte slices lets later mutation
rewrite history accidentally.

## Concepts to teach

- Go module and package boundaries
- Opaque byte payloads
- Defensive ownership of byte slices
- Append versus fetch operations
- Table-driven tests

## Constraints

- Begin from a fresh repository.
- Keep one in-memory log; topics, partitions, files, channels, and networking come later.
- Appending must not retain mutable caller-owned key or payload storage.
- Fetch must not expose mutable storage owned by the log.
- Do not add interfaces with only one implementation unless a present test boundary needs one.

## Suggested progression

Create the module and a minimal broker executable. Add a directly testable record and log
implementation. Append several opaque records, fetch them, and verify insertion order and
copying behaviour. Keep the executable on the same path by making it exercise the API.

## Completion conditions

- `go build ./...`, `go test ./...`, and `go vet ./...` succeed.
- A test appends and fetches multiple records in insertion order.
- A test proves mutation of caller or returned byte slices cannot alter stored records.
- The executable exercises the same implementation used by the tests.
- No declared production function or type is disconnected from the running path.

## On completion, persist

Record the chosen module path, package boundary, record representation, and byte-ownership
rule in the learner instance's design and state.

## Optional deeper paths

Explore why immutable strings and mutable byte slices create different ownership choices
in Go. Do not replace the broker payload with strings.
