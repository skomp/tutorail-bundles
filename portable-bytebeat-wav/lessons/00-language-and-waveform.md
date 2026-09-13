---
id: 00-language-and-waveform
title: Turn time into samples
design_refs: [supported-tracks, sample-model, expression-boundary]
validators: [project-runs, tests-pass]
---

## Purpose

Choose a supported implementation track, establish a runnable project, and generate a
small deterministic sequence of sample values before dealing with files or playback.

## Prerequisites

The learner can run one of: Node.js with JavaScript or TypeScript, Python, Go, or the
Kotlin/JVM toolchain. No audio or signal-processing background is required.

## Learning objectives

- Understand digital audio as samples taken at a fixed rate
- Relate sample index `t` to elapsed time
- Reduce integer output into unsigned 8-bit PCM range
- Establish an idiomatic project and test loop in the chosen language

## Theory

At 8,000 samples per second, sample `t` represents `t / 8000` seconds after the start.
The program will calculate one integer for each `t`. In the main path, only its low
eight bits are stored, yielding values from 0 through 255.

Unsigned 8-bit PCM places its midpoint near 128. A constant sequence is silence; a
changing sequence moves a speaker cone and may become audible once encoded.

Teach integer-width and bitwise details as they actually behave in the selected
language. Do not assume that JavaScript numbers, Python integers, Go integers, and
Kotlin integers overflow or shift identically.

## Concepts to teach

- sample index
- sample rate
- unsigned 8-bit PCM
- masking to eight bits
- deterministic sequences
- selected-language integer semantics

## Constraints

- Ask the learner to choose TypeScript, JavaScript, Python, Go, or Kotlin before setup.
- Use 8,000 Hz mono unsigned 8-bit samples for the authored main path.
- Start without third-party packages.
- Generate enough values to inspect, but do not write a WAV file yet.
- Keep `t` as an integer sample index.

## Suggested progression

- Have the learner select the language track; it fixes project layout, run and test
  commands, and integer semantics for the rest of the course.
- Offer to create the smallest conventional runnable project for that track, and create
  it only once the learner accepts. If they would rather set it up themselves, let them.
- Generate a short sequence from a deliberately simple function of `t`.
- Reduce every value to 0–255 using an idiom correct for the language.
- Add a small deterministic test or inspectable assertion for several known samples.
- Ask the learner to predict how changing the expression changes the sequence.

## Completion conditions

- The project runs with the selected toolchain.
- It produces a deterministic sequence of values, all in the range 0–255.
- At least a few known indices are checked automatically or by clear executable
  evidence.
- The learner can explain the relationship among `t`, sample rate, and elapsed time.

## On completion, persist

Record the selected track, run/test commands, integer semantics that mattered, and
sample parameters in the instance state. Append durable project choices to `DESIGN.md`.

## Optional deeper paths

If asked, explain signed PCM, bit depth, quantisation, or aliasing briefly. Do not require
them before the learner has heard the generated output.
