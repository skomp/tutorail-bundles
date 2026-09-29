---
id: 02-open-drain-and-pull-ups
title: Open drain, pull-ups and two voltages
design_refs: [voltage-domains, pin-assignment]
validators: [pullups-verified]
---

## Purpose

You have a 5 V keyboard and a 3.3 V microcontroller that is not 5 V tolerant, and two wires
between them that either end is allowed to drive. This lesson builds the interface, and —
more importantly — makes you able to say why the two obvious cheaper answers do not work,
because one of them destroys hardware and the other one works perfectly for six lessons and
then fails in lesson 09.

The concept underneath all of it is **open drain**, and it is worth the time. A PS/2 bus,
an I²C bus and an interrupt line shared by four chips all work the same way: nobody ever
drives the line high, everybody may pull it low, and a resistor supplies the high level.
Once you see that, a great deal of hardware stops being arbitrary — including why you cannot
put a resistor divider on such a line, which is the trap this lesson is built around.

There is a second thing to see, and it is the reason the resistor in "pull-up resistor" is
a choice rather than a constant. A pulled-low line snaps down, because a transistor is
pulling it. A released line does not snap up; it *charges*, through the pull-up, into
whatever capacitance the wire and the cable and the breadboard present. That is an RC curve,
and if you choose a pull-up that is too weak the curve is still climbing when the receiver
is supposed to be reading. You will estimate that number today for the pull-ups that are
already on your bench.

Note the "already". `#voltage-domains` is explicit: the keyboard supplies its own pull-ups
on the 5 V side and the level-shifter module carries the 3.3 V side. **You are not adding
pull-ups to make the bus work.** You are measuring what is there and working out what a
different value would have done.

## Prerequisites

- `01-the-ps2-connector-and-what-is-safe` complete: you know which pin is which on your
  connector, the keyboard passes its self test on your 5 V, and you have a current budget.
- `00-first-code-and-a-window-in` complete, and the debug console is still running.
- A BSS138-type 4-channel bidirectional level shifter module, from `BOM.md`.
- Assorted resistors between about 1 k and 10 k, for the thought experiment and the
  measurements.

## Learning objectives

After this lesson you can:

- Draw the difference between a push-pull output and an open-drain output, and say what
  happens when two of each are joined on one wire.
- Explain why open drain is what makes a shared bidirectional line possible without any
  arbitration hardware.
- Give two independent reasons a resistor divider cannot work on this bus, one of which is
  about the direction of the signal and one of which is about the level.
- Say when a unidirectional buffer stops working on this project, and why that is worse than
  failing immediately.
- Describe how a single N-channel MOSFET level-shifter channel conducts in each of its three
  states, including the one that uses the body diode.
- Compute an RC rise time for a given pull-up and an estimated bus capacitance, and compare
  it against the time the receiver has.
- Measure the effective pull-up resistance on a live bus without guessing.

## Theory

### Push-pull: the output you already assume

A normal digital output is **push-pull**. It has two transistors: one that connects the pin
to the supply rail, and one that connects it to ground. Exactly one is on at a time. The pin
is actively driven both high and low, which is fast and strong.

Join two push-pull outputs together and set one high while the other is low, and you have
made a direct path from rail to ground through two transistors. That is a short circuit that
both chips are actively maintaining. It is called contention, and it is why you cannot simply
wire two ordinary outputs together and hope.

### Open drain: delete the top transistor

An **open-drain** output (the bipolar version is called open-collector, and PS/2 documents
use that word) has only the lower transistor. It can pull the pin to ground, or it can turn
that transistor off and let the pin go — high impedance, driving nothing at all. It can
never drive the pin high.

The high level comes from a **pull-up resistor** to the rail. When nobody is pulling, the
resistor holds the line at the rail. When anybody pulls, the line goes low and the resistor
merely passes a small current to ground.

Everything nice follows from that:

- **Any number of devices can share the wire.** There is no contention to arrange, because
  no device is ever fighting another; the worst case is two devices pulling low at once,
  which is the same as one device pulling low.
- **The line is a wired-AND.** It is high only if every device has released it. PS/2 uses
  this directly: a host that wants the keyboard to stop talking simply holds CLOCK low, and
  the keyboard sees it and stops.
