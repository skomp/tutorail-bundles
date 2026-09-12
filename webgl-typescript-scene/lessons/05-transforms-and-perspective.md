---
id: 05-transforms-and-perspective
title: From local coordinates to perspective
design_refs: [matrix-convention, shader-convention]
validators: [typecheck, build, browser-check]
---

## Purpose

Move from clip-space drawing to a genuine 3D coordinate pipeline.

## Prerequisites

Lesson `04-uniforms-and-animation` is complete.

## Learning objectives

- Distinguish local, world, view, clip and normalised device coordinates
- Compose model, view and projection matrices in the course convention
- Use perspective projection and understand the role of `w`
- Animate an object's model transform

## Theory

Geometry begins in local space. The model transform places it in the world, the view transform
expresses it relative to the camera, and projection maps the view frustum into clip space.
Perspective emerges through homogeneous division, not by manually shrinking distant vertices.

## Concepts to teach

Vectors, homogeneous coordinates, matrix composition order, translation, rotation, scale,
view space, perspective field of view, aspect ratio and near/far planes.

## Constraints

Use `gl-matrix`; do not implement a matrix library. Send matrices through uniforms and preserve
the convention in `DESIGN.md`. Render 3D geometry even though occlusion is not correct yet.

## Suggested progression

Create a cube or other simple volume, add model then view then projection transforms, predict
the result of changing each, and update aspect ratio after canvas resize.

## Completion conditions

A rotating 3D object is visible with plausible perspective and correct aspect ratio. The learner
can trace a sample vertex through the named spaces and explain near-plane clipping qualitatively.

## On completion, persist

Record any concrete transform helpers and reaffirm or append the adopted coordinate convention.

## Optional deeper paths

Visualise orthographic projection and compare it without changing the main scene.
