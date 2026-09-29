---
id: a-safety-catch
title: A safety catch
design_refs: [failure-posture, pin-assignment]
validators: [build-ok, safety-catch-works]
optional: true
---

## Purpose

Build a deliberate enable gate into the firmware, so buggy code on an input device cannot type
into whatever window has focus.

You have just described the shape of your reports to the host, and lesson 13 is about to make
the host type a character your firmware chose. From there on, every bug you write is a bug that
reaches your keyboard. `COURSE.md` warns about this and recommends developing against a machine
you do not mind being typed into; that is a good answer and not the only one. This lesson is the
other answer: a physical input the firmware consults before it is allowed to speak, so the
default state of a half-written build is **silent**.

The interesting part is not the gate. It is that a safety catch is the one piece of code where
being *mostly* right is worse than not having written it, because the moment you have one you
stop taking the other precautions. A catch that fails open on a floating pin, or one placed a
step too late in the pipeline, will hold for days and then let a runaway build through on the
afternoon you were counting on it. Neither mistake announces itself. You are going to make sure
yours has neither, by testing it against firmware that is *deliberately* trying to type.

## Prerequisites

This lesson stands alone. It assumes the report descriptor is written and nothing about what you
were doing when the tutor offered it.

- Lesson 12 (`12-the-hid-report-descriptor`) complete: an 8-byte boot-protocol input report, no
  report ID, and `report-descriptor-sane` passing.
- A working debug console on UART0 — the evidence here is a console line, and
  the whole demonstration is "the firmware is clearly running and clearly decoding, and the host
  is receiving nothing".
- **GP4 free.** `#pin-assignment` reserved it for exactly this and it has been unused since
  lesson 00, so there is nothing to rewire. If you have quietly borrowed it, give it back first.
- One jumper wire long enough to reach from GP4 to a ground pin, so you can make and break that
  connection one-handed while watching a screen. A toggle switch is nicer and not required.
- A host with a **plain text editor** you can focus and do not mind having junk typed into.

## Learning objectives

- Design an enable input whose *unpowered, unwired, unconfigured* state is the safe one, and
  explain why that ordering is the whole design.
- Explain why a floating CMOS input is not a logic zero, and what firmware that treats it as one
  will do.
- Place a gate at the single point where a report enters the USB stack, and say why gating
  anywhere downstream leaks reports.
- Handle the armed-to-blocked transition without leaving keys held on the host, per
  `#failure-posture`, while keeping receive, decode and state tracking running.
- Verify a safety mechanism against code actively trying to defeat it, rather than against code
  that happens to behave.

## Theory

**The gate is an input, and its polarity is a safety decision.** Two designs are available and
only one is defensible:

| Design | If the wire falls off | Verdict |
|---|---|---|
| Active-**high**: GP4 high arms, pulled down internally | The pin floats, and a floating input reads whatever it likes | Fails **open**. Unacceptable. |
| Active-**low**: GP4 **low** arms, pulled **up** internally | The pull-up takes the pin high, and high means blocked | Fails **safe**. |

Use the second: **grounding GP4 arms the adapter, anything else blocks it.** The jumper becomes
a thing you hold in place while you want typing to happen, which is also the ergonomics you
want — the safe state requires no action.

**A floating CMOS input is not a zero, and this is the classic bug.** An RP2040 GPIO set as an
input with no pull enabled is connected to essentially nothing. Its voltage is whatever charge
is on the pin capacitance, moved by leakage, by coupling from the wires beside it, and by your
hand approaching the board. It reads high sometimes and low other times, and it reads *both* in
rapid succession. Firmware that says "if GP4 is low, arm" and never enables a pull will arm
itself the first time the pin drifts down, which will be soon. That is a catch that fails open,
and it is worse than no catch, because you have stopped being careful.

So the internal pull-up is not a detail, it is the mechanism. It must be enabled explicitly in
your `gpio_init` path, and **before any path that can send a report is live** — for a USB device,
before you begin servicing the device task. The RP2040's internal pull-ups are weak, in the
region of 50 to 80 kΩ, so there is a short settling time after you enable one while it charges
the pin capacitance; reading the pin in the next instruction can return the pre-charge value.

**Where the gate goes, and the second classic bug.** By the end of lesson 14 your pipeline looks
roughly like:

```
PS/2 frame → decode → key event → key-state bitmap → build 8-byte report → hand to USB stack → host
```

There is exactly one correct place for the gate: immediately before *hand to USB stack*. Gating
**after** the report has been handed to TinyUSB means it is already in the endpoint buffer, and
the host's next `IN` token collects it — the gate did nothing but make you feel better. Gating
only the *build* step while still calling the send function with stale data is the same failure
in a different hat. And gating at the **PS/2 receive** end is wrong for a third reason: it stops
the console evidence, it stops resynchronisation, and it lets the key-state bitmap go stale, so
the moment you arm the adapter it reports a state that does not match the keyboard. Keep
everything upstream running, and block exactly one thing.

