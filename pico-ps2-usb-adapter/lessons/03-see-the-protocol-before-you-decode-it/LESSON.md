---
id: 03-see-the-protocol-before-you-decode-it
title: See the protocol before you decode it
design_refs: [wire-format]
validators: [signal-captured]
supplies:
  - from: lessons/03-see-the-protocol-before-you-decode-it/captures/
    to: captures
    describe: A reference PS/2 trace to compare your own capture against, with a README saying how it was made - read that first, the trace is synthesized and not taken off real hardware
---

## Purpose

You are about to spend three lessons writing a receiver for a protocol. Before a line of
that code exists, you are going to look at the protocol on an instrument and work out its
shape yourself. Not because the shape is secret — it is thirty years old and on a hundred
web pages — but because a protocol you have measured is a protocol you can debug, and a
protocol you have only read about is a protocol whose diagram you will believe over your own
board when the two disagree.

That disagreement is coming. Somewhere in lessons 04 to 09 you will have a receiver that
mostly works, a byte that is wrong, and a choice between "my code is wrong" and "the
protocol is not what the page said". Learners who have never captured the signal make that
call badly and lose days. Learners who have a trace of their own open in another window make
it in ten minutes.

So: capture a keypress, and derive the frame from the capture. Most of it really is
derivable — the framing bits, the parity sense, the clock edge that carries the data, the
clock period. One part of it is a convention that no trace can settle, and knowing *which*
part, and why, is as valuable as the rest.

The bundle ships a reference capture at `captures/model-m-keypress.sr`, with
`captures/README.md` beside it saying exactly how it was made — read that one first, because
the trace is synthesized rather than taken off real hardware. Both are already in your
workspace. It is there to compare against and to work from if your wiring is not ready. It is
a synthesized reference, not a recording of a real keyboard. **Your own capture, off your own
Model M, is the one that matters**, and it is the one the completion condition is about.

## Prerequisites

- `02-open-drain-and-pull-ups` complete: the level shifter is in, both idle levels are
  correct, and either end can pull either line low.
- `01-the-ps2-connector-and-what-is-safe` complete: you know which connector pin is which,
  including the inference you made about clock and data. This lesson settles that inference.
- A sigrok-compatible logic analyser and PulseView, or equivalent.
- No firmware reads the bus yet. GP2 and GP3 are still inputs with internal pulls disabled.

## Learning objectives

After this lesson you can:

- Choose a sample rate for a digital capture, and say what aliasing looks like when you get
  it wrong.
- Set a threshold and a trigger appropriate to the signal you are hunting, and explain why a
  capture with no common ground is worthless even when it looks fine.
- Read a clocked serial frame off a trace: find the clock, find the edge on which data is
  valid, and extract the bits in order.
- Derive, from your own capture and without consulting a specification: the start bit, the
  stop bit, the parity sense, the number of data bits, and the clock period.
- State which single property of the frame a trace cannot settle, why, and what evidence does
  settle it.
- Distinguish clock from data by observation rather than by the numbering inference you
  carried out of lesson 01.

## Theory

### What a logic analyser is, and what it is not

A logic analyser samples each input at a fixed rate and records a single bit per sample: is
this channel above or below a fixed threshold, right now. That is all. It gives you time
resolution and channel count, and it gives you nothing at all about the *shape* of a signal.

This matters because you just spent a lesson reasoning about rise time. On an analyser, an
edge that takes 7 µs to crawl through the threshold and an edge that snaps in 20 ns look
identical: both are a single transition at the instant the threshold is crossed. An analyser
will happily show you a beautiful square wave on a bus whose edges are so slow that a
different receiver would fail. That limit is precisely why the offered
`see-the-edges-on-a-scope` lesson exists.

Three settings decide whether your capture is data or garbage:

- **Sample rate.** Sampling below twice the signal frequency does not fail loudly; it
  *aliases*, producing a slower, plausible-looking waveform that is not the one on the wire.
  Nyquist is the floor, not the target: for reading digital timing you want several times
  that, so that each edge is placed to within a small fraction of a bit.
- **Threshold.** Cheap analyser clones are 3.3 V parts, and many are not 5 V tolerant. Check
  yours before you clip it onto the keyboard's side of the shifter — it is the same clamp-diode
  argument as lesson 01, and it applies to your instrument too. Probing the 3.3 V side is the
  safe default, and it is also the side your firmware will see.
