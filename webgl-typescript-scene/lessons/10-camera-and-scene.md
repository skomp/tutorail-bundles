---
id: 10-camera-and-scene
title: Build the illuminated cube-wave scene
design_refs: [scene-boundary, matrix-convention, resource-ownership, first-demo-scene]
validators: [typecheck, build, browser-check]
---

## Purpose

Turn the renderer into its first complete demo scene: an illuminated field of cubes moving as a
travelling wave beneath a controllable or gently orbiting camera.

## Prerequisites

Lesson `09-normals-and-lighting` is complete.

## Learning objectives

- Keep view/camera state separate from model transforms
- Reuse one mesh with multiple object transforms
- Draw repeated geometry efficiently with instancing
- Distinguish frame-wide, per-mesh and per-instance data
- Implement bounded, understandable camera interaction

## Theory

Moving a camera changes the inverse transform used to express world coordinates in view space.
A scene object references shared mesh resources and contributes its own model transform. Instanced
drawing applies one mesh to many instances in one draw, with per-instance attributes advancing at
a different divisor from per-vertex attributes. Spatial phase offsets turn one time function into
a travelling wave rather than moving every cube identically.

## Concepts to teach

Camera pose, view matrix, orbit controls, scene objects, resource reuse, instanced drawing,
attribute divisors, per-instance data, sine waves, spatial phase and per-frame state.

## Constraints

Build the cube field from one indexed cube mesh and one instanced draw call. Store only stable
per-instance data in its buffer; calculate time-varying wave displacement in the shader. Use an
orbit camera, whether automatic, interactive or both. Avoid entity-component systems and scene
graphs. Keep lighting and texture behaviour from the preceding lessons visible.

## Suggested progression

Extract camera state, render a small fixed set of instances, move placement into a divisor-backed
instance attribute, expand to a grid, derive vertical displacement from time and grid position,
add crest-dependent colour or brightness, orbit the camera, and verify resize behaviour.

## Completion conditions

The scene shows a coherent travelling wave across a grid of lit cubes. It uses one cube mesh and
one instanced draw call, remains legible when time is frozen, and exposes bright crests suitable
for later bloom. Camera motion does not alter the wave model, resize remains correct, and input
cannot trivially place the camera in an unrecoverable state.

## On completion, persist

Add stable anchors for the camera mapping, cube-grid layout, wave equation, instance-data layout
and chosen palette.

## Optional deeper paths

Add pointer lock or inertial orbiting only if it does not obscure the rendering work.
