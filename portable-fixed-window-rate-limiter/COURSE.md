# Build a Fixed-Window Rate Limiter

## Goal

Build a small, reusable in-memory rate limiter in a language you choose. The
finished program decides whether a named client may perform an action, enforces a
fixed request budget per time window, and has deterministic tests for its contract.

The main path is designed for roughly 60–90 minutes. It deliberately avoids web
frameworks, persistence, and distributed coordination: the point is to examine a
small piece of professional software closely enough that its semantics are hard to
misread.

## Teaching approach

The learner makes the API decisions and writes every implementation. The tutor gives
one task at a time, inspects the actual project, and asks for explanations where tests
alone cannot establish intent. It adapts commands, file layout, naming conventions,
and test style to the selected language without changing the behavioural contract.

The tutor must not provide solution code unless the learner explicitly requests it.
When a check fails, diagnose the smallest relevant issue and keep the learner working
on the current task.

## Main path

1. **Contract and language** — establish a runnable project and make the observable
   decision precise.
2. **Windowed counting** — implement per-client fixed-window state using injected time.
3. **Boundaries and evidence** — attack the edge cases, explain the trade-offs, and
   demonstrate the finished behaviour.

## Checkpoints

- After lesson 00: the API contract is precise enough to test independently of its
  implementation.
- After lesson 01: the happy path and window reset work under a controllable clock.
- After lesson 02: boundary and isolation tests pass and the learner can explain what
  the algorithm does not guarantee.

## Optional lessons

- **Concurrent callers** *(optional)* — make the decision atomic under the concurrency
  model of the selected language and demonstrate it with a meaningful test.

## Topics this course must cover

- implementation-language selection
- behavioural API contracts
- fixed-window rate limiting
- per-client state
- dependency injection for time
- deterministic tests
- boundary conditions
- client isolation
- algorithmic trade-offs
- concurrency safety

## Out of scope

Distributed rate limiting, persistence, web-server integration, production telemetry,
and alternative algorithms are outside the main course. The learner may discuss them,
but the tutor should not quietly turn them into required work.
