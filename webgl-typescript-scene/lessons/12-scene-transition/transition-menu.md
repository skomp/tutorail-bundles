# Transition catalogue

Present these after the diagnostic crossfade works.

## Level 1

- **Directional wipe:** a hard or feathered line reveals the second scene.
- **Iris:** a circle expands from a chosen focal point.
- **Luma dissolve:** a procedural noise threshold reveals pixels in a scattered order.

## Level 2

- **Pixel dissolve:** quantised blocks switch according to noise and progress.
- **Radial swirl:** increasing coordinate rotation pulls the first image into the second.
- **Glitch slices:** bounded horizontal offsets temporarily break the images into bands.

## Level 3

- **Displacement:** a procedural field warps both scenes in opposite directions while blending.
- **Kaleidoscope fold:** angular repetition collapses one scene and unfolds the other.
- **Tunnel pull-through:** polar warping accelerates into the first scene and out of the second.

Preserve exact unwarped output at progress zero and one, clamp texture coordinates deliberately,
and retain the crossfade for debugging.
