---
id: 07-what-a-pio-state-machine-is
title: What a PIO state machine is
design_refs: [pin-assignment]
validators: [build-ok, pio-runs]
---

## Purpose

Run a program on something that is not the CPU, and then stop the CPU and watch it keep
running.

Everything in lessons 04 to 06 was the CPU reacting to the wire: an edge arrived, the NVIC
vectored, your handler ran, and every step cost the core that has to do the rest of the job.
That works well at PS/2 speeds. It is still the wrong shape where the *timing* is the
requirement — an interrupt handler samples whenever the CPU got round to it, and keeping
"whenever" early enough is your problem, for ever.

The RP2040 has a second kind of processor for exactly this. PIO — Programmable I/O — is two
blocks of four tiny state machines, nine instructions, no arithmetic to speak of, no memory,
and one thing they are extremely good at: doing something to a pin, or reading something from
one, on an exact cycle. They are not coprocessors that run your C; they are closer to a shift
register you can program.

This lesson does not touch the PS/2 protocol. Get a program running on a state machine,
predict what it will do *before* running it, measure what it did, and watch it survive the CPU
going away. Lesson 08 moves the framing onto one of these, and you should not be learning what
a state machine is while debugging a protocol on it.

## Prerequisites

- `06-handing-data-to-the-main-loop` complete: the interrupt receiver sits behind the small
  receive interface and `queue-lossless` passes. Nothing here changes that code and lesson 08
  needs it intact.
- The debug console works and `firmware-alive` passes — it is the only evidence channel this
  lesson has.
- The logic analyser is connected and you can capture and read a trace, as in
  `03-see-the-protocol-before-you-decode-it`. You will predict a frequency and go and measure
  it.
- You can edit `CMakeLists.txt` confidently; this lesson adds a build step you have not used.

## Learning objectives

After this lesson you can:

- Say what a PIO block contains, what each state machine owns privately versus shares, and
  what each of the nine instructions is for.
- Explain the ISR and OSR shift registers, their shift direction, and what autopush and
  autopull do to them.
- Compute a state machine's clock from the system clock and the divider, and work out the
  instruction count for a target frequency — before running anything.
- State the difference between `wait ... pin N`, `wait ... gpio N` and `jmp pin`, and say
  which pin each looks at on your board.
- Assemble a `.pio` file from `CMakeLists.txt`, and load, configure and start a state machine
  from C.
- Get data out through the RX FIFO, and say what happens when nobody drains it.
- Demonstrate that a PIO program keeps running when the CPU is blocked, and say why that is
  both the feature and a hazard.

## Theory

### What is actually in there

Each PIO block has **four state machines** and **32 words of instruction memory**, shared:
four programs must fit in 32 instructions between them, and two state machines can run the
same program at different points. That limit is the most important constraint on how you
think about PIO. You are not writing a function; you are writing something the size of a
sonnet.

Each state machine privately owns:

| Thing | What it is |
|---|---|
| PC | where in the shared instruction memory this state machine is |
| X, Y | two 32-bit scratch registers. That is all the storage you get |
| ISR | the input shift register: bits shifted in from pins land here |
| OSR | the output shift register: bits shifted out to pins come from here |
| RX FIFO | four 32-bit words, state machine to CPU |
| TX FIFO | four 32-bit words, CPU to state machine |
| clock divider | how often this state machine advances |
| pin mappings | which GPIOs its `in`, `out`, `set` and side-set groups refer to |

There is no stack, no call, no add. The *only* arithmetic in the instruction set is the
post-decrement built into one form of `jmp`. If you want a loop counter above 31, a
multiplication, or an if/else tree, the answer is almost always that the work belongs on the
CPU and the state machine should do only the part that must happen on an exact cycle.

### The nine instructions

Every instruction is 16 bits and takes **exactly one state-machine cycle**, unless it stalls.
That is what makes timing predictable enough to count in your head.

| Instruction | What it does |
|---|---|
| `jmp` | branch, optionally on `!x`, `x--`, `!y`, `y--`, `x!=y`, `pin` or `!osre` |
| `wait` | stall until a pin, an IRQ flag or a source reaches a value. Your edge detector |
| `in` | shift bits *into* the ISR from pins, X, Y, ISR or OSR |
| `out` | shift bits *out of* the OSR to pins, pin directions, X, Y, PC, ISR or an executed instruction |
| `push` | move the ISR into the RX FIFO and clear it |
| `pull` | move a word from the TX FIFO into the OSR |
| `mov` | copy between registers, optionally inverted (`~`) or **bit-reversed** (`::`) |
| `irq` | set or clear one of eight flags, visible to the CPU and the other state machines |
| `set` | write an immediate of 0 to 31 to pins, pin directions, X or Y |

