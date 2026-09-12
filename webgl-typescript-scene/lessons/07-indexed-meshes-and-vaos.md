---
id: 07-indexed-meshes-and-vaos
title: Reusable indexed meshes
design_refs: [mesh-boundary, resource-ownership, api-boundary]
validators: [typecheck, build, browser-check]
---

## Purpose

Turn the one-off object into an explicit mesh representation reusable by procedural and loaded
geometry.

## Prerequisites

Lesson `06-depth-and-culling` is complete.

## Learning objectives

- Reuse vertices with an element/index buffer
- Capture attribute and index bindings in a vertex array object
- Separate CPU-side mesh data from GPU-side resources
- Define the shared `MeshData` boundary

## Theory

Indexed drawing separates vertex records from triangle topology. A VAO captures the attribute
interpretation and element-array binding needed for a draw. CPU data describes a mesh; uploaded
buffers and a VAO are its GPU representation.

## Concepts to teach

Indices, `drawElements`, index scalar types, VAOs, vertex deduplication trade-offs, mesh data,
GPU resources and explicit disposal.

## Constraints

Define `MeshData` with positions, normals, UVs and optional indices even if some attributes are
temporarily unused. Avoid a general engine hierarchy. Validate array lengths and supported index
types before upload.

## Suggested progression

Convert the procedural object to indices, bind its element buffer in a VAO, define `MeshData`,
write one upload path and one draw path, then ensure temporary resources can be deleted.

## Completion conditions

The procedural object renders through an indexed VAO-backed mesh. Its CPU and GPU forms have
distinct types or clearly distinct responsibilities, invalid attribute lengths are rejected,
and the learner can explain what state the VAO does and does not capture.

## On completion, persist

Add a stable design anchor documenting the concrete `MeshData` shape and resource ownership.

## Optional deeper paths

Compare smooth and hard edges, where identical positions may still require distinct vertices.
