---
id: 01-the-ps2-connector-and-what-is-safe
title: The PS/2 connector, and what is safe to touch
design_refs: [voltage-domains]
validators: [wiring-verified]
---

## Purpose

There are six pins on the end of that keyboard cable, four of them carry something, and one
of them will destroy your Pico if it reaches a GPIO. This lesson is the one where you find
out which is which, using a multimeter and your own connector, and where you measure how
much current a thirty-year-old keyboard actually asks for. Nothing gets wired to a GPIO
today. That is not caution for its own sake — it is the shape of the lesson.

The mistake this lesson exists to prevent is not exotic. Almost every pinout you will find
for a mini-DIN-6 is drawn face-on, and face-on drawings of a plug and of a socket are mirror
images of each other. Pin 3 and pin 4 sit next to each other, and one is ground and the
other is +5 V. Read the drawing from the wrong side and you have swapped them, and the
keyboard's controller is powered backwards the first time you apply the rail. The bundle
supplies `docs/PINOUT.md`, which draws both views side by side precisely so that you cannot
do this — and you are still going to verify against the connector in your hand, because a
drawing of a connector is not your connector.

The second half of the lesson is a number nobody can look up for you. The USB host will
give you 500 mA at 5 V once your device is configured, the Pico takes some of that, and an
IBM Model M is an electromechanical object with a sizeable controller and three LEDs. Whether
your budget works is a measurement, not an assumption, and you take it now while the answer
is still cheap to act on.

## Prerequisites

- `00-first-code-and-a-window-in` complete: your firmware runs and the debug console works.
- A multimeter, and a PS/2 extension cable you are willing to cut, or a mini-DIN-6 panel
  socket.
- `docs/PINOUT.md` in your workspace, placed there when the course started.
- The level shifter is still in its bag. It goes in next lesson.

## Learning objectives

After this lesson you can:

- Name the function of each of the six mini-DIN-6 pins and say which two carry nothing.
- Explain why a face-on pinout drawing is ambiguous, and state the rule that resolves it.
- Identify ground and +5 V on an unknown PS/2 connector by measurement rather than by
  reading a picture.
- Say what happens inside an RP2040 when 5 V is applied to a GPIO, at the level of the
  clamp diode, and why "it survived once" is not evidence of safety.
- Measure a device's supply current safely, including what a meter in current mode does to
  the circuit it is measuring.
- State a current budget for the finished adapter with real numbers in it.

## Theory

### The connector

The plug on a PS/2 keyboard is a **mini-DIN-6**: six pins in a circular shell, with a flat
plastic key that only lets it go in one way. Four of the six carry something:

| Pin | Function |
|---|---|
| 1 | DATA |
| 2 | not connected (reserved) |
| 3 | GND |
| 4 | +5 V (VCC) |
| 5 | CLOCK |
| 6 | not connected (reserved) |

That table is not in dispute anywhere. What *is* in dispute, every single time, is which
physical hole is pin 1.

### Why every pinout drawing is half wrong

A connector drawing is a projection, and a projection needs a viewpoint. There are two:

- **Plug view** — looking at the end of the cable, at the pins coming towards you.
- **Socket view** — looking into the receptacle, at the holes going away from you.

These two views are mirror images. The numbering does not change; your side of it does. A
drawing that does not say which view it is is worse than no drawing, because it looks
authoritative.

`docs/PINOUT.md` in your workspace draws both, labelled, so you can hold the connector up
against the correct one. Use it. Then do not stop there, because a drawing of *a*
mini-DIN-6 tells you nothing about whether the cable in your hand is wired the way its
manufacturer intended, whether it is an adapter with an internal crossover, or whether you
have miscounted around a shell with no clear starting mark.

### Identifying ground and +5 V without trusting a picture

Ground and the supply rail are the two you can find electrically, and once you have found
them the orientation of the whole connector is settled, because pins 3 and 4 are adjacent
and their positions fix the direction of the numbering.

Two properties give them away:

- **Ground is usually continuous with the cable's shield and the connector shell.** A
  continuity measurement from the shell to each pin, on an unplugged, unpowered cable, will
  usually find exactly one. "Usually" is doing work in that sentence: not every cable bonds
  shield to ground, so a null result here is not evidence of anything.
- **The supply rail and ground are joined, inside the keyboard, by its decoupling
  capacitors and its regulator load.** With the keyboard attached to the far end and nothing
  powered, a resistance measurement between your candidate VCC and candidate GND reads some
  finite, unremarkable value — and, importantly, is *not* a dead short. A reading of a few
  ohms or less means you have found two pins that are the same net, or a fault, and you
  should stop.

