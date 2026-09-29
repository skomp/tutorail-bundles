---
id: 16-when-it-goes-wrong
title: When it goes wrong
design_refs: [debug-channel, pin-assignment]
validators: [build-ok, fault-diagnosed]
---

## Purpose

Acquire the tools to diagnose the next bug yourself, including the ones your usual
tool cannot see.

Sixteen lessons in, you have debugged everything by printing. That worked because
the bugs were logic bugs in code that was not yet fast, and because every lesson
handed you a check that said which half was wrong. Neither will be true again. The
bugs that remain — and most bugs in the next embedded project you write — fall into
two classes `printf` is structurally incapable of finding: a bug in the timing is
destroyed by the act of printing about it, and a bug that stops the CPU cannot print
at all.

This is the lesson that outlives the course. Two instruments replace the one you
have: **SWD and gdb**, which reach into a chip that is no longer running your code
and say where it stopped, and a **single spare GPIO toggled as a marker**, which puts
your firmware's timeline onto the same analyser trace as the wire. `#pin-assignment`
reserved **GP5** for exactly this in lesson 00 and has kept it unused for sixteen
lessons so that nothing has to be rewired now.

## Prerequisites

- Lesson 00 (`00-first-code-and-a-window-in`): the second Pico is flashed as
  `debugprobe` and carries UART0 on GP0/GP1. The same board carries SWD, so the
  hardware for this lesson is already on the bench.
- Lesson 03 (`03-see-the-protocol-before-you-decode-it`): you can capture, set a
  sample rate and trigger, and read a clocked frame off a trace.
- Lessons 04 (`04-your-first-interrupt`) to 08 (`08-ps2-receive-in-pio`): there is an
  ISR and a PIO path whose timing is worth measuring, and a build that selects
  between them.
- Lesson 15 (`15-the-lock-leds`): the firmware is a working adapter. This lesson adds
  no feature to it — it adds instruments to you.
- GP5 free and unwired, as `#pin-assignment` reserved it.
- A build directory still holding the `.elf` for the image that is flashed. Symbols
  come from the ELF; the UF2 you dragged onto the board has none.

## Learning objectives

- Quantify the observer effect: one console line at 115200 against one PS/2 frame.
- Explain what SWD is — a hardware port into the chip, not a feature of your program
  — and why it works when your firmware is wedged.
- Attach gdb through the probe, halt a running adapter, read registers and memory,
  breakpoint, and continue.
- Say what a Cortex-M0+ does on a fault, and why fault-analysis advice written for
  M3 and M4 misleads on this chip.
- Recover the stacked exception frame and turn the stacked PC into a source line.
- Use `panic()` and the SDK's default fault handler deliberately, and say what each
  leaves behind.
- Distinguish a hang, a fault loop and a wedged main loop from outside, before
  attaching anything.
- Toggle GP5 as a timing marker, capture it beside clock and data, and state a
  measured interval between a wire event and a firmware event.
- Choose, for a given question, whether the honest instrument is the console, the
  debugger or the analyser.

## Theory

### Why `printf` stops telling the truth

The console is UART0 at 115200 8N1. One character is ten bit times, so **one
character costs about 87 µs** and a twelve-character line costs **roughly a
millisecond**. A Model M clocks PS/2 at around 10 to 16 kHz, so one clock period is
**60 to 100 µs** and an eleven-bit frame is **roughly 0.7 to 1.1 ms**. One log line
takes about as long as one entire frame. A `printf` near the receive path does not
perturb the timing slightly; it consumes the whole budget.

Two things make it worse than the arithmetic suggests. **`printf` is not
constant-time**: while the UART's small transmit FIFO has room the call returns
quickly, and once it is full it blocks at 87 µs per character — so the same line
costs nothing on a quiet console and a millisecond on a busy one, and the
disturbance appears and disappears as you add unrelated logging. And it is
**catastrophic inside an ISR**: a handler that blocks for a millisecond has missed
ten clock edges, so the frame it was servicing is garbage — intermittently, because
it depends on FIFO state.

