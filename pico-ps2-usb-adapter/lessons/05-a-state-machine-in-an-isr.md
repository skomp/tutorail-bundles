---
id: 05-a-state-machine-in-an-isr
title: A state machine in an interrupt handler
design_refs: [wire-format]
validators: [build-ok, frames-received]
---

## Purpose

Turn eleven meaningless edges into one byte you are willing to act on — and make the receiver
put itself right when the eleven were not the eleven you thought.

Lesson 04 got a hardware event into your code and counted it. Counting is the easy half. The
hard half is that a PS/2 frame has no header, no length field, no marker of any kind: the bus
idles high, the keyboard starts clocking, eleven bits go past, and the bus idles high again.
The only thing that tells you which of those eleven bits you are looking at is *how many you
have seen since you last thought a frame started*. That is a state machine, it lives inside the
handler, and it is one integer wide.

The interesting failure follows immediately. If that integer is ever wrong by one — a spurious
edge from a nudged jumper, a lost edge because something masked interrupts too long, a connector
re-seated mid-frame — then it stays wrong. Every subsequent byte is a mangled splice of two real
ones, the parity check happens to pass about half the time, and nothing in the design ever puts
it back. A receiver like that works perfectly on the bench and dies permanently the first time
someone bumps the desk.

The fix is not better wiring. It is to notice that the *timing* carries the framing information
the bit stream does not: inside a frame, edges are one bit time apart; between frames they are
much further apart. A receiver that watches the gap between edges can tell "this is the next bit"
from "this is the start of something new", and that single rule turns a permanent failure into a
lost byte. You will build it without that rule first, break it on purpose, and then add it,
because the recovery is the deliverable of this lesson and not the decoding.

## Prerequisites

- `04-your-first-interrupt` is complete: a falling-edge interrupt on GP2 reaches your own
  handler, the handler does only bounded work, the shared counter is `volatile`, and you saw
  33 edges for a press-and-release.
- `03-see-the-protocol-before-you-decode-it` is complete, and you still have both the capture
  and your own decoding of it. You need three numbers from it here: the **bit time**, the gap
  between the two frames of a break sequence, and at least one **known byte** — the make code
  of a key you pressed — read out of the trace by hand.
- GP3 (data) is wired through the level shifter and idles high; `#pin-assignment`.
- The console is still UART0, and `alive` and `edges` are still being printed from the main
  loop.

## Learning objectives

- State the PS/2 device-to-host frame exactly: bit order, parity sense, which bits parity
  covers, and which clock edge carries the data
- Build a framing state machine small enough to live inside an interrupt handler, and say why
  a bit index is sufficient state
- Assemble a byte from a serial bit stream in the correct direction, and diagnose a
  bit-reversed result from the byte alone
- Compute odd parity over the right nine bits and demonstrate that your check is not vacuous
- Explain why a self-clocked frame with no delimiter cannot resynchronise on content, and
  derive an idle-gap threshold from your own measured bit time
- Distinguish a framing error from a parity error from a resynchronisation, and handle each
  without stopping the receiver
- Demonstrate, on the bench, that your receiver recovers from a deliberately induced glitch

## Theory

### The frame, stated exactly

From `#wire-format`, and this is normative for the whole course:

| Bit | Meaning |
|---|---|
| 0 | start bit, always **0** |
| 1–8 | eight data bits, **least significant first** |
| 9 | **odd** parity over the eight data bits |
| 10 | stop bit, always **1** |

The keyboard generates the clock. For device-to-host traffic — the keyboard typing, which is
everything until lesson 09 — the keyboard puts the bit on the data line and then pulls the
clock low, so **the data line is valid on the falling clock edge**. Your lesson 04 handler
already runs at exactly that instant, which is not a coincidence.

The keyboard stays in **scan code set 2** and this course never asks it to switch. You do not
need to know what the bytes mean yet; lesson 10 does that. Here a byte is just a byte, and the
only ones you should recognise are `0xF0`, which prefixes every break, and whatever make code
you read out of your own capture.