**What has to happen on the transitions.** `#failure-posture` says no key may be left held.
**Armed → blocked**: if a key is down when you block, the host is holding it and will hold it
forever, because you are about to go quiet — so send an **all-keys-released** report as the last
act before the gate closes. That is not a special case bolted on; it is the same requirement as
releasing keys on unplug or USB reset, which lesson 17 generalises. **Blocked → armed**: the
host's view and your bitmap may now disagree, because the keyboard was typed on while you were
silent — so send a fresh snapshot of the current bitmap as the first act after the gate opens.

**The device stays enumerated while blocked.** Blocking output is not disappearing from the bus.
The device must still enumerate, stay configured, service the USB device task, and answer `IN`
tokens with nothing to report — an ordinary `NAK`, exactly what an idle keyboard does. A device
that vanishes when blocked is a different and more confusing failure, and it would break the
checks from lessons 11 and 12.

**The console is the evidence.** Print one line, at boot and on change:

```
safety: armed
safety: blocked
```

Spelled exactly like that — `safety` is the key `safety-catch-works` reads, and `armed` and
`blocked` are the only values it understands. While blocked, your `key:` lines keep appearing as
you type, which is the demonstration in one screen: the firmware is receiving, decoding and
tracking state perfectly, and the host is getting nothing.

**Why you must test it against a runaway.** A safety catch tested against firmware that was not
going to type anyway has not been tested. The honest test is a build that tries hard to type —
the obvious one is lesson 13's failure on purpose: send a key-down report and never send the
release, so the host repeats that character forever. Blocked, nothing happens. Armed, you find
out immediately and memorably that your runaway works. That asymmetry is the evidence.

Two precautions before running it, and they are not optional. **Put focus in a plain text
editor** — not a terminal, not a shell, not a browser address bar; a runaway keyboard typing into
a shell is a runaway keyboard executing things. And **hold the jumper in your hand** rather than
fitting it, because removing a wire is faster than finding a window. Unplugging the adapter is
your backstop either way.

## Concepts to teach

- Fail-safe versus fail-open, as a property of the *default* state rather than the intended one;
  active-low enable with an internal pull-up as what that requirement forces.
- Floating CMOS inputs: undefined, unstable, moved by leakage and coupling, and not a zero.
- RP2040 internal pull-up strength and settling; configuring the pull before any path that can
  send a report is live.
- Pipeline placement: the single choke point before the USB stack, why every later placement
  leaks, and why gating at the receive end is the wrong end.
- Transition handling: all-released on close, fresh snapshot on open, per `#failure-posture`; the
  device remaining enumerated, configured and `NAK`ing while blocked.
- The `safety` console key and its two values, and testing a safety property adversarially against
  code trying to defeat it.

## Constraints

- The enable input is **GP4** and nothing else, as a 3.3 V input on the Pico side only. Do not
  run it through the level shifter and do not connect it to the 5 V keyboard side.
- The pull must be an **internal pull-up**, enabled in firmware. Do not rely on an external
  resistor for the safe state — a resistor that falls out is the failure you are defending
  against. Grounding GP4 arms; open blocks. Do not invert it.
- The gate goes immediately before the report enters the USB stack. No report may reach the stack
  while blocked, including one built before the state changed.
- PS/2 receive, framing, decoding and key-state tracking keep running while blocked, and the
  `key:` console lines must continue.
- The device stays enumerated and configured while blocked. `enumerates-as-hid` and
  `report-descriptor-sane` must still pass, and the HID contract is untouched: one interface, boot
  subclass and protocol, no report ID, 8-byte input report. The gate changes *whether* a report
  is sent, never its shape.
- The console key is `safety` with values `armed` and `blocked`, spelled exactly, printed at boot
  and on change rather than on a timer.
- The runaway build is deliberate and temporary. It must not be left in place, and the lesson is
  not complete with it still there.

## Suggested progression

1. State the goal in one line: make the default behaviour of a half-written build silence, then
   prove it by attacking it.
2. Before writing anything, decide the polarity out loud and justify it. Which state does an
   unfitted wire produce, and is that state safe? Get this wrong and everything after is built
   on it.
3. Add GP4 as an input with the internal pull-up enabled, in your initialisation path, and
   confirm from `#pin-assignment` that nothing else claims it.
4. Print `safety: blocked` or `safety: armed` at boot from the pin's state, and verify it reads
   `blocked` with nothing connected and `armed` with a jumper from GP4 to ground.
