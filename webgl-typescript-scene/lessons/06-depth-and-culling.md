---
id: 06-depth-and-culling
title: Occlusion, depth and face orientation
design_refs: [api-boundary, matrix-convention]
validators: [typecheck, build, browser-check]
---

## Purpose

Make the 3D object visually coherent by configuring depth testing and optional face culling.

## Prerequisites

Lesson `05-transforms-and-perspective` is complete.

## Learning objectives

- Explain why submission order alone does not solve 3D visibility
- Enable, clear and configure the depth buffer
- Relate vertex winding to front and back faces
- Diagnose missing faces caused by inconsistent winding

## Theory

Depth testing compares each fragment with stored depth and conditionally updates the colour and
depth buffers. Back-face culling rejects consistently oriented triangles before fragment work.
Both behaviours are WebGL state, not shader magic.

## Concepts to teach

Depth attachment, depth clear, depth function, depth writes, face winding, front face and culling.

## Constraints

First observe the failure without depth testing. Clear depth on every frame. Enable culling only
after triangle winding is known to be consistent.

## Suggested progression

Capture the incorrect overlap, enable depth testing, rotate through several views, inspect mesh
winding, then enable and toggle back-face culling.

## Completion conditions

Faces occlude correctly from multiple angles and no required face disappears under the chosen
culling state. The learner can name the colour and depth buffers cleared each frame.

## On completion, persist

Record the depth function, front-face convention and culling decision.

## Optional deeper paths

Explore depth precision as near and far planes move apart.
