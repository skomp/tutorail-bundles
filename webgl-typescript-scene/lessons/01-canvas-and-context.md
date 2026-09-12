---
id: 01-canvas-and-context
title: Canvas pixels and the WebGL 2 context
design_refs: [platform-toolchain, api-boundary]
validators: [typecheck, build, browser-check]
---

## Purpose

Take control of the drawing surface and establish the first observable WebGL state.

## Prerequisites

Lesson `00-project-setup` is complete.

## Learning objectives

- Request and validate a `webgl2` context
- Relate CSS size, drawing-buffer size and device-pixel ratio
- Set the viewport and clear the colour buffer
- Fail explicitly when WebGL 2 is unavailable

## Theory

The canvas element has a displayed size and an independent pixel buffer. WebGL draws into
that buffer through a stateful context. Clearing is a real GPU operation; CSS background
colour is not a substitute. The viewport maps normalised device coordinates onto pixels.

## Concepts to teach

Canvas sizing, device pixels, context acquisition, clear colour, buffer masks, viewport and
WebGL's state-machine model.

## Constraints

Use `WebGL2RenderingContext` directly. Centralise drawing-buffer resize logic and cap or
explain the chosen device-pixel-ratio policy. Do not create shaders yet.

## Suggested progression

Acquire the context, choose an unmistakable clear colour, resize the drawing buffer, set the
viewport, clear, and inspect the result at more than one browser-window size.

## Completion conditions

Type checking and build succeed. The canvas clears to the chosen colour, remains sharp after
resize, its backing dimensions match the documented policy, and a missing context produces a
useful error rather than a null dereference.

## On completion, persist

Record the drawing-buffer sizing policy and demonstrated context/state concepts.

## Optional deeper paths

Inspect context attributes and the browser's maximum viewport dimensions.
