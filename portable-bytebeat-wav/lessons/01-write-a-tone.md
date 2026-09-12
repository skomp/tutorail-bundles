---
id: 01-write-a-tone
title: Put a tone in a WAV file
design_refs: [sample-model, wav-contract]
validators: [project-runs, tests-pass, output-wav]
---

## Purpose

Create the first audible artifact by generating a simple repeating waveform and
encoding it in a minimal, structurally valid WAV file.

## Prerequisites

Lesson `00-language-and-waveform` is complete and the project generates deterministic
8-bit samples.

## Learning objectives

- Connect waveform period to audible pitch
- Understand the few fields required by a PCM WAV container
- Write little-endian binary integers using the selected language's standard library
- Derive container sizes from sample data

## Theory

A repeating pattern becomes a pitch when its repetition rate falls in the audible
range. A square wave can be made by alternating between a low and high sample value for
equal spans of `t`. Its frequency is the sample rate divided by its period in samples.

WAV is a RIFF container. The minimal file for this course has a RIFF/WAVE header, a PCM
format chunk, and a data chunk. Several header values depend on channel count, sample
rate, bits per sample, and the actual number of data bytes. Multi-byte fields are
little-endian.

The learner should assemble the header through standard binary I/O facilities. Do not
give a complete byte-array solution unless explicitly requested.

## Concepts to teach

- period and frequency
- square waves
- RIFF/WAVE structure
- PCM format metadata
- little-endian encoding
- derived sizes

## Constraints

- Write the result to `output.wav`.
- Use mono, 8,000 Hz, unsigned 8-bit PCM.
- Derive RIFF and data sizes from the generated duration.
- Use standard-library binary and file I/O only.
- Generate a short file that is long enough to hear and quick to regenerate.

## Suggested progression

- Generate a square wave with a predictable period.
- Sketch the three required WAV regions before encoding fields.
- Write the header and then the sample bytes.
- Inspect the file size and, where available, use an installed file-inspection tool.
- Play the completed file with an existing player chosen by the learner.
- Add a focused check for header fields or total size appropriate to the language.

## Completion conditions

- `output.wav` exists and its size agrees with header plus sample data.
- A standard player or inspection tool recognises it as mono 8-bit PCM at 8,000 Hz.
- Playback produces the expected steady tone rather than silence or malformed noise.
- Relevant tests pass.
- The learner can explain how period determines the tone's frequency.

## On completion, persist

Record WAV layout decisions, exact artifact parameters, validation evidence, and the
chosen listening method in the instance state. Append any reusable binary-format
decisions to `DESIGN.md`.

## Optional deeper paths

If asked, inspect the header as hexadecimal or calculate a desired note frequency. Keep
music theory and general-purpose WAV support outside the required work.
