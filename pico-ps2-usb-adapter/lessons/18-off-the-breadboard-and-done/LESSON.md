---
id: 18-off-the-breadboard-and-done
title: Off the breadboard, and done
design_refs: [voltage-domains, pin-assignment, deliberately-unresolved]
validators: [build-ok, firmware-alive]
supplies:
  - from: lessons/18-off-the-breadboard-and-done/perfboard-layout.md
    to: docs/perfboard-layout.md
    describe: A stripboard layout for the circuit you built on the breadboard, so this lesson is about soldering and not about drawing
---

## Purpose

Turn a working circuit into an object you trust.

Everything works — on a breadboard, on your desk, plugged into the machine you have
been developing against, with a console attached and you watching. That is not the
same as working. A breadboard is a temporary arrangement of springs: it holds your
circuit only while nothing moves, and something always moves. The finished object gets
carried, plugged in, tugged, warmed up and left alone for a year.

Two things stand between the breadboard and the object, and this lesson is the first:
**construction** — transferring the circuit to something soldered, relieving the
strain where the cables enter, and proving with a multimeter that you built what you
think you built *before* applying power. The second is **acceptance**, and it is lesson
19 (`19-does-it-pass`). A board that comes up in stages and reports `alive` from inside
its closed case is finished *here*; whether it is a keyboard is a separate question.

One of the two decisions the course deliberately left open becomes yours here, from
`#deliberately-unresolved`: whether the soldered build keeps the level-shifter module
or uses discrete parts. It changes the soldering job and no acceptance criterion.

## Prerequisites

- Lessons 01 (`01-the-ps2-connector-and-what-is-safe`) and 02
  (`02-open-drain-and-pull-ups`): the mini-DIN-6 pinout from both sides, the
  keyboard's measured current draw, and what the level shifter does.
- Lessons 11 (`11-descriptors-you-write-yourself`) to 15 (`15-the-lock-leds`): the
  adapter enumerates with your own VID/PID, presents a boot-protocol keyboard, types,
  and drives the lock LEDs. The firmware is finished; nothing here changes it.
- Lesson 16 (`16-when-it-goes-wrong`): SWD, gdb and the GP5 marker, all of which you
  will want when a soldered board misbehaves and no wire is left to wiggle. And lesson
  17 (`17-robustness-and-the-real-world`) for the `resync` counter, which is how a
  marginal soldered joint announces itself.
- A stripboard layout for this circuit is in your workspace at
  `docs/perfboard-layout.md`, shipped in this lesson's folder as
  `perfboard-layout.md`, covering the level-shifter-module build, so that this lesson
  is about soldering rather than about drawing.
- Tools from `BOM.md`: stripboard or perfboard, iron, solder, flux, a multimeter with
  a continuity beep, a track cutter, heat-shrink, an enclosure, and something to
  relieve strain with.

## Learning objectives

- Say what a breadboard is electrically and name three properties a soldered board
  improves; choose stripboard or perfboard and identify each one's characteristic
  failure.
- Make the level-shifter choice — module or discrete BSS138s and passives — as a
  deliberate decision, and state its consequences for layout and risk.
- Transfer a circuit from breadboard to soldered board, working from a layout, with
  the track cuts marked and verified before anything is soldered.
- Perform a full **continuity and isolation test before first power**, naming which
  pairs must beep and which must not, and why each matters.
- Bring a soldered board up in stages, saying what you measure at each, ending with
  the case closed and the firmware still reporting for itself.
- Recognise a cold joint by sight, explain why it works on the bench and fails warm,
  and name the symptom it produces in *this* project.
- Provide strain relief at both cable entries, explain why an unrelieved pull lifts a
  pad rather than breaking a joint, and keep a way in to the sealed object.

## Theory

### What a breadboard actually is

A solderless breadboard is a grid of phosphor-bronze spring clips, so every connection
is a spring gripping a wire. That gives three properties you have been living with:
**contact resistance that changes when things move**, so a connection that is fine
when you make it can be intermittent an hour later; **capacitance between adjacent
rows**, much of lesson 02's RC estimate, so a soldered board should if anything give
*cleaner* edges — worth confirming on the analyser rather than assuming; and **no
mechanical retention at all**, while a finished object has two cables hanging off it
that will both be pulled. Soldering makes the circuit permanent, not different.

### Stripboard or perfboard

**Stripboard** has continuous copper strips, so components sharing a strip are
connected for free. The price is that you must **cut** the strips wherever a net ends,
and **an uncut track is the characteristic stripboard fault** — invisible from above,
sitting under a component, usually presenting as a dead short between two nets that
should never have met. The discipline that prevents it: mark every cut before
soldering anything, make them all, and check each with the multimeter while the board
is still empty and easy to probe.

