---
id: measure-your-latency
title: Measure your latency
design_refs: [rx-interface]
validators: [latency-measured]
optional: true
---

## Purpose

Find out what your adapter actually costs the typist — in microseconds, measured on an
instrument, rather than inferred from the shape of the code.

The obvious way to answer that question is to bracket the interesting code with
`time_us_32()` and print the difference. That number will be small, it will be real, and it
will not be the answer. It measures how long *your firmware* is busy. The typist waits for
something else entirely: the keyboard's own scan, eleven bits crawling down a wire at PS/2
speed, and then — the dominant term by an order of magnitude — the wait for the host's next
interrupt-IN poll, which happens outside your firmware and on the host's clock.

This is also the only place in the course where the two receive backends are put side by
side with numbers. `DESIGN.md` `#rx-interface` keeps the interrupt receiver from lessons 04
to 06 alive for the life of the course, as the reference implementation and as the thing
this lesson measures against. If you deleted it when the PIO backend started working in
lesson 08, you have thrown away the baseline and restoring it is the first task here. That
rule exists for this lesson.

## Prerequisites

This lesson stands alone. It assumes a finished, working adapter and nothing about what you
were in the middle of.

- Lesson 14 (`14-events-to-state`) complete: a key press produces a HID report the host
  accepts, and no key sticks.
- Lesson 08 (`08-ps2-receive-in-pio`) complete, **and both backends still present and
  selectable at build time** — the lesson 04–06 interrupt receiver and the lesson 08 PIO
  receiver, behind the one receive interface of `#rx-interface`. If the interrupt backend
  was deleted, bring it back from your git history before starting. Your firmware prints
  `backend: interrupt` or `backend: pio` at startup, as it has since lesson 08.
- A logic analyser with at least two free channels, and the PS/2 clock line (GP2) probed as
  it was in lesson 03.
- GP5 free. `#pin-assignment` reserves it for exactly this kind of timing marker, so no wire
  moves. If lesson 16 left marker code on GP5, decide now which one owns the pin in this
  build — two writers on one marker pin produce a trace nobody can read.
- The same host, cable and USB port for every run. The host is a variable in this experiment,
  not a constant you get for free.

## Learning objectives

- State where a latency measurement starts and where it ends, and defend the choice.
- Explain why a firmware-internal interval is not end-to-end latency, and name the three
  things it leaves out.
- Instrument firmware with a GPIO marker pulse and read the interval off a logic analyser
  against the PS/2 clock line.
- Hold the host's polling interval constant across two builds, and say why a comparison
  without that control measures the host rather than the firmware.
- Report a latency *distribution* rather than a single number, and explain why one sample is
  worthless here.
- Compare the interrupt and PIO receive backends with numbers, and interpret an honest null
  result correctly.

## Theory

**Three different things are all called "latency".** Name yours before you measure it.

1. **Firmware-internal time.** From the moment the main loop pops the scan code to the
   moment `tud_hid_report()` returns. Tens of microseconds, typically. This is the number
   the naive measurement produces, and reporting it as the adapter's latency overstates the
   adapter by a factor of a hundred or so.
2. **Wire to host-acknowledged.** From the first clock edge of the make-code frame on GP2 to
   the moment the host has actually taken the report off the endpoint. This is the adapter's
   honest contribution, it is the number this lesson asks for, and it is measurable with the
   kit on your bench.
3. **Finger to glyph.** Keyswitch closure, the Model M's controller scan and debounce, the
   adapter, the host's USB stack, its input subsystem, its compositor and the application's
   redraw. Most of that is not yours and none of it is measurable here. Know that it exists,
   so you do not claim your number is it.

**What the internal measurement leaves out.** First, the frame itself: eleven bits at a PS/2
clock somewhere between roughly 10 and 17 kHz is most of a millisecond, and it has already
elapsed before your code sees a complete byte. Second, any time the byte spent queued — in
the ring buffer of lesson 06, or in the PIO RX FIFO. Third, and largest, `tud_hid_report()`
does not send anything: it queues the report into the endpoint buffer and returns, and the
bytes leave when the host's next IN token arrives. If `bInterval` is 10 ms the report waits
between 0 and 10 ms for a poll your firmware has no influence over. A measurement that stops
when the function returns stops before the part the typist is actually waiting for.

