---
id: 13-observability-and-load
title: Observe the broker under load
design_refs: [observability-contract, group-commit, backpressure-contract]
validators: [go-build, go-test, go-test-race, manual-behaviour]
---

## Purpose

Turn internal claims about batching, latency, capacity, and storage into visible evidence
under controlled workloads.

## Prerequisites

- Complete `12-long-polling-and-overload`.

## Learning objectives

- Instrument the mechanics that explain broker behaviour.
- Build repeatable opaque-record and JSON-application-log workloads.
- Separate offered load, accepted load, durable throughput, and consumed throughput.
- Interpret latency distributions, queue depth, batch size, and sync time together.

## Theory

Metrics are useful when they connect observed behaviour to a mechanism. Throughput without
offered load hides saturation; latency averages hide tails; queue depth without rejections
hides lost demand. The JSON workload demonstrates general usefulness but remains opaque to
the broker.

## Concepts to teach

- Counters, gauges, and histograms
- Latency percentiles
- Coordinated omission awareness
- Load generation
- Saturation and bottlenecks
- Structured application logs as opaque payloads
- Reproducible performance notes

## Constraints

- Instrumentation must not parse application payloads.
- Metrics distinguish append admission, durable acknowledgement, and fetch.
- The load generator has bounded concurrency and a documented workload.
- Results include environment and configuration; they are not universal benchmarks.
- Avoid optimisation until measurements identify a mechanism worth changing.

## Suggested progression

Add measurements around queueing, batching, write, sync, fetch, segments, retention, and
errors. Build a load command with fixed-duration and fixed-count modes, then add a JSON log
producer representing several fictional services. Run below saturation, near saturation,
and above capacity; explain the change in metrics and errors.

## Completion conditions

- The broker exposes the measurements required by `#observability-contract`.
- The load generator reports offered, accepted, acknowledged, rejected, and consumed work.
- A JSON-log workload passes through without broker-specific parsing.
- The learner records at least three load regimes with configuration and environment.
- Observations connect queue depth, batches, sync duration, latency, and overload.

## On completion, persist

Record metric names and meanings, workload definitions, environment, results, identified
bottleneck, and any evidence-backed tuning decision.

## Optional deeper paths

Use `pprof` to inspect a measured CPU or allocation bottleneck. Do not perform speculative
zero-copy refactors without evidence.
