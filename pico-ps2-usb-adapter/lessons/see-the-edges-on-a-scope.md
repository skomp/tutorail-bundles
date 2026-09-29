---
id: see-the-edges-on-a-scope
title: See the edges on a scope
design_refs: [voltage-domains]
validators: [scope-trace-read]
optional: true
---

## Purpose

See the rise time you calculated in lesson 02 — as a curve on a screen, at two pull-up
values, on the bus you actually built.

**This lesson needs an oscilloscope, which this course does not assume.** If you do not have
one on the bench, decline it now and read no further. Nothing later depends on it, and there
is no substitute: the whole point is that a logic analyser cannot show you what a scope
shows you.

In lesson 02 you sized a pull-up against bus capacitance and stated an RC estimate. It was
arithmetic. In lesson 03 an analyser on the same two wires gave you clean square waves, which
quietly implied the arithmetic did not matter. Both are true and neither is the wire, which
carries a voltage that moves continuously — and every digital instrument you own, the analyser
and the RP2040's own input buffer alike, turns that voltage into a one or a zero by comparing
it against a threshold and discarding the rest.

This lesson looks at what gets discarded. You will measure the real rising edge, derive the bus
capacitance from it, change the pull-up and watch the curve change by the factor you predicted,
then push the bus until the receiver can no longer read it.

## Prerequisites

This lesson stands alone. It assumes a finished lesson 02 and nothing about what you were
doing when the tutor offered it.

- Lesson 02 (`02-open-drain-and-pull-ups`) complete: the BSS138-type shifter wired between the
  keyboard's 5 V side and GP2/GP3, both sides idling high at their own rail, and an RC estimate
  stated. Lesson 01 complete, so the keyboard is powered from VBUS and shares a ground.
- A keyboard you can make talk on demand — you will hold a key down for a repeating clock burst
  to trigger on.
- **An oscilloscope**, 20 MHz or better, with a **×10 probe**. A ×1 probe will not do, and the
  lesson explains why rather than asserting it.
- From the lesson 02 assortment: a resistor near 1 k5 and one capacitor between 470 pF and 1 nF;
  and a multimeter, to read the resistance you actually fitted rather than the one on the packet.

## Learning objectives

- Explain why an open-drain bus has a fast falling edge and a slow rising one, and name what
  drives each.
- Predict a 10–90 % rise time from R and C, measure it with scope cursors, and run the
  calculation backwards to derive your bus's real capacitance instead of guessing it.
- Name two distinct ways a logic analyser's reconstruction disagrees with the chip's own input
  buffer, and quantify how much of your own measurement is your probe.
- Relate the curve to the RP2040's V_IH and V_IL, and identify the indeterminate band.
- Choose a pull-up as a trade-off between edge speed, sink current and noise immunity, and say
  what measurement each side of it rests on.

## Theory

**The two edges are not alike.** A PS/2 line is open-drain (`#voltage-domains`): each end has
a transistor that can pull it to ground and nothing that can drive it high, and the shifter
module and the keyboard each supply a resistor to their own rail. So the **falling** edge is
driven — a transistor turns on and drags the line down in tens of nanoseconds, essentially
independent of the pull-up. The **rising** edge is not driven at all. The transistor turns
off, the line is released, and the pull-up must charge every scrap of capacitance on that
wire up to the rail.

That is an RC charge, `V(t) = Vcc × (1 − e^(−t/RC))`. It never quite reaches Vcc, which is
why rise time is quoted between 10 % and 90 %:

```
t_rise(10–90 %) = 2.2 × R × C
```

**What is in C.** Not one thing. The PS/2 cable dominates — a metre or two of cheap multicore
runs 50 to 150 pF per line — then the connector, the breadboard, the shifter module's traces,
the RP2040 input pin and the keyboard's driver. None of this is lookup-able for your bench, but
it is measurable, which is the trick this lesson turns: measure t_rise on the scope, measure R
with the multimeter, and

```
C = t_rise / (2.2 × R)
```

is the capacitance of *your* bus, with *your* cable. The pull-up is now a design decision
with a number underneath it, and "someone on a forum said 4 k7" is visibly not an answer to
a question about your cable.

