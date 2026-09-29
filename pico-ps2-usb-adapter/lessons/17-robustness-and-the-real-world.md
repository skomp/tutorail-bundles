---
id: 17-robustness-and-the-real-world
title: Robustness and the real world
design_refs: [failure-posture, rx-interface]
validators: [build-ok, survives-abuse]
---

## Purpose

Make the adapter behave when the world is not ideal — which is the only way it will
ever actually be used.

Everything so far was built on a bench, in a fixed order, by someone who knew what
they were doing. Power came up with the keyboard already plugged in, the host was
already awake, and no cable was ever pulled mid-sentence. The finished object's
*ordinary* use violates all of that: you plug the adapter into a machine that is
already running and the keyboard in afterwards; the host suspends overnight and
expects a keypress to wake it; someone yanks the cable while a key is down.

`#failure-posture` states four properties, and they are requirements rather than
polish. The adapter must **start with no keyboard attached** and pick one up when it
appears. It must **resynchronise** after a parity or framing error instead of
latching. It must **release every held key** on error, on unplug and on USB reset —
a key left down types forever into whatever has focus and the only recovery is to
unplug the adapter, which makes this the one safety property in the course. And it
must **support USB remote wakeup**, because an ordinary keyboard wakes its host.

None of this is new mechanism. It is the state machines you already have, made
honest about the states you have so far been lucky enough to avoid.

## Prerequisites

- Lesson 05 (`05-a-state-machine-in-an-isr`): the framing state machine with its idle
  timeout, parity checking, and the `resync` counter already printing.
- Lesson 08 (`08-ps2-receive-in-pio`), with **both** backends alive as
  `#rx-interface` requires. Everything here goes through the one interface —
  initialise, and a non-blocking pop of one byte — so it works on both.
- Lesson 09 (`09-talking-back-in-pio`): you can transmit, send `0xFF` and read `0xFA`
  and `0xAA` back. Presence detection is built out of exactly that exchange.
- Lesson 14 (`14-events-to-state`): the key-state bitmap is the single source of
  truth and reports are snapshots built from it. Releasing keys is an operation on
  that bitmap, not on the report.
- Lesson 15 (`15-the-lock-leds`): USB output reports are handled, so you know slow
  work must not happen inside a TinyUSB callback.
- Lesson 16 (`16-when-it-goes-wrong`): SWD, gdb and the GP5 marker. This lesson
  produces exactly the intermittent, state-dependent bugs lesson 16 exists for.

## Learning objectives

- State the four properties of `#failure-posture` and what each one prevents.
- Explain why the idle level of the PS/2 lines cannot tell you whether a keyboard is
  attached, and design an **active** presence probe instead.
- Build a presence state machine that retries rather than latching, and tolerates a
  keyboard slower to start than the probe.
- Distinguish a parity error from a framing error and choose the right recovery for
  each, including why resync requires an idle gap and not just a discarded byte.
- Implement a single "release everything" operation on the key-state bitmap, called
  from every path that needs it, and say why clearing the bitmap is correct where
  synthesising key-up events is not.
- Describe USB suspend and resume at the bus level, name the TinyUSB callbacks, and
  say what a device may and may not do while suspended.
- Explain remote wakeup end to end: the descriptor bit from lesson 11, the host's
  `SET_FEATURE`, the flag TinyUSB hands you, and the wait before the first report.
- Configure the hardware watchdog with a justified period, fed from exactly one
  place, and say why it is the last defence and not the first.
- Emit `ps2`, `usb` and `resync` records that make all of this visible from outside.

## Theory

`#failure-posture` is normative for this lesson, and each of its four properties
exists because of a specific failure: firmware that wedges on the cold start that is
the object's *normal* start; one glitch ending the session until someone power-cycles
a box that is about to be sealed; a key typing forever into whatever has focus; and
an adapter that cannot wake the machine it is plugged into.

### You cannot see an absent keyboard by looking

