# Supported subset for the optional loader

The loader targets only the unmodified packaged `Duck.glb` and must validate these assumptions:

- GLB version 2, one JSON chunk and one BIN chunk
- one selected scene path containing the supported mesh
- triangle-list mesh primitives
- `POSITION`, `NORMAL` and `TEXCOORD_0` attributes
- scalar indices
- non-sparse accessors using component types present in the asset
- buffer-view and accessor byte offsets, with declared byte stride when present
- one base-colour texture whose encoded image is stored in the GLB
- node transforms present in the asset, whether expressed as TRS or a matrix

Reject rather than silently approximate unsupported primitive modes, sparse accessors,
compression extensions, morph targets, skinning, animation, multiple UV sets, material extensions,
external buffers and external images.

The learner should verify the actual asset metadata before implementing each bullet. This file
sets the permitted boundary; it is not a claim that every listed representation is present.
