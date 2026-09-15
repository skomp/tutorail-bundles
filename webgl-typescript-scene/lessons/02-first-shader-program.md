---
id: 02-first-shader-program
title: The smallest programmable pipeline
design_refs: [api-boundary, shader-convention]
validators: [typecheck, build, browser-check]
---

## Purpose

Render one triangle with the smallest complete WebGL 2 shader pipeline.

## Prerequisites

Lesson `01-canvas-and-context` is complete.

## Learning objectives

- Explain the vertex and fragment shader stages
- Compile GLSL ES 3.00 and link a program
- Read shader and program diagnostic logs
- Draw a triangle whose positions originate in the vertex shader

## Theory

Each vertex invocation emits a homogeneous clip-space position `(x, y, z, w)`, whose fourth
component `w` is the homogeneous scale factor. Primitive assembly forms a triangle; rasterisation
produces fragments; the fragment shader emits a colour. Division by `w` produces normalised device
coordinates before viewport mapping.

## Concepts to teach

Shader stages, GLSL version and precision, clip space, the homogeneous `w` component, NDC,
compilation, linking, program use, primitive assembly and `drawArrays`.

## Constraints

Generate three positions from `gl_VertexID`; GPU buffers arrive next lesson. Check compile and
link status and include diagnostic logs in thrown errors. Delete failed shader/program objects.

## Suggested progression

Write and compile each shader separately, link the program, select it, issue one triangle draw,
then deliberately break a shader briefly to observe the diagnostic path.

## Completion conditions

The build succeeds and one triangle appears at predicted clip-space positions. Restoring a
deliberate shader error restores the image, and the learner can explain the value written to
`gl_Position` and why the fragment shader needs a precision declaration.

## On completion, persist

Record the demonstrated pipeline stages and the shader failure-cleanup policy.

## Optional deeper paths

Vary `w` deliberately to explore homogeneous division.