**Where the receiver actually decides.** The RP2040 is not comparing against half the rail.
Its thresholds are fractions of IOVDD: V_IL is 0.35 × IOVDD (≈ 1.16 V at 3.3 V) and V_IH is
0.65 × IOVDD (≈ 2.15 V). Between them the input is **indeterminate** — the chip may read
either, and on a slow noisy edge may read both in quick succession. A Schmitt trigger is
enabled on RP2040 GPIO by default and its hysteresis is usually what saves you; it is margin,
not a fix. The longer an edge spends in that band, the more the outcome depends on whatever
is coupling into the wire.

**What the analyser hides.** It samples the line, compares each sample against **one fixed
threshold**, and stores a bit. Everything between is gone before the software sees it. Two
consequences:

- **Its threshold is not the chip's.** A cheap sigrok clone typically switches near 1.4 V;
  the RP2040 does not call the line high until about 2.15 V. On a slow edge those are
  different *moments*, and a setup margin that looks comfortable on the analyser can be gone
  on the chip.
- **It cannot represent a marginal edge.** An edge that crawls through the band and dithers
  appears as one clean transition, or several, or none, depending on the analyser's own
  hysteresis and sample rate. The square wave is a *reconstruction* and you have been reading
  it as evidence.

Same shape as lesson 16's warning that `printf` perturbs the timing it measures, one layer
down: **the instrument has already decided what you are allowed to see.**

**Your probe is part of the circuit.** A ×1 probe hangs roughly 60 to 100 pF on the node, which
on a bus whose total C is around 100 pF doubles it — you measure a rise time that exists only
because you looked. A ×10 probe adds about 10 to 15 pF for a tenth of the amplitude, which on a
3.3 V signal you can spare. Use ×10, match the channel's attenuation, and compensate the probe
first: an uncompensated ×10 probe distorts exactly the edge you came to look at.

**The trade-off, stated properly.** A stronger pull-up gives a faster edge and more noise
immunity, and costs current: the driver must sink Vcc/R for as long as the line is low — at 5 V
and 1 k, 5 mA through a driver designed in the 1980s. A weaker one costs almost nothing and
gives a lazy edge that lingers in the indeterminate band. There is no correct value, only one
correct for your capacitance, your bus speed and your driver's sink rating; you can now measure
two of the three.

**And the honest part.** A PS/2 clock half-period is 30 to 50 µs, and a 10 k pull-up on 100 pF
gives a 2.2 µs rise — about 5 % of it. PS/2 is enormously forgiving and almost any sane pull-up
works. That is not a reason to skip the measurement; it is why this is a *safe* bus on which to
learn the method. Run the same arithmetic on I²C at 400 kHz, where the spec caps rise time at
300 ns, and the margin evaporates.

## Concepts to teach

- Open-drain edge asymmetry: a driven falling edge, an RC rising edge through the pull-up; the
  charging curve, τ = RC, and why 10–90 % rise time is 2.2 × RC.
- What contributes to bus capacitance, that it is measured rather than looked up, and how to
  derive C from a measured rise time and use it to choose R.
- V_IL, V_IH and the indeterminate band; Schmitt hysteresis as margin, not as a fix.
- What a comparator-and-sampler instrument discards, and the two ways its reconstruction
  disagrees with the chip: a different threshold, and an unrepresentable marginal edge.
- Probe loading as an observer effect; ×1 versus ×10; probe compensation.
- The pull-up trade-off resolved against a measured capacitance and a known bus speed, and why
  PS/2 is forgiving where I²C is not.

## Constraints

- Nothing here changes the firmware or the course's design. The as-built pull-up arrangement
  from `#voltage-domains` is what the rest of the course assumes, and the bus must be back in
  that state — no added capacitor, no parallel resistor, console frames clean — when you finish.
- Experiment on the **3.3 V side only**. Do not add or shunt anything on the 5 V keyboard side;
  that domain is the one that destroys GPIOs, and the keyboard's pull-up is not yours.
- You cannot remove the shifter module's on-board pull-up, so vary the effective resistance by
  fitting a second resistor **in parallel**, and compute the parallel value. Measure every
  resistor you fit: a 5 % part and a misread colour band both make correct arithmetic look wrong.
- Use a ×10 probe with matching attenuation, compensated before the first measurement.
- Keep both captures. "I saw it change" is not a completed lesson; two traces side by side is.

## Suggested progression

1. State the goal in one line: turn lesson 02's arithmetic into two measured curves, and find
   out what the analyser was not showing you.
2. Set the scope up: ×10 probe, attenuation set to match, DC coupling, probe compensated
   against the calibration square wave, ground clip to the common ground of Pico and keyboard —
   not a floating point, not the 5 V rail.