5. Wiggle the jumper near the pin without touching ground and confirm the reading does not move.
   Then, as a deliberate experiment, disable the pull-up in a scratch build and do it again.
   Watch the reading wander — the floating-input failure, seen rather than described. Put the
   pull-up back.
6. Find the line where a built report is handed to the USB stack. There should be one. If there
   is more than one, fix that first: a gate on a pipeline with two exits is a gate on one of them.
7. Put the gate immediately before that call, with nothing downstream of it.
8. Read the pin at the gate, not once at boot, and be able to say why: a catch you can only
   change by rebooting is not a catch you will use.
9. Debounce or settle the reading. A mechanical jumper bounces, and a gate that flutters on
   contact emits half a transition's worth of reports.
10. Handle armed → blocked: send an all-keys-released report as the last thing before the gate
    closes. Handle blocked → armed: send a snapshot of the current bitmap as the first thing
    after it opens. Confirm `safety:` prints on change and not repeatedly.
11. Confirm the device still enumerates and stays configured while blocked, and that `key:` lines
    still appear as you type. If the console goes quiet while blocked, you have gated the wrong
    end.
12. Build the adversary: a runaway that sends a key-down and never releases it, or emits a
    character in a loop. Keep it in a separate configuration or behind a flag you can remove
    cleanly.
13. Before running it: focus a plain text editor, and take the jumper in your hand rather than
    fitting it.
14. Run the runaway with GP4 open. The console shows `safety: blocked`, the `key:` lines prove
    the firmware is alive, and the editor stays empty. Leave it long enough to be convinced — a
    gate that leaks one report every few seconds is a gate that fails.
15. Ground GP4. The console flips to `safety: armed` and the runaway does what it was written to
    do. Let it, briefly.
16. Lift the jumper. Typing stops, and — check this carefully — the host does **not** keep
    repeating the last character. If it does, your all-released report is missing, or is being
    sent after the gate rather than before it.
17. Remove the runaway build, return to your real firmware, keep the gate. Then say in one
    sentence each what would have happened with an active-high enable, and with the gate placed
    after the stack call.

## Completion conditions

- The `build-ok` check passes.
- With GP4 open the console reads `safety: blocked` and **no HID output reaches the host** —
  verified with a deliberately runaway build running, focus in a text editor, for long enough
  that a leak would have shown.
- While blocked, the console continues to emit `key:` lines as the learner types, showing
  receive, decode and state tracking are unaffected, and the device stays enumerated and
  configured.
- Grounding GP4 flips the console to `safety: armed` and the host immediately begins receiving
  the runaway's output.
- Opening GP4 again flips the console back to `safety: blocked` and the host is left with **no
  key held** — the character does not continue to repeat.
- The gate sits immediately before the report enters the USB stack, and the learner can point at
  the single line it guards.
- GP4 is an input with an **internal pull-up**, and the learner can state what the pin reads and
  what the firmware does if the jumper is removed, the wire breaks, or the pull is never enabled —
  and can explain why an active-high enable would fail open and a gate after the stack call would
  leak.
- The runaway build is removed and the working firmware retains the gate.
- The `safety-catch-works` check passes, reading `safety` off the debug console, and
  `enumerates-as-hid` and `report-descriptor-sane` still pass.

## On completion, persist

Record in the instance's `DESIGN.md`/`STATE.md`:

- That this instance has a firmware safety catch on **GP4**, active low with an internal pull-up,
  so GP4 is now in use rather than reserved — and the exact point in the pipeline the gate
  guards, so a later lesson that adds an output path (the offered second interface, or the
  offered macro lesson) knows not to route around it.
- That the adapter sends an all-released report on armed → blocked and a fresh snapshot on
  blocked → armed, an early partial implementation of lesson 17's general "release all held keys
  on error" requirement. Lesson 17 should generalise it rather than duplicate it.
- Whether the learner intends to carry the catch through to the perfboard build in lesson 18, and
  if so that the enclosure needs a switch or a reachable jumper. Lesson 18's acceptance test must
  pass with the adapter armed.

## Optional deeper paths

- **A real switch, debounced properly.** Replace the jumper with a toggle or slide switch, look at
  the contact bounce on the logic analyser, and decide whether your settling logic is adequate or
  merely lucky. An LED driven from the gate makes the state visible without a console, at the cost
  of the one indicator you have.
- **Failing safe elsewhere.** Add a second, independent condition — block output if no valid PS/2
  frame has arrived for several seconds — and argue with yourself about whether that is a safety
  feature or an annoyance. Then go looking for other places in this adapter where the error path is
  the unsafe one: held keys on a parity error, on unplug, on USB reset. Lesson 17 covers exactly
  that ground, and arriving there having already thought about it is a good way to arrive.
