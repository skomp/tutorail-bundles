# Design

## Record model {#record-model}

A record contains an optional opaque key and an opaque byte payload. The broker assigns
the logical offset and append timestamp. It does not parse JSON or attach application
meaning to the payload. Headers and schema registries are outside the first project.

## Offset semantics {#offset-semantics}

Offsets are monotonically increasing logical record numbers scoped to one topic-partition.
They are not byte positions and are never global across the broker. Fetch starts at the
first available record whose offset is greater than or equal to the requested offset.

## Record framing {#record-framing}

Persistent records use a versioned, length-delimited frame with enough lengths to decode
the optional key and payload, plus a checksum covering the fields needed to reject a torn
or corrupted record. Exact field widths and byte order are chosen during the framing
lesson and recorded here in the learner instance.

## Recovery policy {#recovery-policy}

Recovery accepts the longest consecutively valid prefix of a segment. An incomplete or
invalid final frame may be truncated. Corruption before the tail is not silently skipped;
startup reports it and refuses to invent continuity.

## Acknowledgement contract {#acknowledgement-contract}

The durable append operation acknowledges only after the record's batch has been written
and explicitly synchronised according to the chosen storage API. The contract describes
what the program requests from the operating system and does not overclaim the physical
behaviour of every storage device.

## Partition ownership {#partition-ownership}

One goroutine owns each open partition's mutable append state, including its next offset,
active segment, index updates, and pending acknowledgements. Callers communicate through
bounded request channels. Reads may use immutable closed segments and carefully published
active-state snapshots without mutating append state.

## Group commit {#group-commit}

The owner may combine concurrent append requests into a batch, write their frames in
offset order, synchronise once, and acknowledge the included requests afterward. Batch
size and maximum collection delay are bounded and remain explicit tuning choices.

## Segment layout {#segment-layout}

A partition is an ordered sequence of segment files. Each segment is named by its base
logical offset. Only the newest segment is open for append; older segments are immutable.
Segment rollover is based on a configurable size threshold suitable for deterministic
tests.

## Sparse index contract {#sparse-index-contract}

An index maps selected logical offsets to physical positions in one segment. Fetch seeks
to the greatest indexed offset not exceeding the target and scans forward. The log remains
authoritative: an index can be rebuilt and must never make an invalid log valid.

## Retention semantics {#retention-semantics}

Retention removes complete closed segments, never individual records from the active
segment. Size- and age-based limits are evaluated at segment granularity. Fetching an
expired offset returns the earliest available offset explicitly rather than masquerading
as an empty result.

## Topic and partition model {#topic-partition-model}

A topic owns one or more partitions. A keyed append chooses a partition deterministically
from the key and a documented stable hash. Unkeyed appends use an explicit distribution
strategy. Clients address offsets per topic-partition; the broker stores no consumer-group
state in this course.

## Transport boundary {#transport-boundary}

Storage and broker operations are exposed through an internal Go API that is independent
of HTTP or TCP. HTTP is the default external transport. The optional TCP transport calls
the same operations and may not fork the storage implementation.

## Backpressure contract {#backpressure-contract}

Every queue introduced by the broker is bounded. When capacity or a caller's deadline is
exhausted, the broker returns an explicit overload or cancellation result. It does not
create unbounded goroutines or silently drop acknowledged records.

## Observability contract {#observability-contract}

Measurements include append latency, acknowledgement latency, batch size, request-queue
depth, sync duration, bytes and records fetched, segment count, earliest available offset,
and replica lag. Metrics names and export format are chosen during the observability lesson
and recorded in the learner instance.

## Replication boundary {#replication-boundary}

The follower is asynchronous and read-only. It fetches from the leader beginning at its
next local offset, preserves broker-assigned record metadata, retries after interruption,
and reports lag. It does not participate in acknowledgements, elect a leader, accept
producer traffic, or promote itself. Therefore a leader failure may lose records already
acknowledged but not yet copied.
