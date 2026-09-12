---
id: 09-normals-and-lighting
title: Normals and directional light
design_refs: [lighting-model, matrix-convention, mesh-boundary]
validators: [typecheck, build, browser-check]
---

## Purpose

Make shape legible through a small lighting model instead of baked vertex colour.

## Prerequisites

Lesson `08-textures` is complete.

## Learning objectives

- Interpret a normal as a surface orientation
- Transform normals correctly under object transforms
- Compute Lambertian diffuse light with a directional source
- Combine ambient light, diffuse light and texture colour

## Theory

The dot product measures alignment between a unit surface normal and a unit light direction.
Negative values face away and are clamped. Normals are directions, not positions, and under
non-uniform scaling require the inverse-transpose normal matrix.

## Concepts to teach

Normals, normalisation, dot product, directional light, Lambertian diffuse response, ambient
term, world space and normal matrices.

## Constraints

Calculate required lighting in world space. Include ambient and one directional diffuse term.
Do not add specular, shadow or PBR terms on the required path.

## Suggested progression

Visualise normals as colour, add the light vector and diffuse term, combine with texture colour,
rotate the model, then test a non-uniform scale to expose incorrect normal transformation.

## Completion conditions

Illumination changes predictably as object or light rotates, back-facing surfaces receive only
ambient light, and non-uniform scale does not visibly corrupt the lighting. The learner can
explain the spaces used by every vector in the dot product.

## On completion, persist

Record light direction convention, intensity choices and normal-transform implementation.

## Optional deeper paths

Compare flat and smooth normals on procedural geometry.
