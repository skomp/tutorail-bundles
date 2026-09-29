# PS/2 to USB HID keyboard adapter

Firmware for a Raspberry Pi Pico that reads an IBM Model M over PS/2 and presents it to any
computer as an ordinary USB HID boot keyboard. No driver, and it works in a BIOS.

You are writing all of it. This repository starts nearly empty on purpose: what is here is
the scaffolding you would otherwise have to type out, and everything that teaches something
is yours to write.

If you have never built firmware for a microcontroller before, this file is the operational
half — toolchain, build, flash, console. The teaching half is the course.

---

## Read these first

| File | What it is |
|---|---|
| `BOM.md` | the shopping list. **Read it before lesson 00** — two parts on it have a lead time you cannot compress |
| `docs/PINOUT.md` | the PS/2 connector drawn from both sides, and every Pico pin this project claims |
| `device.env` | which serial port your debug console is on, and the VID/PID your device will use. You fill it in during lesson 00 |

---

## What is in here already

```
pico_sdk_import.cmake     boilerplate the Pico SDK requires. Do not edit it.
device.env                your machine-specific settings. Fill it in; it is not committed.
BOM.md                    the shopping list.
docs/PINOUT.md            the pinout reference.
checks/                   the scripts the tutor runs to read evidence off your hardware.
.gitignore
```

And what is not, because you write it:

```
CMakeLists.txt            the build. You will change it in nearly every lesson.
src/  include/  pio/      the firmware.
captures/                 your logic analyser captures.
```

---

## The hardware

The short version, with the full story in `BOM.md` and `docs/PINOUT.md`:

- **Two Picos.** One is the adapter you are building. The other is flashed with Raspberry
  Pi's `debugprobe` firmware and is your debug console and, later, your debugger. You cannot
  do this course with one.
- **A BSS138-type bidirectional level shifter** between the keyboard's 5 V bus and the
  Pico's 3.3 V GPIO. RP2040 pins are not 5 V tolerant, and PS/2 clock and data are
  open-drain lines that both ends have to be able to pull low.
- **A PS/2 keyboard**, and a way to get at its four live pins: pin 1 DATA, pin 3 GND,
  pin 4 +5 V, pin 5 CLOCK.
- **A multimeter and a logic analyser.** An oscilloscope is not needed.

The pin assignment is fixed by the design and is not yours to move:

| | |
|---|---|
| GP0 / GP1 | UART0 TX / RX — the debug console, to the second Pico |
| GP2 | PS/2 clock, through the level shifter |
| GP3 | PS/2 data, through the level shifter |
| GP4, GP5 | reserved; do not use them |
| VBUS (pin 40) | powers the keyboard. **Not** 3V3(OUT) |

---

## Toolchain

You need, once:

- **CMake** 3.13 or newer
- **A C compiler for ARM**: `arm-none-eabi-gcc` and its newlib C library
- **A build tool**: Ninja or Make
- **Python 3**, for the course's checks
- **The Raspberry Pi Pico SDK**, cloned somewhere permanent
- **picotool**, for flashing and for inspecting UF2 files
- **OpenOCD** 0.12 or newer, for SWD through the second Pico (needed from lesson 16; install
  it early anyway)

### Linux (Debian, Ubuntu and relatives)

```
sudo apt install cmake ninja-build build-essential python3 \
                 gcc-arm-none-eabi libnewlib-arm-none-eabi \
                 libstdc++-arm-none-eabi-newlib
```

`picotool` and `openocd` may or may not be packaged for your release; if `apt` does not have
a recent enough one, build them from source. Both are small.

### macOS

```
brew install cmake ninja picotool openocd
brew install --cask gcc-arm-embedded
```

### Windows

Use the official **Pico setup installer** from Raspberry Pi, which installs the compiler,
CMake, Ninja, the SDK and OpenOCD together and sets the environment up for you. Doing it
piecemeal on Windows is a bad afternoon.

### The SDK

Clone it somewhere it can live permanently — not inside this repository:

