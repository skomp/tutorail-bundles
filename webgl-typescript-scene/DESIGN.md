# Renderer design

## Platform and toolchain {#platform-toolchain}

The target is a modern desktop browser with WebGL 2. The project is a plain HTML page.
npm manages dependencies, esbuild bundles TypeScript and serves the directory during
development, and `tsc --noEmit` performs strict type checking. There is no application
framework and no rendering engine.

## API boundary {#api-boundary}

All rendering uses `WebGL2RenderingContext` directly. Helper functions may make resource
creation safer, but must expose rather than conceal shader programs, buffers, vertex array
objects, textures, uniforms, state changes and draw calls.

## Mathematical convention {#matrix-convention}

The renderer uses right-handed coordinates, column vectors and matrices compatible with
`gl-matrix`. A clip-space position is computed as `projection * view * model * position`.
The camera looks down its local negative Z axis. Angles passed to matrix functions are radians.

## Shader convention {#shader-convention}

Shaders use GLSL ES 3.00 with explicit `in` and `out` variables. Attribute locations are
assigned explicitly in shader source or bound deterministically before linking. Shader and
program diagnostics are checked immediately and failure stops resource construction.

## Mesh boundary {#mesh-boundary}

Procedural geometry and loaded models converge on a renderer-owned `MeshData` representation.
Its required vertex semantics are position, normal and texture coordinate, with optional
indices and material texture information. File-format-specific objects do not cross into
draw code. The exact TypeScript shape is decided when the indexed-mesh abstraction is built.

## Resource ownership {#resource-ownership}

GPU resources have explicit owners and are deleted when replaced or no longer needed.
Creation helpers either return a complete usable resource or clean up and fail. The course
does not require a general resource manager, but it must not normalise leaking resources.

## Scene boundary {#scene-boundary}

A scene object combines reusable mesh GPU resources with a model transform. Camera state is
separate from object state. Per-frame rendering sets frame-wide state first and per-object
state immediately before each draw.

## First demo scene {#first-demo-scene}

The first scene is a field of instanced cubes whose vertical positions form travelling sine waves.
One cube mesh and one GPU resource set are reused across the field. Per-instance placement and
colour-phase data combine with frame time in the shader. A restrained orbit camera makes the wave
legible, and bright wave crests give later bloom and reflection lessons useful source material.

The exact grid dimensions, wave equation, palette and camera path are learner decisions. The scene
must remain understandable when animation is paused and must not create or upload a separate mesh
for every cube.

## Demo scene contract {#demo-scene-contract}

The lit 3D scene and learner-chosen secondary scene share a minimal lifecycle: initialise owned
resources, resize from explicit target dimensions, update from elapsed time and input, render to
the currently selected target, and dispose. The concrete TypeScript form is chosen when the
second scene is introduced. It must describe capabilities required by transitions without
becoming a general engine or forcing both scenes to share internal representation.

The secondary effect is a learner choice from the authored menu. That choice may change shaders,
geometry and buffers inside the second scene, but not the lifecycle boundary used by composition.

## Scene transition {#scene-transition}

Transitions render both scenes to separate colour targets and combine those images in a full-screen
pass controlled by normalised progress. Each scene continues updating during the transition unless
the learner deliberately documents a freeze policy. The first required transition may be a crossfade;
the learner then selects one characteristic demo transition whose parameters have defined behaviour
at progress zero and one.

## Lighting model {#lighting-model}

The required lighting model is intentionally small: a constant ambient term plus Lambertian
diffuse illumination from one directional light. Lighting is calculated in world space.
Specular reflection, multiple lights, shadows and PBR material evaluation are outside the
required path.

## Texture convention {#texture-convention}

Texture coordinates follow the model data. Image upload orientation is handled explicitly
and documented rather than corrected through unexplained UV changes. Colour textures are
treated as colour data; full colour-management and HDR pipelines are deferred.

## Asset-loading paths {#asset-loading-paths}

The required path uses `@gltf-transform/core` to read the packaged GLB and adapt its first
supported mesh primitive to `MeshData`. The optional path implements the same adaptation
directly for the narrow feature subset present in the packaged asset. Neither path changes
the renderer API.

## Post-processing pipeline {#post-processing-pipeline}

The scene first renders into off-screen colour and depth attachments. Later passes consume those
textures through a full-screen triangle. Bloom extracts bright colour, applies a separable blur
at reduced resolution and adds the result during composition. Screen-space reflections reconstruct
view-space position from sampled depth and ray-march projected reflection candidates against the
same depth representation. Every pass can be toggled or displayed independently for debugging.

SSR is intentionally approximate: it cannot reflect geometry absent from the current screen and
requires explicit policies for thickness, step size, maximum distance and edge fading. Those
limitations are part of the lesson rather than defects to conceal.

## Packaged model and licence {#packaged-model}

The course packages the Khronos glTF Sample Assets “Duck” GLB. The model files are licensed
under the SCEA Shared Source License 1.0; metadata supplied alongside them is CC BY 4.0.
The original licence and attribution material travels with the model lesson and must be
copied into the learner workspace with the asset.

## Deliberately unresolved decisions {#unresolved-decisions}

The concrete `MeshData` TypeScript shape, camera input mapping, scene composition and final
visual styling are learner decisions made at the lessons that need them. Record those choices
under new stable anchors in the instance's `DESIGN.md`.
