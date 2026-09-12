# Make Music with Integer Arithmetic

## Goal

Build a tiny Bytebeat synthesiser in TypeScript, JavaScript, Python, Go, or Kotlin.
The finished program evaluates a compact integer expression for successive sample
indices and writes the results as a valid mono WAV file that ordinary audio software
can play.

The authored main path is designed for roughly 60–90 minutes. It ends with a file named
`output.wav`. Live playback is deliberately excluded from that estimate because audio
APIs, packages, device access, and setup differ by runtime and operating system.

## Teaching approach

The learner should hear meaningful output early, then discover why integer arithmetic
produces pitch and rhythm. The tutor gives one task at a time, adapts project setup and
binary-writing techniques to the chosen language, and lets the learner experiment
without turning every interesting variation into required work.

Supported tracks are TypeScript on Node.js, JavaScript on Node.js, Python, Go, and
Kotlin/JVM. JavaScript and TypeScript are separate learner-facing choices even when
their implementation guidance overlaps.

The learner writes the implementation. Solution code is given only on explicit request.

## Main path

1. **Language and waveform** — choose a supported track and generate inspectable sample
   values.
2. **Write a tone** — encode a minimal valid WAV file and hear the first result.
3. **Bytebeat rhythm** — use time, shifts, masks, and overflow to create structure.
4. **Compose and export** — shape an original short piece and verify the artifact.

## Checkpoints

- After lesson 00: the project produces a deterministic sequence of 8-bit samples.
- After lesson 01: `output.wav` is structurally valid and audibly contains a tone.
- After lesson 02: a Bytebeat expression produces recognisable rhythmic variation.
- After lesson 03: the learner has exported and explained an original composition.

## Optional lessons

- **Stereo Bytebeat** *(optional, authored)* — extend the file format and give the two
  channels independent expressions.
- **Live playback** *(optional, generated on request after the main path)* — the tutor
  may generate a learner-specific side lesson after asking about language/runtime,
  operating system, package manager, and whether the learner wants streamed synthesis
  or automatic playback. It is outside the 60–90 minute estimate.

## Topics this course must cover

- supported-language selection
- discrete audio samples
- sample rate
- unsigned 8-bit PCM
- WAV containers
- little-endian binary encoding
- Bytebeat expressions
- integer overflow and masking
- bitwise shifts
- audible pitch and rhythm
- deterministic generation
- basic artifact validation
- stereo PCM

## Explicit extension boundary

Live playback is an invited extension, not an authored prerequisite. If the learner
accepts the offer after completing the main path, generate one side lesson in the
instance for their actual environment. Prefer the smallest viable approach, but do not
pretend that installing or troubleshooting an audio dependency belongs to the announced
course duration.
