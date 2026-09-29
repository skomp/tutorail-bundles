---
id: 06-handing-data-to-the-main-loop
title: Handing data to the main loop
design_refs: [rx-interface, debug-channel]
validators: [build-ok, queue-lossless]
---

## Purpose

Get bytes out of interrupt context without losing them, corrupting them or reordering them —
and put them behind an interface narrow enough that lesson 08 can replace everything underneath
it.

You ended lesson 05 with a receiver that decodes correctly and a handoff that drops frames. The
one-slot handoff was not a mistake; it was the smallest thing that let you check the decoding.
But a keyboard that loses a byte does not lose a character, it loses a *state transition*: drop a
`0xF0` and a key is held down forever, into whatever window has focus, until you unplug the
adapter. Lossless is not a quality target here, it is the requirement.

The obstacle is that the producer and the consumer are not two threads. They are asymmetric in a
way with no analogue in ordinary concurrent programming: the handler can pre-empt the main loop
between any two instructions, and the main loop can never pre-empt the handler. That is bad news
and good news at once — bad, because every non-atomic operation in the main loop is a window;
good, because a single-producer single-consumer ring buffer, which needs careful memory ordering
between two real threads, needs none of it here and therefore needs no locks. Which is fortunate,
because you are about to find out exactly how expensive masking interrupts is on this bus.

The other half of the lesson is architectural, and it pays off two lessons later.
`#rx-interface` fixes a deliberately tiny contract — initialise, and a non-blocking pop of one
byte — with two interchangeable backends behind it. You are writing the first now; lesson 08
writes the second in PIO and measures the difference, and that measurement only exists if the two
are genuinely swappable. Anything downstream that reaches past the interface into the ring
buffer, the indices or the handler destroys that, and leaves you with one implementation that has
two spellings.

## Prerequisites

- `05-a-state-machine-in-an-isr` is complete: frames decode correctly, parity and stop bits are
  checked, the idle-gap rule resynchronises after a deliberate glitch, and `frame` and `resync`
  are printed from the main loop.
- You have the number from the end of lesson 05: how many frames the one-slot handoff lost during
  a fast burst. This lesson opens with it.
- `04-your-first-interrupt` gave you the rule that the handler does only bounded work, and your
  measured bit time.
- The console is UART0 and carries `alive`, `edges`, `frame` and `resync` (`#debug-channel`).

## Learning objectives

- Quantify the loss in a naive handoff before replacing it, and compute the throughput the main
  loop can actually sustain
- State precisely what `volatile` does and does not guarantee, and why it is the right tool for
  an ISR-to-main-loop relationship on one core and insufficient across two
- Implement a lock-free single-producer single-consumer ring buffer, and state its single-writer
  invariant as the correctness argument
- Explain why a shared element count is the classic broken alternative, and demonstrate the race
- Measure what masking interrupts costs on this bus, in edges, and design so that no critical
  section is needed on the data path
- Separate a lossless protocol path from a best-effort diagnostic path, and justify the split
- Implement the `#rx-interface` contract as a header with one non-blocking pop, and keep every
  consumer on the near side of it

## Theory

### First, the number

Before designing anything, quantify what you are fixing, with two calculations from figures you
already have.

**What the producer can deliver:** a frame is eleven bits at your measured bit time plus an
inter-frame gap, so the fastest real sequence your keyboard produces — the two frames of a break,
back to back — gives an upper bound of roughly one byte per millisecond, with the sustained rate
under fast typing far lower. **What the consumer can absorb:** UART0 at 115200 8N1 is 86.8 µs per
character, and a `frame: 1c ok` line with its newline is thirteen characters, about 1.1 ms of wire
time. If `printf` blocks until the FIFO drains — and it does, once the FIFO is full — printing one
line per frame puts your main loop at almost exactly the producer's peak rate, with nothing left
over for the USB device task that arrives in lesson 13.

That is the whole problem in two numbers, and it tells you something a bigger buffer cannot fix:
**a buffer buys you time, not throughput.** If the consumer is slower than the producer *on
average*, no capacity saves you and the only honest response is to count what you dropped. If the
consumer is fast enough on average but stalls occasionally, a buffer is exactly the right answer
and the right size is the worst stall times the peak rate. Work out which of those two situations
you are in before choosing a size.

### What `volatile` actually promises