The first instinct is to read the lines: clock low or floating means no keyboard. It
does not work, and the reason is instructive. With a keyboard attached, both lines
idle **high**, pulled up by the keyboard's own pull-ups on the 5 V side. With no
keyboard, that pull-up is gone entirely — but the level-shifter module carries its
own pull-ups on the **3.3 V** side, and those are what your GPIO sees. The pins read
high either way. **Idle and absent are indistinguishable**, which is precisely why
they were hard to tell apart.

Presence detection must therefore be **active**: ask, and see whether anything
answers. Lesson 09 gave you the mechanism. Send `0xFF` (reset) and require `0xFA`
(acknowledge) then `0xAA` (self-test passed) within a timeout.

Two details separate a probe that works from a nuisance. **The keyboard is slow**: a
Model M's power-on self test takes a substantial fraction of a second, so budget
several hundred milliseconds between `0xFA` and `0xAA`. A probe that concludes
"absent" after 50 ms mis-diagnoses a perfectly good keyboard — the instructive
failure hiding inside "just add a timeout" is that the timeout has to be justified by
the device's behaviour, not chosen because it felt short. And **absent is a state to
live in, not an error reported once**: one explicit state machine (absent → probing →
present, with timeout and error transitions back) in one variable, retrying roughly
once a second, not three booleans set from four places. Absent should be comfortable
— USB still enumerated, `alive` still rising, the host seeing a keyboard that reports
nothing. That is correct behaviour, not degraded behaviour.

**Hot-plugging a PS/2 keyboard is out of the original spec** — the connector was
never designed for it and original hosts could be damaged. Here it works, because the
keyboard is powered from VBUS through wiring you built, but there is an inrush as its
supply charges and the lines glitch during insertion. Treat those glitches as
**noise**: a partial frame arriving during a plug-in is discarded by the same framing
machinery as any other glitch, and the transition to present is driven by a
successful probe, not by the first byte that happens to arrive.

### Resynchronising, properly

**A parity error** means eight bits arrived and the odd-parity bit disagrees. You
know the byte is wrong and not which bit, so there is one correct action: **discard
it**. Do not guess it was probably a shift. Print `frame: <hex> parity-error` so it
is visible, and count it.

**A framing error** means the stop bit was not 1, so bit *alignment* is lost, not one
bit's value. Discarding a byte is not enough: reset the bit counter and start at the
next edge and you begin mid-frame, producing plausible garbage that looks exactly
like data. **You must wait for an idle gap** — the clock quiet for longer than one
bit time, the only thing on this bus that unambiguously says no frame is in progress
— and only then arm for a start bit. That gap is the resynchronisation, and `resync`
counts it.

**Never latch.** Setting an error flag and stopping is tempting because it makes the
bug reproducible, and it is wrong: one glitch — a nudged wire, a plug-in, supply
noise — then ends the session until someone power-cycles an adapter that is about to
be sealed in a case. **But a flood is a diagnosis.** One resync is noise; a hundred a
second is a broken link. Choose a threshold of consecutive errors within a window,
and when it is exceeded drop back to absent, release all held keys, and re-probe.
`resync` climbing while `ps2: absent` appears is far better evidence for a human than
either signal alone.

### Releasing held keys: one operation, four callers

`#events-vs-state` gave you the invariant: the bitmap is the source of truth and
reports are snapshots. Releasing everything is therefore one operation — **clear the
bitmap, then send the snapshot it now produces**, which is the all-zero report — and
the whole of the correctness lies in calling it from every path that needs it:

1. **PS/2 error threshold exceeded**, on the transition out of present.
2. **Keyboard unplugged** — any transition to absent.
3. **USB bus reset**, because the host has just discarded its idea of what is held.
4. **USB suspend**, because you cannot send while suspended and must not resume into
   a phantom keypress.