- **Ground.** The analyser's ground clip must go to the circuit's ground. Without it you are
  measuring a voltage against an undefined reference, and the result frequently *looks*
  reasonable, which is what makes it dangerous.

### How fast is this bus, and what does that mean for the rate

You measured a pull-up and calculated a rise time against a half clock period in lesson 02,
using a figure for the PS/2 clock of roughly 10 to 16.7 kHz. One of the things you are doing
today is checking that figure on your own keyboard rather than inheriting it.

Work the arithmetic forward. If the clock is around 15 kHz, a period is around 66 µs. At
1 MS/s you get about 66 samples per clock period, which places every edge to about 1.5 % of a
period — ample. At 50 kS/s you get three samples per period, which is above Nyquist and
completely useless for reading a frame. At 20 kS/s you are *below* Nyquist for a 15 kHz clock
and the analyser will show you something smooth, slow and entirely fictional.

Meet that failure deliberately. Capture the same keypress at a rate that is obviously far too
low and look at what you get: it is not noise, and it is not empty, and that is the point.
Aliasing produces a confident wrong answer.

The other budget is depth. One frame is eleven clock periods, so under a millisecond; but a
press and its release are separated by however long your finger takes. Streaming clones drop
samples when the rate times the channel count outruns the USB link, and a dropped sample in
the middle of a frame is indistinguishable from a real edge. Pick a rate high enough to read
and low enough to sustain, use only the two channels you need, and trigger rather than trying
to capture everything.

### Triggering

A free-running capture of a bus that is idle 99.9 % of the time is a long recording of
nothing with, if you are lucky, a keypress somewhere in it. Trigger instead.

The natural trigger is a falling edge, because this bus idles high and everything interesting
starts with something pulling it low. You have two candidates: the falling edge of the clock
line, and the falling edge of the data line. They are not equivalent, and working out which
one gives you a cleaner view of the *beginning* of a frame is part of the exercise — one of
them fires on the first thing that happens in a transfer, and the other fires very slightly
after it.

### Telling clock from data, at last

Lesson 01 left you with an inference: given the orientation you established from ground and
VCC, the numbering says this pin is clock and that one is data. Today you confirm it by
looking, and the confirmation takes about two seconds.

One of the two lines, during a transfer, is a **metronome**: a uniform train of pulses at a
constant period, exactly as many of them every time, regardless of which key you press. The
other one holds a level for a whole clock period at a time and changes pattern completely
when you press a different key. There is no ambiguity once you have both on screen.

If they are the other way round from what lesson 01's numbering told you, do not quietly swap
the probes and move on. Go back and find out where the numbering went wrong, because the same
error is still in your head and will come back.

### Reading a clocked serial frame

A clocked serial link separates two jobs: one wire says *when*, the other says *what*. To
read it:

1. Find the clock and count its pulses in one burst. That count tells you how many bits are
   in a frame, including whatever framing bits it carries.
2. Find the edge on which the data is stable. This is directly visible: look at where the data
   line's transitions sit relative to the clock's. Data changes shortly after one clock edge
   and is rock steady across the other. The steady one is the one the receiver samples on. If
   you sample on the edge where data is changing, you are sampling at exactly the moment the
   value is undefined — which produces a receiver that works on a short bench cable and fails
   on a long one, because your margin was the propagation delay you happened to have.
3. Walk the burst and write down the data line's level at each of those sampling edges, in
   time order. That is your bit sequence.
4. Now interpret it, which is the next section.

### What the trace can tell you, and what it cannot

You have a sequence of bits per frame. Capture several frames — several different keys, and
each key pressed and released — and put the sequences side by side. Now you can *derive*
rather than look up:

- **The framing bits.** One position is the same value in every frame you ever capture, at the
  start, and it is the value the line is not idling at. Another is the same value in every
  frame at the end, and it matches the idle level. Those are your start and stop bits, and you
  have shown they are framing rather than data by showing they never vary.
- **How many data bits there are.** Total bits, minus the framing bits, minus one more that
  behaves like the next item.