**Plain perfboard** has isolated pads: no free connections, no cuts to forget, every
net a wire you place deliberately. More work and fewer surprises, and its
characteristic fault is a missing wire — a kinder failure, because an open circuit
releases no smoke. The supplied layout is stripboard, so if you take it as given, the
cuts are the step to be careful about.

### The first open decision: module or discrete

`#deliberately-unresolved` leaves this to you, and it should be a decision, not a
default.

**Keep the level-shifter module.** A small breakout carrying four BSS138-type channels
with their gate pull-ups fitted, soldering in as two rows of header pins. One part, no
surface-mount work, and the 3.3 V pull-up values are already what `#voltage-domains`
assumes. This is the **lower-risk soldering job** and it is what the supplied layout
covers.

**Build it discretely.** Only two channels are in use — clock on GP2, data on GP3 — so
a discrete build is two BSS138 MOSFETs and four pull-ups plus the rail connections.
The parts are SOT-23: surface-mount soldering on a board not designed for it, or a
breakout per transistor. More work, more opportunity for error, and the more
satisfying build, because it turns lesson 02's explanation of what the shifter *is*
into something you assembled and can point at — gate, body diode, each pull-up — and
say what each does during a low pull from either side.

Neither is the right answer. Choose, say why, and note that a discrete build means
drawing your own layout. **Lesson 19's acceptance test is identical either way.**

### Two things that do not move

**`#pin-assignment` stands:** PS/2 clock on GP2 and data on GP3, adjacent and in that
order because the PIO program addresses them from a base index; UART0 on GP0/GP1; GP4
and GP5 spoken for. Rotate the Pico if it makes the board tidier, but the *pins* stay
where they went: a finished object wired to a different map needs its firmware
rewritten. And **power comes from VBUS, never from 3V3(OUT)** — a Model M draws more
than the Pico's on-board regulator will supply, as you measured in lesson 01, and this
is one of the very few mistakes here that destroys something.

### Continuity testing before first power

This is the step people skip and the one that pays for the lesson. Board finished,
**nothing plugged in anywhere**, multimeter on continuity.

**These must NOT beep:** 5 V to ground; 3.3 V to ground; **5 V to 3.3 V** — the one
that deserves most attention, because a bridge there puts 5 V onto the supply and GPIO
of a part `#voltage-domains` exists to protect, and a solder bridge between adjacent
tracks is half a millimetre wide and invisible at arm's length; PS/2 clock to PS/2
data; either signal to either rail or to ground; and the high side of a shifter
channel to its own low side, which is supposed to be joined only through a MOSFET.

**These MUST beep:** each net from one physical extreme to the other — the mini-DIN
pin, through the cable, through the connector joint, across the board, through the
shifter, to the Pico pin it should reach, not two points a centimetre apart; ground
continuous everywhere; both rails present at everything that consumes them. Work under
good light, and look at the board through a zoomed phone camera before probing:
bridges invisible to the eye are obvious at 4×.

**The instructive failure is the alternative**, worth naming so the temptation is
recognised rather than merely resisted: powering up takes ten seconds, testing takes
ten minutes, and if there is a short the ten seconds buys you a component that has
already failed. Now you are debugging a board with a fault *and* damage, unable to
tell which came first — perhaps with the Pico carrying your only working firmware
destroyed, or the Model M, which is not replaceable the same afternoon.

### Bringing it up in stages

Never connect everything and apply power. **Pico alone** first, no keyboard, no PS/2
cable: confirm it boots, with the `alive` counter as the evidence it has been since
lesson 00. Then **measure the rails**, including both reference pins of the level
shifter — a shifter with its high side unpowered passes no signals and looks exactly
like a wiring error somewhere else. Then **the keyboard**, watching the current against
lesson 01's idle and typing figures: far above is a fault, zero means it is not being
powered. Then **check the signals** on the analyser — clock, data and the GP5 marker —
before trusting a single keystroke.

The enclosure is the last stage rather than a formality: pinching a wire under a lid,
or resting the Pico's castellated edge on something conductive, is a common way to
break a board that worked five minutes ago. So the case goes on and stage one's
question is asked again. Construction ends where that answer comes back — `alive`
rising with the board in its case, which is what the `firmware-alive` check reads,
with `build-ok` confirming the firmware inside is the one you think it is.

### Cold joints, and why they wait until the lid is on