Two carry more than their names suggest. `mov x, ::y` **reverses bit order** in one cycle —
the cheapest answer to a bus that sends LSB first when you wanted MSB first. And `wait` is
what makes PIO a protocol engine rather than a waveform generator: `wait 0 pin 0` parks the
state machine until that pin reads low and resumes on the cycle the pin changed, not on the
cycle some handler noticed.

Every instruction also carries a **delay** of up to 31 cycles, written in brackets:
`set pins, 1 [7]` executes and then idles 7 more cycles, occupying 8 in total. That is how
you build precise timing without a loop. The delay field is shared with side-set, so using
side-set costs delay range.

### The clock divider, and the thing it cannot do

A state machine advances one instruction per state-machine clock, `f_sm = f_sys / div`.
`f_sys` is 125 MHz on a stock Pico, and `div` is a 16.8 fixed-point number — sixteen integer
bits, eight fractional — running from 1 to 65536. The slowest state-machine clock is
therefore about **1.9 kHz**, so you cannot get a one-second period from the divider.

A visible LED blink needs a *counted delay loop* on top of it, and `set x, N` takes only a
5-bit immediate, so N stops at 31. Longer counts mean nesting two loops with X and Y, or
pulling a 32-bit count from the TX FIFO into the OSR and `mov x, osr`. This is where "an
instruction set with no control flow" stops being abstract and starts costing you words out
of your budget of 32.

For a square wave the arithmetic is small enough to do in your head, and you should:

```
    set pins, 1 [d]
    set pins, 0 [d]
```

Two instructions, each occupying `1 + d` cycles, so the period is `2 * (1 + d)` cycles and
the frequency is `f_sys / (div * 2 * (1 + d))`. Pick a target, choose `d` and `div`, write
the number down, *then* measure. The failure here is common and not subtle: a divider off by
a factor of two, or a `d` counted as `d` cycles rather than `d + 1`, produces a perfectly
healthy square wave at a rate that is not the one you meant. If you did not write the
prediction down first, you will read the measurement and believe it.

### Shift registers, autopush and autopull

The ISR and OSR are not general-purpose registers. They are shift registers with a **shift
direction** and a **bit counter**.

- **Shift right**: `in` puts each new bit at bit 31 and moves the rest down; the first bit
  shifted in ends up nearest the bottom.
- **Shift left**: `in` puts each new bit at bit 0 and moves the rest up; the first bit ends
  up nearest the top.

For a bus that sends LSB first — which PS/2 is, per `#wire-format` — one direction gives you
the byte and the other gives you the byte with its bits reversed. You need not choose today,
but notice that both produce a plausible-looking number.

**Autopush** is a threshold, 1 to 32, set per state machine: when the ISR's bit counter
reaches it, the ISR is pushed to the RX FIFO and cleared, with no `push` in your program. Two
consequences to carry into lesson 08:

- If the RX FIFO is full when autopush fires, the state machine **stalls** on the `in`. It
  does not drop the word and it does not carry on. A state machine nobody drains is a state
  machine that has stopped, and from outside that looks exactly like a bug in the program.
- With a threshold below 32 the word in the FIFO is still 32 bits wide, and your bits are not
  where you want them. Shifting right with threshold N leaves them in the **top** N bits, so
  the CPU must shift down by `32 - N`. Nothing warns you; the value looks entirely reasonable.

**Autopull** is the same idea in reverse for the OSR and TX FIFO, drained by `out`. You will
use it in lesson 09 and not before. An explicit `push` also has a `noblock` form that
discards rather than stalling when the FIFO is full — right for a progress counter, wrong for
a keystroke. You will want it later in this lesson.

### Pin mappings, and the mistake everyone makes once

A state machine does not refer to GPIOs by number in most instructions. It has several
independent **pin groups**, each with a base GPIO and, for some, a count:

| Group | Used by | Note |
|---|---|---|
| IN base | `in pins, N`, and `wait ... pin N` | N pins from the base; lowest GPIO is the LSB |
| OUT base and count | `out pins, N`, `out pindirs, N` | |
| SET base and count | `set pins, V`, `set pindirs, V` | at most 5 pins |
| side-set base | the `side` modifier | |
| JMP pin | `jmp pin` | a single **absolute** GPIO, its own setting |

`in pins, 1` reads the pin at the IN base. **`wait 0 pin 3` does not wait on GP3** — it waits
on the pin three above the IN base. The operand of `wait ... pin` is an index into a mapping,
not a GPIO number. For an absolute GPIO, `wait` has a second form, `wait 0 gpio 3`, which
ignores the mapping. And `jmp pin` uses neither: it tests the one GPIO configured as the
state machine's jump pin.

`#pin-assignment` puts PS/2 **clock on GP2** and **data on GP3**, adjacent and in that order,
precisely so a PIO program can reach both from one base index rather than two scattered
mappings — and so lesson 09 can drive both lines with a single two-pin `set pindirs` group.
Be exact about which mapping each instruction uses when you get there: with the IN base at
GP2, `in pins, 1` shifts in the *clock*, not the data. Adjacency gives you the choice of
reaching either line cheaply; it does not choose for you.

When this goes wrong there is no error. There is a state machine sitting for ever on a `wait`
for a pin that will never change, which looks exactly like a hang.

### The part that is genuinely strange

A PIO program is not running "in" your program. Once loaded and enabled, it runs. It keeps
running while `main` is blocked, while interrupts are masked, if `main` returns, and while
you are stopped at a breakpoint in gdb.

That is the feature — the whole reason lesson 08 exists — and a hazard: a state machine still
driving a pin after you thought you had torn it down will fight whatever you connect next, and
re-flashing does not give you the clean slate you assume. Stopping and restarting a state
machine is something you do on purpose.

## Concepts to teach

- A PIO block: two blocks, four state machines each, 32 shared instruction words; and the
  per-state-machine state — PC, X, Y, ISR, OSR, two four-word FIFOs, divider, pin maps.
- The nine instructions, and that each takes one cycle unless it stalls.
- The delay field, and that `[d]` means `d` *extra* cycles; side-set, at least as "it exists,
  it steals bits from the delay field, and it drives a clock line for free".
- The divider as 16.8 fixed point, and the ~1.9 kHz floor it implies.
- Predicting a frequency from instruction count, delay and divider — arithmetic before
  measurement, not after.
- ISR and OSR as shift registers with a direction and a bit counter.
- Autopush and autopull thresholds; where bits sit when the threshold is below 32; the stall
  when the FIFO is full; `push noblock` and what it costs.
- The pin groups, and that `wait ... pin` is relative while `wait ... gpio` is absolute; why
  `#pin-assignment` made clock and data adjacent, and what that does and does not buy.
- No control flow: no call, no add, one loop construct, 5-bit immediates.
- The build path: a `.pio` source, `pico_generate_pio_header()`, the generated header, and
  configuring a state machine from C.
- That a state machine runs independently of the CPU, including when the CPU is stopped.

## Constraints

- The PIO source lives in `pio/` and is assembled by the build. Do not hand-assemble
  instructions into a C array.
- Do not drive GP2 or GP3. The keyboard is on them and the interrupt receiver is using them.
  The reading exercise below may *look* at GP2 but must set no pin direction on it.
- Drive the on-board LED on GP25 for the slow, visible version and GP5 for the fast version
  you will measure. GP5 is reserved by `#pin-assignment` for lesson 16's marker and carries
  nothing yet, so the analyser probe ends up somewhere useful.
- The interrupt receiver from lessons 04 to 06 must still build and pass its checks at the end
  of this lesson. Nothing here replaces it.
- The console line is `pio: <sm> <freeform>` — state machine index, then what this lesson asks
  for. Spell the key exactly. Everything else you print is ignored by the checks, so print
  whatever helps.
- The freeform part must carry at least one number the **state machine itself produced**. A
  line that only proves the CPU can print is not evidence that a state machine ran.
- The predicted frequency is written down before you measure. If you cannot produce it
  afterwards, the measurement does not count.

## Suggested progression

1. Read `#pin-assignment`: which pins are in use, which reserved, which free today.
2. Add `pio/` and a `.pio` source; wire `pico_generate_pio_header()` into `CMakeLists.txt` and
   confirm the generated header appears. Get the build green with a program that does nothing.