The confirming test is the keyboard itself. Apply 5 V to your candidate pair, from a
current-limited supply if you have one, and watch. A healthy PS/2 keyboard runs a power-on
self test and **flashes its three lock LEDs** within a second or so. That flash is the
keyboard telling you, unambiguously, that it has power the right way round. No flash means
stop and re-check, not "try the other way and see".

### Clock and data, and the limits of a multimeter

The remaining two live pins are clock and data. Both idle high, both sit near the rail, and
a multimeter is a poor instrument for telling them apart: while you type, the *average*
voltage on both of them dips, so a DC voltage reading that changes when you press a key
tells you the pin is live and nothing more. Do not let that reading convince you that you
have identified which is which.

What you can honestly do today is: fix the orientation from ground and VCC, read clock and
data off the numbering that orientation gives you, and write down that this part of the
identification is by inference. It gets confirmed, decisively and visually, in
`03-see-the-protocol-before-you-decode-it`, where one of the two lines is a metronome and
the other is not. An inference you have labelled as an inference is a perfectly respectable
thing to carry for two lessons. An inference you have forgotten is an inference is how
people spend an afternoon debugging a receiver that was wired to the wrong pin.

### Why 5 V on a 3.3 V GPIO is destructive

`#voltage-domains` states the fact: the Model M runs at 5 V, RP2040 GPIO runs at 3.3 V and
is **not** 5 V tolerant. Here is the mechanism, because "not tolerant" is too easy to read
as "not recommended".

Every GPIO pad has protection diodes: one from the pad to the I/O supply rail, one from
ground to the pad. Their job is to shunt electrostatic discharge. The upper one conducts
whenever the pad rises about a diode drop above the I/O rail — and 5 V is about 1.7 V above
3.3 V, so on this bus that diode is not handling a transient, it is conducting continuously.

Three things follow. Current is injected into the 3.3 V rail from the keyboard, which can
push the rail above its own specification and misbehave the whole chip rather than one pin.
The diode itself is sized for microseconds of ESD and not for a steady current, so it
degrades. And the structures around the pad can latch up, which is a low-impedance path from
rail to ground that persists until you remove power and may not be survivable.

None of this necessarily happens in the first second. That is the awkward part: a pin that
has been abused once frequently still works, which is why "I did it and it was fine" is
widely repeated and worth nothing. The damage is cumulative and the failure is later and
looks like something else.

The consequence for this lesson is simple and absolute: **no PS/2 signal line touches a
GPIO until the level shifter is in place**, which is next lesson.

### The current budget

Your finished adapter is a bus-powered USB device. USB 2.0 gives a device 100 mA before it
is configured and up to 500 mA after, if it asks for it in its configuration descriptor —
a number you will write by hand in lesson 11, so it helps to know today what it has to
cover.

Three consumers share that budget: the Pico itself, the level shifter (negligible, but the
pull-ups it carries are not quite nothing), and the keyboard. Only the last one is
uncertain, and it is uncertain by an order of magnitude across the various Model M
revisions and their LEDs.

Power for the keyboard comes from **VBUS**, the raw 5 V from the host, on the Pico's VBUS
pin — not from the 3V3(OUT) pin, which is the wrong voltage and, in any case, comes from an
on-board regulator with far less to give than a Model M wants.

### Measuring current without lying to yourself

Current is measured **in series**: you break the supply path and put the meter in the gap.
Two warnings, both of which cost people meters:

- A meter in current mode is very nearly a **short circuit** through a fuse. Placing it in
  parallel across a supply is how the fuse dies, and on a cheap meter sometimes how the
  meter dies. Move the lead back to the voltage jack the moment you are done; the next
  measurement you take absent-mindedly will be a voltage one.
- A meter in series adds **burden voltage** — the drop across its own shunt plus the lead
  resistance. On a low current range this can be a couple of hundred millivolts, and if the
  keyboard then behaves oddly, resets, or fails its self test, suspect your instrument
  before you suspect the keyboard.

Take two numbers: **idle**, with the keyboard powered and untouched, and **typing**, while
you hold down keys and the LEDs are lit. Watch also for the surge at power-on, which is
larger than either and lasts a moment; note whether your supply copes.

## Concepts to teach