A good joint has *wetted* both surfaces: solder flowed onto the pad and up the lead,
and the fillet is shiny, smooth and concave. A **cold joint** did not get hot enough —
the solder melted but the pad and lead did not — and looks dull, grainy and bulbous.

Cold joints deserve their own section because **they conduct**, and on the bench they
often measure fine. What they are is a mechanical contact across a thin oxide
interface, and that interface degrades with thermal cycling, vibration and time, its
resistance rising as the board warms. So the board passes every test you run, goes
into the case, and starts failing three weeks later, warm, intermittently.

**In this project that failure has a signature you can now read.** A marginal joint on
the clock line does not produce "it stopped working"; it produces occasional lost or
corrupted frames — lesson 17's rising `resync` counter, which lesson 16 gave you the
marker and the analyser to localise. A `resync` count that is zero cold and climbs
after twenty minutes of typing is very nearly a diagnosis on its own, and lesson 19's
soak is where you go looking for it. The remedies are boring and effective: inspect
every joint under magnification, give every wire a gentle **tug test** and redo
anything that moves, and reflow anything dull — with flux, not more solder. Excess
solder is not strength; it is a hiding place.

### Strain relief, and keeping a way in

The cables are the only moving parts and the only things anyone will pull. When a
cable is pulled with no relief, the force goes into the solder joint — and the joint
is stronger than the bond between the copper pad and the substrate, so **the pad lifts
off the board**, taking the track with it. That is a board repair, not a resolder.

Make sure the force never reaches the joint, in rough order of effectiveness: a
**panel-mount mini-DIN socket** in the enclosure wall, so the force goes into the
enclosure and the wires never move — the best answer, and why `BOM.md` offers the
socket as an alternative to a cut cable; a **cable gland or grommet** clamping the
jacket at the wall; a **zip tie through two holes in the board** behind the joints,
free and fitted *before* you solder; a **knot inside the case**; or **hot glue**.

Relieve **both** cables: the Pico's own micro-USB connector is surface-mounted on
small pads, and lifting it is a known and very annoying failure. Inside the enclosure,
heat-shrink anything that could touch and insulate under the board — the castellated
edges are exposed copper. And keep a way in: lesson 19 reads counters off the console
with the case shut, so bring GP0, GP1 and GND — and SWD if you can spare the room —
out to a header or pads reachable without desoldering.

## Concepts to teach

- What a breadboard is electrically: spring contacts, changing contact resistance,
  inter-row capacitance, no mechanical retention.
- Stripboard versus plain perfboard and each one's characteristic fault — the uncut
  track versus the missing wire — and working from a layout: transcribe first, mark
  and verify cuts while the board is bare, solder low to high.
- The level-shifter choice as a real decision: module (fewer joints, lower risk,
  covered by the supplied layout) versus discrete BSS138s and passives (SOT-23 work,
  own layout, deeper understanding).
- `#pin-assignment` and `#voltage-domains` surviving the rebuild: GP2/GP3 adjacent and
  in that order whatever the physical layout, power from VBUS, both shifter references
  powered, and the RP2040 still not 5 V tolerant.
- Continuity and isolation testing before first power: which pairs must not beep,
  which nets must, and why the 5 V-to-3.3 V pair in particular.
- Staged bring-up, ending with the closed case: Pico alone, rails, the keyboard's
  current against lesson 01's figure, the analyser.
- Cold joints: how they look, why they conduct cold, why they fail warm, the symptom
  here — a `resync` counter that climbs after twenty minutes — the tug test, and
  reflowing with flux rather than more solder.
- Strain relief: why an unrelieved pull lifts a pad, the remedies, that **both** cables
  need it, and keeping the console and SWD reachable with the case shut.

## Constraints

- **No power before the continuity and isolation test.** This is the one
  non-negotiable ordering in the lesson.
- `#pin-assignment` does not change: the board may be laid out however suits it, and
  the pins stay where they are. Power from VBUS, never from 3V3(OUT), as
  `#voltage-domains` requires, with both level-shifter reference pins powered.
- The level-shifter build is presented to the learner **as a decision**, as
  `#deliberately-unresolved` requires: the tutor does not choose it on their behalf,
  does not steer by omission, and does not let the choice change what lesson 19 asks.
- The debug console must remain reachable on the assembled object without
  desoldering; do not seal the case over it. Bring-up is staged: do not connect the
  keyboard until the rails have been measured.
- The firmware is not modified in this lesson and no descriptor changes. If something
  misbehaves, the fault is in the construction or in an earlier lesson — find out
  which before changing code.
- This lesson does not run the acceptance tests and does not declare the adapter
  finished. That is lesson 19's job, and a board that types on the development machine
  has not yet been shown to be a keyboard.

