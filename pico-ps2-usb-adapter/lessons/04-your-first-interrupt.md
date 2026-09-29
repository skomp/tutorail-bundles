---
id: 04-your-first-interrupt
title: Your first interrupt
design_refs: [pin-assignment, debug-channel]
validators: [build-ok, edges-counted]
---

## Purpose

Take a hardware event off the wire and into your own code, and prove that the CPU is
reacting to the keyboard rather than to a timer of its own.

Everything so far has been you acting on the board: blink an LED, read a pinout, take a
measurement, capture a trace. The keyboard has been a thing you looked at. From here it is a
thing your firmware has to keep up with, and keeping up is a timing problem before it is a
protocol problem. A PS/2 keyboard clocks at roughly 10 to 17 kHz, putting a clock edge every
60 to 100 microseconds and squeezing a whole eleven-bit frame into a little over a
millisecond. Miss one edge and the byte is wrong; miss one without noticing, and every byte
after it is wrong too.

You could poll instead. At 125 MHz a superloop that does nothing else can sample GP2 a few
thousand times per bit, and it would work today. It stops working the moment that same loop
also has to service TinyUSB, which it does from lesson 13 onwards, because the USB device task
takes an unpredictable amount of time and answers to the host's schedule rather than to the
keyboard's. The structural answer is to let the hardware interrupt the CPU at the instant the
edge happens, so the receiver's timing stops depending on what the main loop is busy with.

This is also why the course reaches interrupts before PIO. Lesson 08 moves the framing onto a
hardware state machine and that is the better implementation, but a PIO program teaches you
nothing about interrupt latency, about what a handler may not do, or about the fact that
memory shared between a handler and a main loop does not behave the way single-threaded C
leads you to expect. Those three things are what you are here for, and unlike PIO they are
true on every microcontroller you will ever touch.

## Prerequisites

- `00-first-code-and-a-window-in` is complete: you can build and flash, and `alive` lines
  from your own firmware appear on the UART0 console carried by the second Pico.
- `02-open-drain-and-pull-ups` is complete: the level shifter is in place and powered, both
  sides idle high at their own rail, and PS/2 clock reaches **GP2** and data reaches **GP3**
  through it (`#pin-assignment`).
- `03-see-the-protocol-before-you-decode-it` is complete, and you still have the capture. You
  need two things off it in this lesson: your keyboard's **measured clock period**, and the
  fact that device-to-host data is valid on the **falling** clock edge (`#wire-format`).
- The Model M is connected and powered from VBUS, and it survives a power-on self test.

## Learning objectives

- Explain what the CPU does when an interrupt fires — what the hardware stacks, where the
  vector comes from, and why a handler is not a thread
- Configure a GPIO edge interrupt through the pico-sdk, and explain why all thirty GPIOs share
  one interrupt line and what that forces the callback to do
- State the components of interrupt latency on this chip, and give a number for your own
  handler's budget derived from your measured clock period
- Name what may not happen inside an interrupt handler, and justify the worst offender with a
  number rather than with a rule
- Predict the edge count for a keypress, a release, a held key and an extended key from the
  eleven-bit frame, and confirm the prediction against the console
- Recognise, from its symptoms, a shared variable the compiler has kept in a register, and say
  why `volatile` is the right tool for that problem and not for the ones lesson 06 deals with

## Theory

### What happens when an interrupt fires

Each of the RP2040's two Cortex-M0+ cores has a **Nested Vectored Interrupt Controller**, the
NVIC. It sits between the peripherals and the core: it notices that a peripheral has raised a
request, decides whether that request outranks what the core is doing, and if so makes the
core stop and run a specific function. The mapping from request to function is the **vector
table**, an array of function pointers at a known address with one entry per exception. Each
core has 26 peripheral interrupt lines, and the one you want is `IO_IRQ_BANK0` — the line
every GPIO in bank 0 raises.

When the NVIC takes an interrupt, the hardware does this with no help from you:

1. Finishes or abandons the current instruction.
2. Pushes eight registers onto the current stack — `R0`–`R3`, `R12`, `LR`, the return
   address, and `xPSR`. Those are the caller-saved registers of the ARM calling convention,
   which is exactly what lets a handler be written as an ordinary C function: the compiler
   saves the rest if the handler uses them.
