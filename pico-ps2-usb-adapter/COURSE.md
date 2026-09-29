# Build a PS/2 to USB HID Keyboard Adapter on the Raspberry Pi Pico

## What you will have at the end

A soldered adapter in a case. You plug an IBM Model M into one end and any modern computer
into the other, and it just types — no driver, working in a BIOS, lock LEDs lit.

And you can say exactly why, at every layer: from the open-drain edge on the PS/2 clock
line to the 8-byte interrupt-IN report the host polls for.

## Who this course is for

You are comfortable with C — pointers, structs, bit manipulation — and with a shell, git
and a reference manual. Nothing here teaches programming.

You have never written microcontroller firmware, never reasoned about a pull-up resistor,
never read a digital signal off a wire, and never met USB below the level of "plug it in".
All of that is taught here, from the beginning.

The teaching effort goes entirely into the embedded, electrical, timing and protocol
layers. The computer-science content is not watered down to match: when the course needs a
lock-free single-producer ring buffer it says so and describes one, rather than building up
to it from first principles.

## How this course teaches

**You build it. Every line of firmware is yours.** The course supplies fixtures, reference
tables, a stripboard layout and the check scripts. It supplies no firmware and no
`CMakeLists.txt`, because the build file is edited in nearly every lesson and is therefore
a thing you must be able to change rather than a thing handed over.

**Every lesson ends in something you can observe or measure.** Not "you have written the
receiver" — a count rising on a console, a byte you recognise, a trace on an analyser, a
character appearing in a text editor. If a lesson cannot be finished by looking at
something, it is not finished.

**You see the signal before you decode it.** Lesson 03 hands you a logic analyser and asks
you to derive the PS/2 frame from your own capture, before any code reads it. A protocol
you have measured is a protocol you can debug.

**You write the slow version first.** The receiver is built with CPU interrupts in lessons
04 to 06 and only then offloaded to PIO in lesson 08. PIO is the better implementation and
it teaches nothing about interrupt latency, shared state between an ISR and a main loop,
`volatile` or critical sections — all of which you are new to and all of which are on the
list below. The interrupt version also gives the PIO version something known-good to be
debugged against, and gives lesson 08's measurement a baseline.

**You write every USB descriptor by hand.** No generator, no copied header. Descriptors are
where a device stops being a mystery, and the only way through that is to write the bytes
and read them back off the host.

**Evidence comes off your board, not off your word.** Your firmware logs structured lines to
a debug console on a second Pico, and the tutor's checks read that console. Firmware that
builds but does not run does not pass. Where a check cannot be automated — a multimeter
reading, a captured trace, a lit LED, a soldered board — you are asked to show it, and there
are eleven such checks, because this is a hardware course and pretending otherwise would be
worse.

## Before you start: what you need on the bench

The full list with reasons is in `BOM.md`, which is placed in your workspace when the
course starts. Lead time is the one thing you cannot compress, so read it first.

Two items are load-bearing and worth naming here:

- **A second Raspberry Pi Pico**, flashed as `debugprobe`. It carries your debug console in
  every lesson and SWD in lesson 16. It is not optional in practice — the checks read that
  console.
- **A BSS138-type 4-channel bidirectional level shifter.** Not a resistor divider, and not a
  unidirectional buffer. Lesson 02 explains why both of those fail on this bus, and the
  second one fails four lessons after you choose it.

A logic analyser (any cheap sigrok-compatible clone) and a multimeter are assumed. An
oscilloscope is **not** assumed; it is used only by an optional lesson.

**One warning the course states plainly rather than enforcing.** Buggy firmware on an input
device types into whatever window has focus. Develop against a machine you do not mind being
typed into, or take the optional `a-safety-catch` lesson, which solves it in firmware.
Neither is required.

## The route

Eight milestones, nineteen lessons. Each milestone is a thing that works.

### M1 — I can run my own code, and see inside it

- **00 `first-code-and-a-window-in`** — your code on the chip, and a console USB cannot
  later steal.

### M2 — the keyboard is safely connected and I have seen its signal

- **01 `the-ps2-connector-and-what-is-safe`** — the four live pins, and proof the Pico can
  power the keyboard, before anything touches a GPIO.
- **02 `open-drain-and-pull-ups`** — the interface between a 5 V open-collector bus and a
  3.3 V part, and why it has to be built that way.
- **03 `see-the-protocol-before-you-decode-it`** — derive the frame format from your own
  capture.

### M3 — raw frames arrive in my program

- **04 `your-first-interrupt`** — a hardware event reaches your code.
- **05 `a-state-machine-in-an-isr`** — eleven edges become one byte you can trust.
- **06 `handing-data-to-the-main-loop`** — bytes leave interrupt context without being lost
  or corrupted.

