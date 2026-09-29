---
id: 08-ps2-receive-in-pio
title: PS/2 receive in PIO
design_refs: [rx-interface, wire-format]
validators: [build-ok, pio-frames-received]
---

## Purpose

Move the framing off the CPU entirely, and then measure what that actually bought — in
microseconds, on your board, by a method you can defend.

You already have a working receiver. Lessons 04 to 06 built it out of an edge interrupt, a
shift register, a parity check, an idle timeout and a ring buffer, and it is genuinely good:
every byte a Model M sends, in order, with a drop counter stuck at zero. This lesson does not
exist because that receiver is broken. It exists because the RP2040 can do the same job
without the CPU being involved at all, and because "offload" is a word used far more often
than it is measured.

So the deal is: build the PIO backend, run both backends behind the same interface, and be
honest about the difference. Maybe it is large. Maybe at PS/2's lazy 10 to 17 kHz it is small
and the real win is somewhere other than raw CPU time. The lesson is not complete when PIO
works; it is complete when you can state a number and say how you got it. "PIO is faster" is
exactly the assertion this lesson is designed to stop you making.

There is one way to fail badly here, and it is tempting: get the PIO backend working, then
delete the interrupt one. `#rx-interface` keeps the interrupt backend for the life of the
course, and the reason is right here — it is the baseline. Delete it and the measurement has
nothing to measure against, and the offered latency lesson later has nothing to compare.

## Prerequisites

- `07-what-a-pio-state-machine-is`: you have loaded, configured and started a state machine,
  drained an RX FIFO, and you know which mapping `wait ... pin` uses on your configuration.
- `06-handing-data-to-the-main-loop`, still passing `queue-lossless`. The interrupt backend is
  the reference this lesson measures against and it must still build.
- `05-a-state-machine-in-an-isr` is where your parity check and resynchronisation live. Both
  have to survive the move, not be dropped on the way.
- You can read `#wire-format` and `#rx-interface` and say what each constrains.
- A capture of one keypress open in front of you — yours from lesson 03, or the supplied
  reference capture. You are about to argue about clock edges.

## Learning objectives

After this lesson you can:

- Write a PIO program that receives an eleven-bit PS/2 frame, synchronising on the clock the
  keyboard generates, and say which edge a device-to-host bit is valid on.
- Choose an autopush threshold deliberately, and say what the frame looks like in the 32-bit
  FIFO word that results — including which end of the word the bits land at.
- Recover the byte, the parity bit and the framing bits on the CPU side, keeping the parity
  check and the resynchronisation you already had.
- Implement a second backend behind an existing interface without changing it, and select
  between them at build time.
- Measure a receive path's CPU cost without the measurement being dominated by your own
  instrumentation.
- Quantify jitter tolerance: construct a condition where one backend loses data and the other
  does not, and explain why.
- State what protocol offload bought on this board, with a number and a method.

## Theory

### What the state machine has to do

From `#wire-format`: eleven bits — one start bit (always 0), eight data bits **LSB first**,
one **odd** parity bit, one stop bit (always 1). The keyboard drives the clock, and for
device-to-host traffic the data line is valid on the **falling** clock edge.

"Valid on the falling edge" is a statement about the device: the keyboard puts the bit on the
data line while the clock is high and then pulls the clock low, so any receiver sampling at
or just after the falling edge sees a settled bit. The receive algorithm is three steps,
repeated: wait for clock high (so you are synchronised to a clock period rather than half way
through one), wait for it to go low, sample data.

In PIO that is two `wait` instructions and one `in`, and the `in` happens on the cycle after
the edge — not "some microseconds later, once the CPU finished what it was doing". That
difference is the point of this lesson and the thing you are going to measure.

The instructive failure here is sampling on the wrong edge, and it does not produce garbage.
On a slow bus with settled data it very often produces *correct bytes*, because the data is
stable for most of the clock period and you happen to catch it. Then the edge rate changes,
or a longer cable adds capacitance, or the keyboard is a different one, and half the bytes
are wrong. Sample on the edge the protocol names, not the one that happened to work.

### Where does the frame start?

The clock idles high between frames, and a frame begins when the keyboard pulls data low and
starts clocking. A receiver that just counts eleven edges for ever has no concept of a frame
boundary, so one lost edge desynchronises it permanently — the failure you met in lesson 05
and solved with an idle timeout.

A PIO receiver has the same problem and one extra tool: the state machine can `wait` for data
low *before* it starts counting, so every frame is entered from a known state. What PIO does
not give you free is the timeout, because there is no clock to time against when nothing is
happening. Decide where resynchronisation lives for this backend before you write the
program — in the state machine, on the CPU side, or split. Each direction has a defensible
answer; the wrong answer is not to have thought about it, which is how you get a backend that
passes on the bench and latches on a glitch.