3. Loads an `EXC_RETURN` pattern into `LR` — not a real address — so that returning from the
   handler triggers the unstacking rather than an ordinary branch.
4. Fetches the handler's address from the vector table and jumps to it.

Three consequences matter more than the mechanism:

- **A handler is not a thread.** It borrows the stack that was already in use, and it runs to
  completion. Nothing else on that core runs until it returns.
- **A handler cannot wait for the main loop.** The main loop is not running. A handler that
  blocks on something only the main loop can produce has hung the firmware, not slowed it.
- **A handler can start between any two instructions of the main loop.** Not between any two
  lines of C — between any two *instructions*. That is the fact lesson 06 is built on, and it
  is already true here.

Cortex-M0+ implements four priority levels (two bits of the eight the architecture defines).
A handler runs with everything below its own priority masked, so a same-priority interrupt
arriving while you are inside a handler waits — it does not nest. When your handler returns,
the core **tail-chains** straight into the waiting one, skipping the unstack-then-restack,
which is why back-to-back interrupts are cheaper than two isolated ones.

### Where the latency goes

Interrupt latency is the time from the electrical edge to the first useful instruction of
your handler. On this chip it is the sum of:

- **Exception entry**, about 16 cycles on a Cortex-M0+, so roughly 128 ns at 125 MHz. This is
  the part everybody quotes and the part that matters least.
- **Instruction fetch.** Your handler lives in flash, which the RP2040 reaches over XIP —
  execute-in-place through a small cache. Code already cached runs at full speed; a cold miss
  costs a real QSPI read, so an interrupt that fires rarely is *systematically* slower than
  the same code in a hot loop. `__not_in_flash_func(...)` places a function in SRAM and takes
  this term to zero.
- **Whatever is already masking interrupts.** A critical section in the main loop, or a
  handler of equal or higher priority already running, delays yours by its whole length.
- **Whatever your handler does before the useful part.** Every branch and every load counts.

Now put a budget on it. Take your measured clock period from lesson 03 — call it T. Your
handler must finish comfortably inside T, because the next edge is T away. With T somewhere
around 60 to 100 µs and an entry cost around 0.1 µs, you have enormous headroom for a few
dozen instructions and none at all for anything that talks to a peripheral at human speed.

### The pico-sdk GPIO interrupt, and the trap inside it

All thirty GPIOs in bank 0 share **one** NVIC line per core. There is no per-pin interrupt
vector, and that single fact explains both the shape of the SDK's API and the mistake
everybody makes with it.

```c
gpio_set_irq_enabled_with_callback(PS2_CLK_PIN, GPIO_IRQ_EDGE_FALL, true, &my_handler);
void my_handler(uint gpio, uint32_t event_mask);
```

The call does three things: it enables the falling-edge condition for that one pin, it
installs `my_handler` as the callback for the **whole bank**, and it enables `IO_IRQ_BANK0` in
the NVIC. The trap is the middle one. There is a single bank callback; calling this function
again with a different function pointer replaces the first, and the pin argument does not make
it per-pin. That is why the callback is handed both the pin and the event mask, and why it has
to check which pin it was called for. For any *further* pin you interrupt on, use
`gpio_set_irq_enabled`, which enables a condition without touching the callback.

The four conditions are `GPIO_IRQ_EDGE_RISE`, `GPIO_IRQ_EDGE_FALL`, `GPIO_IRQ_LEVEL_HIGH` and
`GPIO_IRQ_LEVEL_LOW`. The two edge conditions **latch** in the peripheral's interrupt register,
and the SDK's shared handler acknowledges the latch before calling you. The two level
conditions do not latch: they are true for as long as the level is, so a level interrupt on a
line that stays low re-fires immediately and forever, and the firmware never reaches the main
loop again. It is worth knowing what that hang looks like before you cause one by accident.

Which edge you enable is settled by `#wire-format` and not by preference: for device-to-host
traffic the keyboard presents each data bit and then pulls the clock low, so the data line is
valid **on the falling clock edge**. Enable falling only. Lesson 05 samples the data line at
exactly the moment this handler runs, so choosing the other edge now costs you that lesson.

