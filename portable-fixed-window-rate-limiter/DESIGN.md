# Design

## Behavioural contract {#behavioural-contract}

The limiter receives a client key and answers whether one request is allowed. For a
configured positive limit `N` and window duration `W`, the first `N` requests for one
key in a window are allowed and later requests in that same window are rejected.

The public result must make the allow/reject decision observable. Returning extra
information such as remaining capacity is a learner choice, not a course requirement.

## Window semantics {#window-semantics}

Windows are fixed, non-overlapping intervals aligned to a shared time origin. A request
exactly at a boundary belongs to the new window. This is a fixed-window counter, not a
sliding window and not a token bucket.

## State model {#state-model}

State is held independently per client key and only in memory. An implementation may
store the current window identifier and count, or an equivalent representation. It
must not scan all recorded requests to decide one request.

## Time source {#time-source}

Business logic obtains time through a replaceable clock, function, interface, or
equivalent idiom in the selected language. Tests control that source directly and do
not wait for wall-clock time.

## Concurrency boundary {#concurrency-boundary}

The main path requires correct sequential behaviour. Synchronisation for concurrent
callers is an optional extension because the mechanisms and useful tests vary strongly
between languages and runtimes.
