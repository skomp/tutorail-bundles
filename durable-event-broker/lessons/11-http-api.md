---
id: 11-http-api
title: An HTTP producer and consumer API
design_refs: [transport-boundary, topic-partition-model, record-model]
validators: [go-build, go-test, go-vet, manual-behaviour]
---

## Purpose

Make the broker usable by independent processes while preserving a transport-neutral core.
HTTP is selected to keep the main path focused on broker behaviour rather than application
protocol framing.

## Prerequisites

- Complete `10-topics-and-partitions`.

## Learning objectives

- Adapt HTTP requests to the internal append, batch, fetch, and metadata operations.
- Preserve opaque payloads without assuming UTF-8 or JSON.
- Map domain errors to stable HTTP responses.
- Bound request bodies and close them correctly.

## Theory

Transport code owns parsing, limits, status codes, and response encoding; it does not own
storage semantics. An HTTP representation may encode binary fields for interchange without
changing what the broker stores. Batch append is a first-class operation because the
storage path already has batch behaviour.

## Concepts to teach

- Transport adapters
- HTTP request limits and cancellation
- Binary-safe representations
- Stable error contracts
- Batch APIs
- Test servers and black-box API tests

## Constraints

- HTTP handlers call the same broker operations used by in-process tests.
- Request bodies have explicit limits.
- Responses identify topic, partition, and assigned offsets.
- Fetch can carry arbitrary key and payload bytes safely.
- Storage packages do not import HTTP packages.
- Do not add long polling until the next lesson.

## Suggested progression

Define the smallest external contract, implement single append and bounded fetch, then batch
append and metadata. Add handler tests for success, malformed input, excessive bodies,
unknown resources, expired offsets, cancellation, and storage errors. Exercise the server
with small producer and consumer commands that use the HTTP API.

## Completion conditions

- Independent processes can append and fetch opaque records through HTTP.
- Batch append preserves per-partition result order and reports failure coherently.
- Domain errors map to documented stable status and body shapes.
- Malformed or excessive requests do not reach storage operations.
- Build, test, vet, and a manual producer/consumer run succeed.

## On completion, persist

Record routes, request and response representations, size limits, error mapping, and the
internal boundary handlers depend on.

## Optional deeper paths

The authored optional lesson `tcp-transport` adds a framed TCP protocol against the same
internal operations when the learner accepts it.