- The mini-DIN-6 connector and the four live pins of a PS/2 keyboard.
- Plug view versus socket view, and why a face-on drawing is ambiguous without a label.
- Identifying ground and VCC electrically; using the power-on LED flash as confirmation.
- Why a DMM cannot separate clock from data, and what an honest inference looks like.
- GPIO clamp diodes, injected current, latch-up, and why survival is not evidence.
- VBUS versus 3V3(OUT), and where the keyboard's power comes from.
- USB current allowances before and after configuration.
- Series current measurement, meter burden voltage, and the parallel-meter mistake.

## Constraints

- **Nothing connects to any GPIO in this lesson.** Not "briefly", not "just to see".
- The keyboard is powered from VBUS, never from 3V3(OUT).
- The learner states each of the four live pins with the evidence that identified it, and
  marks clock and data explicitly as inferred from orientation rather than measured.
- The idle and typing currents are numbers the learner measured on their own keyboard, not
  numbers from a forum.
- If the self-test LED flash does not happen, power comes off and the identification is
  redone. It is not retried the other way round.
- The debug console from lesson 00 stays running throughout, so that a Pico that browns out
  during the current measurement is visible immediately.

## Suggested progression

1. Read `docs/PINOUT.md`, and say out loud which of its two drawings applies to the
   connector you are holding and how you know.
2. With everything unpowered, examine your connector or cut cable and pick a candidate pin
   1. Write down the numbering you have assumed, and which view you used to get it.
3. Measure continuity between the connector shell and each pin. Record which pin, if any, is
   bonded to the shell, and record a null result honestly if there is not one.
4. With the keyboard attached and nothing powered, measure resistance between your candidate
   VCC and candidate GND. Confirm it is finite and is not a short.
5. Apply 5 V to that pair, watching the keyboard. Look for the power-on self test LED flash
   within about a second.
6. If the LEDs did not flash, remove power immediately and go back to step 2. Do not swap
   the pair and try again — work out first why the identification was wrong, because that
   reasoning is the thing you are learning.
7. With power confirmed, write down which physical pin is which, in terms of something you
   can find again tomorrow: a wire colour, a mark you made on the shell, a photograph.
8. Now do the mirror exercise deliberately: read the *other* view in `docs/PINOUT.md` and
   work out which two pins you would have joined to 5 V and ground if you had used it. Say
   what would have happened to the keyboard.
9. Break the 5 V path and insert the multimeter in series, in an appropriate current range.
   Measure the idle current with the keyboard doing nothing.
10. Measure again with keys held down and, separately, with lock LEDs lit. Record the
    largest steady figure you see.
11. Watch the reading at the moment power is applied and note the surge, even if your meter
    only shows you a flicker.
12. Add the Pico's own consumption — from its datasheet, or measured the same way — and
    write down a total. Compare it against 500 mA and say how much headroom you have.
13. Return the meter lead to its voltage jack before you put it down.
14. Record the whole identification and both currents where lesson 11 will find them, and
    have the `wiring-verified` check run against your evidence.

## Completion conditions

- The learner states all four live pins on their own connector, each with the specific
  evidence that identified it, and explicitly flags clock and data as inferred from
  orientation and not yet measured.
- The keyboard has been powered from the identified pair and ran its power-on self test,
  witnessed by the LED flash.
- A measured **idle** current and a measured **typing** current are recorded, in
  milliamps, taken with the meter in series on the learner's own keyboard.
- A total budget is written down and compared against the 500 mA a configured USB device may
  draw, with the headroom stated.
- No PS/2 pin has been connected to any GPIO, and the learner can say what the clamp diode
  would have done if one had been.
- The learner can explain the plug-view/socket-view ambiguity and name which view they used.
- The `wiring-verified` check passes.

## On completion, persist

- The pin identification, expressed in something physically findable — wire colours, a
  marked shell, a photo — not just as pin numbers.
- Idle current, typing current, and the observed power-on surge if it was measurable.
- The total current budget and the headroom against 500 mA, for lesson 11's configuration
  descriptor to use.
- The keyboard's make and revision, because current draw varies across them and a future you
  comparing notes will want it.
- The standing rule: signal lines reach a GPIO only through the level shifter.

## Optional deeper paths

- Find the absolute maximum ratings table in the RP2040 datasheet and read the IOVDD-relative
  limit on a GPIO for yourself.
- Read about latch-up: what the parasitic structure actually is, and why it persists until
  power is removed.
- Work out what your meter's burden voltage is on the range you used, and how much of your
  measured current it might have cost you.
- Look at what a PS/2-to-USB passive adapter plug does, and why some old keyboards work
  through one and this one does not.
- Investigate why pins 2 and 6 exist at all, and what a combined keyboard-and-mouse PS/2 port
  does with them.