### LSB first, and the shift register that follows from it

Bit 0 of the byte arrives first. So each arriving data bit goes into the **top** of an
eight-bit register and the register shifts **right**:

```c
/* one arriving data bit, LSB-first assembly */
shifter = (shifter >> 1) | (bit << 7);
```

After eight of those, bit 0 is back at the bottom where it belongs. Write it the other way
round — `shifter = (shifter << 1) | bit` — and you get the bit reversal of the true byte, which
is the single most common mistake in a first PS/2 receiver and is nastier than it sounds: the
result is a plausible-looking byte rather than obvious garbage. The make code of `A` is `0x1C`;
reversed it is `0x38`, which is the make code of a different real key. Your decoder will look
like it works and will type the wrong letters.

There are exactly two candidate causes when your byte disagrees with your capture — the shift
direction, and the clock edge you sampled on. Distinguish them before you change anything: a
wrong shift direction gives you the exact bit reversal of the right answer, while a wrong edge
gives you a byte with no simple relationship to it.

### Odd parity, over exactly nine bits

Odd parity means: the number of `1` bits among the **eight data bits and the parity bit
together** is odd. So the keyboard sets the parity bit to 1 when the data byte has an even
number of `1`s, and to 0 when it has an odd number. Two things to be exact about, because both
are common mistakes:

- Parity does **not** cover the start bit or the stop bit. They are framing, not data. A parity
  computed over ten or eleven bits fails about half the time, which is about the worst possible
  symptom — it looks like noise.
- Parity here is *odd*, not the even parity most serial ports default to. If you reach for a
  remembered formula, check its sense against a byte from your own capture before trusting it.

Parity catches a single flipped bit, which is exactly the kind of error a marginal edge produces.
It cannot catch two flipped bits, and it cannot catch a frame that is correctly received but
misaligned — which is why the resynchronisation rule below is not optional extra credit.

### The state machine

The whole receiver state is one small integer: which bit of the frame the next edge carries.
Call it the bit index, 0 to 10.

- Index 0: this edge carries the start bit. If the data line is **high**, this is not a start
  bit. Discard and stay at 0.
- Indices 1 to 8: shift the sampled bit into the register as above.
- Index 9: this is the parity bit. Remember it.
- Index 10: this is the stop bit. The frame is complete. Validate, publish, and return the
  index to 0.

You could write this as an `enum` with named states — `IDLE`, `DATA`, `PARITY`, `STOP` — and
in a larger protocol you would. Here the states are strictly sequential and the counter *is*
the state, so the counter is the honest representation. Say which you chose and why; a tutor
will ask.

Whatever you choose, it stays inside the handler and stays bounded: a compare, a shift, a
store, a branch. You are still spending well under a microsecond against a 60 to 100 µs budget.

### The thing that is missing

Look at the state machine again and ask what happens after one bad edge.

Nothing puts it right. The index advances on every edge it is given. Feed it one extra edge and
it thinks bit 1 is bit 2 forever; lose one and it is behind forever. The stop-bit check will
catch *some* of those — a misaligned frame often lands with a `0` where the stop bit should be
— but not reliably, because real data contains plenty of `1` bits in that position. Parity will
catch about half of the rest. The receiver will limp along producing occasional plausible
garbage, which is worse than failing outright.

The information you need is not in the bit stream at all. It is in the timing. Inside a frame,
consecutive edges are one bit time apart — your measured 60 to 100 µs. Between frames, even
between the two frames of a break sequence, the gap is several times that. So:

> **If the time since the previous edge exceeds a threshold, this edge is a start bit,
> whatever the state machine thought.**

That one rule makes the receiver self-healing. A glitch costs you at most the frame it landed
in, and the next frame is correct. It is the mechanism `#failure-posture` means when it says
the adapter must resynchronise rather than latch, and the same rule is what lesson 17 leans on
when it induces errors deliberately.

### Choosing the threshold, from your own numbers

Derive it; do not copy it.

