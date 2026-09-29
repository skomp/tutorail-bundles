---
id: 00-first-code-and-a-window-in
title: Your first code on the chip, and a window in
design_refs: [debug-channel, pin-assignment]
validators: [build-ok, firmware-alive]
---

## Purpose

Before you can debug a keyboard you have to be able to debug anything at all, and on a
microcontroller that is not a given: there is no shell on the chip, no log file, no
process to attach to, and nothing that will tell you your program crashed. This lesson
gets your own code running on the RP2040 and then builds the one thing every later lesson
leans on — a console you can read while the firmware runs.

There are two ways to get that console on a Pico, and the obvious one is wrong. A USB
serial console needs three lines of build configuration and no extra hardware; a UART
console needs a second Pico, four jumper wires and a decision about pins. The USB console
is the one that disappears in lesson 11, at the exact moment enumeration is failing and
you most need to see inside the chip. Choosing the harder console now, before it costs you
anything, is the whole point of putting this lesson first.

The other thing this lesson does is destroy a comfortable illusion. When you hold BOOTSEL
and plug the Pico in, a drive appears on your desktop. That drive is not your program
running. It is a program in mask ROM that is *not* your program, presenting itself as a
USB mass-storage device so that a file copy can write flash. Learners lose hours to the
gap between "the drive appeared" and "my code is executing", and the fastest cure is to
meet the distinction on the first day.

## Prerequisites

- You can write and build C, and read a compiler or linker error without help.
- You have the bench set out in `BOM.md` — in particular **two** Raspberry Pi Picos, one
  of which will become the debug probe and never runs your firmware.
- You have a working network connection, because you are about to install a toolchain.
- Nothing is connected to any GPIO. No keyboard, no level shifter. That starts in
  `01-the-ps2-connector-and-what-is-safe`.

## Learning objectives

After this lesson you can:

- Say what happens between power being applied to an RP2040 and your `main` being entered,
  and where BOOTSEL sits in that sequence.
- Explain what a UF2 file is and why the bootloader uses that format rather than a raw
  binary.
- Describe where code and data live on this chip — external QSPI flash executed in place,
  internal SRAM — and why the first call into a function can be slower than the second.
- Configure a pico-sdk project so that `printf` reaches a specific physical route, and say
  what happens to a `printf` when no route is enabled.
- State, without hedging, why this course's debug console is on UART and not on USB, and
  what specifically breaks if it moves.
- Emit a structured log line that the course's checks can read, and read it back on a host.

## Theory

### A program that owns the machine

Everything you have written until now ran under an operating system that started it, gave
it memory, and cleaned up after it. None of that is here. Your firmware is the only program
on the chip; it starts because the hardware jumps to it; it must never return from `main`,
because there is nothing to return to; and if it faults, the chip does not print a stack
trace, it simply stops behaving.

The shape of nearly all firmware, this project included, is a **superloop**: initialise the
peripherals, then loop forever, servicing whatever needs servicing. Interrupts punch into
that loop when hardware demands attention. That is the entire architecture of the adapter
you are building — there is no RTOS here, deliberately.

### Power-on, the boot ROM, and BOOTSEL

The RP2040 has no internal program flash. What it has is a **boot ROM**: a small,
unchangeable program fixed in silicon at the bottom of the address map, which runs first,
every time, and cannot be bricked.

The boot ROM's job is to decide where your code comes from. It looks at the BOOTSEL button
and at the first 256 bytes of the external QSPI flash chip:

- If BOOTSEL is held at power-on, or the flash holds nothing that looks valid, the ROM
  starts its **USB mass-storage bootloader**. A drive called `RPI-RP2` appears on your
  host. The chip is running the ROM, not your program.
- Otherwise the ROM loads the first 256 bytes of flash — the *second stage bootloader*,
  which the SDK links into every binary — and that stage configures the flash interface and
  jumps into your code.

This is why a Pico is effectively unbrickable, and it is also the trap. `RPI-RP2` appearing
means the chip is healthy and waiting. It says nothing whatsoever about your firmware.

### UF2, and why not a plain binary

You program the chip by dragging a `.uf2` file onto that drive. UF2 exists because a
mass-storage write is a terrible channel for firmware: the host's filesystem driver may
send the blocks in any order, may retry, may write metadata in between, and never tells the
device "that was the whole file".

So UF2 abandons the idea of a file. It is a sequence of self-describing 512-byte blocks,
each carrying magic numbers, a target address, a payload, and a block count so the receiver
knows when it is done. Any block can be recognised, placed and written on its own, in any
order, and a stray filesystem write is ignored because it does not carry the magic. The
format is a workaround for a transport that was never meant to carry firmware, and knowing
that is what stops it being mysterious.

