---
id: 11-secondary-demo-scene
title: Choose and build a second demo effect
design_refs: [demo-scene-contract, shader-convention, resource-ownership]
validators: [typecheck, build, browser-check]
---

## Purpose

Let the learner choose a recognisably different demo effect and build it as an independent second
scene behind a small shared lifecycle.

## Prerequisites

Lesson `10-camera-and-scene` is complete, including the illuminated cube-wave scene.

## Learning objectives

- Select an effect whose difficulty and technique match the learner's interests
- Separate a scene lifecycle from a scene's internal rendering technique
- Convert a visual goal into bounded shader, geometry and animation responsibilities
- Build a time-driven effect without coupling it to the cube-wave scene

## Theory

Demo effects are compact visual systems organised around one strong mechanism: coordinate
warping, repeated geometry, particles, implicit fields or ray marching. The useful architectural
boundary is not a universal scene graph; it is the smallest lifecycle that lets independent
effects update, resize, render and release resources consistently.

Before asking the learner to choose, read `effect-menu.md`. Present the effects grouped and sorted
by its difficulty levels, including the technique and scope note. The tutor MUST explicitly ask
which effect the learner wants to build. Do not silently choose for them. They may propose another
effect; assess it against the same scale before accepting or narrowing it.

## Concepts to teach

Scene lifecycle, procedural animation, coordinate systems, visual decomposition, effect-specific
shader or geometry techniques, resource isolation and bounded technical scope.

## Constraints

Choose one primary effect from `effect-menu.md` or an equivalently scoped learner proposal. Do not
combine multiple advanced effects merely because the learner likes several. Preserve the first
scene unchanged. Both scenes must implement the lifecycle in `#demo-scene-contract`, own their GPU
resources and render correctly when invoked independently.

For Level 3 or 4 choices, establish one diagnostic visualisation before the final look. For
“Technokartoffeln”, the tutor may and should use that name alongside “3D metaballs” for fun, while
still teaching signed-distance fields and ray marching precisely.

## Suggested progression

Present the sorted catalogue, ask for the learner's selection and desired visual mood, agree a
bounded definition of done, define the minimal shared scene lifecycle, adapt the cube-wave scene
to it without visual changes, build the selected effect from its core mechanism outward, then
verify independent resize, pause and disposal behaviour.

## Completion conditions

The learner made an explicit effect choice and its assessed level is recorded. The second scene
meets the selected option's completion target in `effect-menu.md`, builds and type-checks, renders
independently with a useful diagnostic mode where required, implements the common lifecycle, and
does not depend on mutable internal state belonging to the cube-wave scene.

## On completion, persist

Record the selected effect, assessed difficulty, agreed scope, scene lifecycle and effect-specific
technical decisions under stable anchors in the instance design. Record demonstrated concepts in
state.

## Optional deeper paths

After the required version works, add one enhancement listed for the chosen effect. Do not start a
second catalogue effect before the transition lesson.