### What may not happen inside a handler

The rule is "nothing slow, nothing blocking, nothing unbounded". It is easy to nod at and easy
to violate, so attach a number to the worst case.

**`printf` is the worst case.** Your console is UART0 at 115200 8N1: ten bit times per
character, so 86.8 µs per character on the wire. A modest twelve-character line is over a
millisecond, against a per-edge budget of 60 to 100 µs. Printing one short line inside the
handler is not "a bit slow" — it is ten to twenty times your whole budget, and it will eat ten
to twenty clock edges. Worse, the pico-sdk's stdio takes a lock; if the main loop already holds
it when your handler tries to, the handler waits for a main loop that cannot run, and the
firmware is simply dead.

The rest follows from the same principle: no `malloc` or `free` (unbounded, and not reentrant
against a main loop that may be inside one); no `sleep_ms`, no `busy_wait_*`, no polling for
anything; no floating point, because the M0+ has no FPU and every operation is a library call
of unpredictable length; no taking a lock the main loop holds, for the deadlock reason above;
and no calling into code that was not written to be reentrant.

What is left is: read a register, do a little arithmetic, store to memory, return. That is
enough for this lesson and, as it turns out, enough for lesson 05 as well.

### Edges you did not ask for

A PS/2 keyboard drives its clock only while it is sending, and the bus idles high the rest of
the time, so a quiet bus should produce no interrupts at all. Reality adds some anyway:
power-on, hot-plug, a DuPont jumper nudged in a breadboard, a connector not fully seated, a
long unshielded wire next to something switching.

Two things follow. First, a count that climbs on an untouched bus is a wiring fault and not a
software feature, and it is worth finding now rather than in lesson 05 where it will look like
a protocol bug. Second — and this is the seed of the next lesson — a receiver that assumes "an
edge means the next data bit" has no way back once it has been handed an edge that was not one.

### Why eleven

One frame is eleven bits: a start bit, eight data bits least-significant first, an odd parity
bit, and a stop bit (`#wire-format`). The keyboard clocks each of them, so **one frame is
eleven falling edges** — and from that, everything you are about to see is predictable.
Pressing an ordinary key sends its make code, one frame, **11** edges. Releasing it sends
`0xF0` and then the same code, two frames, **22**. So a full press-and-release of an ordinary
key is **33**; predict it before you test it. Holding a key produces typematic repeat — after
about half a second the keyboard resends the make code roughly ten times a second — so the
count climbs in steps of 11. An extended key (the cursor keys, right Ctrl, right Alt) prefixes
`0xE0`, adding one frame to the make and one to the break, so press-and-release is 55.

Being able to derive those numbers, rather than recognise them, is a completion condition for
this lesson.

### What the compiler is allowed to assume

C is defined in terms of an abstract machine that executes one thing at a time. Within that
model the compiler may do anything it likes to your program as long as the observable
behaviour is unchanged — the *as-if* rule, and the reason optimised C is fast. One of the
things it does constantly is decide that a variable's value cannot have changed since it last
loaded it, and keep the value in a register instead of going back to memory.

An interrupt handler is outside that abstract machine. It is not called from the code the
compiler is looking at; from the compiler's point of view it is never called at all.

You are about to write a counter that a handler increments and the main loop reads. Do not go
looking for the answer before you have seen what happens; the symptom is far more memorable
than the explanation, and the tutor will name the tool once you have met the problem. Only
this is worth saying in advance: whatever you reach for, `volatile` is a statement about what
the *compiler* may assume and nothing else. It is not a lock, it is not atomic, and it does not
make a read-modify-write safe. Lesson 06 is where that distinction earns its keep.

## Concepts to teach