There is a wrong way that looks more principled: synthesising `up` events for each
key and pushing them through the decoder as if the keyboard had sent break codes. It
puts the decoder in charge of state that belongs to the bitmap, and it breaks the
accounting — the `key:` records are checked for every `down` being matched by an
`up`, and synthesised ups for keys you are unsure of produce mismatches
indistinguishable from a real bug. **Clear the bitmap and rebuild the report.** Log
one line saying a release happened if you want a record; do not fabricate `key: up`.

The demonstration that makes this real: hold a key down and unplug the keyboard while
it is held. Without the release, the host repeats that character forever.

### USB suspend, resume and remote wakeup

**Suspend is the absence of traffic, not a message.** A host with nothing to say lets
the bus go idle, and a full-speed device that sees idle for more than about 3 ms must
enter suspend. Nothing is sent, which is why a device has to watch for it. While
suspended the host is not polling your interrupt IN endpoint, so anything you "send"
goes nowhere.

There is a power rule this course should be honest about: a suspended device may draw
only a few hundred microamps, or a couple of milliamps if configured and
remote-wakeup capable. **This adapter cannot meet that** — it is powering a Model M
from VBUS. That is a real non-compliance, worth naming rather than glossing. The
*protocol* behaviour still matters completely: the host really does stop polling.

The TinyUSB callbacks are where this surfaces. `tud_suspend_cb()` fires when the bus
goes idle and is handed a flag saying whether the host enabled remote wakeup;
`tud_resume_cb()` when it returns; `tud_mount_cb()` and `tud_umount_cb()` bracket
configuration. Each emits exactly one record, and the spelling matters because
`survives-abuse` reads it:

| Event | Record |
|---|---|
| bus went idle, device suspended | `usb: suspended` |
| bus activity returned | `usb: resumed` |
| USB bus reset seen | `usb: reset` |
| host has configured the device | `usb: configured` |
| we drove resume signalling | `usb: wakeup-sent` |

And from the presence state machine: `ps2: absent` when nothing answers the probe,
`ps2: present` when a keyboard is in service, and `ps2: reset-ok` when `0xFF` got
`0xFA` then `0xAA`. `resync` continues as it has since lesson 05, and the check reads
that too.

**Remote wakeup has four parts, and three are not in this lesson.**

1. **The descriptor bit, written in lesson 11.** The configuration descriptor's
   `bmAttributes` must have the remote-wakeup bit set — `0xA0` rather than a bare
   `0x80`. This is the instructive failure at its most concentrated: if that byte is
   `0x80` the host never offers remote wakeup, `tud_suspend_cb` always reports it
   disabled, your wakeup call does nothing, and **there is no error anywhere**. One
   bit, in a file you last touched six lessons ago. Check it first.
2. **The host enabling it**, with `SET_FEATURE(DEVICE_REMOTE_WAKEUP)`. Whether it
   does is the host's business — some enable it only at sleep, and power settings can
   disable it entirely. Hence the flag rather than an assumption.
3. **The signalling**, which TinyUSB performs: resume driven on the bus for 1 to
   15 ms, only while suspended and only if the host enabled it.
4. **Waiting.** The trap is sending the keypress report immediately after requesting
   wakeup. The host needs tens of milliseconds to resume and poll again; a report
   queued instantly is dropped, or arrives around a bus reset and is lost in a way
   that looks random. The right behaviour falls out of `#events-vs-state` for free:
   update the bitmap, request the wakeup, and let the ordinary send-on-change path
   deliver once the device is configured and polled again. If the key is released
   before the host is back, the bitmap is already correct and nothing spurious is
   sent — which is exactly what a real keyboard does.

**A bus reset** wipes the host's address, configuration and idea of held keys. Yours
must be wiped to match; that is caller 3 above.

### The watchdog, added last and on purpose

Arm the RP2040's hardware watchdog with a period, and if the firmware fails to feed
it within that period the chip resets. Three things matter more than the API.

**Feed it from exactly one place: the bottom of the superloop, after the loop has
done its work.** The classic anti-pattern is feeding it from a timer interrupt or
inside the USB task — convenient, never misses, and useless, because the interrupt
keeps feeding while the main loop is wedged. A watchdog that cannot observe what it
protects is decoration.

