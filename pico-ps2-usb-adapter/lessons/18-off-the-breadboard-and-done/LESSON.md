---
id: 18-off-the-breadboard-and-done
title: Off the breadboard, and done
design_refs: [voltage-domains, pin-assignment, hid-contract]
validators: [finished-adapter]
---

## Purpose

Turn a working circuit into an object you trust, and then prove that the object is a
keyboard.

Everything works — on a breadboard, on your desk, plugged into the machine you have
been developing against, with a console attached and you watching. That is not the
same as working. A breadboard is a temporary arrangement of springs: it holds your
circuit only while nothing moves, and something always moves. The finished object gets
carried, plugged in, tugged, warmed up and left alone for a year.

Two things stand between the breadboard and the object. **Construction** —
transferring the circuit to something soldered, relieving the strain where the cables
enter, and proving with a multimeter that you built what you think you built *before*
applying power. And **acceptance** — turning each requirement of the original brief
into a test and running all of them on a machine that has never seen this device.
That includes the one test that cannot be faked and is the reason lesson 12's report
is eight bytes with no report ID: typing in the host's firmware setup screen, where
there is no operating system, no driver, and nothing but boot protocol.

Two decisions the course deliberately left open also become yours here, both recorded
in `#deliberately-unresolved`. The acceptance test is designed to pass either way.

## Prerequisites

- Lessons 01 (`01-the-ps2-connector-and-what-is-safe`) and 02
  (`02-open-drain-and-pull-ups`): you know the mini-DIN-6 pinout from both sides, you
  measured the keyboard's current draw, and you know what the level shifter does.
- Lessons 11 (`11-descriptors-you-write-yourself`) to 15 (`15-the-lock-leds`): the
  adapter enumerates with your own VID/PID, presents a boot-protocol keyboard, types,
  and drives the lock LEDs.
- Lesson 16 (`16-when-it-goes-wrong`): SWD, gdb and the GP5 marker. You will want all
  three when a soldered board misbehaves and there is no wire left to wiggle.
- Lesson 17 (`17-robustness-and-the-real-world`): hot-plug, resync, release-on-error,
  suspend/resume/wakeup and the watchdog. Several acceptance tests below are lesson
  17's behaviours performed on the finished object.
- A stripboard layout for this circuit is in your workspace at
  `docs/perfboard-layout.md`, covering the level-shifter-module build, so that this
  lesson is about soldering rather than about drawing.
- Tools from `BOM.md`: stripboard or perfboard, iron, solder, flux, a multimeter with
  a continuity beep, a track cutter or drill bit, heat-shrink, an enclosure, and
  something to relieve strain with.
- A **second host machine** that has never had this device plugged into it, and whose
  firmware setup screen you can enter without breaking anything.

## Learning objectives

- Say what a breadboard is electrically and name three properties a soldered board
  improves; choose between stripboard and plain perfboard and identify each one's
  characteristic failure.
- Make the level-shifter choice — module or discrete BSS138s and passives — as a
  deliberate decision, and state its consequences for layout and risk.
- Transfer a circuit from breadboard to soldered board, working from a layout, with
  the track cuts marked and verified before anything is soldered.
- Perform a full **continuity and isolation test before first power**, naming which
  pairs must beep and which must not, and why each matters.
- Bring a soldered board up in stages, saying what you measure at each.
- Recognise a cold joint by sight, explain why it works on the bench and fails warm,
  and name the symptom it produces in *this* project.
- Provide strain relief at both cable entries, and explain why an unrelieved pull
  lifts a pad rather than breaking a joint.
- Convert the course's original requirements into an explicit acceptance test list.
- Test in a host's firmware setup screen and explain why boot protocol is what makes
  that work.
- Decide whether the finished adapter carries a vendor debug interface, and justify it
  against `#hid-contract`.

## Theory

### What a breadboard actually is

A solderless breadboard is a grid of phosphor-bronze spring clips, so every connection
is a spring gripping a wire. That gives three properties you have been living with:
**contact resistance that changes when things move** (a well-used clip grips less, and
a connection that is fine when you make it can be intermittent an hour later);
**capacitance between adjacent rows**, a few picofarads per row pair plus what the long
jumpers add — a good deal of the bus capacitance in lesson 02's RC estimate was the
breadboard, so a soldered board should if anything give you *cleaner* edges, worth
confirming on the analyser rather than assuming; and **no mechanical retention at
all**, while a finished object has two cables hanging off it that will both be pulled.
Soldering does not make the circuit different. It makes it permanent.

