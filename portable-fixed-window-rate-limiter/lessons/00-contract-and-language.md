---
id: 00-contract-and-language
title: Make the decision precise
design_refs: [behavioural-contract]
validators: [project-runs]
---

## Purpose

Choose the implementation language, establish its smallest conventional project, and
turn “rate limit a client” into an observable contract before writing the algorithm.

## Prerequisites

The learner can create and run a small program in at least one programming language.
No particular language, build tool, or repository layout is assumed.

## Learning objectives

- Separate a behavioural contract from an implementation strategy
- Choose an API shape that is idiomatic in the selected language
- Establish a fast run-and-test feedback loop

## Theory

A rate limiter is easy to describe vaguely and surprisingly easy to implement with a
different boundary rule than its caller expects. Start with observable behaviour: a
client key goes in, an allow/reject decision comes out, and a configured budget says
how many decisions may be positive within one window.

The course names two of those values and uses the same names everywhere. `N` is the
request limit: the number of requests the limiter allows for one client key in one
window. `W` is the window duration: the length of the interval that budget applies to.
Both symbols belong to the course, not to the learner's prior knowledge, so define them
in these terms the first time either one comes up — before using `N` or `W` in a task,
an example, or a test. Every later lesson relies on them.

Do not teach the counting implementation yet. Help the learner express examples for
the first allowed request, the last allowed request, and the first rejected request.

## Concepts to teach

- behavioural contract
- the symbols `N` (request limit) and `W` (window duration)
- public API versus internal representation
- language-idiomatic project and test structure

## Constraints

- Let the learner choose any general-purpose implementation language.
- Use a local in-memory component, not an HTTP service.
- Configure a positive request limit `N` and a positive window duration `W`.
- Make the decision callable repeatedly for different client keys.
- Do not prescribe class-oriented or functional structure across languages.

## Suggested progression

- Ask which language the learner wants and why; adapt all later guidance to it.
- Offer to set the project up yourself, and say what you would create before you
  create it: the smallest conventional runnable project for that language, its test
  target, and version control if the learner wants it. Wait for the learner to accept;
  create nothing under their files until they have. On acceptance, create that skeleton
  yourself and show it to them — the skeleton only, never any part of the limiter, which
  stays theirs to write. If the learner would rather do it themselves, let them, and
  continue once it runs.
- Define the public contract in prose and then as an API signature or stub.
- Add one focused test or executable example covering the budget within one window.

## Completion conditions

- The project runs using the normal toolchain for the selected language.
- The public API accepts a client key and exposes an allow/reject decision.
- A test or executable example states that the first `N` requests are allowed and
  request `N + 1` is rejected.
- The learner can explain which parts are contract and which remain implementation
  choices.

## On completion, persist

Record the selected language, toolchain commands, public API contract, limit, and
window duration in the instance state. Append durable API choices to `DESIGN.md`.

## Optional deeper paths

Discuss alternative return values such as remaining capacity or reset time only if the
learner asks; they are not needed by the main path.
