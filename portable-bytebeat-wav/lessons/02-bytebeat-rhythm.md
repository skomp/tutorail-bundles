---
id: 02-bytebeat-rhythm
title: Find rhythm in the bits
design_refs: [sample-model, expression-boundary, wav-contract]
validators: [project-runs, tests-pass, output-wav]
---

## Purpose

Replace the regular test tone with a compact Bytebeat expression and connect its
arithmetic and bitwise structure to what the learner hears.

## Prerequisites

Lesson `01-write-a-tone` is complete and `output.wav` is recognised and audible.

## Learning objectives

- Evaluate an integer expression once per sample
- Hear multiplication of `t` as pitch and shifted `t` as slower-changing structure
- Use masks and bitwise combinations intentionally
- Experiment while preserving deterministic output

## Theory

Bytebeat treats the sample index itself as musical raw material. Multiplying `t`
changes how quickly low bits repeat. Right shifts expose values that change at half,
quarter, or slower rates. AND, OR, and XOR combine patterns; retaining the low eight
bits supplies the deliberately wrapping output characteristic.

The exact expression matters less than the reasoning loop: predict a structural change,
generate the file, listen, and relate the result back to part of the expression.

Explain precedence before the expression becomes dense. Encourage parentheses that
make intent visible even when the language's precedence rules would produce the same
result.

## Concepts to teach

- Bytebeat
- low-bit repetition
- right shifts as slower-changing control values
- bitwise AND, OR, and XOR
- masking and wraparound
- operator precedence
- experimental feedback loops

## Constraints

- Keep one deterministic expression or named sample function.
- Do not evaluate arbitrary user-supplied source text.
- Preserve the working WAV writer and file parameters.
- Use explicit parentheses when combining arithmetic and bitwise operators.
- Make changes one at a time so the learner can attribute audible effects.

## Suggested progression

- Begin with a minimal expression based on `t` and listen to its ramp-like result.
- Multiply `t` and compare the perceived pitch.
- Introduce one right-shifted term and listen for slower structure.
- Combine one additional masked or bitwise term.
- Add tests for selected `t` values to keep the expression portable and deterministic.
- Ask the learner to explain which subexpression contributes pitch or rhythm.

## Completion conditions

- `output.wav` contains the Bytebeat-generated samples and remains structurally valid.
- The expression uses at least one shift and one intentional bitwise combination.
- Selected sample values are checked deterministically.
- The learner can connect at least two parts of the expression to audible behaviour.
- The learner can explain why only the low eight bits are written.

## On completion, persist

Record the current expression or function name, observations from the controlled
experiments, and language-specific integer behaviour in the instance state.

## Optional deeper paths

If asked, discuss aliasing, classic Bytebeat expression families, or visualising the
sample stream. Avoid turning exploration into a catalogue of unexplained formulas.
