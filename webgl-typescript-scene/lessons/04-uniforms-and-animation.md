---
id: 04-uniforms-and-animation
title: Uniforms, time and the render loop
design_refs: [api-boundary, shader-convention]
validators: [typecheck, build, browser-check]
---

## Purpose

Turn a one-shot draw into a time-dependent rendering loop and distinguish uniform from
per-vertex data.

## Prerequisites

Lesson `03-vertex-data` is complete.

## Learning objectives

- Set a uniform on the active program
- Drive animation with `requestAnimationFrame`
- Use frame timestamps rather than fixed frame increments
- Separate one-time setup from per-frame work

## Theory

Uniforms are constant for all shader invocations in a draw call. Animation redraws discrete
frames from time-dependent state; refresh rate is not a clock. Resource creation does not
belong in the per-frame loop.

## Concepts to teach

Uniform locations, active programs, frame timestamps, delta versus absolute time, render-loop
structure and per-frame clearing.

## Constraints

Animate a visible property through a uniform. Do not allocate GPU resources per frame. Handle
a missing required uniform location explicitly.

## Suggested progression

Add a scalar uniform, make it affect the shader, introduce the frame callback, and verify that
refreshing or resizing does not create multiple loops.

## Completion conditions

The animation is time-based, continues smoothly at varying refresh rates, and draws from one
intentional loop. Build and type check pass. The learner can classify current data as
per-vertex, per-draw or per-frame.

## On completion, persist

Record the render-loop timing convention.

## Optional deeper paths

Pause rendering when the document is hidden and discuss when on-demand rendering is preferable.