`volatile` on an object tells the compiler two things and only two. First, every read in the
source must be a real load from memory and every write a real store: the value may not be cached
in a register across accesses, and an access may not be elided even if the compiler can prove it
redundant. Second, volatile accesses may not be reordered **with respect to each other**.

That is the entire guarantee, and it is worth being blunt about what is *not* in it:

- **`volatile` is not atomic.** `count++` on a volatile is still load, add, store. An interrupt
  landing between the load and the store loses the handler's increment.
- **`volatile` is not a memory barrier for anything else.** It orders volatile accesses against
  volatile accesses, and says nothing about a non-volatile store you wanted to happen first.
- **`volatile` says nothing about hardware.** It is a statement to the compiler. On a machine
  with multiple cores and store buffers it does not make one core's writes visible to another.

So why is it sufficient here, and only here? Because the problem you have is exactly the problem
it solves. There is one core. The handler runs to completion between two instructions of the main
loop and cannot interleave with them. Cortex-M0+ is in-order and does not reorder memory accesses
as seen by that core. A naturally-aligned 32-bit or 8-bit load or store is a single instruction
and cannot be torn. The only thing that can go wrong is the compiler deciding a value cannot have
changed — precisely what `volatile` forbids.

Change one premise and the reasoning collapses. Put the producer on core 1 and the consumer on
core 0 and you need real barriers (`__dmb()`); `volatile` alone is then a bug. This course keeps
everything on core 0 deliberately — say so in your own design notes, because a future reader will
otherwise assume you got lucky.

### A lock-free single-producer single-consumer ring buffer

You know what a ring buffer is, so here is the exact shape rather than a derivation.

- A byte array whose length is a **power of two**, so wrapping is a mask (`& (SIZE - 1)`) and not
  a division — a modulo by a non-power-of-two on a Cortex-M0+ is a library call.
- A **head** index, advanced by the producer after it stores a byte. Written only by the handler.
- A **tail** index, advanced by the consumer after it reads a byte. Written only by the main loop.
- **Empty** is `head == tail`. **Full** is `((head + 1) & mask) == tail`.

That last line is why the buffer holds `SIZE - 1` bytes and not `SIZE`: one slot is sacrificed so
that full and empty are distinguishable without a third variable. Spend the byte; the alternative
costs you the entire correctness argument below.

**The correctness argument is one sentence: each index has exactly one writer.**

Follow it through. The producer reads `tail` to decide whether the buffer is full but never
writes it; the consumer reads `head` to decide whether it is empty but never writes it. Each side
therefore only ever needs a possibly-*stale* value of the other's index — and staleness is safe in
the conservative direction both ways. A stale `tail` makes the producer believe the buffer is
fuller than it is: worst case it drops a byte it could have stored, and it never overwrites a byte
the consumer has not read. A stale `head` makes the consumer believe the buffer is emptier than it
is: worst case it returns "empty" and finds the byte a moment later, and it never reads a slot that
has not been written.

Neither side can corrupt the other, and no lock is required because there is nothing to serialise.
The ordering that *does* matter is within the producer: **store the byte, then publish the new
head.** Publish first and the consumer may read a slot the producer has not filled. With both the
array and the indices `volatile`, the compiler must keep those two stores in that order, and on
one in-order core that is the whole requirement.

Write that invariant down as a comment next to the declarations. It is the thing a future change
will break.

### The classic broken alternative

The obvious-looking design keeps `head`, `tail` and a `count` of elements, with the producer doing
`count++` and the consumer `count--`. That design has two writers for `count`, and `++` is
load-modify-store. If the handler fires between the main loop's load and its store, the handler's
increment is overwritten and the count is permanently one too low — a slow leak of buffer capacity
that ends in a receiver reporting itself empty while holding bytes. The window is a few
instructions wide, so it will not reproduce on the bench in a ten-second test, and a race that does
not reproduce is not a race that is absent.

The same trap wears other clothes. "Reset both indices to zero when the buffer is empty" is a
tidy-looking optimisation in which the consumer writes `head`; it is the same bug. Any change that
gives an index a second writer is the same bug. That is why the invariant is worth a comment.

### What masking interrupts costs, in edges

The reflex when two contexts share data is to reach for a critical section. The pico-sdk gives you
`save_and_disable_interrupts()` and `restore_interrupts()`, which set and restore `PRIMASK`, and
`irq_set_enabled(IO_IRQ_BANK0, false)` for a targeted mask. What they cost here is startling.