- **Both directions live on one wire.** In lessons 04 to 08 only the keyboard drives. In
  lesson 09 your firmware drives the same two wires while the keyboard is still clocking
  them. Open drain is what makes that a wiring question rather than a redesign.

The cost is that the rising edge is passive, which is the whole of the next section.

### Why a resistor divider cannot work here

The obvious way to get 5 V down to 3.3 V is two resistors: the signal into the top of the
divider, the tap into the 3.3 V input. It is cheap, it is two components, and for a
one-directional push-pull signal it is a legitimate answer. Here it fails twice over, for
reasons that are independent of each other.

**It has no answer for the other direction.** A divider is an attenuator, and attenuators
have an input end and an output end. This bus does not. When your firmware needs to pull the
line low — which lesson 09 requires — it is pulling on the *bottom* of a divider whose top
is tied to a 5 V line held up by the keyboard's own pull-up. What the keyboard sees is not
ground. It sees whatever the divider's ratio produces from 5 V, which for a divider sized to
turn 5 V into 3.3 V is around two-thirds of the rail: a solid, confident logic **high**. Your
transmit does not arrive weakly. It does not arrive at all.

**It is not a divider on an open-drain line in the first place.** A divider's ratio assumes
a driven source with a low impedance. Here the 5 V "source" is a pull-up resistor of a few
kilohms. Your divider's top resistor is in series with it, and its bottom resistor is in
parallel with the load — so the network the keyboard is driving is not the one you designed,
the idle high level on both sides is dragged down by whatever you chose, and the rise time
is worse than it was before you helped.

The first reason is the fatal one, and it is the one worth carrying: **a divider assumes a
direction, and this line does not have one.**

### Why a unidirectional buffer is the crueller mistake

A level-translating buffer — a 5 V-in, 3.3 V-out logic gate — fixes the level problem
properly and is the right answer to a great many interfacing questions. It has an input pin
and an output pin.

On this project it works. It works in lesson 03 when you capture the signal, in 04 when you
count edges, in 05 when you assemble frames, in 06, in 07, in 08 — every lesson in which the
keyboard is the only thing that ever drives the bus. Then lesson 09 asks you to send the
keyboard a command, and there is no path from your GPIO to the wire, because you installed a
one-way street.

That is worse than a divider, not better. A mistake that fails immediately is cheap. A
mistake that fails six lessons later, after you have built a working receiver on top of it,
is expensive — and by then the evidence points at your transmit code, not at a component you
chose in week one. `#voltage-domains` exists to stop this, and this is the paragraph that
explains why it is worded so firmly.

### What the level shifter actually does

The BSS138-type module is one N-channel MOSFET per channel, in a circuit that is far cleverer
than it looks. The gate is tied to the **lower** supply (3.3 V). The source sits on the low
side, the drain on the high side, and each side has its own pull-up to its own rail.

Three states, and the third is the interesting one:

- **Both sides idle.** Both pull-ups hold their sides at their own rails. The source is at
  3.3 V and the gate is at 3.3 V, so the gate-source voltage is zero, the MOSFET is off, and
  the two sides are isolated. The low side sits at 3.3 V; the high side sits at 5 V. Correct
  levels on both, with nothing conducting.
- **The low side is pulled down** — by your GPIO. The source goes towards 0 V while the gate
  stays at 3.3 V, so the gate-source voltage is now about 3.3 V, the MOSFET turns on hard,
  and it pulls the high side down through itself. The keyboard sees a low.
- **The high side is pulled down** — by the keyboard. The gate-source voltage has not changed
  yet, so the MOSFET is still off. What conducts first is the MOSFET's **body diode**, from
  source to drain, which drags the low side down to about a diode drop above the high side.
  That fall in the source voltage is what raises the gate-source voltage, which turns the
  MOSFET properly on, which completes the pull. The diode starts the job and the transistor
  finishes it.

That third state is why this circuit is bidirectional with no direction pin and no logic in
it. It is worth being able to recite, because it also tells you the circuit's limits: the
rising edges on both sides are passive pull-ups, so everything in the next section applies on
both sides at once.

### Rise time, and why the pull-up value is a trade-off

The falling edge is driven by a transistor and is fast. The rising edge is a resistor
charging a capacitor, and it is an exponential:

