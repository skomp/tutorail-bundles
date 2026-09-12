# Secondary-scene effect catalogue

Present these levels in order. Difficulty measures the new graphics reasoning required at this
point in the course, not how impressive an effect can look after artistic tuning.

## Level 1 — approachable

### Plasma

- **Technique:** combine sine waves in a full-screen fragment shader and map the field through a palette.
- **Completion target:** animated, resolution-independent plasma with a deliberate palette.
- **Enhancement:** polar-coordinate or domain-warped plasma.

### Starfield flight

- **Technique:** point sprites or quads advance and wrap in depth; perspective controls size and speed.
- **Completion target:** stable forward flight with recycled, depth-cued stars and no per-frame resources.
- **Enhancement:** velocity streaks.

### Raster-bar horizon

- **Technique:** layer soft horizontal bands displaced and coloured by periodic functions.
- **Completion target:** several independently moving bars with intentional colour mixing.
- **Enhancement:** curve the bands into a synthwave horizon.

## Level 2 — moderate

### Infinite textured tunnel

- **Technique:** polar-coordinate mapping, longitudinal repetition and animated sampling.
- **Completion target:** convincing forward motion plus a controllable bend or wobble.
- **Enhancement:** synchronised rings or lighting pulses.

### Particle vortex

- **Technique:** stable particle attributes with analytic, time-driven orbital motion in the vertex shader.
- **Completion target:** thousands of particles forming a controllable vortex without buffer replacement.
- **Enhancement:** colour and point size driven by height or angular velocity.

### Wobbling planet

- **Technique:** periodically displace sphere vertices and update normals for the changing surface.
- **Completion target:** a continuously deformed, correctly lit sphere without cracks.
- **Enhancement:** atmosphere rim or latitude palette.

## Level 3 — challenging

### 2D metaballs — “Technokartoffeln Lite”

- **Technique:** sum inverse-distance influence fields per fragment, then contour the implicit surface.
- **Completion target:** smoothly merging blobs with a scalar-field diagnostic view.
- **Enhancement:** pseudo-lighting from the field gradient.

### Procedural heightfield flight

- **Technique:** displace a grid from a height function and derive normals from neighbouring samples.
- **Completion target:** coherent terrain motion with lighting that follows the generated surface.
- **Enhancement:** distance fog and multi-octave noise.

### Twisted SDF tunnel

- **Technique:** ray march a repeated signed-distance field after twisting its coordinate domain.
- **Completion target:** stable hits, estimated normals, depth shading and a step-count diagnostic.
- **Enhancement:** repeat a second primitive or palette by travelled distance.

## Level 4 — advanced

### 3D metaballs — “Technokartoffeln”

- **Technique:** smooth-min sphere SDFs, bounded ray marching and gradient-estimated normals.
- **Completion target:** merging animated forms with normal diagnostics and graceful misses.
- **Scope warning:** limit ball count; do not add reflections or volumetrics in this lesson.
- **Enhancement:** colour from contributing-ball weights.

### Ray-marched fractal object

- **Technique:** use one documented distance estimator inside a bounded ray marcher.
- **Completion target:** a stable framed fractal with iteration/step diagnostics and safe parameters.
- **Scope warning:** deriving a new fractal is out of scope.
- **Enhancement:** orbit-trap colouring.

### Procedural city fly-through

- **Technique:** spatial hashing and repeated cells create buildings using instancing or ray marching.
- **Completion target:** repeatable city blocks, depth cues and a bounded or looping flight path.
- **Scope warning:** choose instancing or ray marching, not both.
- **Enhancement:** emissive window patterns.

## Assessing a learner proposal

- **Level 1:** one known pipeline stage plus simple shader mathematics.
- **Level 2:** a new coordinate mapping, analytic particle system or vertex deformation.
- **Level 3:** implicit fields, generated normals or bounded ray marching with diagnostics.
- **Level 4:** costly iterative geometry, distance estimators or several coupled advanced mechanisms.

If a proposal depends on simulation feedback, compute shaders, audio analysis, skeletal animation
or several render passes, narrow it or defer it until after the post-processing chapter.