### M4 — PIO does the framing, in both directions

- **07 `what-a-pio-state-machine-is`** — run a program on something that is not the CPU.
- **08 `ps2-receive-in-pio`** — move the framing off the CPU, and measure what that bought.
- **09 `talking-back-in-pio`** — drive the bus in the other direction, on a line the device
  clocks.

### M5 — I have key events for every key on the board

- **10 `scan-codes-to-key-events`** — a byte stream becomes key-down and key-up events for
  every key, Pause and Print Screen included.

### M6 — the host says "a keyboard is plugged in", and it types

- **11 `descriptors-you-write-yourself`** — answer the questions a host asks a device it has
  never seen.
- **12 `the-hid-report-descriptor`** — describe the shape of your reports in a language the
  host can parse.
- **13 `your-first-keystroke`** — make the host type a character your firmware chose.

### M7 — it is actually a Model M adapter, lock LEDs and all

- **14 `events-to-state`** — join the two halves: PS/2 emits events, USB HID reports state.
- **15 `the-lock-leds`** — close the loop, and let the host tell the keyboard something.

### M8 — a finished object I trust

- **16 `when-it-goes-wrong`** — the tools to diagnose the next bug yourself.
- **17 `robustness-and-the-real-world`** — behave when things are not ideal.
- **18 `off-the-breadboard-and-done`** — a working circuit becomes an object you trust.

## Lessons the tutor may offer you

These are written and shipped with the course, and none of them is on the route above. The
tutor offers each one after the lesson that earns it; take it or decline it, and the course
finishes either way.

| Lesson | What it is for | Offered after |
|---|---|---|
| `see-the-edges-on-a-scope` | see the rise time you calculated, on a real bus. **Needs an oscilloscope.** | 02 |
| `watch-the-enumeration` | see the enumeration conversation as packets rather than infer it. **Needs a Linux or Windows host — USB capture does not work on macOS.** | 11 |
| `a-safety-catch` | stop buggy firmware typing into whatever has focus | 13 |
| `a-second-interface-for-debugging` | a channel through USB itself, and why it cannot live on the keyboard interface | 13 |
| `measure-your-latency` | what the adapter actually costs the typist | 14 |
| `nkro-without-a-driver` | report more than six keys, and understand what you give up | 14 |
| `remap-and-macros` | make the layout yours | 15 |

## Topics this course must cover

Named as you would ask about them, not as a lesson happens to be titled.

- microcontroller execution model
- boot ROM and UF2
- XIP flash and the memory map
- GPIO
- push-pull vs open-drain
- pull-up sizing
- RC on a bus
- logic levels, and 3.3 V vs 5 V
- level shifting
- current budget
- reading a pinout
- interrupts
- ISR latency
- what you may not do in an ISR
- ISR and main-loop shared state
- `volatile`
- critical sections
- lock-free single-producer ring buffers
- framing state machines
- resynchronisation and timeouts
- parity
- RP2040 PIO
- the PIO instruction set
- PIO shift registers and autopush
- clock dividers
- protocol offload, and how to measure it
- PS/2 electrical interface
- PS/2 framing in both directions
- bus arbitration on a shared line
- scan code set 2
- make and break
- extended and break prefixes
- typematic repeat
- USB bus topology and addresses
- endpoints and transfer types
- USB enumeration
- USB descriptors
- HID report descriptors
- usages, arrays and bitmaps
- boot protocol vs report protocol
- HID keyboard reports
- modifiers
- rollover
- HID output reports and lock LEDs
- USB suspend, resume and remote wakeup
- firmware architecture with swappable backends
- where state lives in a small firmware
- SWD and gdb
- reading a hard fault
- the observer effect of `printf` on timing
- logic analyser use
- sample rate and triggering
- soldering
- continuity testing
- strain relief

## Where this course stops

Listed so that when you hit one of these you know you have reached a boundary and not a
hole. If you want one of them, it is a different course.

- USB host mode, hubs, USB 3, and isochronous or bulk transfers
- DMA, which the RP2040 has and this project does not need
- an RTOS — the architecture here is a superloop plus interrupts, deliberately
- Rust, MicroPython and CircuitPython
- PCB design and fabrication
- wireless of any kind
- the Model M's internal matrix and controller, beyond what rollover forces you to know
- reading your own keyboard's HID input reports back from the host, which no desktop OS
  permits
- USB packet capture on macOS, which does not work
- NKRO beyond the optional lesson
- ESP32-S3 and other platforms, discussed once in lesson 00 and then left alone