### Stripboard or perfboard

**Stripboard** has continuous copper strips, so components sharing a strip are
connected for free. The price is that you must **cut** the strips wherever a net ends,
and **an uncut track is the characteristic stripboard fault** — invisible from above,
sitting under a component, and usually presenting as a dead short between two nets
that should never have met. The discipline that prevents it: mark every cut before
soldering anything, make them all, and check each with the multimeter while the board
is still empty and easy to probe.

**Plain perfboard** has isolated pads: no free connections, no cuts to forget, every
net a wire you place deliberately. More work and fewer surprises, and its
characteristic fault is a missing wire — a kinder failure, because an open circuit
releases no smoke. The layout at `docs/perfboard-layout.md` — shipped in this lesson's
folder as `perfboard-layout.md` — is a stripboard layout, so
if you take it as given, the cuts are the step to be careful about.

### The first open decision: module or discrete

`#deliberately-unresolved` leaves this to you, and it should be a decision rather than
a default.

**Keep the level-shifter module.** A small breakout carrying four BSS138-type channels
with their gate pull-ups fitted, soldering in as two rows of header pins. One part, no
surface-mount work, and the 3.3 V pull-up values are already what `#voltage-domains`
assumes. This is the **lower-risk soldering job** and it is what the supplied layout
covers.

**Build it discretely.** Only two channels are in use — clock on GP2, data on GP3 — so
a discrete build is two BSS138 MOSFETs and four pull-ups plus the rail connections.
The parts are SOT-23, so either surface-mount soldering on a board not designed for it
or a breakout per transistor. More work, more opportunity for error, and the more
satisfying build: it turns lesson 02's explanation of what the shifter *is* into
something you assembled, so you can point at the gate, the body diode and each pull-up
and say what each does during a low pull from either side.

Neither is the right answer. Choose, say why, and note that a discrete build means
drawing your own layout. **The acceptance test is identical either way**, and it is
the acceptance test that decides whether you are finished.

### Two things that do not move

**`#pin-assignment` stands:** PS/2 clock on GP2 and data on GP3, adjacent and in that
order because the PIO program addresses them from a base index; UART0 on GP0/GP1; GP4
and GP5 spoken for. If the layout rotates the Pico to make the board tidier, the *pins*
still go where they went — a finished object wired to a different map is one that needs
its firmware rewritten. And **power comes from VBUS, never from 3V3(OUT)**, because a
Model M draws more than the Pico's on-board regulator will supply, as you measured in
lesson 01. This is one of the very few mistakes here that destroys something.

### Continuity testing before first power

This is the step people skip and the one that pays for the lesson. Board finished,
**nothing plugged in anywhere**, multimeter on continuity.

**These must NOT beep:** 5 V to ground; 3.3 V to ground; **5 V to 3.3 V** — the one
that deserves most attention, because a bridge here puts 5 V onto the RP2040's supply
and GPIO, and `#voltage-domains` exists because the RP2040 is not 5 V tolerant, and a
solder bridge between adjacent tracks is half a millimetre wide and invisible at arm's
length; PS/2 clock to PS/2 data; either signal to either rail or to ground; and the
high side of a shifter channel to its own low side, which is supposed to be joined
only through a MOSFET.

**These MUST beep:** each net from one physical extreme to the other — the mini-DIN
pin, through the cable, through the connector joint, across the board, through the
shifter, to the Pico pin it should reach, not two points a centimetre apart; ground
continuous everywhere; both rails present at everything that consumes them.

Work under good light, and look at the board through a zoomed phone camera before
probing: bridges invisible to the eye are obvious at 4×.

**The instructive failure is the alternative**, worth naming so the temptation is
recognised rather than merely resisted. Powering up first takes ten seconds and
testing takes ten minutes, and the ten seconds is very appealing when the board is
finished. What it buys you, if there is a short, is a component that has already
failed — and now you are debugging a board with a fault *and* damage and cannot tell
which came first. You may also have destroyed the Pico carrying your only working
firmware, or the Model M, which is not replaceable the same afternoon.

