---
id: stereo-bytebeat
title: Compose in two channels
design_refs: [sample-model, wav-contract, expression-boundary, stereo-layout]
validators: [project-runs, tests-pass, output-wav]
optional: true
---

## Purpose

Extend the working mono synthesiser to stereo and use independent left and right sample
functions to create an audible spatial relationship.

## Prerequisites

Lesson `02-bytebeat-rhythm` is complete and the mono WAV writer produces a valid,
audible file.

## Learning objectives

- Distinguish samples from multi-channel frames
- Interleave channel samples correctly
- Recalculate format fields that depend on channel count
- Design related rather than accidentally duplicated channel expressions

## Theory

In interleaved stereo PCM, one frame contains a left sample followed by a right sample.
At 8-bit depth, each frame therefore occupies two bytes. Channel count affects block
alignment and byte rate, while the data size counts all bytes across both channels.

Stereo is most informative when the channels share some structure but differ
intentionally—for example in one shifted or masked term—so the learner can hear the
relationship.

## Concepts to teach

- channels and sample frames
- interleaved PCM
- block alignment
- byte rate
- related signal design

## Constraints

- Keep unsigned 8-bit PCM at 8,000 frames per second.
- Interleave exactly one left and one right byte per frame.
- Update every WAV field affected by the channel count.
- Use two deterministic expressions with an intentional relationship.
- Preserve or retain tests for the mono logic where practical.

## Suggested progression

- Separate “sample at `t`” from “frame at `t`” in the design.
- Derive left and right values for a few known frames.
- Interleave them and update the header calculations.
- Inspect metadata, file size, and initial data bytes.
- Listen on stereo-capable output and refine one controlled channel difference.

## Completion conditions

- `output.wav` is recognised as two-channel 8-bit PCM at 8,000 Hz.
- Header sizes, byte rate, block alignment, and data length agree.
- Tests establish left-right interleaving for known frames.
- Playback presents an intentional audible difference between the channels.
- The learner can explain the distinction between sample rate and bytes per second.

## On completion, persist

Record the stereo layout, channel-expression relationship, recalculated header fields,
and validation evidence in the instance state and `DESIGN.md`.

## Optional deeper paths

If asked, discuss panning a mono source, more channels, or 16-bit stereo. Do not combine
those changes into this lesson's required work.
