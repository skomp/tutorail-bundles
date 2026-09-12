---
id: 03-vertex-data
title: Moving vertices into GPU buffers
design_refs: [api-boundary, shader-convention, resource-ownership]
validators: [typecheck, build, browser-check]
---

## Purpose

Replace shader-generated positions with application-owned vertex data uploaded to the GPU.

## Prerequisites

Lesson `02-first-shader-program` is complete.

## Learning objectives

- Upload typed-array data to a buffer
- Describe attribute layout precisely
- Connect a buffer to a vertex-shader input
- Add per-vertex colour and observe interpolation

## Theory

A buffer is untyped storage until an attribute pointer interprets its bytes. Attribute state
includes component count, scalar type, normalisation, stride and offset. Varyings are
interpolated across a primitive before fragment shading.

## Concepts to teach

Typed arrays, buffer targets, usage hints, vertex attributes, attribute locations, layouts,
interleaved versus separate data and interpolation.

## Constraints

Use at least position and colour attributes. Make byte-based stride and offset calculations
explicit. Keep the vertex format simple enough to inspect manually.

## Suggested progression

Upload positions, connect the position attribute, then add colour data and pass it between
shader stages. Change one layout parameter intentionally and reason from the corrupted image.

## Completion conditions

The buffered triangle renders with an interpolated colour gradient. Build and type check pass,
and the learner can account for every attribute-layout argument in bytes.

## On completion, persist

Record the chosen temporary vertex layout and concepts demonstrated.

## Optional deeper paths

Compare interleaved and separate buffers without refactoring the main path.