The GPIO peripheral **latches** an edge condition, so an edge arriving while the interrupt is
masked is not lost — the handler runs when you unmask. But the latch is **one bit deep**. Two
edges during the masked window produce one interrupt, and the second edge is simply gone.

So the budget is not "keep critical sections short". It is: **a critical section longer than one
bit time silently eats a data bit**, and your bit time is 60 to 100 µs. A `printf` inside a
critical section is not a performance problem, it is a decoder that stops working. Even a few
microseconds of masking per byte eats a margin you will want back in lesson 13, when the USB stack
starts competing for the same CPU.

The conclusion is therefore not "use short critical sections". It is that the ring buffer above is
designed so the data path needs **none at all**, and that is the main reason to prefer it over
anything requiring mutual exclusion. Where you do still want one — reading two diagnostic counters
that must agree, say — it belongs off the data path and should be a handful of instructions.

### Two paths: lossless for the protocol, best-effort for diagnostics

`#rx-interface` says the interface pops **one byte**. Not a byte and a status, not a frame struct
— one byte. That constrains the design in a way worth making explicit rather than working around.
Split the two concerns:

- The **protocol path** carries good bytes only, through the ring buffer, losslessly, with a drop
  counter that must stay at zero. This is what lesson 10's decoder consumes and what lesson 08's
  PIO backend must reproduce exactly.
- The **diagnostic path** carries error reports, the `resync` count, the drop count and whatever
  else you want to see. It is allowed to be lossy — a plain counter plus a last-value slot —
  because errors are rare and losing the second of two error reports in the same millisecond costs
  you nothing.

The split is not tidiness. The two paths have different requirements: the protocol path has a
correctness requirement, and the diagnostic path has a "do not perturb the thing you are measuring"
requirement. Conflating them puts a status byte into the interface that the PIO backend would have
to synthesise, and at that point the two backends are no longer the same thing. Your `frame:` lines
therefore come from the diagnostic path, and your `queue:` line reports the protocol path.

### What the interface looks like, and why it is this small

Two entry points, in a header of their own:

```c
void ps2_rx_init(void);
bool ps2_rx_pop(uint8_t *out);   /* returns false immediately if nothing is waiting */
```

Non-blocking is the load-bearing word. A pop that waits would put the main loop's liveness in the
hands of the keyboard, and from lesson 13 the main loop has a USB device task it must service on
the host's schedule. Returning `false` and letting the caller get on with something else is not a
convenience; it is what makes a superloop viable.

Put the interrupt backend in its own implementation file, named for the backend rather than the
protocol, so that lesson 08 **adds** a second file instead of editing this one. The build-time
selection mechanism is lesson 08's business — you have only one backend today — but the file
layout that makes it a one-line CMake change is this lesson's.

Then hold the line: nothing outside that file may name the ring buffer, the indices, the handler
or the GPIO pins. The interrupt backend is not deleted when PIO works — `#rx-interface` keeps it
for the life of the course as the reference implementation and as lesson 08's baseline — and a
baseline is worth nothing if downstream code has grown into one of the two implementations.

### Doing the slow work in the handler because it is easier

There is a tempting shortcut at every step of this lesson: format the line in the handler, decode
the scan code there, keep the whole frame struct there. Each removes a small awkwardness and each
spends microseconds you do not have, in the one context where spending them loses data rather than
time. So restate lesson 04's rule as a design principle rather than a prohibition: **the handler
does the work that cannot be deferred, and nothing else.** Sampling a pin at the moment of an edge
cannot be deferred; assembling and validating the frame is cheap and needs the handler's state, so
it stays; formatting, decoding, printing and deciding can all wait a millisecond, so they go to the
main loop. When you are unsure which side something belongs on, ask what happens if it is delayed
by a millisecond — if the answer is "nothing", it is main-loop work.

## Concepts to teach