### Autopush thresholds, and the trap in them

The autopush threshold decides when a word appears in the RX FIFO. Two choices are
reasonable and the difference matters:

- **Threshold 11** — shift in start, eight data bits, parity and stop, and let the CPU pick
  the frame apart. The framing and parity checks stay in C exactly where lesson 05 wrote them.
- **Threshold 8** — `wait` over the start bit, shift in only the data, `wait` over parity and
  stop. The word is a clean byte with no unpacking, and you have just thrown away the parity
  bit, the `parity-error` value your `frame:` lines must be able to report, and the only
  evidence that distinguishes a corrupted byte from a valid one.

This course wants the parity check to survive the move, so a threshold that discards parity is
not really on offer. Make the choice knowingly, because the *mistake* in this area is why it
is spelled out: a threshold off by one relative to the number of bits you actually shift in.
The symptom is horrible. Every frame shifts by one bit position, so every byte you print is a
plausible scan code that is not the one pressed, and parity fails about half the time — which
reads as flaky wiring. **If your bytes are wrong but consistently wrong, count bits before
you reach for the multimeter.**

Then there is where the bits land. From lesson 07: with the ISR shifting **right** and a
threshold of N below 32, the N bits you collected sit in the **top** N bits of the word that
reaches the FIFO and everything below is zero, so the CPU must shift down by `32 - N` before
anything makes sense. Nothing warns you — the value you read is a large, entirely reasonable
32-bit number.

And the bit order. PS/2 sends LSB first; one shift direction reassembles that into the byte
that was sent and the other reassembles it bit-reversed, and *both* give you a byte. Work out
which your configuration produces by reasoning about the shift, then confirm against a key
whose scan code you already know from lesson 05 — not the other way round. If you do need to
reverse it, `mov x, ::y` costs one cycle and doing it in C is fine too; just know which you
are doing and why.

### One interface, two backends

`#rx-interface` is normative here and it is small: **initialise, and a non-blocking pop of one
byte**. Nothing downstream may reach into a backend's internals, because the entire value of
the arrangement is that the two are interchangeable — the moment lesson 10's decoder knows
which backend is underneath it, you have one implementation with two spellings.

Concretely, for this lesson:

- Both backends implement the same header. The header does not grow a `ps2_rx_pio_*`.
- Selection is made **at build time** from `CMakeLists.txt` — an option that compiles one
  backend source or the other. Not a runtime `if`, because then both are linked in and the
  CPU-cost measurement stops being clean.
- The firmware prints which it selected, once at startup: `backend: interrupt` or
  `backend: pio`, exactly those spellings.
- Both builds satisfy the same checks. `queue-lossless` and the lesson 05 frame checks are
  neither PIO-specific nor interrupt-specific; they are the same experiment run against two
  implementations, which is what makes them a contract rather than a test of one code path.

If a check passes for one backend and not the other you have not found a flaky check. You have
found a real difference in behaviour, and working out which backend is right is the most
valuable half-hour in this lesson.

### Measuring CPU cost without measuring your own instrumentation

The trap first, because it will eat you otherwise: **printing a `frame:` line costs vastly
more CPU than either backend does.** At 115200 baud, `frame: 1c ok` is about fourteen
characters — a little over a millisecond of serial time, plus whatever your stdio route does
to get it there. A PS/2 frame at 12 kHz occupies under a millisecond on the wire and
assembling it costs microseconds. Measure with per-frame printing on and you are measuring
your UART; both backends will come out identical, correctly and uselessly. Hold printing
constant across the two builds, and switch it off during the measurement window.

The method that works:

1. Add a free-running counter the main loop increments on every pass of its idle path, and
   nothing else.
2. With no keyboard traffic, measure counts per second over a long window. That is your
   calibration: counts per second of completely idle CPU.
3. Hold a key down so typematic repeat delivers a steady stream — the Model M's default repeat
   is around eleven characters a second, so a thousand frames takes roughly a minute and a
   half. Count frames received and loop counts accumulated over the same window.
4. The shortfall in loop counts, converted through the calibration, is the CPU time the
   receive path consumed. Normalise to a thousand frames and print
   `cpu: <microseconds per 1000 frames>`.
5. Rebuild with the other backend, change nothing else, repeat.

This measures what you want — CPU time taken away from everything else — rather than a
timestamp difference inside a handler, which measures the handler and not its cost to the
system. It also catches the interrupt backend's real overhead, which is not just the body of
the ISR: it is the vectoring, the register save and restore and the return, eleven times per
byte.