This is the **Heisenbug**. You add the print, the bug goes; you remove it, the bug
returns; you conclude the print is load-bearing. It is — on the timing, and the
timing is the bug. The cure is not to print more carefully but to stop measuring
microsecond events with a millisecond instrument.

### SWD: a way in that does not need your program

**SWD is a two-wire hardware debug port** — `SWCLK`, `SWDIO`, plus a shared ground —
into the RP2040's debug access port. It is not a library and your firmware does not
have to be running to provide it. The debug hardware sits beside the cores and can
halt them, single-step them, read any memory the bus reaches, read and write the
core registers, and set hardware breakpoints and watchpoints. **That is the point:**
a wedged firmware cannot print, but a halted core can still be read.

Three links, worth naming so you know which to suspect: the **target** (Pico #1,
exposing SWD on its three-pin debug header); the **probe** (Pico #2 running
`debugprobe`, appearing to the host as a CMSIS-DAP device *and* as the USB-serial
bridge carrying your console — one board, both jobs, which is why `#debug-channel`
put the console there); and the **host**, running OpenOCD (CMSIS-DAP to the probe, a
gdb server on a TCP port) with `arm-none-eabi-gdb` attached to it. Ground is not
optional and is the first thing to check when OpenOCD reports no target.

**Symbols come from the ELF**, not the UF2 and not the chip. If the ELF in your build
directory is not the build that is flashed, gdb shows you the wrong source lines with
complete confidence — far nastier than showing none. **Build with debug information**,
but resist dropping to `-O0` "so the debugger behaves": that changes code size and
timing enough to move the bug you are chasing, which is the printf mistake in a
different hat. If one variable is `<optimized out>` and you truly need it, mark that
one thing `volatile`.

### What a fault looks like on this chip

The RP2040's cores are **Cortex-M0+**, and most fault-analysis writing you will find
is about M3, M4 and M7. Those have separate MemManage, BusFault and UsageFault
handlers and status registers — `CFSR`, `HFSR`, `MMFAR`, `BFAR` — that say what
faulted and where. **The M0+ has none of it.** There is one `HardFault` and no fault
status registers. Following an M4 tutorial here ends in reading an address that is
not a register and believing the noise.

What you get instead is the **stacked exception frame**, and it is enough. On
exception entry the core pushes eight words onto the active stack:

| Offset | Register |
|---|---|
| +0x00 … +0x0C | R0, R1, R2, R3 |
| +0x10 | R12 |
| +0x14 | LR — the return address of whatever was interrupted |
| +0x18 | **PC — the faulting instruction** |
| +0x1C | xPSR |

The word at **+0x18** is the one you came for. Which stack? `LR` inside the handler
holds an `EXC_RETURN` whose bit 2 says whether the interrupted code used MSP or PSP.
This firmware is a superloop with no RTOS, so it is MSP — know the rule anyway,
because the first time it is not, eight words of something else look just as
plausible. Turning that PC into a line is three commands: read eight words at the
stack pointer, take the seventh, then `info line *0x<pc>` and `disassemble` around
it. Do it by hand once; the sequence is the same on every Cortex-M part you will
ever meet.

**What actually faults on an M0+:** a branch or call to an address with the Thumb bit
clear (what a null or corrupted function pointer produces); execution from an
unmapped address; an unaligned 32-bit load or store, which the M0+ does not support
at all where M3 and M4 tolerate some; an undefined instruction. Note the absence: a
stray write through a *data* pointer often does not fault here, because much of the
address map is mapped to something. Build a deliberate fault out of control flow, not
out of a data write.

### `panic`, and what the SDK leaves behind

`panic()` prints a message to `stdout` and then executes a breakpoint. That is the
bridge between your two tools: the message reaches the UART, so you know what and
roughly where, and the breakpoint holds the core so gdb tells you the rest.
`hard_assert()` routes through it.

The SDK's default `HardFault` handler is a breakpoint followed by an infinite loop.
With a debugger attached that is exactly right — the core stops with the stacked
frame intact. With no debugger attached it is an infinite loop, which brings us to
the third skill here.

### A hang is not always a hang

Triage from outside before attaching anything. Three signals distinguish four states:

| `alive` | LED / visible activity | Host still sees the device | Most likely |
|---|---|---|---|
| rising | yes | yes | not wedged; the bug is elsewhere |
| stopped | stopped | device gone | fault loop, or a reset loop |
| stopped | stopped | still enumerated | main loop wedged, USB serviced elsewhere |
| rising | rising | device gone | USB stack broken, core fine |

The second row is what this lesson is named after. "It hangs" and "it faulted" look
identical from the console — both stop printing — and need completely different
investigations. **Telling them apart takes one action: attach, halt, read `$pc`.** If
`$pc` is inside the fault handler it was never a hang.

**Which core?** The RP2040 has two, and OpenOCD presents them to gdb as two threads.
This firmware runs on core0; core1 has never been started and sits in the bootrom.
That is not an idle detail: `info threads` shows two, `backtrace` shows whichever is
selected, and a learner who lands on core1 gets a perfectly valid backtrace of
bootrom code with nothing to do with their bug. Confirm which thread you are reading
before you believe a stack trace.

### GP5: putting your firmware on the analyser's timeline

The debugger answers "where did it stop". It cannot answer "how long after the
falling clock edge did my ISR start", because halting destroys the timing.

For that you need an instrument that costs nothing. **Setting or clearing a GPIO
through the RP2040's single-cycle IO block is one or two instructions — single-digit
nanoseconds at 125 MHz**, five orders of magnitude cheaper than a console line, and
it touches no FIFO, no buffer and no interrupt mask. `#pin-assignment` reserved GP5
for it in lesson 00 and has kept it unused ever since, precisely so this costs no
rewiring. Put a third analyser probe on it beside clock (GP2) and data (GP3), with
the analyser's ground tied to the Pico's — a shared ground is mandatory, and its
absence produces a capture that looks like noise rather than an error message.

Raise the marker at the start of the region you care about and drop it at the end.
The rising edge is a timestamp your firmware placed; the wire edges are timestamps
the keyboard placed; the analyser puts both on one time base. That directly answers
*what is my interrupt latency* (falling clock edge to marker rising edge, including
exception entry and any critical section that had interrupts masked), *how long does
my ISR take* (the pulse width, with jitter visible over many frames), *did the
decoder see frame N* (one pulse per accepted frame), and the question nothing else
can answer — *was that late byte late on the wire, or late in my code?*

**One pin, several events**: encode by pulse width or pulse count — a short pulse for
ISR entry, a long one for a ring-buffer pop. **The trap that catches everyone once**:
a marker pulse tens of nanoseconds wide, captured at 8 MS/s (125 ns per sample), can
land entirely between two samples and simply not exist in the capture. Lesson 03
taught sample rate for the PS/2 clock, where 8 MS/s is luxurious; for a marker it may
not be. Raise the rate, or stretch the marker — and if you stretch it, the stretch is
now part of what you are measuring.

### Choosing the instrument

| Question | Instrument | Why not the others |
|---|---|---|
| What value did this have? | console, or gdb at a breakpoint | the analyser cannot see memory |
| Where did it stop? | gdb | a stopped program cannot print |
| Why only at speed? | GP5 marker + analyser | printing changes the speed; halting removes it |
| Wire or my code? | analyser with the marker | the console shows only your side |
| Hang or fault? | gdb: halt and read `$pc` | identical from the console |
| Is it happening over an hour? | console counters | gdb and the analyser do not run unattended |

## Concepts to teach

- The observer effect quantified: one 115200 line versus one PS/2 frame; `printf`
  blocking when the FIFO fills; why it is catastrophic in an ISR; and the Heisenbug
  as the characteristic failure of this subject rather than a curiosity.
- SWD as hardware independent of the running program; the target/probe/host chain and
  where it breaks; symbols living in the ELF and what a stale ELF does.
- Debug information versus optimisation level, and why `-O0` repeats the printf
  mistake.
- The Cortex-M0+ fault model: one `HardFault`, **no CFSR/HFSR/BFAR**, and why M3/M4
  advice misleads here.
- The stacked exception frame, the stacked PC at +0x18, and `EXC_RETURN` choosing MSP
  or PSP.