The asymmetry between an ISR and a main loop on one core, and why it is not the same as two
threads. `volatile`: what it guarantees (no caching in registers, no elision, ordering among
volatile accesses) and what it does not (atomicity, barriers for non-volatile accesses, cross-core
visibility); why it suffices on one core and is a bug across two, with `__dmb()` named as what the
two-core case would need. Lock-free single-producer single-consumer ring buffers: a power-of-two
array and a mask, head written only by the producer and tail only by the consumer, the sacrificed
slot that distinguishes full from empty, the single-writer invariant as the correctness argument,
stale indices being safe in the conservative direction, and store-then-publish ordering. The
broken `count` variant and why its race will not reproduce on demand. Critical sections:
`save_and_disable_interrupts`/`restore_interrupts`, the one-deep GPIO edge latch, and therefore
the rule that masking for longer than one bit time loses a data bit. Buffer sizing as worst-stall
times peak rate, and the difference between buying time and buying throughput. Drop policy:
discard the newest and count it, never overwrite the oldest, because overwriting makes the
producer move the tail and breaks the invariant. Separating a lossless protocol path from a
best-effort diagnostic path. The `#rx-interface` contract: initialise plus a non-blocking pop of
one byte, backends in separate files, nothing downstream touching internals, and the interrupt
backend kept as lesson 08's baseline.

## Constraints

- The receive interface is exactly **initialise** plus a **non-blocking pop of one byte**
  (`#rx-interface`). No other function is public, and `ps2_rx_pop` never waits.
- The interrupt backend lives in its own implementation file. **Nothing outside it** may name the
  ring buffer, `head`, `tail`, the handler or the PS/2 pins.
- The ring buffer is **lock-free**: no critical section, no mask, no lock anywhere on the byte
  path. If your design needs one, the design is wrong.
- **Head is written only by the handler; tail only by the main loop.** No element count, no
  reset-when-empty, no third index. The invariant is written as a comment beside the declarations.
- The producer **stores the byte before publishing the new head**, and the relevant objects are
  `volatile`.
- **When the buffer is full, drop the newest byte and count it.** Do not overwrite the oldest, do
  not block, do not disable the interrupt.
- The buffer length is a power of two, and the learner can state the calculation behind the size
  they chose.
- The handler still does only bounded work and still prints nothing.
- Console output: keep `alive`, `frame` and `resync`; add `queue: <popped> <dropped>` — total
  bytes popped by the main loop, then total bytes dropped by a full buffer — printed when it
  changes. Spell it exactly; the `queue-lossless` check ignores anything that does not match.
- Everything stays on **core 0**, and the console stays on UART0 (`#debug-channel`).

## Suggested progression

1. Open with the number from lesson 05: how many frames the single-slot handoff lost under a
   burst. If you did not record it, reproduce it now — you are about to claim an improvement and
   you need the before.
2. Do the two throughput calculations: bytes per second the keyboard can deliver at your measured
   bit time, and characters per second the console can absorb. Decide whether you are short of
   capacity or short of throughput, and write the conclusion down.
3. Decide which of your current console lines belong on the lossless path and which on the
   best-effort diagnostic path, and say why for each.
4. Write the interface header: initialise, and the non-blocking pop. Two declarations, plus a
   comment that nothing downstream may reach past them and that lesson 08 replaces the
   implementation.
5. Move the lesson 05 handler and state machine into a backend implementation file named for the
   backend. Nothing should change behaviourally; build with the `build-ok` check and confirm the
   console is unchanged before going further.
6. Choose the buffer size from worst-stall times peak rate, round up to a power of two, and record
   the calculation. Resist choosing 256 because it is round.
7. Declare the array, `head` and `tail`, and write the single-writer invariant as a comment beside
   them.
8. Implement the producer inside the handler: compute the next head, compare against tail, and on
   full increment the drop counter and discard; otherwise store the byte and *then* publish the
   new head.
9. Implement `ps2_rx_pop`: return false when head equals tail, otherwise take the byte and then
   publish the new tail.
10. Rewrite the main loop to drain the buffer — pop until empty — printing a `frame:` line per byte
    from the diagnostic path, and print `queue: <popped> <dropped>` when either number changes.
11. Delete the single-slot handoff entirely. Two handoff mechanisms is one too many, and the old
    one will silently win somewhere.
12. Build, flash, type, and confirm bytes still arrive correctly and in order. Correctness first,
    losslessness next.
13. Remove `volatile` from the head index, rebuild optimised, observe, and put it back. Note which
    of the two guarantees in the theory section you just watched being violated.
14. Demonstrate the `count` race deliberately: add a variant with one element count incremented by
    the handler and decremented by the main loop, and widen the window on purpose — a few no-ops
    between the consumer's load and its store — until the count visibly drifts under typematic
    repeat. Say in one sentence why the un-widened version has the same bug. Revert.