Be honest about the result. PS/2 is slow. It is entirely possible that both numbers are small
and the difference real but undramatic. That is a finding, not a failure — and it sets up the
half of the comparison where the difference is not small at all.

### Jitter tolerance: where the difference is large

CPU time is one axis. The other is what happens when the CPU is *not available* at the moment
an edge arrives.

The interrupt backend samples when its handler runs, which is after the interrupt latency: the
current instruction finishing, the vectoring, the register save, any higher-priority handler
already running, and any interval during which you had interrupts masked. A PS/2 bit period is
roughly 60 to 100 microseconds, so there is a lot of headroom — right up until there is not.
Mask interrupts for a millisecond in a critical section and the interrupt receiver misses edges
and mangles a frame.

The PIO backend does not care. The state machine's `wait` resumes on the cycle the edge
happens, whatever the CPU is doing, and the RX FIFO buffers four words — roughly four whole
frames — before anything is at risk. The CPU can be unavailable for milliseconds and lose
nothing.

So construct the experiment: a deliberate, repeating blockage in the main loop, interrupts
masked for a millisecond or so, and type into it. One backend starts reporting framing errors
and resyncs; the other does not notice. Both numbers go in your notes. This is the part of
"what offload bought" that is not a rounding error, and it is the part that tells you something
true about every fast protocol you will put on this chip.

## Concepts to teach

- Protocol offload: what it means to move the timing-critical part of a protocol off the CPU.
- The device-to-host sampling rule from `#wire-format`, and how to show it on a trace.
- Synchronising a PIO receiver to a frame boundary rather than free-running on edges, and
  where resynchronisation and the idle timeout live when the framing is in hardware.
- Autopush thresholds: choosing one deliberately, and the off-by-one symptom.
- Where bits land in the 32-bit FIFO word for a threshold below 32, and the `32 - N` shift.
- Shift direction and LSB-first buses; `mov ::` as the one-cycle bit reversal.
- Keeping the parity check and framing checks across a change of backend.
- `#rx-interface` as a contract: initialise and non-blocking pop, nothing more; build-time
  selection; and why the reference implementation is kept rather than deleted.
- Measurement method: idle-loop calibration, and why a timestamp inside the handler measures
  the wrong thing.
- The observer effect of console printing on a measurement — the Heisenbug lesson 16 makes a
  whole lesson of.
- Interrupt latency versus a state machine's `wait`, and what the four-word FIFO buys.
- Jitter tolerance as a second axis of comparison, separate from CPU cost.

## Constraints

- The PIO receive program lives in `pio/` and is assembled by the build.
- `#rx-interface` does not change: two functions, initialise and a non-blocking pop of one
  byte. No new entry points, no backend-specific calls escaping the header.
- The interrupt backend is **not** deleted, **not** commented out, and still builds and passes
  its checks when selected. `#rx-interface` requires it for the life of the course.
- Backend selection is at build time via `CMakeLists.txt`. Exactly one backend is compiled
  into any given image.
- Every build prints `backend: interrupt` or `backend: pio` at startup, spelled exactly so.
- `frame:` lines keep their lesson 05 format and semantics for both backends, including
  `parity-error` and `framing-error`, and `resync` keeps counting. Parity is checked in the PIO
  build too; an implementation that cannot report a parity error has not kept the contract.
- `cpu: <microseconds per 1000 frames>` is printed by both builds, measured by the same method,
  with per-frame console printing in the same state for both.
- The measurement is not taken with per-frame `frame:` printing enabled, and the learner can
  say why.
- The pin assignment does not change: clock GP2, data GP3, per `#pin-assignment`.

## Suggested progression

1. Re-read `#wire-format`'s direction table and find the falling edge on your lesson 03
   capture. Say out loud where in the clock period the data is settled.
2. Write down, before touching PIO, the three-step receive algorithm for one bit and the number
   of bits per frame.
3. Write a first PIO program that does nothing but shift in a fixed number of bits on clock
   edges and push. Print the raw 32-bit word as a non-`frame:` debug line.
4. Press a key whose scan code you know from lesson 05 and look at the raw word. Do not decode
   it yet: work out where in the 32 bits your data sits, and confirm the `32 - N` shift by
   arithmetic rather than by trying values.
5. Work out from the shift direction whether the byte is in the order the keyboard sent it or
   reversed, and confirm against the known scan code.
6. Decide your autopush threshold deliberately, and write down which bit of the shifted word is
   the start bit, which are data, which is parity and which is stop.
7. Introduce the off-by-one on purpose — threshold one away from the bits you shift — and see
   what a whole-frame shift does to your bytes. It looks like bad wiring. Recognising this
   symptom is worth the five minutes.
