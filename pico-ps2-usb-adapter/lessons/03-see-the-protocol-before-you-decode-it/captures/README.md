# About `model-m-keypress.sr`

## Read this first: it is synthesized, not captured

**`model-m-keypress.sr` is not a recording of real hardware.** No IBM Model M was
connected to a logic analyser to produce it. The waveform was constructed by a script from
the frame definition in `DESIGN.md` — start bit, eight data bits LSB first, odd parity,
stop bit, data valid on the falling clock edge — and then decoded back out of its own
samples to confirm the bytes come out right.

This matters, and it is stated plainly here rather than buried, because a learner who
believes they are comparing their trace against a real keyboard when they are not is worse
off than a learner with no reference trace at all. If your own capture disagrees with this
file about *timing*, this file is the one that is wrong. If it disagrees about *structure* —
the bit order, the parity rule, the sampling edge — then one of you has a bug worth finding,
and it is more likely to be in your wiring or your analyser settings than in the frame
definition, which is the same one every PS/2 keyboard obeys.

## What is in the file

| Property | Value |
|---|---|
| Format | sigrok session file (`.sr`, srzip version 2) — open it with **File → Open** in PulseView |
| Channels | 2 — channel 0 is **CLOCK**, channel 1 is **DATA** |
| Sample rate | 1 MHz, so one sample is one microsecond |
| Length | 25 270 samples, about 25.3 ms |
| Key | `A` — scan code set 2 make code `0x1C` |
| Content | idle high, then the make frame, then the two-byte break sequence |

The sequence in full, with the time each frame starts:

| Time | Byte | What it is |
|---|---|---|
| 0 – 5.04 ms | — | idle: both lines released high |
| 5.04 ms | `0x1C` | make code for `A` — the key going **down** |
| 5.92 – 17.93 ms | — | the key is held; the keyboard says nothing |
| 17.93 ms | `0xF0` | the set 2 **break prefix** |
| 18.81 – 19.42 ms | — | inter-byte gap |
| 19.42 ms | `0x1C` | the make code again, which after `0xF0` means the key came **up** |
| 20.3 – 25.3 ms | — | idle |

Note what the break sequence is and is not. Set 2 signals a release as **`0xF0` followed by
the make code**. It does *not* set bit 7 of the make code — that is scan code set 1, and a
decoder that confuses the two silently mangles every key whose make code already has bit 7
set.

## The timing that was chosen

These numbers are the script's, not a keyboard's. A real Model M will be near them and will
not match them.

| Parameter | Value in this file | What real hardware does |
|---|---|---|
| Clock period | 80 µs exactly (12.5 kHz) | roughly 60–100 µs, and it drifts within one frame |
| Clock low / high | 40 µs / 40 µs | roughly symmetric, but not exactly |
| Data setup before the falling edge | 30 µs | the specification requires at least 5 µs |
| Edges | perfectly square, one sample wide | an RC curve on an open-drain line with a pull-up, with a rise time you can measure |
| Jitter | none | present, and interesting |

The last two rows are the ones worth dwelling on. This trace has vertical edges because it
was generated as ones and zeros. A real bus has a slow rise governed by the pull-up
resistance and the bus capacitance, and a logic analyser hides that behind its input
threshold — which is exactly the point the offered `see-the-edges-on-a-scope` lesson makes.
Do not conclude from this file that your own edges should look square.

## How to use it

- **If your wiring is not ready yet**, open this file and practise on it: count the eleven
  bits, find the start bit, sample the data on each falling clock edge, work the byte out
  LSB first, and check the parity by hand. The method is the point of lesson 03, and the
  method works on a synthetic trace exactly as well as on a real one.
- **Once your wiring is ready**, capture your own keypress and work from that. Yours is the
  one that matters: it is evidence that your level shifter, your pull-ups and your analyser
  settings are all right, and this file is evidence of nothing but arithmetic.
- **Compare structure, not shape.** Same bit count, same bit order, same parity rule, same
  sampling edge. Different periods, different edges, different gaps.

## Reproducing it

The generator is not shipped with the course. It is a few dozen lines: emit one byte per
sample with CLOCK in bit 0 and DATA in bit 1, wrap the sample bytes in a ZIP alongside a
`version` file containing `2` and a `metadata` INI naming the channels and the sample rate.
Writing your own is a reasonable afternoon if you want a synthetic trace for a key this file
does not cover — and if you do write one, decode it back out of its own samples before you
trust it, which is what was done to this one.
