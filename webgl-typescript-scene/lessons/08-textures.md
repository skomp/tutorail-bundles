---
id: 08-textures
title: Texture coordinates and sampling
design_refs: [texture-convention, mesh-boundary, shader-convention]
validators: [typecheck, build, browser-check]
---

## Purpose

Give mesh surfaces image-based colour and make all texture state explicit.

## Prerequisites

Lesson `07-indexed-meshes-and-vaos` is complete.

## Learning objectives

- Upload an image into a 2D texture
- Pass UV coordinates to the fragment shader
- Bind texture units and sampler uniforms
- Explain wrapping, filtering, mipmaps and image orientation

## Theory

UV coordinates parameterise a 2D image over a surface. A texture object stores image levels and
sampling parameters; a sampler uniform selects a texture unit. Filtering chooses how discrete
texels contribute to a sample.

## Concepts to teach

Texture targets, texture units, samplers, UV interpolation, asynchronous images, placeholder
pixels, wrapping, minification, magnification, mipmaps and unpack orientation.

## Constraints

Use a tiny generated or packaged learning texture before the model asset. Make the vertical
orientation decision explicit. Keep rendering valid while an image is still loading.

## Suggested progression

Render UVs as colours, upload a labelled image, bind it through a sampler, test orientation,
then compare nearest and linear filtering and enable a valid mipmap policy.

## Completion conditions

The textured object has predictable orientation, remains renderable during load, and shows an
observable filtering difference under scale. The learner can trace a texture sample from vertex
attribute to fragment colour.

## On completion, persist

Record the chosen upload-orientation and sampler policies.

## Optional deeper paths

Discuss colour space at a conceptual level without building a full colour-management pipeline.
