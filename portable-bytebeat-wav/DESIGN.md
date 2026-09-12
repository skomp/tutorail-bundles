# Design

## Supported tracks {#supported-tracks}

The authored course supports TypeScript on Node.js, JavaScript on Node.js, Python, Go,
and Kotlin/JVM. The selected track determines project layout, binary I/O APIs, integer
conversion details, and test commands, but not the audio semantics.

## Sample model {#sample-model}

The main path uses mono, unsigned 8-bit PCM at 8,000 samples per second. Each generated
sample is reduced to the range 0–255. Silence is centred near 128. These intentionally
simple parameters make classic Bytebeat expressions direct and keep the WAV writer
small.

## WAV contract {#wav-contract}

The program writes `output.wav` as a RIFF/WAVE file containing a PCM `fmt ` chunk and a
`data` chunk. Multi-byte integer fields are little-endian. Header sizes must be derived
from the generated sample count rather than copied from one fixed-duration example.

## Expression boundary {#expression-boundary}

A Bytebeat expression maps the non-negative integer sample index `t` to an integer. The
main path evaluates a hard-coded expression or an equivalent named function; parsing
expressions supplied by users is outside scope. The low eight bits become the sample.

## Composition scope {#composition-scope}

The final piece is short, deterministic, and generated without third-party audio
libraries. It may change expression over time or combine subexpressions. Musical merit
is subjective; structural validity and the learner's explanation are not.

## Generated live-playback extension {#generated-live-playback-extension}

Live playback is not portable enough to author as one fixed lesson. After the main path,
the tutor may offer and, on acceptance, generate an instance-only side lesson targeted
to the selected language, runtime, operating system, available package manager, and the
learner's choice between real-time streaming and automatic playback of generated audio.

The generated lesson must preserve the working offline WAV path, state any external
dependency before installation, and count its time separately from the authored course.

## Stereo layout {#stereo-layout}

The authored stereo extension uses interleaved unsigned 8-bit PCM frames: left sample,
right sample, then the next frame. Channel count, byte rate, block alignment, data size,
and RIFF size must agree with the two-channel layout.