3. Probe the **3.3 V side** of the clock line at GP2, and hold a key down so the keyboard
   streams typematic repeat.
4. Trigger on the **falling** clock edge, get a stable display, and read off the clock period.
   Confirm it matches what lesson 03's analyser gave you.
5. Zoom the timebase onto a single **rising** edge until it fills the screen. This is the
   shape lesson 02 described and the analyser never showed you.
6. Put cursors at 10 % and 90 % of the transition and record the rise time.
7. Power down and measure the actual 3.3 V-side pull-up with the multimeter. Record it.
8. Compute C. Compare with your lesson 02 estimate and say whether it was high or low, and by
   how much.
9. Put cursors at 1.16 V and 2.15 V and measure how long the edge spends in the
    indeterminate band. Compare with the clock half-period.
10. Predict, before changing anything: with 1 k5 in parallel with the module's pull-up, what
    is the effective R, and what rise time does that imply on the C you just derived?
11. Fit it, measure, and check the prediction. If it is out by more than your measurement
    error, find out why before moving on — usually a mis-measured R, the probe you forgot to
    account for, or cursors at 0 % and 100 %.
12. Save or photograph both traces with the timebase and measured rise time legible.
13. Say which edge the receiver can read, and be honest: at PS/2's clock rate both of yours
    almost certainly can be. Then compute where the boundary is — what R, or what C, would
    push the rise time to a meaningful fraction of the half-period.
14. Go and cross it. With the original pull-up restored, hang 470 pF to 1 nF from the 3.3 V
    clock line to ground and look again. The edge will be dramatically worse.
15. With it still fitted, watch the debug console: parity errors, framing errors and a rising
    `resync` count are the receiver telling you it can no longer read the edge on your screen.
    That is the whole lesson in one view — a curve and its consequence.
16. Remove the capacitor and the parallel resistor, restore the as-built bus, and confirm the
    console is clean.
17. Finally, switch to a ×1 probe and re-measure the original edge. Note how much of the
    change was the wire and how much was you.

## Completion conditions

- The learner presents **two traces of the same rising edge at two different effective pull-up
  values**, each with timebase and measured 10–90 % rise time legible, and for each states the
  measured R and explains the resulting edge — not "it is faster", but a rise time consistent
  with 2.2 × R × C on one consistent C.
- The learner derives the bus capacitance from one trace and shows it predicts the other's rise
  time within measurement error, or accounts for the discrepancy.
- The learner identifies V_IH on each trace and states the time spent in the indeterminate band
  as a fraction of the clock half-period.
- The learner states **which edge the receiver can still read and why** — including the honest
  answer that at PS/2 speeds both may be, together with the computed condition under which one
  would not be.
- The learner names at least two things the analyser's square wave did not show, one being that
  its switching threshold is not the RP2040's V_IH, and says what the ×10 probe changed about
  the measurement, with a number.
- The bus is back in its as-built `#voltage-domains` state and the console shows clean frames.
- The `scope-trace-read` check passes. It is manual: the tutor looks at the two traces and hears
  the explanation.

## On completion, persist

Record in the instance's `DESIGN.md`/`STATE.md`:

- The **measured** bus capacitance for this learner's cable and breadboard, with the rise time
  and resistance it came from, so later timing discussions have a real number, and the as-built
  effective pull-up on the 3.3 V side, measured rather than assumed.
- That the learner has seen the difference between the analyser's reconstruction and the scope's
  measurement, and can name the analyser's threshold as a source of disagreement — worth
  referring back to in lesson 16, where instrument perturbation returns.
- That the bus was restored to its as-built state afterwards.

## Optional deeper paths

- **Measure the falling edge.** Zoom in and see how much faster it is, then work out what limits
  it — transistor on-resistance, scope bandwidth, or the probe's ground-lead inductance, which
  rings visibly with the long crocodile lead instead of the spring tip.
- **Find the sink current.** Hold the line low, measure across the pull-up, and compute what
  each pull-up value costs a 1980s driver. Then probe the data line while the clock switches,
  with the jumpers alongside each other and then separated, to see the cross-talk the noise
  margin is absorbing.
- **Where the method matters.** Using the capacitance you measured, find the largest pull-up
  that would meet I²C's 300 ns limit at 400 kHz on this same physical bus. It is a much smaller
  resistor than you would guess.