**The marker.** You cannot see the USB bus without an analyser you do not have, but you can
see a GPIO pin, and TinyUSB will tell you when the host has the bytes.
`tud_hid_report_complete_cb()` is invoked after the IN transaction has completed on the wire
— the closest honest end point available from inside the firmware, and it includes the poll
wait. So drive GP5 **high** at the start boundary and **low** in the completion callback:
one clean pulse per keypress, whose width the analyser measures directly and which pairs
with one keypress on the clock channel beside it. A pulse, not a toggle — a toggle makes you
pair edges by hand and loses its meaning permanently the first time an event is missed. And
keep the marker honest: `gpio_put` costs tens of nanoseconds against a millisecond interval
and perturbs nothing, but a `printf` anywhere inside the marked path costs milliseconds at
115200 baud and changes the very thing you are measuring. That is lesson 16's Heisenbug
arriving on schedule. Buffer the number and print it after the pulse has ended.

**Where the start boundary goes, and why it is the hard part.** The end boundary is easy; the
start boundary is where a comparison between two backends is won or lost. The fair start is
the wire event — the first clock edge of the make-code frame — which the *analyser* can see
and your firmware can only approximate. The interrupt backend can raise the marker in the ISR
on the start bit; the PIO backend learns about the byte only when it is read out of the RX
FIFO, which is already a whole frame later. Time the two from different logical points and
you will "prove" whichever backend you gave the head start. The analyser is the arbiter: with
clock on one channel and marker on the other, you can see how far the marker's rising edge
sits from the real start of the frame in each build, and either correct for it or say so.

**Holding the host constant.** The polling interval is set by `bInterval` in the endpoint
descriptor you wrote in lesson 11, and it dominates the number. Change nothing in the
descriptors between the two builds, and use the same host, port, key and keyboard. If one
build advertises a 1 ms interval and the other 10 ms, the difference you measure is the
host's scheduler and your firmware is not in the result at all.

**Why one sample is worthless, and what to expect.** Your keypress lands at a uniformly
random phase relative to the host's poll, so the poll wait alone is a uniform
0-to-`bInterval` spread: with `bInterval` at 10 ms, two consecutive presses of the same key
can differ by 10 ms with nothing whatever changed. Take at least thirty presses per backend
and report minimum, median and maximum. The **minimum** is the fair comparator between
backends, because it is the sample where the poll wait was nearly zero and the firmware's own
cost is what is left; the **maximum** is what the typist occasionally feels. The two backends
differ only by the CPU work of framing, which lesson 08 already quantified in its `cpu` line,
and against a millisecond-scale poll wait that difference is likely to be invisible. A result
saying "the backend choice does not change what the typist experiences; the polling interval
does" is not a failure to find an effect. It is the correct engineering conclusion, and it
tells you which knob would actually matter.

## Concepts to teach

- The three latency boundaries, and why naming the boundary is part of reporting a number.
- Why `tud_hid_report()` returning is not the report being delivered, what
  `tud_hid_report_complete_cb()` actually signals, and how `bInterval` makes the poll wait
  the dominant term.
- GPIO marker instrumentation: a pulse rather than a toggle, why the marker must be cheap,
  how to correlate it with the PS/2 clock line, and the observer effect of a `printf` in the
  measured path.
- Fair comparison: identical descriptors, host, port and key, and equivalent start boundaries
  in both backends.
- Distributions rather than single samples; minimum as the firmware comparator, maximum as
  the felt worst case.
- `#rx-interface`: why the interrupt backend is kept alive, and what a learner who deleted it
  lost.

## Constraints

- The two builds differ **only** in which receive backend is selected. The receive interface
  of `#rx-interface` is not bypassed, and no measurement code reaches into a backend's
  internals in a way the other backend cannot match.
- The USB descriptors are byte-identical between the two builds, `bInterval` included, and
  each backend is measured over at least thirty presses of the same key on the same host,
  cable and port.
- No `printf` and no blocking call inside the marked interval.
- The marker uses GP5 and only GP5. GP2 and GP3 are not rewired, and nothing else drives GP5
  in these builds.
