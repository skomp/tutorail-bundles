---
id: 12-scene-transition
title: Transition between independent scenes
design_refs: [demo-scene-contract, scene-transition, resource-ownership]
validators: [typecheck, build, browser-check]
---

## Purpose

Connect the fixed cube-wave scene and learner-chosen effect through an image-space transition
without coupling either scene's internals to the other.

## Prerequisites

Lesson `11-secondary-demo-scene` is complete and both scenes render independently.

## Learning objectives

- Render two independent scenes into separate colour targets
- Express transition progress independently from frame time
- Compose scene textures in a full-screen shader
- Preserve exact endpoints while applying easing or a selected transition pattern

## Theory

A transition operates on complete scene images. Each scene renders as usual into its own target;
a composition pass samples both. Normalised progress selects the endpoints and drives the blend.
Easing changes timing, while masks, displacement or geometric wipes change spatial selection.

Before selecting the characteristic transition, read `transition-menu.md` and ask the learner
which style fits their two scenes. A plain crossfade is built first as the diagnostic baseline.

## Concepts to teach

Off-screen colour targets, framebuffer completeness, full-screen triangles, texture sampling,
normalised progress, easing, transition masks, render ordering and scene independence.

## Constraints

At progress zero the output must equal the first scene; at one it must equal the second. Neither
scene may manipulate the other's internal resources. The transition owns its targets and resizes
and disposes them explicitly. Keep a crossfade mode after the selected transition works.

## Suggested progression

Render each scene to its own target, display each directly, implement crossfade with manual progress,
add time-based direction and easing, present `transition-menu.md`, ask for a choice, then implement
and validate the selected transition at endpoints and intermediate values.

## Completion conditions

Each scene and render target can be displayed independently. Crossfade and one learner-selected
transition work in both directions, preserve exact endpoints, respond correctly after resize and
do not leak resources. Scene update/freeze behaviour during transitions is documented.

## On completion, persist

Record the selected transition, progress/easing convention, target formats, resize policy and
whether inactive scenes continue updating.

## Optional deeper paths

Sequence transitions automatically or make one transition parameter react to the selected effect.
