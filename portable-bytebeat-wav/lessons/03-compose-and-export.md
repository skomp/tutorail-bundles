---
id: 03-compose-and-export
title: Shape a tiny composition
design_refs: [wav-contract, expression-boundary, composition-scope, generated-live-playback-extension]
validators: [project-runs, tests-pass, output-wav]
---

## Purpose

Turn the experiment into a short original composition, verify the artifact from end to
end, and offer clearly bounded ways to continue.

## Prerequisites

Lesson `02-bytebeat-rhythm` is complete and the learner can explain the current
expression's main audible structures.

## Learning objectives

- Use sample-derived time to create sections or controlled variation
- Make an intentional compositional change rather than random expression growth
- Validate a generated binary artifact independently of listening alone
- Distinguish the authored course from environment-specific extensions

## Theory

A composition needs change over a longer timescale than one waveform period. Integer
division or shifting can derive a section index from `t`; that index may select between
expressions or alter one term. Abrupt transitions are acceptable in Bytebeat, but they
should be intentional.

Listening establishes that the artifact is meaningful, while structural inspection and
deterministic tests establish that it is reproducible and valid. Both forms of evidence
matter.

## Concepts to teach

- coarse time and musical sections
- deterministic composition
- end-to-end artifact validation
- subjective versus objective completion criteria
- bounded optional extensions

## Constraints

- Keep the piece deterministic and reasonably short.
- Create at least two recognisably different sections or one deliberate evolving rule.
- Preserve mono unsigned 8-bit PCM at 8,000 Hz on the main path.
- Do not require live audio libraries or device APIs.
- Keep the final output at `output.wav`.

## Suggested progression

- Decide what should change over the duration and derive a coarse time value.
- Add one intentional section change or evolving control term.
- Regenerate and listen from beginning to end.
- Run tests and inspect the final WAV metadata and duration.
- Ask the learner to explain the composition in terms of `t` and its subexpressions.
- After the main-path completion conditions are met, make the authored stereo offer from
  the manifest. The mono course is finished by then, so a later two-channel `output.wav`
  does not disturb this lesson's completion conditions.
- After the main-path completion conditions are met, also offer a generated live-playback
  side lesson. Explain that it is outside the 60–90 minute estimate. Generate it only
  after the learner accepts and after asking for language/runtime, operating system,
  package manager, and streamed synthesis versus automatic file playback.

## Completion conditions

- `output.wav` is a valid mono 8-bit PCM WAV at 8,000 Hz with the intended duration.
- It contains at least two recognisable sections or one deliberate evolving structure.
- All deterministic sample and format tests pass.
- The learner can explain how coarse time changes the output and identify which parts
  of the result are subjective musical choices.
- The core project remains usable without third-party audio playback dependencies.

## On completion, persist

Record final duration, composition structure, validation commands/evidence, and the
learner's explanation in the instance state. Record whether the authored stereo lesson
and generated live-playback extension were declined, deferred, or accepted using the
runner's normal progress mechanisms.

## Optional deeper paths

Besides the explicit stereo and generated live-playback offers, discuss fade envelopes,
16-bit PCM, waveform visualisation, or expression input only if asked. Each can become a
learner-requested generated side lesson; none changes completion of the authored course.
