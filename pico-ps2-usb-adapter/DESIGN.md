# Design decisions

Durable decisions about the adapter that later lessons depend on. Each one was made
before the course was written, and a lesson that contradicts one breaks something
concrete — the section says what.

This file is read by the tutor. A term the learner has to understand at their first task
is defined in `COURSE.md` or in the lesson body, not here.

## Pin assignment {#pin-assignment}

PS/2 **clock on GP2** and PS/2 **data on GP3** — adjacent, and in that order.

The order is not cosmetic. A PIO state machine addresses pins from a base index, and two
adjacent pins can be reached from one mapping where two scattered ones cannot.

Be precise about *how*, because the near-miss version of this argument is wrong and a
lesson written from it would teach a bug. `in pins, N` shifts in N bits **starting at the
IN base**, and `wait <level> pin <index>` has the state machine's input IO mapping applied
first — the datasheet's wording is "PIN: Input pin selected by Index. This state machine's
input IO mapping is applied first". So both are IN-base-relative, and with the base at GP2
they both address the **clock**. Only `wait <level> gpio <n>` takes an absolute GPIO
number, and `jmp pin` has its own separate setting in `EXECCTRL_JMP_PIN`.

What adjacency actually buys is therefore a *choice* rather than a free read: either line
is one base away, so a program may put the IN base on whichever of the two it needs to shift
and reach the other absolutely. The place it is genuinely load-bearing is lesson 09, where a
single two-pin `set pindirs` group based at GP2 expresses the whole line-state vocabulary of
the host-to-device sequence — release both, pull clock low, pull data low, release clock —
in one instruction per state. Scattering the pins costs that, and costs instructions a
nine-instruction program can rarely spare.

