# Build a Durable Event Broker in Go

## Goal

Build a general-purpose event broker whose behaviour can be explained from its storage
and concurrency mechanisms. The finished broker stores opaque keyed records, assigns
partition-local offsets, survives abrupt termination, serves multiple topics and
partitions over HTTP, applies retention, exposes useful measurements, and maintains a
deliberately limited asynchronous follower.

The project uses JSON application logs as one visible workload, but JSON is not part of
the broker's record model. Later projects may interpret the same opaque payloads in other
ways.

## Intended learner

The course assumes an experienced programmer who is new to event-broker internals. It
does not teach basic programming. Go-specific concepts are introduced when the project
needs them, especially goroutines, channels, cancellation, file I/O, and binary encoding.

## Teaching philosophy

Every abstraction must earn its place on the working path. Begin with the smallest usable
log, observe a concrete limitation, and add the mechanism that resolves it. Do not create
unused interfaces, speculative packages, or declarations that leave `go test` noisy.

The tutor gives exactly one implementation task at a time. It explains the relevant
theory before asking for a change, does not provide solution code unless requested, and
advances only from validated evidence. Measurements and fault experiments are evidence,
not decoration: durability, batching, indexes, overload behaviour, and replication lag
must be observed rather than asserted.

## Main-path map

1. Run a broker with an in-memory append/fetch path.
2. Introduce partition-local logical offsets and replay.
3. Design a versioned, checksummed binary record frame.
4. Persist records and recover the longest valid prefix after interruption.
5. Define what an acknowledgement promises and measure explicit synchronisation.
6. Give one goroutine ownership of each partition's mutable append state.
7. Derive group commit from the latency and throughput cost of per-record sync.
8. Roll the log into immutable segments.
9. Add sparse indexes for offset lookup.
10. Delete complete closed segments under explicit retention rules.
11. Generalise the storage engine to topics and partitions.
12. Expose the broker through an HTTP transport that does not leak into storage.
13. Add long-poll consumption, bounded queues, cancellation, and overload behaviour.
14. Instrument and load-test the system using both opaque and JSON-log workloads.
15. Add a restartable asynchronous follower and expose the guarantees still missing.

## Milestones

### Replayable log

The learner can append records and replay them from logical offsets through an in-process
API.

### Crash-recoverable storage

The learner can interrupt a write, restart the process, and recover the valid prefix
without inventing or silently accepting a damaged record.

### Explicit durability

Acknowledgement timing has a documented contract, group commit is measured, and shutdown
does not strand callers.

### Networked broker

Independent producer and consumer processes can use multiple topics and partitions while
the broker enforces bounded resource use.

### Replicated boundary

A follower can resume copying a partition and report lag. A failure experiment proves
why asynchronous copying is not quorum durability or failover.

## Optional lessons

- **Property-based framing** explores arbitrary and truncated decoder inputs. It may be
  re-offered if the decoder proves unsafe outside hand-written examples.
- **TCP transport** implements a length-prefixed protocol without replacing HTTP or
  changing the broker core.
- **Page-cache experiments** investigate the boundary between a successful write and
  stable storage in more depth.

The course remains complete when every optional offer is declined.

**Complete is not the same as covered.** A learner who declines every offer finishes the
course: every main-path lesson's completion conditions are reachable without any optional
lesson, which is the obligation `bundle-format.md` section 13 places on an author. They do
not, however, meet everything the coverage list below names. Three of its topics are taught
only by an optional lesson:

- property-based record-framing tests — **Property-based framing**
- length-prefixed TCP protocols — **TCP transport**
- operating-system page-cache behaviour — **Page-cache experiments**

They are in the list because the course does teach them and a tutor may offer them. They
are not on the main path because the course finishes without them.

## Topics this course must cover

- opaque key/value records
- logical partition offsets
- replayable append-only logs
- binary record framing
- checksums
- partial-write recovery
- file synchronisation and durability acknowledgements
- Go goroutine ownership
- Go channels for ordered append requests
- cancellation and graceful shutdown
- batching and group commit
- log segments
- sparse offset indexes
- retention by complete segment
- topics and partitions
- keyed and unkeyed partition selection
- HTTP producer and consumer APIs
- long polling
- backpressure and overload
- broker metrics and load testing
- asynchronous replication
- replica lag
- missing quorum and failover guarantees
- property-based record-framing tests
- length-prefixed TCP protocols
- operating-system page-cache behaviour

## Explicit exclusions

This course does not implement Kafka protocol compatibility, leader election, synchronous
or quorum replication, replica promotion, split-brain prevention, consumer groups,
rebalancing, broker-managed consumer offsets, transactions, exactly-once processing, log
compaction, authentication, encryption, or production deployment. Those exclusions define
the hand-off to later projects rather than defects to conceal.

## Prerequisites

- Comfortable writing and testing non-trivial software in at least one language.
- Basic familiarity with Go syntax. The tutor may fill focused Go gaps as they arise.
- A local Go toolchain capable of running the race detector.
- No cloud account, container runtime, or external broker is required.