Take your measured bit time T. A sensible threshold is **about three times T** — long enough
that nothing inside a frame ever trips it, short enough that the very next frame after a glitch
is clean. Check the number against your own capture: measure the gap between the last edge of
`0xF0` and the first edge of the code that follows it, which is the *smallest* real inter-frame
gap your keyboard produces. Your threshold must sit comfortably between one bit time and that
gap.

The two ways of being wrong are not symmetric, and this is worth internalising:

- **Too short** and the threshold fires *inside* a frame. The index resets partway through
  every frame and no frame ever completes. The receiver is dead, loudly.
- **Too long** and the threshold only fires when you stop typing. A glitch then costs you
  everything until the next pause. The receiver is degraded, quietly, and still recovers.

So when in doubt, err long. A quiet degradation that self-corrects beats a receiver that never
produces a byte.

For the timing itself, `time_us_32()` reads the always-on timer in a single load and is safe in
a handler. It wraps every 71 minutes or so, which does not matter at all provided you
**subtract** timestamps rather than compare them: unsigned subtraction is modular, so
`now - last` is correct across the wrap. Comparing `now > last + threshold` is not. This is one
of the few places where the C rule you half-remember is exactly right and worth being precise
about.

### Errors are not fatal, and they are not the same thing

Three distinct outcomes, and the vocabulary matters because the console keys carry it:

- **Framing error.** The eleven bits arrived but the stop bit was `0`. You have a complete frame
  whose data you do not trust. Report `framing-error` with the byte as assembled, and start the
  next frame.
- **Parity error.** Eleven bits arrived, the stop bit was fine, and the parity bit disagrees with
  the data. Report `parity-error` with the byte as assembled, start the next frame, and do not
  pass the byte downstream.
- **Resynchronisation.** A partially-assembled frame was abandoned — the idle gap expired
  mid-frame, or the data line was high when a start bit was due. No frame completed, so there is
  nothing to report as a frame; increment the `resync` counter instead.

Count a resynchronisation only when a *partial* frame is actually discarded, that is, when the bit
index was not already 0. Otherwise the counter tracks how long you have been idle and tells you
nothing. None of these three disables the interrupt, latches a flag or stops the receiver:
`#failure-posture` is explicit that one glitch must not end the session.

### Handing one frame to the main loop — provisionally

The handler still must not print, so it needs somewhere to leave the frame where the main loop
will find it. For this lesson, use the smallest thing that works: one slot holding the byte and
its status, plus a `volatile` flag saying the slot is full. The handler fills the slot and sets
the flag; the main loop, when it sees the flag, prints and clears it.

**This design loses frames and you should expect it to.** If two frames complete before the main
loop gets around to the slot — and printing one line takes longer than a frame does — the second
overwrites the first. That is fine for a lesson whose evidence is "the bytes are correct" and
completely unacceptable for a keyboard. It is also exactly the pressure lesson 06 exists to
relieve, so do not pre-empt it: build the one-slot handoff, watch it drop frames under a burst,
and leave it dropping them. Lesson 06 will ask you what you saw.

### What the handler now costs

Count what you added: one GPIO read, one compare against a threshold, one subtract, a shift, a
couple of branches, two stores. Tens of cycles — a fraction of a microsecond at 125 MHz against a
budget of 60 to 100 µs. The state machine is not where your latency will ever go. The two things
that could still eat the budget are a `printf` that crept into the handler and a critical section
elsewhere that masks interrupts for too long; lesson 06 measures the second one.

## Concepts to teach

The PS/2 device-to-host frame in full: start bit, eight data bits LSB first, odd parity, stop
bit, sampled on the falling clock edge (`#wire-format`). Shift registers and bit order; why
LSB-first assembly shifts right; the bit-reversal symptom and how it differs from a wrong-edge
symptom. Odd parity, and precisely which bits it covers. Framing state machines: a bit index as
sufficient state, and when a named-state enum would be the better representation instead.
Self-clocked streams with no delimiter, and why content cannot resynchronise them. Timeout-driven
resynchronisation; deriving the threshold from a measured bit time and a measured inter-frame gap;
the asymmetry between a too-short and a too-long threshold. `time_us_32()` and modular unsigned
subtraction across the 32-bit microsecond wrap. Framing error versus parity error versus
resynchronisation, and reporting each without stopping the receiver (`#failure-posture`).
Provisional single-slot handoff from handler to main loop, and why it is provisional.