### Where your code actually lives

Three regions matter to you:

- **QSPI flash**, a separate chip on the board, mapped at `0x10000000`. Your code is not
  copied into RAM; it is **executed in place** (XIP) through a small cache. A call into a
  function whose instructions are not in that cache pays a flash access; the second call
  usually does not. Later in this course, when you are measuring microseconds, that
  difference is measurable and you should not be surprised by it.
- **SRAM** at `0x20000000` — 264 KB, holding your data, your stack, and anything you
  deliberately place there.
- **Peripherals** in a block starting at `0x40000000`, plus the single-cycle I/O block
  higher up. A peripheral register is a memory address; writing to it changes hardware.

### `printf` does not have a destination until you give it one

In the pico-sdk, `stdout` is wired to a **stdio driver**, and which drivers exist is a
build-time decision. Two are relevant: UART and USB CDC. Your CMake target enables one,
both, or neither, and your code calls the SDK's stdio initialisation before printing.

If you enable neither, `printf` compiles, links, runs, and goes nowhere. There is no error,
no warning, and no return code you would have looked at. This is the single most common "my
board is dead" report from a first firmware project, and the board is fine.

If you enable USB CDC, `printf` output arrives on a virtual serial port over the Pico's own
USB connector, and the SDK's USB stack claims that connector. Remember that.

### Why this course's console is UART, and why that is not negotiable

`#debug-channel` in `DESIGN.md` fixes this, and the reason is worth having in your own
words rather than taking on authority.

**USB is the artefact under test.** From lesson 11 onward the whole subject of the course
is what your firmware presents on its USB connector. A USB console is either taken away
from you when TinyUSB claims the peripheral for HID, or survives only as a second interface
on a composite device — which is to say it becomes a variable in the very experiment you
are running. When your device fails to enumerate, a console that exists only if enumeration
succeeded tells you nothing.

**The failure is delayed and expensive.** Putting stdio on USB in this lesson costs you
nothing today, works beautifully for ten lessons, and takes your diagnostic channel away in
the week you need it most. That asymmetry is why the decision is made now, and made once.

**The checks read this console.** Every automated validator in this course opens the UART
and reads structured lines your firmware prints. A console that does not exist is a course
that cannot advance you on evidence.

The console is therefore **UART0 on GP0 (TX) and GP1 (RX)**, at **115200 8N1**, wired to a
second Pico running the `debugprobe` firmware, which presents it to your host as an ordinary
serial port. That same second Pico carries SWD, which you will use in lesson 16, so the
hardware is on the bench either way.

### The log line contract

Every check in this course reads the debug console and looks for lines of exactly this
shape, one record per line, ASCII, newline-terminated:

```
key: value
```

The key is lower-case letters, digits and hyphens. **Any line that does not match this
shape is ignored by every check** — SDK noise, partial lines, and your own scratch `printf`
debugging all pass through harmlessly. That is deliberate: you stay free to print whatever
you like alongside the structured records.

This lesson introduces one key: **`alive`**, whose value is a counter that must increase
strictly, printed roughly once a second. It is the firmware's pulse. For the rest of the
course, `alive` stopping means your main loop stopped, which is a diagnosis you will be
glad to have for free.

### Why an RP2040 at all

You could build this adapter on an ESP32-S3 or an STM32. The RP2040 is chosen for two
reasons: its PIO block, which is the subject of a third of this course and has no direct
equivalent on the other two; and the sheer volume of community material a stuck learner
will find when searching. An RP2350 works unchanged if that is what you have. This is the
only lesson that discusses the choice; after this the course assumes it.

## Concepts to teach

- Bare-metal execution: no OS, `main` never returns, the superloop.
- The RP2040 boot ROM, the BOOTSEL path, and the second stage bootloader.
- Why `RPI-RP2` appearing is not evidence that firmware runs.
- The UF2 format as an answer to an untrustworthy transport.
- XIP flash versus SRAM, and the memory map at the level of "which region is which".
- pico-sdk stdio drivers as a build-time choice; a `printf` with no route.
- The `#debug-channel` argument in the learner's own words, including what breaks.
- UART basics: 115200 8N1, TX to RX, and common ground.
- The `key: value` console contract, and the `alive` key.

## Constraints

- Stdio goes to **UART only**. USB CDC stdio must be disabled in the build, not merely
  unused. If you find yourself reading the console over the Pico's own USB cable, stop.
- UART0 on **GP0 and GP1**, 115200 8N1, as `#pin-assignment` fixes. Do not relocate it.
- Nothing may touch GP2 or GP3 in this lesson. They are spoken for.
- `CMakeLists.txt` is yours to write. The course does not supply one, here or ever, because
  you will edit it in nearly every lesson.