- **The parity sense.** Take the candidate data bits of each frame and count the ones. Then
  count the ones including the candidate parity bit. Across a dozen different frames, one of
  those two totals will be odd every single time. That tells you both that the bit is a parity
  bit and which sense it has — and if neither total is consistently odd or consistently even,
  your framing assumption is wrong and you should go back to step 1 rather than invent an
  explanation.
- **The clock period.** Measure it with the analyser's cursors, across several periods and
  divided, rather than off a single edge pair. Then check it against the figure lesson 02's
  rise-time margin was computed with.

And here is the one you cannot derive. **The order of the data bits within the byte is a
convention, and no trace can reveal it.** You have eight bits in a definite time order; whether
the first one in time is the least significant or the most significant bit of the byte is a
decision made by the people who defined the protocol, and both readings are self-consistent.
The two candidate bytes are bit-reverses of each other, and every structural test you can run
on the trace — parity, framing, repeatability, the same key giving the same frame — passes
identically for both.

That is not a gap in the method; it is a genuine property of the situation, and recognising it
is the skill. Note what a trace *can* still tell you about it: capture a key being pressed and
then released, and you will find the release produces more frames than the press did, sharing a
byte with it. The byte that is present on release and absent on press is a prefix that is the
same for every key on the board. When you decide your bit order, that prefix byte is the thing
you check it against — one ordering gives the value PS/2 actually uses for it and the other
gives its bit-reverse, and lesson 05's receiver will tell you loudly which one you picked,
because a whole keyboard's worth of codes either lands on a sensible, stable, distinct set or
lands on a mirror image of one.

So: choose an ordering, **write down that it is a choice**, write down the test that will
falsify it, and carry it into lesson 04. `DESIGN.md` `#wire-format` records what this course
uses; your tutor has it. The point of this lesson is that you arrive at lesson 04 knowing
exactly which part of your understanding is measured and which part is assumed.

### One more thing the trace shows you

While you have the capture open, notice how long the gaps are. Between the frames of one
release sequence there is a short, consistent inter-frame gap. Between one keypress and the
next there is an enormous human-scale one. That contrast is the basis of the idle timeout that
resynchronises your receiver in lesson 05, and seeing it now is cheaper than deducing it then.

## Concepts to teach

- What a logic analyser measures, and the edge-shape information it discards.
- Sample rate, Nyquist as a floor rather than a target, and what aliasing looks like.
- Input threshold and 5 V tolerance; probing the 3.3 V side and why.
- Common ground, and why a capture without one looks plausible.
- Sample depth, streaming rate limits, and dropped samples masquerading as edges.
- Edge triggering, and choosing between the clock line and the data line as the trigger.
- Distinguishing a clock from a data line by inspection.
- Reading a clocked serial frame: bit count, the sampling edge, the bit sequence.
- Deriving start, stop, data-bit count and parity sense from multiple frames.
- The limit of derivation: intra-byte bit order as a convention, and what evidence settles it.
- Measuring a clock period properly, over many periods.
- Inter-frame gaps versus inter-keypress gaps.

## Constraints

- The learner presents a capture **they took from their own keyboard**. The supplied reference
  at `captures/model-m-keypress.sr` may be used to get oriented or to work the reading exercise
  while wiring is unfinished, but it is a synthesized reference and it does not satisfy the
  completion condition on its own.
- No firmware reads the bus in this lesson. GP2 and GP3 stay inputs with internal pulls
  disabled; the keyboard is clocking into nothing, which is fine.
- The analyser probes the **3.3 V side** of the shifter unless the learner has confirmed their
  instrument is 5 V tolerant, and can say how they confirmed it.
- The analyser's ground is connected to the circuit ground.
- The clock period is measured across multiple periods and divided, not read off one pair of
  edges.
- The frame structure is derived from the learner's own frames. A frame diagram from a web page
  may be consulted *afterwards* to compare against, and any disagreement must be resolved in
  favour of the trace or explained.
- The bit-order choice is recorded explicitly as a choice, with the test that would falsify it.

## Suggested progression

1. Clip the analyser onto the 3.3 V side of the shifter for both channels, plus ground. Name
   the two channels in your software before you capture anything.
2. Take a free-running capture at a sensible rate with the keyboard idle, and confirm both
   lines sit high and stay there. If they do not, stop: something from lesson 02 is not right.
