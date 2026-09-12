---
id: tcp-transport
title: A framed TCP transport
optional: true
design_refs: [transport-boundary, backpressure-contract, record-model]
validators: [go-build, go-test, go-test-race, manual-behaviour]
---

## Purpose

Add a compact streaming transport that exposes the realities hidden by HTTP: messages need
framing, reads and writes may be partial, and connection lifetime must participate in
cancellation and shutdown.

## Prerequisites

- The internal broker API and HTTP adapter from `11-http-api` exist.

## Learning objectives

- Design a versioned length-prefixed request and response protocol.
- Decode several messages from one connection without assuming read boundaries.
- Handle short reads, short writes, malformed lengths, deadlines, and disconnects.
- Reuse broker operations without forking storage or acknowledgement semantics.

## Theory

TCP is an ordered byte stream, not a message channel. One write need not correspond to one
read, and a read may contain part of a frame or several frames. Length-prefix validation
must happen before allocation. A persistent connection also makes request correlation and
shutdown explicit.

## Concepts to teach

- Byte-stream framing
- Partial reads and exact-read helpers
- Protocol versions and operation codes
- Request correlation
- Connection deadlines and cancellation
- Per-connection resource bounds
- Graceful server shutdown

## Constraints

- The protocol has a documented maximum frame size and version.
- All broker actions call the same internal operations as HTTP.
- The decoder makes no assumptions about network read boundaries.
- One malformed connection cannot crash the broker.
- Connection and request concurrency are bounded.
- HTTP remains available and unchanged.

## Suggested progression

Define a minimal append and fetch envelope, implement exact framed I/O, and test using a
connection that deliberately fragments and combines writes. Add request identifiers if
more than one outstanding request is supported. Propagate disconnect and deadlines, then
exercise concurrent connections and shutdown under the race detector.

## Completion conditions

- TCP append and fetch produce the same domain results as HTTP.
- Tests cover frames split across reads and several frames delivered in one read.
- Oversized, truncated, unknown-version, and unknown-operation requests fail safely.
- Disconnect and shutdown release resources without goroutine leaks.
- Race-enabled tests and a manual cross-process run succeed.

## On completion, persist

Record wire version, frame envelope, size limit, operation set, correlation model,
connection bounds, deadlines, and shutdown behaviour.

## Optional deeper paths

Measure HTTP and TCP only with comparable semantics and payloads; do not treat protocol
overhead as the broker's storage throughput.