### Bringing it up in stages

Never connect everything and apply power. **Pico alone** first, no keyboard, no PS/2
cable: confirm it boots, with the `alive` counter as the evidence it has been since
lesson 00. Then **measure the rails**, including both reference pins of the level
shifter — a shifter with its high side unpowered passes no signals and looks exactly
like a wiring error somewhere else. Then **the keyboard**, watching the current against
lesson 01's idle and typing figures: far above is a fault, zero means it is not being
powered. Then **check the signals** on the analyser — clock, data and the GP5 marker —
before trusting a single keystroke.

### Cold joints, and why they wait until the lid is on

A good joint has *wetted* both surfaces: solder flowed onto the pad and up the lead,
and the fillet is shiny, smooth and concave. A **cold joint** did not get hot enough —
the solder melted but the pad and lead did not — and looks dull, grainy and bulbous,
with the wire sitting in a bead rather than joined to it.

Cold joints deserve their own section because **they conduct**. At room temperature on
the bench they often measure fine and work perfectly. What they are is a mechanical
contact across a thin oxide interface, and that interface degrades with thermal
cycling, with vibration and with time, and its resistance rises as the board warms. So
the board passes every test you run, goes into the case, and starts failing three
weeks later, warm, intermittently.

**In this project that failure has a signature you can now read.** A marginal joint on
the clock line does not produce "it stopped working"; it produces occasional lost or
corrupted frames — which lesson 17 turned into a rising `resync` counter, and lesson
16 gave you the marker and the analyser to localise. A `resync` count that is zero
cold and climbs after twenty minutes of typing is very nearly a diagnosis on its own.
The remedies are boring and effective: inspect every joint under magnification, give
every wire a gentle **tug test** and redo anything that moves, and reflow anything
dull — with flux, not more solder. Excess solder is not strength; it is a hiding place.

### Strain relief, and keeping a way in

The cables are the only moving parts and the only things anyone will pull. When a
cable is pulled with no relief, the force goes into the solder joint — and the joint
is stronger than the bond between the copper pad and the substrate, so **the pad lifts
off the board**, taking the track with it. That is a board repair, not a resolder.

Make sure the force never reaches the joint, in rough order of effectiveness: a
**panel-mount mini-DIN socket** in the enclosure wall, so the force goes into the
enclosure and the wires never move — the best answer, and why `BOM.md` offers the
socket as an alternative to a cut cable; a **cable gland or grommet** clamping the
jacket at the wall; a **zip tie through two holes drilled in the board** behind the
joints, which costs nothing and must be fitted *before* you solder; a **knot inside
the case**; or **hot glue over the joints**, mediocre but better than nothing.

Relieve **both** cables: if the host cable plugs into the Pico's own micro-USB
connector, that connector is surface-mounted on small pads and lifting it is a known
and very annoying failure. Inside the enclosure, heat-shrink anything that could touch
and put something insulating under the board — the Pico's castellated edges are
exposed copper. And keep a way in: a sealed adapter with no debug console is one you
cannot diagnose, so bring GP0, GP1 and GND — and the three SWD pins if you can spare
the room — out to a header or pads reachable without desoldering.

### The second open decision: the vendor debug interface

`#deliberately-unresolved` leaves this to you as well. If you took the offered
`a-second-interface-for-debugging` lesson, your firmware may present a second USB
interface carrying a vendor channel; if you did not, it presents one HID interface.
Either is a legitimate finished adapter.

What is **not** negotiable is `#hid-contract`: the keyboard interface stays
boot-protocol compatible — subclass 1, protocol 1, **no report ID**, an eight-byte
input report, a one-byte LED output report. A second *interface* does not touch any of
that. A second top-level *collection* on the keyboard interface does: it forces a
report ID, makes the input report nine bytes, and breaks boot protocol *silently* —
the device works perfectly on a running desktop and dies in firmware setup. That is
exactly what the acceptance test below is built to catch, and why the firmware-setup
test is not optional. **The acceptance test must pass either way**, and if it passes
with the second interface present, then the second interface is genuinely harmless —
which is the claim the offered lesson made, and this is where it is verified.

### Acceptance: turning the brief back into tests

The course opened with a promise: plug a Model M into the box and into any computer,
and it just types — no driver, working in a BIOS, lock LEDs lit. Here is that promise
as a test list. A build that passes all of it is finished.