```
git clone --recurse-submodules https://github.com/raspberrypi/pico-sdk.git
export PICO_SDK_PATH=/absolute/path/to/pico-sdk
```

**`--recurse-submodules` matters.** TinyUSB, which you need from lesson 11, is a submodule.
Without it, everything builds fine for ten lessons and then the USB work will not compile.
If you have already cloned without it:

```
cd /path/to/pico-sdk && git submodule update --init
```

Put the `PICO_SDK_PATH` export in your shell profile, or pass `-DPICO_SDK_PATH=...` to
CMake every time. `pico_sdk_import.cmake` in this repository is what turns that variable
into a working build; it is the SDK's own boilerplate, unmodified, and nothing in this
course changes it.

The tutor can confirm all of the above for you with the `toolchain-present` check before you
write a line of code — so that a failure in lesson 00 is your firmware and not your
environment.

---

## Configure

Open `device.env` and fill in the serial port of your debug console. Every line in it is
commented, including how to find the port on Linux, macOS and Windows.

`device.env` is deliberately not committed: it names a device path that is true only on the
machine you are sitting at.

---

## Build

`CMakeLists.txt` is already in this directory. It is minimal on purpose and routes
`printf` nowhere at all, so a build from it is silent until lesson 00 has you decide
where the console lives and add the two lines that say so. The cycle is:

```
cmake -S . -B build
cmake --build build --parallel
```

After the first configure, `cmake --build build` on its own is enough; it re-runs the
configure step by itself when you change `CMakeLists.txt`.

**Build into `build/`, at the root of this repository.** The directory is not
configurable: the `build-ok` check runs exactly the two commands above and looks under
`build/` for what they produced.

Add `-G Ninja` on the configure line if you want Ninja rather than Make — CMake remembers
the choice in the build tree afterwards. Add `-DPICO_BOARD=pico2` if you are building for a
Pico 2 / RP2350; the default is `pico`.

A successful build leaves `build/<your-project-name>.uf2` and a matching `.elf`. The `.uf2`
is what you drag onto the board; the `.elf` is what a debugger reads symbols from.

If the build tree ever gets into a confusing state, delete `build/` and configure again. It
is entirely disposable, which is why `.gitignore` ignores it.

The tutor runs this for you as the `build-ok` check.

---

## Flash

Three routes. The first always works; the third is the one you will actually use day to day.

### 1. BOOTSEL and drag-and-drop

Hold the **BOOTSEL** button on the Pico while you plug its USB cable in, then let go. The
board appears as a USB mass-storage volume called `RPI-RP2`. Copy your `.uf2` onto it; the
board reboots into your firmware as soon as the copy finishes and the volume disappears.

The volume vanishing mid-copy is normal and is not an error, even though some file managers
report it as one.

This route needs no tools and works from a cold, bricked or empty board. It also means
reaching for the button every single time, which gets old by lesson 04.

### 2. picotool

With the board in BOOTSEL as above:

```
picotool load build/<your-project-name>.uf2
picotool reboot
```

`picotool load -f` claims to reboot a *running* board into BOOTSEL for you. It cannot do
that here: that trick needs the firmware to expose a USB reset interface, and this project
deliberately keeps its USB interface clean for the keyboard. So you still press the button.

`picotool info -a build/<your-project-name>.uf2` is separately useful for reading what is
actually inside a binary.

### 3. SWD, through the second Pico

Once the debug probe is wired (see `docs/PINOUT.md`), you can load firmware over SWD with no
button and no replug:

```
openocd -f interface/cmsis-dap.cfg -f target/rp2040.cfg \
        -c "adapter speed 5000" \
        -c "program build/<your-project-name>.elf verify reset exit"
```

Use `target/rp2350.cfg` for a Pico 2.

This is worth setting up on day one. It turns a twenty-second ritual into a one-line command,
and it is the same connection lesson 16 uses to put you in `gdb`:

```
openocd -f interface/cmsis-dap.cfg -f target/rp2040.cfg -c "adapter speed 5000"
# and in another terminal
arm-none-eabi-gdb build/<your-project-name>.elf
(gdb) target extended-remote localhost:3333
```

