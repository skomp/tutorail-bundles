---
id: 17-depth-reconstruction-and-ssr
title: Reconstruct 3D positions for screen-space reflections
design_refs: [post-processing-pipeline, matrix-convention, scene-boundary]
validators: [typecheck, build, browser-check]
---

## Purpose

Use depth to recover geometric information in a post-processing shader, then apply it in a
screen-space reflection effect whose strengths and blind spots are visible.

## Prerequisites

Lesson `16-bloom` is complete. The off-screen pass must provide depth and a world- or view-space
normal texture; add the normal attachment before reflection marching.

## Learning objectives

- Convert a sampled depth value back through NDC into view-space position
- Explain why inverse projection is required and homogeneous division occurs again
- Derive a view-space reflection ray from position and normal
- March the ray in view space while comparing projected samples with scene depth
- Identify and mitigate characteristic SSR artefacts

## Theory

The depth buffer stores a non-linear projection of view-space depth. A screen-space UV plus depth
reconstructs a clip-space point; multiplying by the inverse projection and dividing by `w` recovers
view-space position. SSR advances a reflected ray, projects candidates into screen UVs and looks
for a crossing against reconstructed scene depth. It has no information about off-screen or hidden
geometry.

## Concepts to teach

Depth linearisation, inverse projection, NDC reconstruction, normal buffers, reflection vectors,
view-space ray marching, reprojection, hit testing, thickness bias, maximum distance, edge fade,
self-intersection, missed geometry and temporal instability.

## Constraints

Perform reconstruction and ray comparisons in one documented coordinate space. Add a view-space
normal attachment with a defined encoding. Begin with a reconstruction diagnostic that visualises
position or linear depth. Bound loop iterations for WebGL shader compilation and performance.
Expose step count, thickness and maximum distance as controlled parameters. SSR must be toggleable
and must fade rather than smear invalid/off-screen hits.

## Suggested progression

Add and inspect the normal target, reconstruct and visualise linear/view-space depth, reconstruct
positions, verify them by camera motion, derive the reflection ray, display projected ray steps,
add depth-crossing detection, refine the first hit locally, sample reflected colour, then add edge,
distance and grazing-angle fades.

## Completion conditions

The reconstruction diagnostic remains spatially coherent under camera movement and resize. A
reflective procedural surface shows plausible reflections of visible scene content. Off-screen
and missing hits fade safely; bounded marching cannot hang the shader; SSR can be disabled without
changing the base scene; and the learner can explain at least four failure modes inherent to SSR.

## On completion, persist

Record depth/normal encodings, reconstruction equations and the chosen march, hit and fade policies.
Record observed limitations rather than treating them as unfinished correctness bugs.

## Optional deeper paths

Add binary-search hit refinement, roughness-dependent blur or temporal accumulation, one at a time.