| # | Requirement | Test |
|---|---|---|
| 1 | works on a machine that has never seen it | plug into the second host, cold, and type |
| 2 | needs no driver | nothing installed, nothing prompted for, working within seconds |
| 3 | is a keyboard, not something claiming to be one | enumerates with your VID/PID and strings, as a boot keyboard |
| 4 | **works in firmware setup** | enter the host's BIOS/UEFI setup and navigate and type in it |
| 5 | types correctly | a paragraph of real text, character for character, capitals and punctuation |
| 6 | lock LEDs follow the host | toggle Caps and Num Lock from the host and from the Model M |
| 7 | starts with no keyboard | power it up with nothing attached, then attach the keyboard |
| 8 | survives keyboard replug | unplug and replug the keyboard, mid-press at least once |
| 9 | survives its own replug | unplug and replug the adapter while typing |
| 10 | survives suspend and resume | suspend the host, wake it **with a keypress**, type immediately |
| 11 | never sticks a key | after every test, `held` is zero and the last report is all zeroes |
| 12 | is stable warm | an hour of real typing, then check `resync` and the dropped counter |

Three deserve a note. **Test 1 is not a formality**: your development machine has seen
this VID/PID, may have cached descriptors, and on some platforms has remembered
decisions about the device — a host that has never seen it is the only honest test of
enumeration.

**Test 4 is the one that cannot be faked, and it is why the whole HID chapter was
shaped as it was.** In firmware setup there is no operating system and no
general-purpose HID stack: the platform uses the **boot protocol**, issuing
`SET_PROTOCOL` with the boot value and then reading a fixed eight-byte report whose
shape it already knows, without parsing your report descriptor at all. This works if
and only if your interface declares subclass 1 and protocol 1 and your input report is
the eight bytes `#hid-contract` specifies, with no report ID. **Every other test on
this list passes with a nine-byte report. This one does not**, and that asymmetry is
why lesson 12's trap was called the central conceptual trap of the chapter. Navigate
with the arrows, use Enter and Escape, and type into a text field — taking care which
field: do not set a firmware password you will not remember.

**Test 12 is the one that catches the cold joint**, which is why it is on the list
rather than in a footnote: an hour of typing warms the board, and a `resync` counter
that was zero cold and is not zero warm is a temperature-dependent connection. The
console you kept a way into is how you read it.

## Concepts to teach

- What a breadboard is electrically: spring contacts, changing contact resistance,
  inter-row capacitance, and no mechanical retention.
- Stripboard versus plain perfboard, and each one's characteristic fault — the uncut
  track versus the missing wire.
- The level-shifter choice as a real decision: module (fewer joints, lower risk,
  covered by the supplied layout) versus discrete BSS138s and passives (SOT-23 work,
  own layout, deeper understanding).
- Working from a layout: transcribe first, mark and verify cuts while the board is
  bare, solder low to high.
- `#pin-assignment` and `#voltage-domains` surviving the rebuild: GP2/GP3 adjacent and
  in that order regardless of physical layout, power from VBUS, both shifter
  references powered, and the RP2040 still not 5 V tolerant.
- Continuity and isolation testing before first power: which pairs must not beep,
  which nets must, and why the 5 V-to-3.3 V pair in particular.
- Staged bring-up: Pico alone, rails measured, the keyboard with its current checked
  against lesson 01's figure, then signals on the analyser.
- Cold joints: how they look, why they conduct cold, why they fail warm, and the
  symptom here — a `resync` counter that climbs after twenty minutes; the tug test,
  and reflowing with flux rather than more solder.
- Strain relief: why an unrelieved pull lifts a pad, the range of remedies, and that
  **both** cables need it; and keeping the console and SWD reachable on the finished
  object.
- The vendor debug interface as the learner's choice, and why a second *interface* is
  compatible with `#hid-contract` where a second top-level *collection* is not.
- Boot protocol as what makes the firmware-setup test pass, and why that test is the
  only one on the list that catches a nine-byte report.
- Acceptance testing as converting a brief into a checklist, including the tests that
  only fail on a fresh host and the ones that only fail warm.

## Constraints

- **No power before the continuity and isolation test.** This is the one
  non-negotiable ordering in the lesson.