15. Measure what masking costs. Wrap a deliberately long region — around 500 µs — in
    `save_and_disable_interrupts()`/`restore_interrupts()` while a key repeats, and watch `resync`
    climb and frames go wrong. Shorten it until the damage stops and compare that boundary against
    your bit time. Then remove the critical section and confirm the design needs none.
16. Prove the drop counter is real: slow the main loop on purpose — a sleep in the drain loop, or a
    much longer line per byte — hold a key down, and confirm `dropped` rises. A counter that has
    only ever read zero is not evidence that nothing was dropped.
17. Remove the slowdown, power-cycle for a clean boot, and confirm `dropped` returns to zero and
    stays there.
18. Run the burst test: type as fast as you can for at least ten seconds, or hold a key through a
    long typematic run, and confirm every byte appears in order with `dropped` at zero and `popped`
    matching the frames you expect. Compare against the number from step 1.
19. Audit the boundary: search your tree for the ring buffer's identifiers, the indices, the handler
    and the PS/2 pin numbers, and confirm every hit is inside the backend file. Fix anything that is
    not, now, while there is only one caller.
20. Confirm the handler's body is still bounded: sample, shift, validate, push, return. No
    formatting, no decoding, no printing.
21. With the tutor, run the `build-ok` and `queue-lossless` checks.

## Completion conditions

- The `build-ok` check passes.
- The `queue-lossless` check sees `queue: <popped> <dropped>` with `dropped` at **zero** across a
  sustained fast-typing burst, `popped` rising, and `frame` lines still correct and in order.
- The learner has demonstrated that the drop counter *can* rise — by deliberately slowing the
  consumer — and that it returns to zero on a clean boot with the slowdown removed. A zero that has
  never been anything else does not count.
- Nothing outside the backend implementation file names the ring buffer, its indices, the handler
  or the PS/2 pins; the only public surface is initialise plus the non-blocking pop, and the learner
  can say why lesson 08 depends on that (`#rx-interface`).
- There is **no lock and no critical section on the byte path**, and the learner can state the
  single-writer invariant and explain why a stale index is safe on each side.
- The learner can say what `volatile` guarantees and what it does not, why it suffices here, and
  what would additionally be required if the producer ran on core 1.
- The learner can describe the `count` race they induced and explain why the narrow-window version
  has the same defect despite not reproducing; can state the masking boundary they measured and
  relate it to their bit time and the one-deep GPIO edge latch; and can justify their buffer size
  with a calculation, including why a larger buffer would not help if the consumer were slower than
  the producer on average.
- The handler still does only bounded work; the console is still UART0 and still prints `alive`,
  `frame` and `resync`.

## On completion, persist

In the instance's `DESIGN.md`: the receive interface as implemented — the two functions, the
non-blocking guarantee, and the rule that nothing downstream reaches past them, with the note that
the interrupt backend stays for the life of the course as lesson 08's baseline (`#rx-interface`);
the ring buffer's size and the calculation behind it; the single-writer invariant; the drop policy
(discard newest, count it) and why overwriting the oldest was rejected; the decision that everything
runs on core 0 and what that assumption buys; and the split between the lossless protocol path and
the best-effort diagnostic path.

In `STATE.md`: lesson 06 complete; the before-and-after numbers for frame loss; the masking boundary
measured in step 15; the file layout adopted for backends and therefore what lesson 08 adds rather
than edits; and which instructive failures were actually run — the non-`volatile` index, the `count`
race, the over-long critical section, the forced drop.

## Optional deeper paths

- **Two cores for real.** Move the receiver to core 1 with `multicore_launch_core1`, watch the
  reasoning in this lesson stop being sufficient, and find out what `__dmb()` and the SIO FIFO
  offer instead. Then come back to core 0 and write down why this course stays there.
- **The hardware alternative.** The RP2040 has hardware spinlocks, and the SDK's `queue_t` is built
  on them. Read that implementation against yours: it is safe across cores and it is not lock-free.
  Decide which property you actually needed.
- **Size it from a real stall.** Instrument the longest gap between two consecutive drains of the
  buffer over a minute of typing and compare it with the size you calculated. Sizing from a
  measured worst case is a habit worth acquiring before lesson 13 adds a USB stack with stalls you
  did not choose.
- **Overwrite instead of drop.** Implement the overwrite-oldest policy properly and find out what
  it forces: the producer has to advance the tail, which gives the tail two writers. Having built
  it once, you will never be tempted again.