3. Capture a keypress with a falling-edge trigger. Get one burst on screen.
4. Identify which channel is the clock by inspection, and compare that against the inference
   you carried out of lesson 01. If they disagree, find out why before continuing.
5. Deliberately capture the same keypress at a rate far below Nyquist for the clock. Look at
   what you get. Write down what it would have told you if you had trusted it.
6. Return to a good rate and measure the clock period with cursors across at least five
   periods, divided. Convert it to a frequency.
7. Compare that period against the figure you used in lesson 02's rise-time margin, and say
   whether your margin holds.
8. Count the clock pulses in one burst. Write the number down.
9. Determine which clock edge the data is stable across, by looking at where the data
   transitions sit. State it explicitly, and say what would go wrong if you chose the other
   one.
10. Read the bit sequence off one frame at that edge, in time order, and write it down as a
    row of ones and zeros.
11. Capture several more frames: different keys, and each key both pressed and released. Build a
    table of bit sequences.
12. From that table, identify the bits that never vary and say which are start and stop.
13. From the same table, work out the parity sense by counting ones across the candidate data
    field and then across the data field plus the candidate parity bit.
14. Count the frames a release produces compared with a press, and identify the byte that
    appears on release and never on press. That is the prefix the next section of the course
    depends on.
15. Form both candidate bytes for one frame — the two bit orders — and state which one you are
    choosing, why, and what observation in lesson 05 would prove you wrong.
16. Measure the gap between the frames within one release sequence, and the gap between two
    separate keypresses. Note the ratio.
17. Open `captures/model-m-keypress.sr` and read it the same way. Say where it agrees with your
    own trace and where it does not, and which one you believe.
18. Only now, if you want to, look up a PS/2 frame diagram. Compare it against what you derived
    and resolve any difference explicitly.
19. Have the `signal-captured` check run against your capture and your reading of it.

## Completion conditions

- The learner presents a capture of one keypress taken from their own Model M, with both
  channels labelled and the sample rate stated.
- The learner reads out of that capture: the start bit, the count of data bits, the parity bit
  with its sense, and the stop bit — and for each one names the observation across multiple
  frames that established it.
- The learner states the **measured clock period** in microseconds, with the method (cursors
  over several periods, divided), and the frequency it implies.
- The learner states which clock edge carries valid data for keyboard-to-host traffic, having
  determined it from the trace, and can say what the failure mode of the other choice is.
- The learner has confirmed by inspection which physical line is the clock, and has reconciled
  that with the lesson 01 inference.
- The learner has seen their own capture aliased at too low a sample rate and can describe what
  it looked like.
- The learner states their chosen intra-byte bit order **as a choice**, names the falsifying
  test, and can explain why the trace alone does not settle it.
- The learner has identified the byte that appears on release and not on press.
- The `signal-captured` check passes.

## On completion, persist

- The measured clock period and frequency, and the sample rate the capture was taken at.
- The derived frame structure: total bits, start, data count, parity sense, stop.
- The clock edge on which device-to-host data is valid.
- The chosen intra-byte bit order, marked as a choice, with the test that will confirm or
  refute it in lesson 05.
- Which physical connector pin and which GPIO carry clock and which carry data, now confirmed
  by observation rather than inferred.
- The observed inter-frame gap and inter-keypress gap, for lesson 05's idle timeout to be sized
  against.
- Where the learner's own capture file lives, so lessons 04 to 09 can be checked against it.

## Optional deeper paths

- Take the offered `see-the-edges-on-a-scope` lesson and see what the analyser's threshold was
  hiding on those same edges.
- Write a sigrok protocol decoder stanza for this frame and let the software annotate your own
  capture — then check its annotations against your hand reading.
- Capture the moment of power-on and find the frames the keyboard sends of its own accord
  before you have touched a key.
- Hold a key down long enough for typematic repeat to start, and look at the timing of the
  repeats. You will meet this again in lesson 10.
- Hold the clock line low by hand during a transfer and watch what the keyboard does. That is
  the inhibit mechanism lesson 09 uses, seen from the outside.
- Work out how many bits per second this protocol actually delivers, and compare it with what
  a modern interface carries on two wires.