- `#pin-assignment` does not change. The board may be laid out however suits it; the
  pins stay where they are.
- Power from VBUS, never from 3V3(OUT), as `#voltage-domains` requires, and both
  level-shifter reference pins powered.
- `#hid-contract` is untouched: no report ID, eight bytes, boot subclass and protocol.
  Nothing in this lesson changes the descriptors.
- The two open decisions are presented to the learner **as decisions**. The tutor does
  not choose the level-shifter build or the vendor interface on their behalf, and the
  acceptance criteria are identical either way.
- The debug console must remain reachable on the assembled object without
  desoldering. Do not seal the case over it.
- The firmware is not modified in this lesson. If a test fails, the fault is in the
  construction or in something an earlier lesson left wrong — find out which before
  changing code.
- The acceptance list is run in full, on a host that has never seen the device. A
  partial run is not an acceptance test.
- Bring-up is staged. Do not connect the keyboard until the rails have been measured.

## Suggested progression

1. Mark the transition: the firmware is finished and nothing here changes behaviour.
   Have the learner say what is still true only because the circuit is on a bench, and
   what would break first if they carried it to another room.
2. Make the module-versus-discrete decision consciously. Lay out both options, have
   the learner choose and **state the reason**, including that a discrete build means
   drawing their own layout and that the acceptance test does not care.
3. Work through the layout at `docs/perfboard-layout.md` — or their own — until they
   can point at every net and name it, and say where each cut is and why. Do not start
   soldering before this; a layout you have not read is one you will mis-transcribe.
4. Transcribe onto the bare board, mark every cut, make the cuts, and **verify each
   one with the multimeter while the board is still empty**. The cheapest possible
   moment to find a missed cut.
5. Solder in order, low profile first. Talk about what a good joint looks like before
   there are twenty to inspect: shiny, concave, wetted on both surfaces.
6. Solder the PS/2 connector or cable, **fitting the strain relief before or as part
   of that** — a zip tie threaded after the joints are made is a job nobody enjoys.
   Relieve the host-side cable too.
7. Inspect before testing: good light, magnification or a zoomed photo, every joint
   looked at. Tug test every wire, reflow anything dull.
8. **Run the full continuity and isolation test with nothing powered**, walking the
   must-not-beep and must-beep lists explicitly rather than "checking it over". Where
   a reading is ambiguous, work out why before moving on.
9. Bring it up in stages — Pico alone with `alive` on the console; rails measured
   including both shifter references; then the keyboard with its current compared
   against lesson 01's figure; then the analyser on clock, data and the GP5 marker.
   Stop at the first stage that surprises you.
10. First functional test on the **development** machine, where every diagnostic is
    still to hand: type, check the LEDs, glance at `resync` and the dropped counter.
    Fix anything here, not in the case.
11. Fit the enclosure: insulate under the board, heat-shrink anything that could
    touch, check the cables cannot move, and **bring the console and SWD pins out** to
    somewhere reachable. Power up again and confirm nothing was pinched or shorted by
    assembly — a real and common way to break a board that worked five minutes ago.
12. Move to the **second host**, which has never seen this device, and run acceptance
    tests 1, 2, 3 and 5: cold plug-in, no driver, correct identity, a paragraph checked
    character by character.
13. **The firmware setup test.** Enter the host's BIOS/UEFI setup with the adapter as
    the only keyboard, navigate with the arrows, use Enter and Escape, and type into a
    text field — avoiding anything that sets a password. Have the learner explain while
    they are in there why it works: `SET_PROTOCOL(0)`, a fixed eight-byte report, no
    report descriptor parsed, and what a ninth byte would do.
14. Run lesson 17's robustness tests on the finished object: boot with no keyboard
    then attach it; unplug the keyboard mid-press and confirm nothing sticks; unplug
    and replug the adapter while typing; suspend the host and wake it with a keypress.
    Each of these was verified on a breadboard and is now verified through solder.
15. Check the lock LEDs both ways — toggled from the host and from the Model M.
16. **Soak.** An hour of real typing, real work if possible, then read `resync` and the
    dropped counter. A counter that was zero cold and is not warm sends you back to the
    joints with a specific suspicion.