**Size the period from the longest legitimate blocking operation.** Here that is the
lesson 09 transmit and especially the lesson 15 LED write — a bus inhibit, a
request-to-send, eleven bits clocked at the keyboard's own rate, an acknowledgement —
comfortably milliseconds. Around 100 ms leaves room and still catches a wedge
quickly; 10 ms resets the adapter every time Caps Lock changes, which is a
spectacular own goal and exactly the kind of bug that gets blamed on the host.

**Pause it while debugging.** The enable takes a flag that stops the countdown while
the core is halted. Without it, every breakpoint from lesson 16 resets the board a
hundred milliseconds later, and a target that vanishes mid-inspection is baffling.

And the honest framing: **a watchdog does not fix a bug, it hides one.** It converts
a permanent hang into an intermittent reboot — better for the user, worse for you,
because the evidence is destroyed on every recovery. Two things keep it honest. Add
it *last*, so it catches the unknown rather than papering over the known. And record
*that it fired*: query on boot whether the watchdog caused the reset and say so,
optionally with a faulting PC stashed by lesson 16's handler. A reboot loop that
reports itself is a diagnosis; a silent one is indistinguishable from a hang.

## Concepts to teach

- `#failure-posture` as four requirements, each with the failure it prevents, and
  release-held-keys as a safety property rather than a feature.
- Why the idle line level cannot distinguish absent from idle: the 5 V pull-ups
  belong to the keyboard, the 3.3 V pull-ups to the shifter, and the GPIO sees the
  latter either way.
- Active presence detection on lesson 09's transmit (`0xFF`, `0xFA`, `0xAA`) with
  timeouts justified by the keyboard's self-test; a presence state machine that
  retries and never latches, with absent as a normal state.
- PS/2 hot-plug being out of the original spec; insertion inrush and line glitches
  treated as noise rather than data.
- Parity error versus framing error, and why resync needs an idle gap longer than a
  bit time; never latching, but treating a *flood* as a link failure.
- Release-all as one operation on the bitmap with four callers, and why synthesising
  key-up events breaks both `#events-vs-state` and the down/up accounting.
- USB suspend as the absence of traffic for ~3 ms rather than a message; the suspend
  current budget this adapter cannot meet; the TinyUSB callbacks and one record each;
  a bus reset wiping the host's state and the device's with it.
- Remote wakeup end to end: the `bmAttributes` bit, the host's `SET_FEATURE`, the
  flag TinyUSB passes, the signalling, and the wait before the first report.
- The watchdog: one feed point at the bottom of the superloop, a justified period,
  pause-on-debug, reporting that it fired, and why it is added last.
- The console vocabulary `ps2`, `usb` and `resync`, spelled exactly.

## Constraints

- Everything goes through the `#rx-interface` contract. No robustness feature may
  reach into a backend's internals, behaviour must be identical on both, and the
  interrupt backend is **not** deleted.
- Releasing keys clears the bitmap and lets the ordinary snapshot path build the
  report. It must not synthesise `key: up` records and must not bypass send-on-change
  with a hand-built report.
- The release is **one** function called from all four paths. Four copies of the logic
  is the defect this lesson exists to prevent.
- `ps2`, `usb` and `resync` records are spelled exactly as above, with exactly those
  values. `survives-abuse` reads them and a near-miss spelling is invisible to it.
- The adapter must enumerate and stay enumerated with **no keyboard attached**,
  without blocking or spinning, and `alive` must keep rising. The presence probe runs
  about once a second while absent, not once per loop iteration.
- No blocking wait longer than the watchdog period anywhere in the main loop, and the
  watchdog is configured with pause-on-debug so lesson 16's gdb sessions work.
- No `printf` inside a USB callback or an ISR. Record in a variable, print from the
  main loop.
- `#hid-contract` is untouched: no report ID, eight bytes, boot subclass and protocol.
  If the `bmAttributes` bit needs fixing, that is a correction to lesson 11's work,
  not a new feature.

