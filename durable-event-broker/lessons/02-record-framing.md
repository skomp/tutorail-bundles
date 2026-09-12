---
id: 02-record-framing
title: A versioned binary record frame
design_refs: [record-model, offset-semantics, record-framing]
validators: [go-build, go-test]
---

## Purpose

Define the durable bytes before writing them to a file. The frame must delimit variable
data, reject damage, and leave room to recognise incompatible future versions.

## Prerequisites

- Complete `01-offsets-and-replay`.

## Learning objectives

- Design a deterministic binary frame for variable-length records.
- Choose and document field widths, byte order, checksum coverage, and size limits.
- Encode and decode without trusting unbounded lengths from input.
- Distinguish malformed, truncated, unsupported, and checksum-invalid data.

## Theory

A persistent format is an API to future versions of the program. Length prefixes make
frames skippable and detectable; a version identifies interpretation; a checksum detects
damage but does not repair it. Every decoded length is untrusted input and must be checked
before allocation or slicing.

## Concepts to teach

- Binary encoding and byte order
- Length-delimited frames
- Format versioning
- Checksums and their limits
- Defensive decoding and size bounds
- Round-trip and malformed-input testing

## Constraints

- The frame carries offset, append timestamp, optional key, opaque payload, version, and checksum.
- Define a maximum frame size and reject larger declarations before allocation.
- The decoder must never panic on arbitrary input.
- Encoding the same record produces the same bytes.
- Do not write to disk yet; keep the codec independently testable.

## Suggested progression

Write the format down, including byte order and checksum range. Implement encoding, then
decoding with explicit errors. Test empty keys and payloads, binary zero bytes, maximum
accepted sizes, truncation at several boundaries, version mismatch, and corruption.

## Completion conditions

- Round-trip tests cover keyed and unkeyed records with arbitrary byte payloads.
- Corrupt checksum, unsupported version, impossible length, and truncated frame are distinguishable.
- No malformed input causes a panic or unbounded allocation.
- The concrete frame decision is recorded under `#record-framing` in the learner design.
- `go build ./...` and `go test ./...` succeed.

## On completion, persist

Record exact frame layout, byte order, maximum size, checksum algorithm and coverage, and
the decoder's error categories.

## Optional deeper paths

The authored optional lesson `property-based-framing` exercises the decoder beyond
hand-written cases when the learner accepts it.