17. If the adapter carries the vendor debug interface, confirm explicitly that the
    firmware-setup test still passed with it present, and have the learner say why a
    second interface is compatible with `#hid-contract` where a second collection
    would not be.
18. Close the course: have the learner trace one keypress end to end out loud — the
    open-drain falling edge, the shifter, the PIO state machine, eleven bits, parity,
    the ring buffer, the scan-code decoder, the key-state bitmap, the eight-byte
    report, the interrupt IN endpoint, the host's poll. If they can do that in front of
    the object they built, they are finished.

## Completion conditions

- The circuit is on a soldered board in an enclosure, with `#pin-assignment` unchanged
  and power taken from VBUS as `#voltage-domains` requires.
- The learner **made the level-shifter choice deliberately** and can state why, and the
  choice changed no acceptance criterion.
- A **full continuity and isolation test was performed before first power**, and the
  learner can say which pairs must not conduct and why 5 V to 3.3 V matters most.
- Bring-up was staged, and the measured keyboard current matches lesson 01's figure.
- **Strain relief is fitted on both cables** — a firm tug on either moves nothing on
  the board — and every joint has been inspected and tug-tested, anything dull
  reflowed. The debug console, ideally SWD too, remains reachable without desoldering.
- **All twelve acceptance tests above pass**, run in full on a host that has never seen
  the device. In particular: it enumerates cold with the learner's own VID/PID and
  strings with nothing installed or prompted for; it types a paragraph correctly; the
  lock LEDs follow the host toggled from both ends; lesson 17's behaviours hold through
  solder, including **a keypress waking a suspended host**; and after an hour of typing
  `resync` and the dropped counter are where they should be, with any rise investigated
  rather than noted.
- **It types in the host's firmware setup screen** — arrows, Enter, Escape and a text
  field — and the learner can explain why boot protocol makes that work and what a
  report ID would have done to it.
- If the adapter carries the vendor debug interface, **every test passed with it
  present**, the firmware-setup test included.
- The `finished-adapter` validator is satisfied. It is a **manual** check — obviously:
  no script can look at a soldered board in a case and tell you it is trustworthy.

## On completion, persist

Record in the instance's `DESIGN.md`/`STATE.md`:

- Which level-shifter build was chosen and why, so a future repair works on the right
  circuit; which board type was used; and where the track cuts are if it is
  stripboard. That last is the hardest thing to recover from a finished board later.
- Any deviation from `docs/perfboard-layout.md`, however small, with the reason.
- How strain relief is implemented at each cable entry, and how the enclosure comes
  apart.
- Where the debug console and SWD pins are brought out, and how to reach them.
- The measured keyboard current on the finished build beside the lesson 01 bench
  figure, so a later change in draw is detectable.
- The acceptance results: which host, which firmware setup screen, the date, and
  anything that needed a second attempt and what fixed it.
- Whether the vendor debug interface is present in the shipped firmware, and that the
  firmware-setup test passed with it.
- The `resync` and dropped-byte counters after the soak, as the baseline a future
  intermittent fault will be compared against.
- Any known non-compliance — the USB suspend current from lesson 17 in particular — so
  the limits are written down rather than rediscovered.

## Optional deeper paths

- **Measure the edges again.** Put the analyser, or a scope if you have one, on the
  soldered board's clock line and compare the rise time with the breadboard's. Lesson
  02's RC estimate included the breadboard's capacitance; this tells you how much.
- **A real PCB.** The course stops before PCB design, but this circuit is two layers
  and about a dozen nets — as gentle an introduction to KiCad as exists. What you would
  change: the connector footprint, the mounting holes, and whether the Pico is
  socketed.
- **Powering the keyboard through a switch.** Lesson 17 noted the adapter cannot meet
  the USB suspend current budget. A high-side switch on the keyboard's 5 V, opened on
  suspend, is the real answer — and it needs re-probing on resume, which your presence
  state machine already knows how to do.
- **A case you made**: 3D printed or laser cut, with the mini-DIN socket and USB
  cutout positioned properly rather than drilled into a project box.
- **Leave it plugged in for a month** and then read the counters. The failures this
  lesson is about take weeks, and time is the only way to know you avoided them.
- **Build the second one.** The fastest way to find out which parts of your layout,
  your notes and your `DESIGN.md` were actually sufficient is to build the adapter
  again from them without looking at the first.