## Suggested progression

1. Re-read `#failure-posture` and turn each bullet into a test the learner could
   perform with their hands in the next ten minutes. The rest of the lesson
   implements what those tests demand.
2. Start from the cold-boot failure. Unplug the keyboard, power-cycle the adapter,
   and observe what the current firmware does — wedge, spin, or quietly nothing — and
   note that this is the *normal* start for the finished object.
3. Kill the obvious idea before it costs an afternoon: ask how the firmware could
   tell "no keyboard" from "keyboard idle" by reading the pins, and follow it to the
   pull-up argument until the learner sees both cases read high.
4. Design the probe on lesson 09's transmit: `0xFF`, then `0xFA` and `0xAA`. Have the
   learner pick the timeouts and **justify each one** against the keyboard's
   self-test duration rather than against a round number.
5. Build the presence state machine as one explicit state variable, and wire
   `ps2: absent`, `ps2: present` and `ps2: reset-ok` to its transitions. Confirm
   absent is comfortable — USB still enumerated, `alive` still rising.
6. Test hot-plug both ways, several times, including plugging in slowly and crookedly
   so the contacts chatter. The Model M's LEDs flashing its self-test is free
   confirmation the probe reached it. If insertion glitches are accepted as frames,
   fix the framing path, not the probe.
7. Turn to error recovery: have the learner state the difference between a parity and
   a framing error, then confirm the firmware discards on parity, waits for an idle
   gap on framing, and counts `resync` only for the latter.
8. **Induce a framing error deliberately** — glitch or briefly interrupt the clock
   mid-frame while typing. `resync` should step and typing should continue. If it
   latches, that is the instructive failure and worth sitting in before fixing.
9. Add the error threshold: a burst drops back to absent, releases held keys and
   re-probes. Test it by pulling the keyboard half out so contacts chatter rather
   than cleanly disconnecting — the nastiest real case.
10. Write the release-everything operation over the bitmap and wire the first two
    callers: error threshold, and any transition to absent.
11. **The stuck-key demonstration.** In a scratch document, hold a key and unplug the
    keyboard mid-press. Before the fix the host repeats forever and the only escape
    is unplugging the adapter — worth experiencing once, deliberately. After the fix
    it stops immediately; check `held` returns to zero and the last `report` is all
    zeroes.
12. Add the suspend, resume, mount and unmount callbacks with their four records,
    then suspend the host and watch `usb: suspended` appear. Confirm the device does
    not try to send while suspended.
13. Wire the remaining two callers — USB bus reset and USB suspend — testing the
    reset path by replugging the adapter itself.
14. Attempt remote wakeup and expect it to fail. Check the flag `tud_suspend_cb`
    handed you; when it says disabled, walk back to lesson 11's configuration
    descriptor and inspect `bmAttributes`. Fixing `0x80` to `0xA0` and seeing the flag
    flip teaches how far a one-bit descriptor error can travel.
15. Then wake the host for real: suspend it, press a key, watch `usb: wakeup-sent`
    and the machine return. Reason about why the keypress report should not be sent
    immediately, and why the bitmap driving send-on-change is the right answer rather
    than a workaround.
16. Add the watchdog last. Have the learner enumerate the longest blocking operations
    — the lesson 09 transmit and the lesson 15 LED write — bound them, and pick a
    period from that. Feed at exactly one point at the bottom of the superloop.
    Enable pause-on-debug.
17. Prove it works and does not misfire: trigger a deliberate wedge and watch the
    board return; then hammer Caps Lock and confirm the LED write does **not** cause a
    reset. Report a watchdog-caused boot on the console so a reboot loop is never
    silent.
18. Run the whole abuse sequence in one session while `survives-abuse` watches: boot
    with no keyboard, plug it in, type, glitch the clock, hold a key and unplug,
    replug, suspend the host, wake it with a keypress, replug the adapter. Then
    re-run `no-stuck-keys` to confirm nothing regressed.