- The firmware prints `latency: <microseconds>` — one line per measured keypress, the value
  being the interval for that one keypress-to-report path. The existing `backend: interrupt`
  or `backend: pio` line identifies which build produced them.
- Any reported figure is accompanied by a stated method: where the interval starts, where it
  ends, and what is excluded.
- The instrumentation must not change the adapter's behaviour. Typing still works and no key
  sticks while the marker code is in.

## Suggested progression

1. Restate the question: how long does the typist wait, and which part of that is the
   adapter's fault.
2. Have the learner propose a measurement before hearing any theory, and write the proposal
   down. Most will propose the firmware-internal interval.
3. Build and run exactly that proposal: a timestamp at pop, a timestamp after
   `tud_hid_report()`, print the difference. Note the number. It is small.
4. Now ask what the host saw. Work out from `bInterval` how long a report can sit in the
   endpoint buffer, and compare that with the number just measured.
5. Redefine the boundaries as wire to host-acknowledged, and agree where each end lands in
   the code.
6. Add the GP5 marker: high at the start boundary, low in `tud_hid_report_complete_cb()`,
   one pulse per press.
7. Put the analyser on GP2 and GP5, capture a single keypress, and read the pulse width off
   the trace.
8. On the same capture, measure how far the marker's rising edge sits from the real first
   clock edge of the frame. That offset is what makes the backend comparison fair or unfair.
9. Have the firmware compute the same interval itself and print it as
   `latency: <microseconds>`, then cross-check a handful of those lines against the analyser's
   pulse widths. Where they disagree, the firmware's timestamping is wrong and the analyser
   wins.
10. Collect at least thirty presses on the current backend; compute minimum, median, maximum.
11. Rebuild with the other backend selected, changing nothing else. Confirm the `backend:`
    line reports the switch and the descriptors are unchanged, then repeat the collection with
    the same key, host and port.
12. Put the two distributions side by side. Ask which statistic isolates the firmware, and why
    the medians are dominated by something neither backend controls.
13. Instructive probe: change `bInterval` in one build, measure again, and watch the whole
    distribution move much further than the backend choice ever did. Restore the descriptor
    afterwards.
14. Have the learner write the result as one sentence a colleague could act on: a number, a
    boundary, a method, and the one knob that would actually reduce it.

## Completion conditions

- The learner reports keypress-to-report latency for **both** receive backends, each as a
  distribution over at least thirty presses — minimum, median and maximum — not a single
  sample.
- The method is stated: where the interval starts, where it ends, and what it excludes,
  naming the keyboard's own scan time and the host's input stack as outside it.
- The host's polling interval is held constant across both runs, and the learner can show the
  descriptors are identical between the two builds.
- A logic analyser capture shows the GP5 marker pulse alongside the PS/2 clock line for at
  least one keypress, and the learner reads the interval off that trace.
- The firmware's `latency: <microseconds>` lines agree with the analyser's pulse widths to
  within the learner's stated measurement error, and the `backend:` line identifies which
  build produced each set.
- The learner can say, unprompted, why the firmware-internal interval they measured first is
  not the adapter's latency, and roughly by what factor it understates it.
- The adapter still types and no key sticks with the instrumentation in place, and the
  `latency-measured` check passes.

## On completion, persist

Record in the instance's `DESIGN.md`/`STATE.md`:

- The measured distribution for each backend, with the polling interval used and the
  measurement boundaries stated beside it. A number without its boundary is not a result.
- Which backend the finished adapter ships with, and whether latency was a factor in that
  choice or not.
- That GP5 now carries a timing marker in these builds, and whether the marker code stays in
  the main build or is compiled out.
- Which knob dominates end-to-end latency, so a later lesson does not re-measure it.

## Optional deeper paths

- Measure the keyboard's own contribution: watch the clock line while triggering off a
  separate contact on the keyswitch, and see how much delay the Model M's controller adds
  before your firmware exists at all.
- Measure jitter rather than mean latency. For a typist, variance is more noticeable than a
  constant offset, and the poll-phase spread is pure jitter.
- Measure the report path under load: hold a key so typematic repeat is running while typing
  another, and see whether the tail of the distribution grows.
