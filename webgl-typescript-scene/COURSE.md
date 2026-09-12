# Learn WebGL 2 by Building a 3D Scene

## Goal

Build a small interactive scene that renders procedural geometry and an open-licensed
glTF model with textures, perspective, depth, a movable camera and directional lighting.
The renderer uses the WebGL 2 API directly. TypeScript, npm and esbuild provide the thin
development shell; no rendering engine or web framework hides the graphics pipeline.

## Prerequisites

The learner should already be comfortable with TypeScript modules, functions, classes or
plain objects, typed arrays, promises and basic npm commands. No prior graphics programming,
GLSL or linear-algebra implementation is assumed. Familiarity with vectors is helpful but
not required.

## Teaching philosophy

Every concept should become visible on screen as soon as possible. Begin with the smallest
complete rendering pipeline, then add one source of complexity at a time. Ask the learner
to predict visual results before running code and to diagnose deliberately localised errors
from shader logs, WebGL state and images.

The learner writes the renderer. The tutor may explain APIs and small fragments, but provides
complete solution code only when requested. Keep tasks narrow enough that failures have a
small search space. Use the browser image as evidence alongside type checking and builds;
a successful build alone does not establish correct rendering.

The course uses column vectors and a documented matrix convention throughout. Do not turn
matrix arithmetic into a second course: teach what each transform means and use `gl-matrix`
for the implementation.

## Course map

1. Establish the plain HTML, TypeScript and esbuild workspace.
2. Acquire a WebGL 2 context and make canvas pixels match display pixels.
3. Compile shaders, link a program and draw the first triangle.
4. Move vertex data into GPU buffers and connect attributes.
5. Use uniforms and a render loop to animate the image.
6. Move into 3D with model, view and projection transforms.
7. Make occlusion meaningful with depth testing and face culling.
8. Represent reusable indexed meshes with vertex array objects.
9. Sample a 2D texture and handle image orientation and sampler state.
10. Add normals and directional plus ambient lighting.
11. Turn reusable meshes, instancing and a camera into a travelling cube-wave scene.
12. Choose and build a second scene around a classic demo effect.
13. Render both scenes independently and transition between them.
14. Load the supplied glTF model through a parsing library.
15. Generalise render targets into an inspectable post-processing pipeline.
16. Extract and blur bright regions for bloom.
17. Reconstruct view-space positions from depth and build screen-space reflections.
18. Compose and validate the final multi-scene demo.

## Checkpoints

- **Pipeline checkpoint:** a GPU-buffer-backed triangle renders without console errors.
- **3D checkpoint:** an animated indexed object has correct perspective and occlusion.
- **Surface checkpoint:** texture and directional lighting respond correctly to transforms.
- **Scene checkpoint:** a controllable camera renders multiple scene objects.
- **Demo checkpoint:** a learner-chosen classic effect forms a distinct second scene and a
  selectable image-space transition connects both scenes.
- **Post-processing checkpoint:** off-screen rendering, bloom and depth-based SSR are inspectable
  as separate passes.
- **Final checkpoint:** the supplied duck model appears in the composed scene with attribution
  and the selected post-processing effects can be toggled for comparison.

## Topics this course must cover

- WebGL 2 context creation
- canvas drawing-buffer size and device-pixel ratio
- the programmable rendering pipeline
- clip space and normalised device coordinates
- vertex shaders
- fragment shaders
- GLSL types and precision
- shader compilation and program linking diagnostics
- GPU buffers
- vertex attributes
- primitive assembly
- draw calls
- WebGL state
- uniforms
- render loops and frame time
- vectors and coordinate spaces
- model, view and projection transforms
- perspective projection
- homogeneous coordinates
- depth buffers and depth testing
- face winding and back-face culling
- indexed drawing
- vertex array objects
- mesh representation
- texture coordinates
- texture upload and sampling
- texture filtering and wrapping
- mipmaps and power-of-two considerations
- normals and normal transformation
- ambient and directional diffuse lighting
- resize handling
- camera controls
- scene objects and per-object transforms
- instanced drawing
- per-instance attributes
- sine-wave spatial animation
- time-driven procedural demo effects
- independent scene lifecycles
- rendering multiple scenes to textures
- transition progress and easing
- image-space scene transitions
- asynchronous asset loading
- glTF model integration
- framebuffers and render targets
- full-screen post-processing passes
- multiple render targets
- high-dynamic-range intermediate colour
- separable blur and bloom composition
- depth textures
- depth linearisation
- inverse projection and view-space position reconstruction
- view-space reflection vectors
- screen-space ray marching
- screen-space reflection limitations and artefacts
- WebGL resource lifetime
- debugging black screens and visual errors

## Explicit boundaries

This course does not teach TypeScript fundamentals, general frontend application design,
React, a rendering engine, physically based rendering, shadows, skeletal animation, compute
shaders, WebGPU or a complete glTF implementation. Post-processing is deliberately limited to
the render-target pipeline, bloom and one depth-reconstructing screen-space reflection effect.
The optional loader lesson supports only the packaged model's documented subset and must say so
clearly.

## Optional path

`minimal-gltf-loader` is an optional lesson, offered while you are in lesson 14. It is not
part of the numbered sequence above, and declining it costs you nothing: you keep the
library-backed model loader that lesson builds. Taking it implements the narrow loader
behind the same `MeshData` boundary, so every later lesson and every WebGL concept is
identical either way.