## Constraints

- The handler samples GP3 at the falling edge of GP2 and **never** the other way round.
- Data bits are assembled **LSB first**. Parity is **odd** and covers the eight data bits and
  the parity bit only.
- The receiver **must not latch** on any error. Nothing in this lesson may disable the GPIO
  interrupt, stop the state machine permanently, or require a reset to recover.
- The idle threshold is **derived from the learner's own measured bit time**, and the derivation
  is written down. A number quoted from a web page is not acceptable evidence even if it happens
  to be the same number.
- Timestamps are compared by **unsigned subtraction**, never by adding the threshold to the
  previous timestamp.
- The handler still prints nothing, blocks on nothing, allocates nothing, and uses no floating
  point. Everything reaches the console from the main loop.
- Console output: `frame: <hex byte> <ok|parity-error|framing-error>` on every **completed**
  frame, with the byte as two lowercase hex digits; `resync: <n>` when the resynchronisation
  counter changes. Keep `alive` running. Spell both keys exactly as given — the
  `frames-received` check reads them and ignores every line that does not match.
- **Do not build a ring buffer in this lesson.** The one-slot handoff is deliberate and lesson
  06 replaces it.
- The console stays on UART0 (`#debug-channel`).

## Suggested progression

1. Write down your threshold derivation before touching code: measured bit time, measured
   smallest inter-frame gap from the lesson 03 capture, chosen threshold, and one sentence on
   why it sits between them.
2. Read one known byte out of your lesson 03 capture by hand — the make code of a key you can
   press on demand. This is the value you will check the firmware against, and it must come from
   your trace and not from a table on the internet.
3. Extend the lesson 04 handler to sample GP3 whenever it runs, and add the bit index. Leave the
   edge counter in place; it is still useful evidence.
4. Implement indices 1 to 8 as the shift register, index 9 as the parity bit, index 10 as the
   stop bit and the completion point. Do **not** implement the idle timeout yet.
5. Add the one-slot handoff and make the main loop print `frame: <hex> <status>` when the slot is
   full. At this stage every completed frame can be reported `ok`; the checks come next.
6. Build with the `build-ok` check, flash, and press your known key. Compare the printed byte
   against the byte you read off your own capture.
7. If they disagree, decide which of the two candidate causes it is *before* changing anything: a
   bit reversal points at the shift direction, anything else points at the sampled edge. Say which
   and why, then fix it.
8. Confirm the break sequence: pressing and releasing your key should print three frames, the
   second of which is `f0`.
9. Add the parity computation and the `parity-error` status. Press keys whose make codes have
   both odd and even popcounts and confirm you get no parity errors on a healthy bus.
10. Prove the parity check is not vacuous: invert its sense, rebuild, and confirm that *every*
    frame now reports `parity-error`. Put it back. A check that has never failed is not yet
    evidence of anything.
11. Add the stop-bit check and the `framing-error` status.
12. Now break it on purpose, with no timeout in the code. Hold a key so typematic repeat streams
    frames continuously, and glitch the clock line: either momentarily pull the 3.3 V-side clock
    line to ground through a 1 kΩ resistor, which is electrically what the bus does anyway on an
    open-drain line, or pull the clock jumper and re-seat it. Watch the console.
13. Confirm the damage is **permanent**: keep typing after the glitch and confirm the bytes stay
    wrong, and that releasing and pressing the key again does not help. Record what the console
    looked like. This is the failure the rest of the lesson exists to fix.
