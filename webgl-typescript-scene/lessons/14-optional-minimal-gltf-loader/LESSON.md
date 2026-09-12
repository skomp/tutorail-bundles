---
id: 14-optional-minimal-gltf-loader
title: Optional — decode the packaged GLB yourself
design_refs: [asset-loading-paths, mesh-boundary, packaged-model]
validators: [typecheck, build, browser-check]
---

## Purpose

Optionally look below the parsing library and implement only the GLB/glTF subset needed by the
packaged model. This is a file-format lesson, not a prerequisite for later WebGL concepts.

## Prerequisites

Lesson `13-load-gltf-model` is complete, including a working library-backed adapter.

## Learning objectives

- Describe the GLB header and JSON/BIN chunks
- Resolve buffer views and accessors into typed vertex/index data
- Map glTF attribute semantics into `MeshData`
- State exact format limitations instead of implying general glTF support

## Theory

A GLB is a binary container with a header and typed chunks. glTF accessors describe typed,
strided views over buffer-view byte ranges. Correct decoding combines offsets, component types,
counts, vector shapes and alignment. The full specification contains many cases this lesson
deliberately excludes.

For the exact supported subset and the cases that must be rejected, read `supported-subset.md`
before proposing implementation tasks.

## Concepts to teach

Binary headers, little-endian reads, JSON chunks, binary chunks, buffer views, accessors,
component types, byte offsets, byte stride, index arrays, image buffer views and explicit scope.

## Constraints

The learner may skip this lesson without implementing anything; record that choice and advance.
If taken, keep the library adapter available until the new decoder produces equivalent visible
output. Implement only `supported-subset.md`, reject everything else clearly, and return the same
`MeshData` boundary. Do not grow the renderer around glTF structures.

## Suggested progression

Choose or skip the path. If chosen, parse and validate the GLB envelope, decode JSON, locate the
binary chunk, implement accessor extraction, adapt the supported primitive, decode its embedded
image, compare with the library-backed result, and switch adapters only after equivalence.

## Completion conditions

Either the learner explicitly chooses to skip and the working library path remains intact, or:
type checking and build pass; the minimal loader renders the same packaged duck; malformed or
unsupported input fails explicitly; and its documentation does not claim general glTF support.

## On completion, persist

Record whether the lesson was skipped or taken. If taken, add a stable anchor specifying the
implemented subset and rejection behaviour; retain the parsing library as a reference path unless
the learner deliberately removes it.

## Optional deeper paths

Compare one omitted feature with the glTF 2.0 specification, but do not implement it on the main
course path.