---

## The debug console

This is where you see what your firmware is doing, and it is where every automated check in
this course gets its evidence.

Your firmware prints to UART0 on GP0/GP1 at **115200 8N1**. The second Pico, running
`debugprobe`, carries that to your computer as a USB serial port. Open it with whatever you
like:

```
# Linux / macOS
picocom -b 115200 /dev/serial/by-id/usb-Raspberry_Pi_Debugprobe...-if00
screen /dev/cu.usbmodem1101 115200          # ctrl-a k to quit
minicom -b 115200 -D /dev/ttyACM0

# Windows
# PuTTY, connection type Serial, COM7, speed 115200
```

Three things to know about it:

- **The port is exclusive in practice.** If you have `picocom` open, a check that tries to
  read the same port will either fail or steal characters from you. Close your terminal
  before the tutor runs a console check.
- **Getting your firmware to print at all is lesson 00's job.** A Pico does not route
  `printf` anywhere by default; deciding where it goes, and making that happen, is the first
  real thing you will do. Until you do, the console is silent and the board is fine.
- **Do not move the console to USB**, however tempting it looks once lesson 11 has USB
  working. The whole reason the console is a separate wire on a separate board is that USB is
  the thing under test. `#debug-channel` in `tutorial/DESIGN.md` has the argument in full.

### The log line format

Checks read lines of exactly this shape, ASCII, one per line:

```
key: value
```

where `key` is lower-case letters, digits and hyphens. Anything that does not match — your
own `printf` debugging, SDK noise, a half-printed line — is ignored by every check, on
purpose. Print whatever you find useful alongside; you will not break anything.

Each lesson tells you which keys it needs and exactly how to spell them.

---

## How the course checks your work

The tutor runs the checks; you do not. Some are scripts in `checks/` that build your
firmware, read your console or ask the host about your device. Eleven of them are manual,
because a multimeter reading, a captured trace, a lit LED and a soldered board need a human
to look at them — that is the honest answer for this subject, not a gap.

Some checks need you to do something physical while they watch: press a key five times,
unplug the keyboard mid-press, hold seven keys down. The check says so and waits. The
machine reads the evidence; you cause it.

---

## Safety

**RP2040 GPIO is not 5 V tolerant.** Nothing from the keyboard reaches GP2 or GP3 except
through the level shifter. There is no warning stage: the pin simply stops working, possibly
not until days later. Lesson 01 is built entirely around not making this mistake, and
`docs/PINOUT.md` exists because reading a mini-DIN-6 pinout mirrored is how people make it.

**Buggy firmware on an input device types into whatever has focus.** A missing key-release
report types one character forever and the only cure is to unplug the adapter. Develop
against a machine you do not mind being typed into, or take the offered `a-safety-catch`
lesson, which adds a firmware gate on GP4. Neither is required, and no check assumes either.

---

## When something is wrong

| Symptom | Usual cause |
|---|---|
| `SDK location was not specified` from CMake | `PICO_SDK_PATH` is not set in the shell you are building in |
| Something about TinyUSB not being found, from lesson 11 onward | the SDK was cloned without `--recurse-submodules` |
| CMake spends minutes building `picotool` on a fresh build tree | SDK 2.x builds its own copy when it cannot find one. Install `picotool` system-wide and it stops |
| No `RPI-RP2` volume when you hold BOOTSEL | a charge-only USB cable. Very common, and it looks exactly like a dead board |
| Console is silent | in lesson 00, probably expected — see above. Later: TX wired to TX instead of to the probe's RX, no shared ground, or a baud mismatch |
| Console prints convincing garbage | baud mismatch between your firmware and 115200 |
| Permission denied opening the serial port on Linux | you are not in the `dialout` group |
| The check hangs forever opening a port on macOS | you gave it the `/dev/tty.*` name instead of `/dev/cu.*` |
| A GPIO that used to work has stopped | it met 5 V. Move to a spare pin and find out how before you continue |