Interrupts and the NVIC; the vector table; exception entry and the eight hardware-stacked
registers; `EXC_RETURN`; the four Cortex-M0+ priority levels and tail-chaining; why a handler
is not a thread and cannot wait for the main loop. Interrupt latency and its components —
exception entry, XIP cache misses on a cold handler, masking elsewhere, the handler's own
prologue — with `__not_in_flash_func` as the fix for the second. The pico-sdk GPIO IRQ API: one
shared `IO_IRQ_BANK0` line for all thirty pins, one bank-wide callback,
`gpio_set_irq_enabled_with_callback` versus `gpio_set_irq_enabled`, the `(gpio, event_mask)`
signature, edge conditions that latch versus level conditions that do not. Which edge carries
device-to-host data, and why (`#wire-format`). What may not happen inside a handler, with
`printf` costed at 86.8 µs per character. Spurious edges from hot-plug and loose wiring. The
eleven-bit frame as eleven falling edges, and the arithmetic of make, break, typematic repeat
and the extended prefix. The as-if rule, why a variable shared with a handler sits outside the
compiler's model of the program, and `volatile` as a statement about the compiler only.

## Constraints

- **The handler increments a counter and does nothing else.** No printing, no blocking, no
  allocation, no floating point, no calls into stdio.
- **Everything printed comes from the main loop**, over UART0. Do not add
  `pico_enable_stdio_usb` and do not move the console to USB: `#debug-channel` is the reason
  the checks can read anything at all, and USB is the artefact under test from lesson 11.
- **Falling edges on GP2 only.** Not rising, not both, not a level condition. GP3 may be
  configured as an input but must not be interrupt-enabled yet.
- **No internal pull-up or pull-down on GP2 or GP3.** The level-shifter module carries the
  3.3 V side's pull-up (`#voltage-domains`); adding another changes the RC on a line you
  characterised in lesson 02.
- **The order of initialisation is deliberate**: the shared counter exists and is zero, then
  the pin is fully configured, then the interrupt is armed. Not the other way round.
- Keep printing `alive`. Add `edges: <n>` and print it **when the count changes**, not on a
  timer — the `edges-counted` check reads a count that moves when the keyboard moves it.
- Build optimised. If a symptom disappears at `-O0`, that is information about the bug and not
  a fix for it, and the firmware ships optimised.
- **For the tutor:** do not name `volatile`, or hint at it, until the learner has run the
  spin-on-change loop and seen the console stop. That failure is the point of steps 9 to 12 and
  it cannot be had twice.

## Suggested progression

1. Confirm the bench before writing code: keyboard plugged in, shifter powered, second Pico
   attached, `alive` arriving. With the multimeter, confirm GP2 and GP3 idle high at 3.3 V on
   the Pico side — an interrupt armed on a floating pin produces nonsense that looks exactly
   like a software bug.
2. Write down, from your own lesson 03 capture, the measured clock period and the bit time. You
   use it in this lesson's latency budget and again in lesson 05 for the resynchronisation
   threshold, so put it somewhere durable.
3. Add GP2 as a plain input with internal pulls disabled and — before any interrupt exists —
   read its level in the main loop, printing it once a second alongside `alive`. Hold a key and
   confirm the level changes. Debug wiring with a polling loop, which has only one failure mode.
4. Write the handler: a bank callback taking `(uint gpio, uint32_t events)` that checks it was
   called for GP2 with a falling-edge event and increments a `uint32_t` counter. Nothing else.
5. Arm it with `gpio_set_irq_enabled_with_callback` for `GPIO_IRQ_EDGE_FALL` on GP2 only, with
   the counter and the pin both settled before the arming call.
6. In the main loop, print `edges: <n>` whenever the count differs from the value last printed,
   and keep the `alive` counter going.
7. Build with the `build-ok` check, flash, and watch for thirty seconds with nothing touched.
   The count must be still. If it climbs on an untouched bus, stop and fix the wiring or the
   shifter — lesson 05 cannot be debugged on top of this.
8. Press a key and confirm the count moves at all. You now have a hardware event in your own
   code.
9. Change the main loop so it spins waiting for the shared counter to differ from the last value
   printed and prints as soon as it does — no delay, no timer, just the comparison. Rebuild
   optimised and flash.
10. Type. Read what the console does, or does not do. Before changing a line, write down what you
    expected, what happened, and what the difference implies about where the count is read from.
11. Rebuild the identical source without optimisation and run it again. Note whether the symptom
    moves. A bug whose existence depends on the optimisation level is a bug about what the
    compiler was permitted to assume, not about the hardware, and that signature is worth
    recognising for the rest of your life.