## Suggested progression

1. Mark the transition: the firmware is finished and nothing here changes behaviour.
   Have the learner say what is true only because the circuit is on a bench, and what
   would break first if they carried it to another room.
2. Make the module-versus-discrete decision consciously. Lay out both options, have
   the learner choose and **state the reason**, including that a discrete build means
   drawing their own layout and that lesson 19's acceptance test does not care.
3. Work through the layout at `docs/perfboard-layout.md` — or their own — until they
   can name every net and say where each cut is and why. A layout you have not read is
   one you will mis-transcribe, so do not start soldering before this.
4. Transcribe onto the bare board, mark every cut, make the cuts, and **verify each
   one with the multimeter while the board is still empty** — the cheapest possible
   moment to find a missed cut. Then solder in order, low profile first, after saying
   what a good joint looks like: shiny, concave, wetted on both surfaces.
5. Solder the PS/2 connector or cable, **fitting the strain relief before or as part
   of that** — a zip tie threaded after the joints are made is a job nobody enjoys.
   Relieve the host-side cable too.
6. Inspect before testing: good light, magnification or a zoomed photo, every joint
   looked at. Tug test every wire, reflow anything dull.
7. **Run the full continuity and isolation test with nothing powered**, walking the
   must-not-beep and must-beep lists explicitly rather than "checking it over". Where
   a reading is ambiguous, work out why before moving on.
8. Bring it up in stages — Pico alone with `alive` on the console; rails measured
   including both shifter references; then the keyboard with its current compared
   against lesson 01's figure; then the analyser on clock, data and the GP5 marker.
   Stop at the first stage that surprises you.
9. First functional test on the **development** machine, where every diagnostic is
   still to hand: type, check the LEDs, glance at `resync` and the dropped counter.
   Fix anything here, not in the case.
10. Fit the enclosure: insulate under the board, heat-shrink anything that could
    touch, check the cables cannot move, and **bring the console and SWD pins out** to
    somewhere reachable. Power up with the case closed and confirm `alive` is still
    rising, read through the way in you left yourself — assembly is a common way to
    pinch or short a board that worked five minutes ago. Stop there: the object
    exists, and lesson 19 decides whether it is a keyboard.

## Completion conditions

- The circuit is on a soldered board in a closed enclosure, with `#pin-assignment`
  unchanged and power taken from VBUS as `#voltage-domains` requires.
- The learner **made the level-shifter choice deliberately** and can say why, and what
  the choice did and did not change.
- A **full continuity and isolation test was performed before first power**, and the
  learner can say which pairs must not conduct and why 5 V to 3.3 V matters most.
- Bring-up was staged, and the measured keyboard current matches lesson 01's figure.
- **Strain relief is fitted on both cables** — a firm tug on either moves nothing on
  the board — and every joint has been inspected and tug-tested, anything dull
  reflowed. The debug console, ideally SWD too, remains reachable without desoldering.
- The firmware in the object is lesson 17's, unmodified: `build-ok` passes on the tree
  that produced it, and with the case closed the `firmware-alive` check reads a rising
  `alive`. That, not a paragraph of typing, is where construction ends.

## On completion, persist

Record in the instance's `DESIGN.md`/`STATE.md`:

- Which level-shifter build was chosen and why, which board type was used, where the
  track cuts are if it is stripboard, and any deviation from the supplied layout. The
  cuts and the deviations are the hardest things to recover from a finished board.
- How strain relief is implemented at each cable entry, how the enclosure comes apart,
  and where the debug console and SWD pins are brought out.
- The measured keyboard current beside the lesson 01 bench figure, so a later change
  in draw is detectable; and the `resync` and dropped-byte counters read after
  assembly, as the **cold baseline** lesson 19's soak is compared against.
- Anything that had to be resoldered and what it looked like, so a later intermittent
  fault starts with a list of suspects rather than with the whole board.

## Optional deeper paths

- **Measure the edges again.** Put the analyser, or a scope, on the soldered board's
  clock line and compare the rise time with the breadboard's. Lesson 02's RC estimate
  included the breadboard's capacitance; this tells you how much.
- **A real PCB.** Two layers and about a dozen nets — as gentle an introduction to
  KiCad as exists. What you would change: the connector footprint, the mounting holes,
  whether the Pico is socketed. **A case you made** is the same exercise in plastic.
- **Build the second one.** The fastest way to find out which parts of your layout,
  your notes and your `DESIGN.md` were actually sufficient is to build the adapter
  again from them without looking at the first.