14. Add the idle-gap rule using `time_us_32()` and unsigned subtraction: if the gap since the
    previous edge exceeds your threshold, treat this edge as a start bit regardless of the current
    index, and count a `resync` if a partial frame was discarded.
15. Add the start-bit rule: at index 0, a high data line is not a start bit — discard the edge and
    stay at 0.
16. Print `resync: <n>` from the main loop when the counter changes.
17. Repeat the glitch from step 12. `resync` must increment and correct `frame` lines must return
    within a frame or two, with no reset and no unplug. **This recovery is the deliverable.**
18. Explore the threshold you derived. Set it to half a bit time, rebuild, and confirm no frame
    ever completes. Set it to 50 ms and confirm that recovery now waits until you stop typing.
    Restore your derived value and state which of the two mistakes you would rather ship.
19. Type a short known string and read the frames against your own decoding, confirming that `f0`
    precedes every break code and that extended keys carry `e0`.
20. Confirm by inspection that the handler still contains no printing, no blocking and no
    allocation, and that every console line comes from the main loop.
21. Type a fast burst and note, without fixing it, how many frames the single-slot handoff lost.
    Write the number down; lesson 06 opens with it.
22. With the tutor, run the `build-ok` and `frames-received` checks.

## Completion conditions

- The `build-ok` check passes.
- The `frames-received` check sees correct, parity-checked `frame` lines for a key the learner
  presses on demand, with the status spelled `ok`, `parity-error` or `framing-error`, and sees a
  `resync` counter.
- The byte printed for the learner's known key matches the byte they decoded by hand from their
  own lesson 03 capture, and the break sequence prints `f0` followed by the same code.
- After a deliberately induced glitch, `resync` increments and correct frames resume within one or
  two frames, with no reset, no replug and no power cycle. The learner has done this on the bench
  and can describe what the console showed before and after the timeout rule existed.
- The learner can state the threshold they chose, the two measurements they derived it from, and
  what goes wrong at each end of the range — having seen both failures.
- The learner can explain why parity does not cover the start and stop bits, has demonstrated that
  their parity check is not vacuous by inverting it, and can say what a bit-reversed byte looks
  like and how it differs from a wrong-edge byte.
- The handler contains only bounded work; the one-slot handoff is still in place and the learner
  can say how many frames it lost under a burst.

## On completion, persist

In the instance's `DESIGN.md`: the frame format as the receiver implements it; the chosen
resynchronisation threshold **with its derivation** from the learner's measured bit time and
inter-frame gap; the rule that framing and parity errors are reported and never latched; the
definition the project uses for the `resync` counter (a partial frame discarded, not every idle
period); and a note that the single-slot handoff is provisional and owned by lesson 06.

In `STATE.md`: lesson 05 complete; the known byte the learner verified against and where it came
from; the glitch method they used and that recovery was observed; the frame loss they measured
under a burst with the one-slot handoff, as the starting evidence for lesson 06.

## Optional deeper paths

- **A named-state machine.** Rewrite the receiver with an explicit `enum` and a transition table
  instead of a bit index, and compare the two for size and readability. Decide which you would
  want when the protocol grows a second direction in lesson 09.
- **Glitch the line from firmware instead of from a jumper.** Add a build that deliberately
  advances the bit index by one every few hundred frames, so the glitch is reproducible and
  automatable. Keep it behind a compile-time flag, and note how much easier this makes lesson 17.
- **Watch the recovery on the analyser.** Capture GP2 and GP3 across a glitch and mark, on the
  trace, the exact edge at which your timeout rule re-synchronised. This is the first time
  firmware state and a captured waveform have to be lined up, and lesson 16 does it properly.
- **The clock is not constant.** Measure the bit time across a long typematic burst and see how
  much your keyboard's clock actually varies. A Model M's controller is old and its tolerance is
  wide; a threshold derived from one measurement should survive the spread.
- **Set 1 and set 3.** Read what changes if the keyboard is asked to use a different scan code
  set, and confirm for yourself why `#wire-format` fixes the adapter to set 2 and never asks.