- The firmware must print `alive` with a strictly increasing value, spelled exactly
  `alive`, roughly once per second, and must keep doing so indefinitely.
- The LED must be driven by your code, not by anything the bootloader does.
- Do not delay so long that the console looks dead, and do not print `alive` in a tight loop
  that floods the port.

## Suggested progression

1. Install the ARM cross-toolchain, CMake and the Pico SDK on your machine, and set
   `PICO_SDK_PATH` so a build can find it. This needs the network, which is why it is your
   work and not a supplied file.
2. Confirm the environment before writing code: the `toolchain-present` check exists for
   exactly this, so that a failure later in this lesson is your code and not your setup.
3. Read the supplied `README.md` in your workspace for how this repository is meant to be
   built, and glance at the supplied `pico_sdk_import.cmake`, which is SDK boilerplate you
   will never modify.
4. Write a minimal `CMakeLists.txt`: project, SDK initialisation, one executable, link the
   core SDK library, and produce the extra outputs including the `.uf2`.
5. Write a `main` that does nothing but toggle the on-board LED in a loop. Build it.
6. Flash it: hold BOOTSEL while plugging the Pico in, confirm `RPI-RP2` appears, copy the
   `.uf2`, and watch the drive dismount as the chip reboots into your code.
7. Say out loud what each of those two states was — the boot ROM, then your program — and
   what you would have seen on the desktop if your `.uf2` had been corrupt.
8. Now add a `printf` to the loop and rebuild **without** enabling any stdio route. Flash
   it. Observe that absolutely nothing happens and nothing complains. Meet this failure
   deliberately now, because the next time you meet it you will not lose an hour to it.
9. Enable the UART stdio route in your CMake target, explicitly disable the USB one, and
   call the SDK's stdio initialisation at the top of `main`.
10. Flash the second Pico with the `debugprobe` firmware. It is a separate device with a
    separate job and never runs your code.
11. Wire the console: your Pico's GP0 (UART0 TX) to the probe's UART RX pin, your GP1
    (UART0 RX) to the probe's UART TX pin, and — the one everybody forgets — **ground to
    ground**. Check the probe's pin numbers against the `debugprobe` documentation for the
    build you flashed, not against memory.
12. Find the serial port the probe presents on your host, open it at 115200 8N1, and get
    your `printf` output onto the screen. If you see nothing, suspect TX and RX swapped, and
    then missing ground, in that order.
13. Record the port in `device.env`, which is already in your workspace waiting to be filled
    in. The checks read it to find your console.
14. Replace the scratch `printf` with the structured record: a counter that increments and
    is printed as `alive: <n>` about once a second. Keep the LED blinking, so that a dead
    console and a dead chip look different from across the room.
15. Have the `build-ok` and `firmware-alive` checks run against it.
16. Before you finish, unplug the debug probe's USB cable and watch the console go silent
    while the LED keeps blinking. That is the difference between your firmware and your view
    of it, and it is worth having seen once.

## Completion conditions

- The `build-ok` check passes against a `CMakeLists.txt` you wrote.
- The `firmware-alive` check reads `alive` from the debug console with a value that is
  strictly increasing across successive readings, sustained over several seconds.
- The on-board LED is blinking under your code's control while that console output is
  flowing, so the two are visibly independent.
- `device.env` names a serial port that the checks actually opened.
- The build configuration enables the UART stdio route and disables the USB one, and the
  learner can point at both lines.
- The learner can answer, unprompted: what is running when `RPI-RP2` is mounted; what a UF2
  block carries and why; where a `printf` goes when no stdio driver is enabled; and what
  specifically would break in lesson 11 if this console were on USB.

## On completion, persist

- The serial port path or identifier of the debug console, and the baud rate.
- The Pico SDK version and install path, and the ARM toolchain version.
- Which board is the target and which is the probe, physically labelled if possible —
  swapping them wastes an evening.
- The decision, with its reason: stdio on UART0, USB stdio disabled, per `#debug-channel`.
- That GP0 and GP1 are now committed, and GP2 and GP3 are reserved for lesson 02.

## Optional deeper paths

- Read the first 256 bytes of a built `.bin` and identify the second stage bootloader,
  including the checksum the boot ROM validates.
- Open a `.uf2` in a hex editor and decode one block by hand: magic, flags, target address,
  payload length, block number and total.
- Look at the linker script the SDK uses and find where the XIP region, SRAM and the stack
  are placed, and what building for RAM instead of flash would change.
- Measure the XIP cache effect: time a call into a function cold and warm, and see what the
  cache is worth.
- Find out what `picotool` can do that dragging a file cannot — reboot a running board into
  BOOTSEL over USB, read flash back, and inspect the binary information the SDK embeds in
  your own firmware.
