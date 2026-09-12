---
id: 15-render-to-texture
title: Render the scene into textures
design_refs: [post-processing-pipeline, resource-ownership, scene-boundary]
validators: [typecheck, build, browser-check]
---

## Purpose

Insert an inspectable off-screen scene pass between geometry rendering and the canvas so later
image-space effects have explicit inputs.

## Prerequisites

Lesson `13-load-gltf-model` is complete. The optional lesson `minimal-gltf-loader` was taken or
declined; either way a working `MeshData` adapter exists.

## Learning objectives

- Create and validate a framebuffer
- Attach colour and depth textures with compatible dimensions and formats
- Render a full-screen triangle sampling an earlier pass
- Resize render targets without leaking GPU resources

## Theory

A framebuffer redirects draw output from the canvas to attached images. Post-processing is a
second rendering pipeline over those images. Framebuffer completeness is a precise compatibility
check, not proof that the resulting pixels are meaningful.

## Concepts to teach

Framebuffer objects, colour attachments, depth textures, attachment formats, completeness,
full-screen triangles, texture feedback hazards, viewport changes and render-target lifetime.

## Constraints

Build on the two-scene render-target work without replacing its transition boundary. Preserve the
existing scene shaders. Use one scene colour texture and one sampleable depth texture.
Never sample an attachment while writing to it. Restore or explicitly set framebuffer and viewport
state for every pass. Provide a direct-copy composition shader before adding effects.

## Suggested progression

Allocate attachments, check completeness, render the scene off-screen, display its colour through
a full-screen triangle, expose the depth texture as a diagnostic view, then integrate resize and
cleanup.

## Completion conditions

The direct-copy result matches the pre-framebuffer scene, colour and depth diagnostic views can be
selected, resize recreates attachments at the intended resolution without accumulating resources,
and an incomplete configuration produces a useful failure.

## On completion, persist

Record attachment formats, render-target sizing and pass ordering.

## Optional deeper paths

Measure the effect of rendering post-processing targets below device resolution.
