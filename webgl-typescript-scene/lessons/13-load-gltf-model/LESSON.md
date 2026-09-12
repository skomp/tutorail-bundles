---
id: 13-load-gltf-model
title: Load a glTF model without changing the renderer
design_refs: [asset-loading-paths, mesh-boundary, packaged-model, resource-ownership]
validators: [has-model, typecheck, build, browser-check]
---

## Purpose

Bring a real authored asset into the existing renderer while keeping file-format concerns at
the edge of the program.

## Prerequisites

Lesson `12-scene-transition` is complete and the concrete `MeshData` anchor exists in the
instance design.

## Learning objectives

- Load a GLB asynchronously with `@gltf-transform/core`
- Extract one supported mesh primitive into the existing `MeshData` representation
- Preserve position, normal, texture-coordinate and index semantics
- Upload loaded data through the same GPU path as procedural data

## Theory

glTF separates scene structure, mesh primitives, accessors, materials, images and transforms.
The parsing library owns format decoding; the course adapter owns the boundary between decoded
content and renderer data. A successful parse does not guarantee that every optional glTF
feature is supported by this renderer.

## Concepts to teach

GLB containers, scenes, nodes, mesh primitives, accessors, attribute semantics, indices,
materials, textures, asynchronous loading, validation and adapter boundaries.

## Constraints

Before starting, copy every file under `model/` to a repository-root `models/` directory:
`Duck.glb`, `LICENSE.md`, `SCEA.txt` and `ATTRIBUTION.md`. Read `model/ATTRIBUTION.md` when
introducing the asset and retain all four files together.

Use `@gltf-transform/core` only for asset parsing and traversal, never for rendering. Support
the packaged model first. Reject missing required attributes with useful errors. Do not expose
library types to the renderer or attempt complete glTF feature support.

## Suggested progression

Fetch and parse `models/Duck.glb`, inspect its scene and first mesh primitive, adapt accessors to
`MeshData`, handle its base-colour texture, upload through the established mesh path, then place
the duck as a normal scene object.

## Completion conditions

The model and all licence files exist under `models/`. Type checking and build succeed. The duck
renders with correct geometry, orientation, texture and lighting through the same draw path as
procedural meshes. Asset failure produces a visible or logged diagnostic. No glTF-Transform type
appears in core rendering interfaces.

## On completion, persist

Record the supported glTF semantics, chosen scene/primitive traversal policy and any deliberate
unsupported features. Record the model attribution in the project documentation.

## Optional deeper paths

The optional lesson `minimal-gltf-loader` replaces the parsing-library adapter with one you
write. The tutor offers it here; it is not required for WebGL coverage or the final scene.