12. Apply the fix the tutor now names, rebuild **optimised**, and confirm the count moves on a
    keypress. Note that you have fixed a visibility problem and nothing else.
13. Predict, then measure: one press-and-release of an ordinary key should add exactly 33. Do it
    five times and check the total went up by 165.
14. Hold a key down and watch the count climb in steps of 11 while typematic repeat runs; release
    it and watch it stop. Time the delay before the repeat starts.
15. Press and release an extended key — a cursor key, or right Ctrl — and account for the
    difference against an ordinary key.
16. Unplug and replug the keyboard while watching the console. Account for the edges that
    produces; it will not be a multiple of eleven. Say in one sentence what that means for a
    receiver that counts bits.
17. Deliberately move the arming call before the pin configuration, rebuild, observe, restore the
    correct order, and record what you saw.
18. Deliberately put a `printf` inside the handler, rebuild, and hold a key down. Either the count
    stops being a multiple of eleven because edges were lost, or the firmware hangs outright on
    the stdio lock; both are the same lesson. Remove it, and keep the number: 86.8 µs per
    character against a 60 to 100 µs budget.
19. With the tutor, run the `build-ok` and `edges-counted` checks.

## Completion conditions

- The `build-ok` check passes.
- The `edges-counted` check sees an `edges` count that is **still** on an untouched bus and
  rises when keys are pressed, printed on change, with `alive` still printed alongside.
- One press-and-release of an ordinary key raises the count by exactly **33**, repeatably across
  at least five presses.
- The learner can derive 11, 22, 33 and 55 from the frame format without being told, and can say
  which of those an extended key produces and why.
- The learner can name at least three things that must not happen inside a handler, and can
  justify the `printf` prohibition with the 86.8 µs-per-character figure set against their own
  measured bit time.
- The learner can describe the failure they met in steps 10 and 11 in terms of what the compiler
  was allowed to assume, can say why `volatile` addresses it, and can state correctly that
  `volatile` is neither atomicity nor a lock — naming lesson 06 as where the rest of that story
  lives.
- The handler's body contains the counter increment and nothing else, and every console line is
  emitted from the main loop.
- The console is still UART0. Nothing has been moved to USB stdio.

## On completion, persist

In the instance's `DESIGN.md`: that the interrupt receive path triggers on the **falling** edge
of **GP2**, and why; the learner's measured clock period and bit time, as the number the next
lesson's timeout is derived from; the project rule that the interrupt handler does only bounded
work and never prints; and the note that the shared edge counter is `volatile` for a
compiler-visibility reason, with the full shared-state treatment deferred to lesson 06.

In `STATE.md`: lesson 04 complete; the observed `edges` behaviour including the 33-per-press
figure; and which of the instructive failures were actually run — the cached counter, the
`printf` in the handler, the arm-before-configure ordering — and which were skipped, so a later
session knows what the learner has and has not seen.

## Optional deeper paths

- **Measure your own latency.** Toggle GP5 — the pin `#pin-assignment` reserves for exactly this
  kind of marker — as the first statement of the handler, and capture GP2 and GP5 together on
  the analyser. The delay between edge and marker is your real latency. Then move the handler
  into SRAM with `__not_in_flash_func` and measure again; the difference is the XIP cache, and
  it is usually larger than the exception entry everybody quotes.
- **Priorities.** Set the GPIO IRQ's priority with `irq_set_priority`, add a second interrupt
  source, and observe which one waits. Four levels is not many, and lesson 13 puts USB into the
  same contest.
- **Both edges.** Temporarily enable rising as well, confirm you get 22 per frame, then say
  precisely why lesson 05 wants the falling edge and not either.
- **Under the SDK.** Read `io_bank0_hw->intr` and the per-core enable and status registers
  directly and find your pin's bits. The SDK call is a thin wrapper, and the register view makes
  the shared-line design obvious.
- **Cause the level-interrupt hang on purpose.** Enable `GPIO_IRQ_LEVEL_LOW` on GP2 for one build
  and watch the firmware stop reaching the main loop. Knowing what that failure looks like is
  worth two minutes.