19. Finally, build the **other** receive backend and repeat the critical parts.
    `#rx-interface` promises both satisfy the same checks, and this is the lesson most
    likely to have broken that promise.

## Completion conditions

- `build-ok` passes, and passes with **both** receive backends selected.
- The adapter **boots with no keyboard attached**: it enumerates, `alive` keeps
  rising, `ps2: absent` appears, and nothing blocks or spins.
- Plugging the keyboard in while running brings it into service without a power
  cycle: `ps2: reset-ok` and `ps2: present` appear, the Model M flashes its
  self-test, and typing works immediately.
- An **induced framing error** is recovered from: `resync` steps, typing continues,
  and the firmware does not latch.
- A sustained fault — the keyboard pulled half out so contacts chatter — drops back
  to `ps2: absent`, releases held keys and re-probes, rather than producing an endless
  stream of garbage.
- **No key is ever left held.** With a key physically down, unplugging the keyboard
  gives `held: 0` and an all-zero `report`, and the host stops repeating. The same
  holds across USB reset and USB suspend.
- USB state changes appear, correctly spelled: `usb: configured`, `usb: suspended`,
  `usb: resumed`, `usb: reset`.
- **A suspended host is woken by a keypress**, with `usb: wakeup-sent` on the console,
  and the learner can explain the whole chain — the `bmAttributes` bit, the host's
  `SET_FEATURE`, the flag TinyUSB passed, and why the first report waits.
- The watchdog is enabled, fed from exactly one place at the bottom of the main loop,
  with a period the learner can justify against the longest blocking operation, and
  with pause-on-debug set. Repeated Caps Lock toggles do not reset the board, and a
  watchdog-caused boot is reported on the console.
- The `survives-abuse` validator passes, reading the `ps2`, `usb` and `resync` records
  produced by the abuse sequence.
- `no-stuck-keys` still passes and typing a paragraph still produces the right text.

## On completion, persist

Record in the instance's `DESIGN.md`/`STATE.md`:

- The presence state machine: its states, the probe sequence, the timeouts chosen and
  **the justification for each**, and the retry cadence while absent.
- The error thresholds — how many consecutive errors in what window drop the link
  back to absent — and the reasoning, so a later session does not tune it blind.
- Where the single release-everything operation lives and which four paths call it. A
  fifth path added later must call it too, and this note is what says so.
- Which TinyUSB callback emits which record, and that reset and suspend both release
  held keys.
- That remote wakeup depends on `bmAttributes` being `0xA0`, and that it was checked
  — recorded because it is the failure that leaves no error message anywhere.
- The watchdog period, the single feed point, the blocking operation it was sized
  against, and that pause-on-debug is enabled.
- That behaviour was verified on **both** backends, and any difference found.
- Any respect in which the adapter is deliberately not USB-compliant — the suspend
  current in particular — so the limits are written down rather than rediscovered.

## Optional deeper paths

- **`0xFE` resend.** PS/2 has a retransmit request and lesson 09 gave you the path to
  send one. Work out when it helps, when it makes things worse, and why
  discard-and-resync is the sufficient default.
- **Typematic settings.** `0xF3` sets the keyboard's repeat rate and delay. Consider
  whether the adapter should, and what two stacked repeat mechanisms do to the typist.
- **Suspend current, measured.** Put an ammeter in VBUS while the host sleeps, compare
  with the USB budget, and decide what a compliant design would do — most likely
  switch the keyboard's supply, which then needs re-probing on resume, which your
  presence machine already knows how to do.
- **A fault breadcrumb across the watchdog.** Combine lesson 16's fault handler with
  the watchdog scratch registers so a reset leaves the faulting PC behind — what turns
  an intermittent field failure into a solvable one.
- **Brown-out and power sequencing.** What happens when VBUS sags under the Model M's
  draw? Brown-out detection and a bulk capacitor near the keyboard's supply — a
  question that becomes physical in lesson 18.