```
V(t) = Vcc * (1 - e^(-t / RC))
```

`R` is the pull-up. `C` is everything the wire looks like to it: the keyboard's cable, your
breadboard, the jumper wires, the analyser probe when you clip it on, the input capacitance
of the pins. It adds up faster than people expect, and a metre or two of keyboard cable is
the dominant term. A working estimate for this bench is in the region of a hundred to a few
hundred picofarads, and you should treat that as an estimate and label it as one.

Two useful landmarks off that curve: the line reaches about 63 % of the rail in one time
constant `RC`, and about 90 % in `2.3 RC`. What you actually care about is reaching the
receiver's input-high threshold — for the RP2040 that is a fraction of its 3.3 V I/O supply,
and you should read the number out of the datasheet rather than take it from a lesson.

Now the comparison that makes it concrete. A PS/2 clock runs somewhere around 10 to 16.7 kHz,
so a clock period is roughly 60 to 100 µs and a half period 30 to 50 µs. With a 10 k pull-up
and 150 pF, `RC` is 1.5 µs — the edge is over long before anything needs to read it, and you
have a comfortable margin. Push the pull-up to 47 k and the same capacitance gives 7 µs, which
is still inside a half period but has started to eat into it. Push it to 470 k and the line
is a slow triangle that never confidently reaches a valid high, and your receiver sees
garbage that gets worse as you add cable.

So the pull-up is a trade-off, in both directions: weaker means slower edges, stronger means
more current wasted while the line is held low and a harder job for whatever is pulling. It is
not a value you look up. This is exactly what the offered `see-the-edges-on-a-scope` lesson
goes and looks at, if you have a scope.

### One trap before you measure anything

An unconfigured microcontroller pin is not necessarily floating. On the RP2040 the pad reset
state has an internal pull-down enabled — check the pad control section of the datasheet and
confirm it for yourself — and an internal pull-down of a few tens of kilohms fighting the
module's pull-up will park your low side somewhere in the middle and make every measurement
you take in this lesson wrong in a way that looks like a bad solder joint.

Configure GP2 and GP3 explicitly as inputs with **no** internal pull-up or pull-down, and do
it before you trust an idle reading. The bus already has its pull-ups; adding the chip's
internal ones on top just changes the effective resistance you are about to measure.

## Concepts to teach

- Push-pull outputs, and contention when two are joined.
- Open drain and open collector; the pull-up as the source of the high level.
- Wired-AND behaviour, and PS/2's use of it to inhibit the keyboard.
- Why a resistor divider assumes a direction, and what the keyboard sees when the 3.3 V side
  pulls low through one.
- Why a unidirectional buffer passes every test until lesson 09.
- The BSS138 channel's three conduction states, including the body-diode path.
- RC rise time; time constant; the 63 % and 90 % landmarks; input-high threshold.
- Bus capacitance as a sum of cable, breadboard, probe and pin.
- Pad reset state, and internal pulls fighting external ones.

## Constraints

- The keyboard's 5 V side connects only to the **high** side of the shifter, and GP2 and GP3
  connect only to the **low** side. `#pin-assignment` fixes clock on GP2 and data on GP3, in
  that order, because lessons 07 and 08 need them adjacent.
- The shifter's low-side reference comes from the Pico's 3.3 V, and its high-side reference
  from VBUS. Grounds are common.
- **Do not add a pull-up before you have measured the one that is already there.** If you
  conclude one is needed, say what measurement led you there.
- GP2 and GP3 stay inputs for this whole lesson, with internal pulls explicitly disabled. Your
  firmware does not drive the bus until lesson 09.
- A resistor divider is not an acceptable solution, and neither is a unidirectional buffer.
  The learner must be able to say why, in their own words, without quoting `DESIGN.md`.
- The bus-capacitance figure is an estimate and must be recorded as one, with the reasoning
  that produced it.

## Suggested progression

1. Before touching the shifter, work through both wrong answers on paper. Sketch the divider,
   put 5 V and its pull-up at the top, and work out what the keyboard sees when the 3.3 V side
   pulls its end to ground. Write the number down.
2. Then sketch the unidirectional buffer and find the lesson at which it breaks. Say what the
   symptom will look like when it does.