8. Add frame-start synchronisation so every frame is entered from a known state, and decide
   where resynchronisation lives for this backend. Write the decision down.
9. Bring the parity and framing checks across to the CPU side of the PIO backend, so `frame:`
   lines carry `ok`, `parity-error` or `framing-error` exactly as before and `resync` counts.
10. Put the PIO backend behind `#rx-interface` — same header, same two functions — add the
    build-time selection to `CMakeLists.txt`, and print `backend:` at startup.
11. Build both backends in turn and run the lesson 05 and 06 checks against each. Any check that
    passes for one and fails for the other is a real behavioural difference: find out which
    backend is right before going on.
12. Type a paragraph through the PIO backend and confirm the bytes match what the interrupt
    backend produces for the same text, in order, with no drops.
13. Build the measurement rig: the idle-loop counter, and the calibration run with no traffic.
    Record counts per second of idle CPU.
14. Switch off per-frame printing for the measurement window, and say why before you do it.
15. Hold a key down until typematic repeat has delivered of the order of a thousand frames.
    Compute microseconds per 1000 frames and print `cpu:`.
16. Repeat exactly the same procedure on the other build, changing nothing but the backend.
17. Compare. Write down both numbers, the method and the window length, and resist the urge to
    round the interrupt backend up or the PIO one down.
18. Now the jitter experiment: a deliberate repeating blockage of around a millisecond with
    interrupts masked, typed through on each backend in turn. Record framing errors and resyncs
    for both.
19. Increase the blockage until the PIO backend also loses data, and work out from the FIFO
    depth and the frame rate why it happens where it happens.
20. State the conclusion in your own words, with numbers: what offload cost, what it bought in
    CPU time, and what it bought in jitter tolerance. If the CPU saving turned out small, say
    so — that is the honest result on a 12 kHz bus and it is not a failure.
21. Confirm the interrupt backend is still in the tree, still selectable, and still passes.

## Completion conditions

- `build-ok` passes for **both** backend selections.
- The `pio-frames-received` check passes against the PIO build, with `backend: pio` on the
  console.
- The lesson 05 and lesson 06 checks pass against the interrupt build, with
  `backend: interrupt` on the console — the reference implementation is intact.
- The same typed text produces the same byte sequence through both backends.
- `frame:` lines from the PIO build carry `parity-error` when the learner induces a parity
  error, and `resync` increments when the learner glitches the line: the lesson 05 behaviour
  survived the move.
- Both builds print a `cpu:` value, and the learner can state both numbers, the measurement
  window, the calibration, and why per-frame printing was off.
- The learner can state which clock edge they sample on and why, and point at it on a trace.
- The learner can say where their frame's bits sit in the 32-bit FIFO word and why, without
  trying values.
- The jitter experiment is recorded: the blockage duration at which the interrupt backend
  starts losing frames, the one at which the PIO backend does, and the FIFO-depth reasoning for
  the second.
- The learner states the measured difference in CPU time as a number. "PIO is faster" is not a
  completion condition; "PIO cost N microseconds per thousand frames against the interrupt
  backend's M, measured this way" is.

## On completion, persist

- The autopush threshold chosen, the shift direction, and the resulting bit layout of the FIFO
  word. Lesson 09 shares the pins and lesson 17 revisits the error paths.
- Where resynchronisation lives in the PIO backend, and why.
- The build option name and values that select the backend, so later lessons can ask for a
  rebuild against either one.
- Both `cpu:` numbers, with method, window length and the console-printing state during the
  measurement. The offered `measure-your-latency` lesson compares against these, and a number
  without its method is not usable.
- The jitter thresholds for both backends, and the FIFO-depth reasoning.
- Which PIO block, state machine and instruction words are occupied, and what is left for
  lesson 09's transmit.

## Optional deeper paths

- Do the frame unpacking in PIO instead of C: `mov` with bit reversal, or `in null, N` to shift
  dead bits in so the word arrives pre-aligned. Count what it cost in instructions and decide
  whether you would keep it.
- Measure the interrupt backend's latency directly with a spare GPIO toggled at the top of the
  ISR, captured against the clock edge. This previews the lesson 16 technique and turns
  "interrupt latency" from a word into a number on your board.
- Work out what bus speed would make the interrupt backend genuinely unable to keep up, and
  identify the protocol properties that make offload mandatory rather than merely tidy.
- Read the state machine's stall flags and FIFO level registers from the CPU and log them.
  Knowing a state machine is stalled, rather than inferring it from silence, is a debugging tool
  you will want in lesson 09.