> **Correction, 2026-09-29.** This section previously claimed that "with clock at the base
> and data at base+1, one `in pins, 1` reads the data line while `wait 0 pin 0` has just
> synchronised on the clock". That is wrong in both halves: with the IN base at GP2, `in
> pins, 1` reads the clock, and `wait 0 pin 0` also refers to GP2. The decision — clock on
> GP2, data on GP3, adjacent and in that order — is unchanged and still correct; only its
> justification was wrong. Lessons 07 and 08 teach the real semantics.

The rest of the assignment:

| Pin | Use |
|---|---|
| GP0, GP1 | UART0 TX and RX to the second Pico running `debugprobe` — the debug console |
| GP2 | PS/2 clock, through the level shifter |
| GP3 | PS/2 data, through the level shifter |
| GP4 | reserved for the offered `a-safety-catch` lesson's enable input |
| GP5 | reserved for the lesson 16 timing marker the learner toggles for the analyser |
| GP23, GP24, GP25, GP29 | used by the Pico board itself. Not available. |

GP4 and GP5 are reserved rather than used, so that a learner who takes the offered lessons
does not have to move a wire that three earlier lessons assumed.

**An RP2040 pad resets with its internal pull-down enabled, and GP2 and GP3 must have it
turned off explicitly.** The reset value of a `PADS_BANK0` GPIO register is `0x56`: input
enable set, pull-down enable set, pull-up clear. So a pin the firmware has not configured is
not floating — it is being pulled down, against the level-shifter module's pull-up, and the
bus idles somewhere in the middle of the rail instead of high. The symptom is a lesson 02
idle measurement that reads about half of 3.3 V and a receiver that sees nothing, and neither
points at the cause.

This is the one piece of RP2040-specific behaviour that reaches out of the datasheet and
breaks the electrical design, which is why it is recorded here rather than left to a lesson.
Lesson 02 has the learner confirm the reset value in the datasheet rather than taking it on
trust, and lesson 03 carries the constraint forward.

**What breaks if a lesson contradicts it.** The PIO programs in lessons 07 and 08 assume
clock and data are adjacent and in that order. Lesson 16's capture correlation assumes a
marker pin exists and is not already carrying something. Resolved.

## Voltage domains {#voltage-domains}

The Model M runs at **5 V** and is powered from VBUS. RP2040 GPIO is **3.3 V** and is
**not** 5 V tolerant — this is the fact that destroys hardware, and it is the reason this
decision exists rather than being left to the learner.

A **BSS138-type bidirectional MOSFET level shifter** sits between the two domains. The
choice is forced twice over:

- PS/2 clock and data are **open-drain**, and either end may pull either line low. A
  resistor divider cannot work on such a line: it is a one-way attenuator, and it has no
  answer at all for the moment the 3.3 V side pulls the line down.
- A **unidirectional buffer** works for lesson 04 through 08, where only the keyboard
  ever drives, and then breaks lesson 09, where the host has to drive the same two wires.
  A learner who chooses one early does not find out until the transmit lesson.

Pull-ups exist on **both** sides and neither is the learner's to add: the keyboard supplies
its own on the 5 V side, and the level-shifter module carries the 3.3 V side. Lesson 02's
pull-up experiment is about understanding and measuring what is already there, and about
what a different value would do — not about making the bus work.

Power comes from VBUS, not from 3V3(OUT). A Model M draws more than the Pico's on-board
regulator will give.

**What breaks if a lesson contradicts it.** Lesson 09's transmit, and the hardware.
Resolved.

## Wire format {#wire-format}

The keyboard stays in **scan code set 2** and the adapter never asks it to switch. Set 2
is what a PS/2 keyboard sends at power-on, and asking for set 1 or set 3 adds a command
exchange, a failure path and a second table for nothing.

The frame is **eleven bits**: one start bit (always 0), eight data bits **LSB first**, one
**odd** parity bit, one stop bit (always 1).

Direction decides which clock edge carries the data, and this is the detail that costs a
learner an afternoon if a lesson states it loosely:

| Direction | Who drives the clock | Data is valid on |
|---|---|---|
| device to host (the keyboard typing) | the keyboard | the **falling** clock edge |
| host to device (a command, e.g. `0xED`) | the keyboard, still | the **rising** clock edge, when the device samples |

The keyboard generates the clock in **both** directions. The host never clocks the bus; it
inhibits the bus, requests to send, and then presents each bit for the device to clock in.

**What breaks if a lesson contradicts it.** A lesson that says break equals make with bit 7
set has described **set 1**, and produces a decoder that silently mangles half the keyboard
— the keys whose make code already has bit 7 set. Resolved.

## Receive interface {#rx-interface}

**One receive interface, two backends, chosen at build time.**

The interface is deliberately tiny: initialise, and a **non-blocking pop of one byte**.
Nothing downstream may reach into a backend's internals, because the whole value of the
arrangement is that the two are interchangeable.

| Backend | Written in | Kept because |
|---|---|---|
| interrupt | lessons 04–06 | it is the reference implementation, and it is what lesson 08 and the offered latency lesson measure against |
| PIO | lesson 08 | it is the real implementation for the rest of the course |

Both backends MUST satisfy the same checks. `queue-lossless` and `pio-frames-received` are
the same experiment run against the two of them.

The interrupt backend is **not** deleted when the PIO one works. A learner who deletes it
has thrown away the baseline for the only measurement in the course that quantifies what
offload bought.

**What breaks if a lesson contradicts it.** The offload comparison in lesson 08 loses its
baseline, and a lesson that lets downstream code touch a backend's internals makes the two
non-interchangeable — at which point there is one implementation with two spellings.
Resolved.

## Events versus state {#events-vs-state}

The adapter holds a **key-state bitmap** as its single source of truth.

- PS/2 produces **events** that mutate that bitmap: this key went down, this key came up.
- USB HID reports are **snapshots** built from the bitmap, and are sent **only when it
  changes**.
- Nothing downstream of the decoder consumes PS/2 events directly.

This is the conceptual hinge of the whole course, and it is the one place where the obvious
implementation is wrong in a way that does not show up immediately. Sending one HID report
per PS/2 event looks correct at typing speed on the bench. It produces stuck keys the moment
two events arrive inside one USB polling interval, which happens under fast typing, and the
resulting bug is intermittent, unreproducible on demand, and miserable to find.

The modifier bitmap and the six-key array in the report are both **derived** from the state
bitmap at the moment the report is built. Neither is accumulated as events arrive.

**The `key:` console line carries the mapped HID usage name, never the physical key.** This
matters only once a learner takes the offered `remap-and-macros` lesson, and it is recorded
here because that is the moment it stops being obvious. The down/up pairing invariant that
`key-events-decoded` enforces is about the identity that reaches the host, which is exactly
the identity a remap changes; pairing physical names would leave a remap that emits a
different usage on release looking perfectly healthy. A learner who wants the physical name
in the log is free to print it on a free-form line, which no check reads.

**What breaks if a lesson contradicts it.** Stuck keys under load, arriving several lessons
after the decision that caused them. Resolved.

## HID contract {#hid-contract}

**One HID interface, boot-protocol compatible.**

| Property | Value |
|---|---|
| `bInterfaceClass` | 3 (HID) |
| `bInterfaceSubClass` | 1 (boot) |
| `bInterfaceProtocol` | 1 (keyboard) |
| report ID | **none** |
| input report | 8 bytes: modifier bitmap, reserved byte, six-key array |
| output report | 1 byte: the LED bitmap |
| rollover | six-key, with `ErrorRollOver` (`0x01`) in all six slots on overflow |

This shape is forced by two requirements of the brief: the adapter needs **no driver**, and
it must work **in a BIOS** — and firmware setup screens understand boot protocol and nothing
else.

**Adding a second top-level collection to *this* interface forces report IDs.** That makes
the input report nine bytes and breaks boot protocol *silently*: the device still works
perfectly on a running desktop, and fails in firmware setup, which is the one place a
learner is least likely to test. Any debug or vendor channel therefore goes on a **separate
interface**, which is exactly what the offered `a-second-interface-for-debugging` lesson
does.

The development VID/PID is the pid.codes test pair **`1209:0001`**, which is explicitly
allocated for development and explicitly not for distribution. A made-up VID is not an
option for anything that leaves the bench, and lesson 11 says why.

**What breaks if a lesson contradicts it.** A device that works on the desk and fails in the
BIOS, with no error anywhere. Resolved.

## Failure posture {#failure-posture}

What the adapter does when the world is not ideal. These are requirements, not polish, and
the last one is a safety property rather than a feature.

- **Start with no keyboard attached**, and pick one up when it appears. The finished object
  gets plugged into a computer that is already on, or booted with the keyboard unplugged.
- **Resynchronise after a parity or framing error**, rather than latching. One glitch must
  not end the session.
- **Release all held keys** on any error, on unplug, and on USB reset. A key left down types
  forever into whatever has focus, and the learner's only recovery is to unplug the adapter.
- **Support USB remote wakeup.** An ordinary keyboard wakes the host it is plugged into, and
  an adapter that does not is visibly not an ordinary keyboard.

**One stated non-compliance, so that nobody later "fixes" it.** A bus-powered USB device is
required to drop to the suspend current budget — single-digit milliamps — while the host is
suspended. This adapter cannot, because it is powering a Model M, and a Model M does not have
a low-power state to be put into. The adapter therefore keeps the keyboard alive through
suspend and draws more than the specification allows. That is a deliberate trade: the
alternative is cutting the keyboard's supply and losing the ability to wake the host with a
keypress, which is the one thing a keyboard must be able to do. Lesson 17 records it as a
known limit rather than glossing it, and no check asserts compliance.

**What breaks if a lesson contradicts it.** A lesson that assumes the keyboard is present at
boot produces firmware that wedges on a cold start — which is exactly how the finished object
will be used. Resolved.

## Debug channel {#debug-channel}

The debug console is **UART0 to a second Pico running `debugprobe`**, and deliberately not
USB.

The reason is that USB is the artefact under test. The moment the firmware claims USB for
HID, a USB console is either gone or is itself a variable in the experiment — and lessons 11
to 15 are precisely where enumeration is failing and the learner most needs to see inside.
A learner who puts stdio on USB in lesson 00 loses their diagnostic channel at the exact
lesson where they cannot do without it.

The same second Pico carries **SWD** for lesson 16, so the hardware is already on the bench.

Every console-reading validator depends on this. The firmware emits structured log lines,
and `checks/_console.py` opens the port and reads them; a check cannot read a console that
does not exist.

**What breaks if a lesson contradicts it.** Moving stdio to USB costs the learner their
diagnostic channel during lessons 11 to 15 and makes every console-reading validator
unrunnable. Resolved.

## Deliberately unresolved {#deliberately-unresolved}

Three choices are the learner's, and the course presents them as choices rather than
deciding for them. A tutor should not resolve one on the learner's behalf.

- **Whether the finished perfboard build keeps the level-shifter module or uses discrete
  BSS138s and passives.** Lesson 18 presents both. The supplied layout covers the module,
  which is the lower-risk soldering job, and the discrete build is the more satisfying one.
- **Whether the finished adapter carries the vendor debug interface.** The offered
  `a-second-interface-for-debugging` lesson adds it; the main path does not. Lesson 18's
  acceptance test must pass either way.
- **Which host the learner develops against.** Buggy firmware on an input device types into
  whatever has focus. The course recommends a machine the learner does not mind being typed
  into, and the offered `a-safety-catch` lesson adds a firmware gate for learners who would
  rather solve it that way. Neither is required, and neither is assumed by any check.