3. Wire the shifter: high-side reference to VBUS, low-side reference to 3.3 V, grounds common,
   and nothing else yet. Power it and confirm both reference rails with the meter.
4. Bring the keyboard's clock and data onto two high-side channels, still with nothing on the
   low side, and confirm the keyboard still passes its self test.
5. Configure GP2 and GP3 as inputs with internal pulls disabled, and flash that build. Confirm
   the `alive` counter is still running on the console, so you know the firmware you are about
   to trust is the firmware on the chip.
6. Connect the corresponding low-side channels to GP2 (clock) and GP3 (data).
7. Measure the idle level on all four points: both high-side lines and both low-side lines.
   The high side should sit at the 5 V rail and the low side at 3.3 V. Anything in between is
   the trap from the previous section, or a reference rail you have not connected.
8. Now prove the bus is bidirectional, by hand, with no firmware involved. Pull one high-side
   line to ground through a resistor of a few hundred ohms and watch the corresponding low side
   follow down. Then release it and pull the *low* side down the same way, and watch the high
   side follow. Do this for both channels.
9. Measure the effective pull-up on each side rather than guessing it. Hold the line low
   through the meter in current mode and read the current; the pull-up is the rail voltage
   divided by that current. Do it on the 5 V side and on the 3.3 V side, and note that what you
   are measuring is the parallel combination of everything pulling up on that node.
10. Estimate the bus capacitance: cable length times a per-metre figure you can justify, plus
    a contribution for the breadboard and jumpers. Write down where each term came from.
11. Compute the time constant for your measured pull-up and your estimated capacitance, and
    then the time to reach the RP2040's input-high threshold. State it in microseconds.
12. Compare that number against a PS/2 half clock period and say how much margin you have.
13. Work out, from the same arithmetic, the pull-up value at which your margin disappears.
    That number is the answer to "why not just use a bigger resistor".
14. Press a key with the whole interface connected and confirm the keyboard still runs
    normally — it is clocking into a receiver that does not exist yet, and that is fine.
15. Have the `pullups-verified` check run against your measurements and your reasoning.

## Completion conditions

- Both idle levels are measured and correct: the high side at the 5 V rail, the low side at
  the 3.3 V rail, on both clock and data.
- Either end can pull either line low and the other side follows, demonstrated by the learner
  on both channels and in both directions.
- The learner states a measured effective pull-up resistance for each side, with the method
  that produced it.
- The learner states an **RC estimate** for their bus: the pull-up, the estimated capacitance
  with its justification, the time constant, and the time to reach the input-high threshold,
  compared against a PS/2 half clock period.
- The learner names the pull-up value at which the margin runs out, and can say what the
  symptom would be.
- The learner can give both reasons a resistor divider fails and the lesson number at which a
  unidirectional buffer fails, in their own words.
- The learner can walk through the three states of a BSS138 channel including the body-diode
  path.
- GP2 and GP3 are wired per `#pin-assignment` and are configured as inputs with internal pulls
  disabled.
- The `pullups-verified` check passes.

## On completion, persist

- The measured pull-up resistance on each side, and the method used.
- The bus capacitance estimate, its derivation, and the resulting time constant and rise time.
- The margin against a PS/2 half clock period, and the pull-up value at which it vanishes.
- The confirmed wiring: which shifter channel carries clock and which carries data, which
  reference rail is on which side, and where ground is bonded.
- The note that GP2 and GP3 remain inputs until lesson 09, and that internal pulls are
  deliberately off.

## Optional deeper paths

- Take the offered `see-the-edges-on-a-scope` lesson, which measures the edge you just
  calculated at two different pull-up values.
- Work out the current wasted by the pull-up while the line is held low, at your value and at
  a much stronger one, and relate it to the budget from lesson 01.
- Read the I²C specification's treatment of bus capacitance and rise time, and see the same
  arithmetic done by a standards body with a hard limit attached.
- Find out what an active pull-up or bus accelerator does, and why I²C fast-mode-plus devices
  sometimes need one.
- Look at how a BSS138 module behaves at speeds far above this bus, and find the point at
  which this circuit stops being a good answer.
- Consider what would change if the keyboard's own pull-up were much stronger than the
  module's, and which side would then dominate your measurement.