- What faults on an M0+ (bad control flow, unaligned access, undefined instruction)
  and what does not reliably fault.
- `panic()` and `hard_assert()` as message-plus-breakpoint, bridging console and
  debugger; the SDK's default handler as breakpoint-then-loop.
- Hang versus fault loop versus wedged main loop, triaged from outside and settled by
  reading `$pc`; two cores, two gdb threads, and reading the wrong backtrace.
- A GPIO toggle as a near-free instrument, and GP5 reserved for it since lesson 00.
- Correlating firmware and wire events on one time base; interrupt latency as the
  distance between two edges; encoding several events on one pin by width or count.
- Sample rate versus marker width: a pulse narrower than the sample period is not in
  the capture.

## Constraints

- The marker goes on **GP5** and nowhere else; `#pin-assignment` reserved it and two
  offered lessons assume the rest of the map is undisturbed.
- Marker code is a direct GPIO set or clear. It must not call anything that can
  block, allocate, lock or print — a marker that is expensive measures itself.
- `stdio` stays on UART0 as `#debug-channel` requires. Nothing here is a reason to
  move it, and moving it breaks every console-reading check.
- No `printf` in an ISR or the PIO service path, in any build, including a temporary
  one. Set the marker, or store to a variable the main loop prints.
- The deliberate fault is behind a build option or guard so it can be re-triggered
  and cannot be left enabled by accident. Do not reproduce it by editing working code
  and hoping to remember.
- The normal build's optimisation and flags do not change. A debug-only variant may
  be added, but later evidence comes from the normal build.
- The `alive` counter keeps printing, so `firmware-alive` keeps passing and the
  triage table stays usable.
- The adapter still works as an adapter afterwards. This lesson adds instruments, not
  behaviour.

## Suggested progression

1. Establish the motivating problem first. Ask what the learner would do today if the
   adapter dropped one frame in a thousand under fast typing; follow the answer to
   `printf`, then do the arithmetic together — line length at 115200 against one
   clock period and one frame.
2. Make the Heisenbug concrete rather than described: put a `printf` where it
   measurably damages reception, watch the frame or resync counters degrade, then
   remove it and watch them recover.
3. Wire SWD — three wires from the probe to the target's debug header, ground
   included — and confirm the probe still carries the console at the same time.
4. Bring the toolchain up end to end: OpenOCD finds the target and reports two cores,
   gdb attaches and loads symbols from the build's ELF. Halt the **running** adapter,
   read `$pc` and `$sp`, continue.
5. Exercise the basics on known-good code: a breakpoint in the main loop, `info
   threads`, `backtrace`, printing a variable, examining the ring buffer indices.
   Have the learner deliberately select the other core and read its backtrace, so they
   meet the wrong-core trap on purpose.
6. Teach the ELF-mismatch failure before it bites: point gdb at a stale ELF and watch
   it name a source line confidently, then fix the workflow so it cannot recur.
7. Cover the M0+ fault model explicitly, including what is absent — have the learner
   look for `CFSR` and find there is no such register.
8. **Inject a fault deliberately**, behind a guard: a call through a bad function
   pointer, or an unaligned 32-bit access, triggered on demand. Observe it from
   *outside* first — console stops, `alive` freezes, the host may or may not still
   list the device — and run the triage table before attaching.
9. Attach and catch it. Halt, confirm `$pc` is in the fault handler and not in the
   learner's code, then walk the stacked frame: eight words from the stack, the word
   at +0x18 as the stacked PC, then the source line and the instruction. The learner
   **names the faulting line**, and can say why the LR in the frame and the LR in the
   handler are different things.
10. Contrast with `panic()`: add one on a condition the learner can trigger, and
    observe both halves — the UART message and the halted core.
11. Contrast with a genuine hang: wedge the main loop deliberately, observe that the
    console looks *identical* to the fault, then attach and see `$pc` in the
    learner's own code. Doing both ways round in one session is the point of the
    lesson's title.
12. Switch instruments. Raise GP5 as the first statement of the receive path, drop it
    as the last, put a third analyser probe on it with grounds tied, and say out loud
    why the pin was free.