3. Write the smallest square-wave program: two `set pins` instructions with delays, wrapped.
4. Before configuring anything, compute on paper the state-machine clock for your divider, the
   cycles per period, and the output frequency. Write all three down.
5. Configure from C — load the program, point the SET group at GP25, set the divider, set the
   pin direction, enable — and get the LED moving at all.
6. Aim for roughly 2 Hz and discover the divider cannot get you there. Work out why from the
   16.8 format, then add a counted loop with X, and meet the 5-bit immediate limit of `set`.
7. Blink at a rate you predicted, and check the prediction against a clock or a stopwatch.
8. Retarget to GP5 in the tens or hundreds of kilohertz and capture it. Compare measured period
   against prediction to at least three significant figures.
9. If it does not match, do not adjust code until it does. Identify which of the three
   predicted numbers was wrong — divider, cycles per period, or system clock. That diagnosis is
   the exercise.
10. Make the state machine produce a number of its own: a counter in X, `push noblock`ed
    periodically. PIO has no add, so work out how to count with what `jmp x--` gives you.
11. Drain the RX FIFO in the main loop and print it as `pio: <sm> <...>` about once a second,
    alongside your existing `alive` line.
12. Stop draining, and compare `push` with `push noblock`: one stalls and the pin stops
    toggling, the other keeps toggling and loses counts. Say which you want for a progress
    counter and which for a keystroke.
13. Block the CPU hard — a busy loop of a second or two with interrupts masked — and capture the
    pin across it. The square wave must not falter, and the pushed counter must keep rising.
14. Second program, reading: put a state machine's IN base at GP2 and have it `wait` for clock
    edges, counting them and pushing the count. Drive nothing; set no pin direction.
15. Get it wrong first in the obvious way — write the wait operand as the GPIO number. The state
    machine waits for ever and the count stays at zero. Then fix it, by the index relative to
    the IN base or by the absolute `gpio` form, and say which you used and why.
16. Type, and compare the PIO edge count against your lesson 04 ISR count for the same presses.
    They should agree; if not, one of them is counting both edges, and finding out which takes
    five minutes and saves an hour in lesson 08.
17. Leave both programs in the tree, keep `alive` printing, and confirm the interrupt receiver
    still passes its checks with PIO running alongside.

## Completion conditions

- `build-ok` passes with a `.pio` source assembled by the build, not by hand.
- The `pio-runs` check sees `pio: <sm> <freeform>` lines carrying a rising value, and the rise
  is produced by the state machine rather than the CPU.
- The learner can state, for the square wave: system clock, divider, cycles per period,
  predicted frequency, and the frequency measured on the analyser, agreeing within measurement
  error.
- The learner can explain a discrepancy met on the way, or say honestly that the first
  prediction was right.
- A capture shows the pin toggling at an unchanged rate across at least one second during which
  the CPU was blocked with interrupts masked, and the pushed counter rose across it.
- The learner can say what `wait 0 pin 0` waits on for their configuration, what
  `wait 0 gpio 2` waits on, and why those are not the same instruction.
- The learner can say what happens when the RX FIFO fills with nobody draining, and what
  `noblock` changes.
- The PIO edge count and the lesson 04 ISR edge count agree for the same keypresses.
- The interrupt receiver still builds and still passes `queue-lossless`.

## On completion, persist

- Which PIO block and state machine index were used, and which are free. Lessons 08 and 09
  both want one.
- The divider, delay, and predicted versus measured frequency with units — the board's first
  timing calibration, which lesson 16 refers back to.
- Which convention the learner settled on for waiting on the clock line: the index relative to
  the IN base, or the absolute `gpio` form. Lesson 08 builds on this and a tutor should not
  have to guess.
- How many of the block's 32 instruction words the programs occupy.
- Any discrepancy found between the PIO and ISR edge counts, and its cause.

## Optional deeper paths

- Rewrite the square wave with side-set instead of `set pins`, watch the instruction count
  fall, and work out what you gave up in delay range.
- Run the *same* loaded program on two state machines at different dividers, and watch two pins
  toggle at two rates from one copy of the instructions — the clearest demonstration of what is
  shared and what is not.
- `irq`: have a state machine raise a flag the CPU takes as an interrupt rather than polling a
  FIFO. PS/2 receive will not need it; it is what you would reach for if it did.
- Read the default config function `pioasm` generates for you — knowing what it sets is the
  difference between configuring a state machine and copying a configuration.
