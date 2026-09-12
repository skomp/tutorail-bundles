---
id: 18-finish-the-scene
title: Compose and validate the final scene
design_refs: [scene-boundary, lighting-model, texture-convention, resource-ownership, packaged-model, post-processing-pipeline]
validators: [typecheck, build, browser-check, git-diff]
---

## Purpose

Turn the accumulated demonstrations into one coherent interactive scene and validate the
renderer as a system.

## Prerequisites

Lessons `15-render-to-texture`, `16-bloom` and `17-depth-reconstruction-and-ssr` are complete.

## Learning objectives

- Compose procedural and loaded geometry in one scene
- Audit geometry, lighting and post-processing state across the whole renderer
- Diagnose failures systematically rather than through random state changes
- Explain the complete path from asset bytes through reconstructed screen-space geometry

## Theory

Rendering bugs often arise at boundaries: stale state between passes, mismatched coordinate
spaces, incomplete asynchronous resources, wrong attachment layouts or incorrect canvas sizes.
Explicit geometry, effect and composition phases keep these boundaries inspectable.

## Concepts to teach

State auditing, pass ordering, asset readiness, resize integration, render-target cleanup,
black-screen debugging, effect isolation, visual validation and end-to-end pipeline reasoning.

## Constraints

The final demo must retain both independently renderable scenes and their transition. The lit 3D
scene must include the packaged duck and at least one reflective procedural mesh, a
controllable camera, perspective, depth testing, textured surfaces, ambient plus directional
lighting, bloom and SSR. Bloom and SSR must be independently toggleable and expose diagnostic
intermediate views. Retain model attribution and licences.

## Suggested progression

Choose a composition that makes reflections and bloom readable, integrate asynchronous loading,
tune camera and lighting, tune effects without hiding their artefacts, test resize and extreme
camera positions, audit allocations/state transitions, then perform deliberate geometry-pass and
post-processing failure investigations.

## Completion conditions

Type checking and production build succeed. Both scenes and their transition remain selectable.
All required objects render with correct perspective,
occlusion, texture orientation and lighting. Bloom remains seeded by intended bright surfaces; SSR
reflects visible content and fades invalid hits; both effects toggle cleanly; diagnostic views work;
camera and targets survive resize; no resource is created continuously per frame; and licence files
remain with the model. The learner can explain the end-to-end pipeline and isolate failures by pass.

## On completion, persist

Record final scene and effect decisions, demonstrated coverage topics, validator evidence and any
explicitly deferred improvements. Do not copy a source snapshot into state or design notes.

## Optional deeper paths

Profile pass costs with GPU timing where supported, or add one optional SSR refinement from the
previous lesson.