13. Capture a keypress on three channels — clock, data, marker — triggering on the
    clock as in lesson 03, and **measure the interval from the falling clock edge to
    the marker rising edge**. State what that number is.
14. Meet the sample-rate trap: if the pulse is not visible, work out whether the code
    did not run or the pulse is narrower than the sample period. Raise the rate or
    widen the pulse, and note that widening changes the measurement.
15. Do something only correlation can do: build the other receive backend
    (`#rx-interface` keeps both alive) and compare the same interval. The first time
    the learner has a number rather than an opinion about the two.
16. Have the learner say which instrument they would reach for given four symptoms.
    If the answer to the timing question is still "add a print", the lesson is not
    finished.
17. Guard or remove the injected fault and the wedge, confirm the adapter works
    normally, and keep the marker — lessons 17 and 18 both want it.

## Completion conditions

- `build-ok` passes for the firmware carrying the marker, and the `alive` counter
  still rises on the console in the normal build.
- SWD works end to end: OpenOCD reports the target, gdb attaches to a **running**
  adapter, halts it, reads registers, sets a breakpoint, and continues with the
  adapter still working afterwards.
- The learner **deliberately introduced a fault, caught it in gdb, and named the
  faulting source line** — the line, not the address — recovered from the stacked
  frame rather than guessed.
- The learner can state unprompted that there is no CFSR on a Cortex-M0+, that the
  stacked frame is the evidence, and where the stacked PC sits in it.
- The learner can show that a fault and a hang are identical from outside and
  immediately distinguishable in gdb, and can say which thread they read and why.
- A capture exists showing PS/2 clock, PS/2 data **and** the GP5 marker on one time
  base, and the learner **states a measured interval between a wire edge and a marker
  edge**, with the sample rate used and what the number means.
- The learner can explain the Heisenbug with the arithmetic, including why the
  disturbance varies with unrelated logging.
- The `fault-diagnosed` validator is satisfied. It is a **manual** check: a human
  looks at the gdb session and the capture, because no script can watch someone
  debug.
- The injected fault is guarded or removed, and the adapter receives and types as
  before.

## On completion, persist

Record in the instance's `DESIGN.md`/`STATE.md`:

- That SWD is wired and works, with the OpenOCD and gdb invocation that connects, and
  which ELF carries the symbols — so a later session does not debug a stale one.
- That **GP5 is now in use as the timing marker**, what it brackets, and how several
  events are encoded on it. Later lessons must not assume GP5 is free.
- The measured interval from the falling clock edge to the marker edge, the backend
  and the sample rate — the baseline for lesson 17 and the offered latency lesson.
- The triage procedure for the next time the board goes quiet: what `alive`, the LED
  and the host's device list say, and that halting and reading `$pc` is the one action
  that separates a fault from a hang.
- That the Cortex-M0+ has a single `HardFault`, no fault status registers, and the
  stacked PC at +0x18 — recorded because it is the fact most likely to be "corrected"
  back by advice written for other Cortex-M parts.
- Where the injected fault lives and how it is guarded.

## Optional deeper paths

- **Flash through SWD instead of BOOTSEL** — `load` from gdb, or `picotool` over the
  probe. Removes the unplug-hold-replug cycle and makes the ELF-mismatch failure
  structurally impossible.
- **Hardware watchpoints.** Watch the ring buffer's head or tail index and catch the
  exact instruction that corrupts it — the most effective tool against the class of
  bug lesson 06 warned about, and impossible with printing.
- **A fault handler that survives a reset.** Stash the stacked PC and LR in the
  watchdog scratch registers and print them on the next boot, so a fault in a sealed
  enclosure leaves a breadcrumb. Pairs with lesson 17's watchdog.
- **`monitor reset halt`** and debugging from the first instruction, for bugs before
  `main` — clock setup, XIP configuration, a static initialiser.
- **Why not semihosting.** It is far slower than the UART and stops dead without a
  debugger attached — worth understanding so keeping UART0 is a decision.
- **Cycle counting without a cycle counter.** The M0+ has no DWT cycle counter; work
  out where the marker is the only honest answer.
