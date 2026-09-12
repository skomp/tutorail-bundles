---
id: property-based-framing
title: Property-based tests for record framing
optional: true
design_refs: [record-framing, recovery-policy]
validators: [go-build, go-test]
---

## Purpose

Strengthen the binary codec against inputs the hand-written examples did not anticipate,
then repair any unsafe assumptions in the framing implementation.

## Prerequisites

- The learner has designed and implemented the record codec from `02-record-framing`.

## Learning objectives

- Express round-trip and decoder-safety properties independently of particular examples.
- Generate bounded arbitrary records and byte slices.
- Shrink a failure to a useful counterexample.
- Convert every discovered bug into a stable regression test.

## Theory

Example tests check cases the author selected. Property-based tests quantify an invariant
over a generated input space. For a binary codec, two useful properties are that decoding
an encoded valid record returns the same logical record, and that decoding arbitrary bytes
returns a bounded result or error without panic or excessive allocation.

Generators must respect intentional format limits for valid records. Arbitrary-byte tests
do the opposite: they treat every field as attacker-controlled. Shrinking matters because
a small failing frame reveals the faulty assumption better than a long random blob.

## Concepts to teach

- Properties versus examples
- Generators and bounds
- Shrinking
- Round-trip invariants
- Fuzzing support in the Go toolchain or a justified property library
- Regression tests from counterexamples

## Constraints

- The learner chooses Go's built-in fuzzing or a maintained property-testing library after
  comparing what the required properties need.
- Generated valid records stay within documented maximum sizes.
- Arbitrary-byte decoding has a finite test resource budget.
- A panic, excessive allocation, invalid acceptance, or round-trip mismatch is a failure.
- Repairs happen in the framing implementation named by `repair_in`, not as test exclusions.

## Suggested progression

State the properties in plain language, add the valid-record round trip, then exercise the
decoder with arbitrary and truncated bytes. Inspect any reduced counterexample, repair the
codec, and retain a deterministic regression case before continuing generation.

## Completion conditions

- A generated round-trip property covers keyed and unkeyed opaque records.
- An arbitrary-byte property demonstrates that the decoder does not panic.
- Generated lengths cannot request unbounded allocations.
- Every discovered defect has a deterministic regression test.
- The normal `go test ./...` suite remains deterministic and succeeds.

## On completion, persist

Record the properties, generation bounds, chosen tooling, counterexamples found, repairs,
and retained regression cases. Mark `frame-decoder-breaks-on-arbitrary-input` resolved only
after the evidence that triggered the detour has been rerun successfully.

## Optional deeper paths

Run longer fuzzing campaigns outside the ordinary deterministic validator and preserve any
new corpus entries that expose distinct behaviour.
