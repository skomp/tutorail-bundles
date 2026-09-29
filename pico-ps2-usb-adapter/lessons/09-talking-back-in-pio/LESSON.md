---
id: 09-talking-back-in-pio
title: "Talking back: driving the bus in PIO"
design_refs: [wire-format, voltage-domains]
validators: [build-ok, keyboard-acks-command]
---

## Purpose

Send a byte to the keyboard, on the same two wires it has been sending to you, and have it
answer.

Up to here the adapter has been a listener: the keyboard talked, you sampled, and the wires
only ever carried traffic one way. That is the easy half of PS/2. The other half is what makes
lesson 15 possible at all — the lock LEDs light only because the host tells the adapter and the
adapter tells the keyboard, with a command sent *to* the device over the very lines the device
has been driving.

This is the hardest protocol lesson in the course, for a reason worth naming before you start.
In every clocked bus you have met, one end is the master and it generates the clock. PS/2 is
not like that. **The keyboard generates the clock in both directions.** When the host wants to
send, it does not clock the bus: it signals that it wants to send, waits for the keyboard to
start clocking, and then presents each bit for the keyboard to take — one bit per clock the
*device* produces. The host is the talker and the device is still the timekeeper. Almost
everyone gets this wrong once, and the symptom is silence: a perfectly correct byte, presented
perfectly, that nobody ever clocks in.

The end of this lesson is one of the good moments in the course. You send `0xFF`, the keyboard
answers `0xFA`, and then — after a pause long enough to make you think it has failed — the
Model M runs its power-on self test, flashes its three LEDs, and answers `0xAA`. A keyboard
that has sat there passively since lesson 01 does something because you told it to.

## Prerequisites

- `08-ps2-receive-in-pio` complete: the PIO receive backend works, both backends pass, and
  `#rx-interface` is intact. Receive must work *before* transmit, because the only way to know
  a command was accepted is to read the reply.
- `07-what-a-pio-state-machine-is`: pin groups, `set pindirs`, the OSR, autopull, and the fact
  that a state machine driving a pin keeps driving it until you stop it.
- `02-open-drain-and-pull-ups`: what an open-drain line is, who supplies the pull-ups, and why
  a bidirectional level shifter was not optional. This is the lesson where a unidirectional
  buffer would have failed, four lessons after you would have chosen it.
- The logic analyser on both GP2 and GP3, ready to capture. You will not debug this lesson from
  console lines alone and should not try.

### The command table is supplied

`docs/ps2-commands.md` is in your workspace. It holds the PS/2 host-to-device command bytes and
the device's response codes: what `0xFF`, `0xED` and `0xF3` mean, what `0xFA`, `0xFE` and
`0xAA` mean coming back, and which commands take a following argument byte.

Look codes up in it. Do not derive them from captures and do not go hunting on the web — a
command byte is an arbitrary number somebody chose in the 1980s, and rediscovering it teaches
nothing. **The sequence is the lesson**: inhibit, request to send, the device-clocked write,
the acknowledge bit, the reply.

## Learning objectives

After this lesson you can:

- Describe the PS/2 host-to-device sequence step by step, saying which end drives which line at
  each step, and why the device clocks the bus in both directions.
- State which clock edge the device samples host data on, and show it on a capture.
- Drive an open-drain line from an RP2040 pin correctly — by changing the pin direction, never
  by driving a logic high.
- Arbitrate for a shared bus: decide whether it is safe to start transmitting, and handle
  losing the race to a device that started a frame first.
- Distinguish the bus-level acknowledge bit from a protocol-level `0xFA`, and implement a
  bounded resend on a rejected frame.
- Hand the two pins between transmit and receive without losing the reply that arrives
  immediately afterwards.
- Send `0xFF` and read the reset sequence back.

## Theory

### One wire, two talkers

Both PS/2 lines are **open-drain**, and `#voltage-domains` is the decision that made that work
on a 3.3 V part. Nobody drives either line high. The pull-ups — the keyboard's own on the 5 V
side, the shifter module's on the 3.3 V side — supply the high level, and any device may pull a
line low at any time. A line is high only when everybody has let go of it. That is what makes a
two-wire bidirectional bus possible, and it dictates exactly one rule:

> **You never drive a PS/2 line high. You either pull it low, or you release it.**

On the RP2040 you express that through the **pin direction**, not the output value. Set the
pin's output register to 0 once, at initialisation, and never touch it again. To pull the line
low, make the pin an output — it drives the 0 that is already there. To release it, make the
pin an input, and the pull-up takes the line high. In PIO that is `set pindirs, 1` and
`set pindirs, 0`.

Get this wrong and you have a 3.3 V push-pull output fighting a 5 V open-collector keyboard
through a level shifter: a short circuit through two FETs, and one of the few things in this
course that can damage hardware rather than merely not work.

`#pin-assignment` pays off here. Clock on GP2 and data on GP3, adjacent and in that order,
means a single two-pin `set pindirs` group based at GP2 reaches both lines in one instruction —
one bit for clock, one for data, four combinations, the whole line-state vocabulary of this
protocol as a two-bit immediate.

There is a second-order trap in `out pindirs` for anyone shifting data bits straight from the
OSR into pin directions: a `1` in a pin direction makes the pin an output, which pulls the line
low, which is a logic **0** on the wire. The word you load into the TX FIFO is the complement
of what you want the keyboard to see. Not subtle once said aloud, and invisible until you
capture the line.

### The sequence, step by step

1. **Inhibit.** The host pulls the **clock** line low and holds it. While clock is low the
   keyboard may not transmit; anything it wanted to say it buffers. Hold it at least 100
   microseconds, because the device samples the clock line periodically rather than
   continuously and a brief dip may go unseen.

2. **Request to send.** With clock still low, the host pulls the **data** line low. Both lines
   low is a state that never occurs in normal traffic, so it is unambiguous.

3. **Release the clock.** The host makes its clock pin an input again and leaves data low. The
   keyboard sees clock go high with data held low and knows the host wants to send.

   **This is the step that fails.** Release the clock too early — before the inhibit has been
   held long enough, or before data went low — and the keyboard never recognises the request.
   It reports nothing. It simply does not clock, and your transmit routine waits for edges that
   are not coming. Symptom: `timeout`, every time, on a bus that is otherwise fine. When you
   see that, look at the capture and check the *order* and the *durations* of steps 1 to 3, not
   your bit-shifting code.

4. **The device clocks the byte out of the host.** The keyboard generates clock pulses; the
   host never does. For each clock the host presents the next bit on data while clock is low,
   and the device **samples it on the rising edge**, per `#wire-format`. Eight data bits **LSB
   first**, then the **odd parity** bit, then the host releases data for the **stop bit**,
   which the pull-up makes high. Note what this means: your transmit loop is not a timed loop.
   It is edge-driven, and every bit period is as long as the keyboard decides. That is exactly
   what PIO is good at and exactly what a CPU delay loop is bad at.

5. **The acknowledge bit.** After the stop bit the keyboard pulls **data** low itself and
   generates one more clock. That low is the **ACK bit** — the device saying "I received eleven
   bits". The host reads it, then waits for both lines to return high, which is bus idle and
   the end of the transaction. Ignoring the ACK bit is tempting, because things mostly work
   without it, right up until a frame is corrupted and you have no idea the command was lost.

6. **The reply.** The device then answers on its own terms, clocking as usual, and your
   *receive* path picks it up. For nearly every command the reply is `0xFA`. `0xFE` is resend —
   it did not like the frame. `0xFF` (reset) is special: `0xFA` first, then several hundred
   milliseconds of self test, during which the Model M flashes its LEDs, and then `0xAA` for a
   passed test. Look the codes up in `docs/ps2-commands.md`.

### Two different things both called "ack"

| | What it is | Where it appears |
|---|---|---|
| the **ACK bit** | the device pulling data low on the twelfth clock | on the wire, inside your transmit routine |
| `0xFA` | a whole frame the device sends back afterwards | on your receive path, as a `frame:` line |

The first says "I received your eleven bits". The second says "I understood your command and
accepted it". A frame can be acknowledged at the bus level and then answered with `0xFE` resend
at the protocol level — different failures, different recoveries.

Your `tx:` line reports the **bus-level** outcome of one attempt: `ack` when the device pulled
data low for the ACK bit, `nak` when it did not, `timeout` when it never clocked at all inside
your window. The protocol-level reply arrives through the normal receive path as an ordinary
`frame:` line. Keep the two layers separate in code as well as in the log, because when this
goes wrong the question is always "which layer failed?".

On `nak`, and on a `0xFE` reply, resend the byte. But **bound the resends.** A device that is
unplugged, wedged, or holding clock low because it is busy will never succeed, and an unbounded
retry turns a recoverable hiccup into a hung adapter — which contradicts `#failure-posture` and
which you would meet again, painfully, in lesson 17. Pick a small number of attempts, decide
what happens when they are exhausted, and log each one.

### Timing, and the way to hold the bus that resets your keyboard

Three durations matter. These are the canonical numbers, from the PS/2 protocol as documented
in IBM's technical references and the write-ups derived from them — verify all three against
your own capture rather than against this page:

- the inhibit is held at least **100 microseconds** before the request to send;
- the device should begin clocking within roughly **15 milliseconds** of the request, and if it
  has not, that is your `timeout`;
- the host-to-device frame should complete within roughly **2 milliseconds** of the first
  clock; a host that stalls mid-frame may find the device abandoning it.

And the failure this lesson wants you to meet: **do not hold the bus inhibited longer than you
need to.** Clock held low is the keyboard's cue to shut up, and while it is held the keyboard
is buffering whatever you are typing. Hold it for tens of milliseconds and you lose keystrokes;
hold it far longer and some keyboards, the Model M among them, treat it as an error and go and
re-run their self test — which from the console looks exactly like your firmware crashing. If
`0xAA` appears when you did not ask for a reset, measure how long your clock line was low. The
100 microseconds is a floor, not a target.

### Arbitration: whose turn is it?

The keyboard may start a frame at any moment the bus is idle. You may want to start one at the
same moment. Somebody loses, the rule is that the **device wins**, and the host's job is to
notice. Before inhibiting, check the bus is actually idle — both lines high. After inhibiting,
check data again: if data is low, the keyboard had already started a frame before your
clock-low took effect and your inhibit has caught it mid-word. Release, let the frame finish,
try again.

Get this wrong and the failure is intermittent, which is the worst kind: it happens only when
you send a command at the exact moment a key is pressed, which on the bench is approximately
never and in lesson 15 — where the host sends an LED update while you are typing — is
approximately always.

### Handing the pins over, and getting them back in time

Your PIO receive state machine is sitting on these two pins waiting for a falling clock edge,
and your transmit sequence needs to drive both. Two state machines driving one pin is a race,
and a receiver that wakes mid-transmit will happily assemble your own outgoing bits into a
nonsense frame. You have real choices, and the course does not make them for you: one state
machine with two programs and the CPU restarting it at the right address; two state machines
sharing the pins with the receiver disabled for the duration; or the CPU driving inhibit and
request-to-send through ordinary GPIO with PIO taking over only the device-clocked part.

Whichever you choose, two constraints bind. **One thing drives a pin at a time**, and the
handover is explicit — disabling a state machine is something you do on purpose, and so is
restarting it in a known state. A state machine stalled mid-frame when you disable it will
resume mid-frame when you re-enable it, with a part-filled ISR and a non-zero bit counter, so
clearing FIFOs, resetting the shift counters and setting the PC is part of the handover rather
than an optimisation. And **receive must be back up before the reply arrives**: the device
answers within milliseconds of the ACK bit and `0xFA` is not resent. A routine that tears down
the receiver, sends, and rebuilds the receiver at its leisure will look perfect on the analyser
and lose every reply.

## Concepts to teach

- Open-drain arbitration: nobody drives high, and a line is high only when everyone releases it.
- Driving an open-drain line by pin *direction* with the output value parked at 0, `set pindirs`
  over a two-pin group, and what a push-pull drive would do to the hardware.
- The inverted sense of `out pindirs`: a 1 in a pin direction is a 0 on the wire.
- The full host-to-device sequence: idle check, inhibit, request to send, release clock,
  device-clocked data, parity, stop, ACK bit, return to idle.
- That the **device clocks both directions** and the host never clocks the bus.
- Host-to-device data is sampled on the **rising** edge, per `#wire-format` — the opposite edge
  from device-to-host — so transmit is edge-driven rather than timed, which is why PIO suits it.
- The ACK bit versus the `0xFA` response: two layers, two meanings, two failure modes; and a
  bounded resend on NAK or `0xFE`.
- The inhibit floor, the request-to-send timeout, and what an over-long inhibit does to a Model M.
- Bus arbitration when device and host start together, and the device-wins rule.
- Pin handover, clean state machine restart, and the deadline the reply imposes.
- Where command and response codes are looked up, and why they are supplied rather than derived.

## Constraints

- Neither PS/2 line is ever driven high. Pull low by making the pin an output with its value at
  0; release by making it an input. Any code path that writes a 1 to a PS/2 pin's output value
  is wrong even if it appears to work.
- The pin assignment does not change: clock GP2, data GP3, per `#pin-assignment`.
- Transmit does not bypass the level shifter or assume a direction-locked buffer.
  `#voltage-domains` requires the bidirectional path in both directions, and this is the lesson
  that uses it.
- `#rx-interface` still holds. Transmit is a **new** interface alongside it, not a third
  function bolted into the receive header, and it must not make the two receive backends
  non-interchangeable. If transmit needs something backend-specific, that is a design problem to
  solve, not a licence to reach into a backend.
- The receiver must be running again in time to catch the reply. A transmit that returns before
  the receiver is ready is incomplete.
- The ACK bit is read and reported; resends are bounded, with no unbounded retry loop anywhere.
- Every attempt prints `tx: <hex byte sent> <ack|nak|timeout>` — exactly that key, exactly those
  three values, lower-case hex.
- Replies appear as ordinary `frame:` lines through the existing receive path, with their
  existing parity and framing semantics. Do not invent a second path for them.
- Command bytes and response codes come from `docs/ps2-commands.md`. Do not build a table of
  your own, and do not hard-code a number without naming what the table calls it.
- Both receive backends still build and pass.

## Suggested progression

1. Open `docs/ps2-commands.md` and find `0xFF`, `0xFA`, `0xFE` and `0xAA`. That is all the
   code-table work this lesson needs.
2. Re-read `#wire-format`'s direction table. Say out loud which edge the device samples host
   data on, and confirm it is not the edge you have sampled on since lesson 05.
3. Draw the sequence on paper as two timing rows, clock and data, marking for every interval
   which end is pulling which line low. Fifteen minutes here saves an evening later.
4. Prove the release-and-pull-low mechanism on its own, with no protocol: park the pin value at
   0, toggle the direction, and capture the line. Confirm it goes low when the pin becomes an
   output and rises with a visible RC edge — the one you calculated in lesson 02 — on release.
5. If your probe can reach the 5 V side of the shifter, confirm the keyboard's side follows.
   This is where `#voltage-domains` is either right or you have the wrong shifter.
6. Implement just the inhibit: clock low, hold, release. Capture it and measure the duration you
   actually got against the one you intended.
7. While inhibited, type. Confirm the keystrokes arrive *after* you release — the keyboard
   buffered them. Then hold the inhibit for far too long and find out what your Model M does
   about it. Record what you saw.
8. Add the request to send: clock low, then data low, then release clock. Check the ordering and
   the timing on the trace, not in your head.
9. Look for the keyboard's clock pulses in the capture. If they are absent, the fault is in
   steps 6 to 8 — order or duration — and not in code you have not written yet.
10. Add the data: present each bit while clock is low, let the device clock it in on the rising
    edge, LSB first, then the odd parity bit.
11. Release data for the stop bit and confirm on the capture that the pull-up, not your
    firmware, takes it high.
12. Read the ACK bit and report `tx: <byte> ack` when you see it, `nak` when you do not.
13. Add the timeout path and make it report `timeout` rather than hanging. Provoke it by
    unplugging the keyboard and sending anyway.
14. Add the bounded resend on `nak` and on a `0xFE` reply, logging each attempt.
15. Solve the handover: stop the receive state machine for the transmit, restart it cleanly
    afterwards, and confirm from a capture that nothing drives a pin while something else does.
16. Verify the handover deadline: send a command and check the reply arrives. If `tx: ... ack`
    appears with no `frame:` after it, your receiver came back too late.
17. Send `0xFF`. Expect `tx: ff ack`, then `frame: fa ok`, then a pause of several hundred
    milliseconds, then `frame: aa ok`. **Watch the keyboard while this happens** — the Model M
    flashes its LEDs through its self test. This is the moment the lesson is for.
18. Capture the whole exchange on both lines and walk it: your inhibit, your request, eleven
    bits clocked by the keyboard, the ACK bit, then the keyboard's own frames coming back. Be
    able to point at the direction change.
19. Test arbitration: send commands repeatedly while typing hard, and confirm neither the
    outgoing byte nor the incoming keystrokes are mangled. Find the case where the keyboard had
    already started a frame, and handle it.
20. Confirm both receive backends still build, and that transmit works with each selected.
21. Record the timings you measured — inhibit duration, request-to-clock delay, bit period,
    reset-to-`0xAA` gap. Lesson 15 sends real commands under real load and will want them.

## Completion conditions

- `build-ok` passes, with both receive backends still building.
- The `keyboard-acks-command` check passes: `tx: ff ack`, then `frame: fa ok`, then
  `frame: aa ok`.
- The learner saw the Model M's LEDs flash its power-on self test, and can say what the gap
  between `0xFA` and `0xAA` was in milliseconds.
- A capture of the full exchange exists and the learner can walk it: inhibit, request to send,
  the device's clock pulses, the eleven bits, the ACK bit, the return to idle, and the replies —
  saying which end pulls which line low at each stage, and which edge the device sampled on.
- The learner can state the rule that a PS/2 line is never driven high, and say how their code
  enforces it.
- The `timeout` path is demonstrated and not merely written: sending with the keyboard unplugged
  produces `tx: ff timeout` and the firmware carries on.
- Resends are bounded, and the learner can say what the bound is and what happens when it is
  exhausted.
- The learner can state the difference between the ACK bit and `0xFA` without prompting.
- Commands sent during heavy typing neither corrupt the outgoing byte nor lose keystrokes.
- `#rx-interface` is unchanged and both backends still pass their own checks.

## On completion, persist

- The transmit interface as it ended up: entry points, whether it blocks, and how a caller
  learns the outcome. Lesson 15 calls this from a path that must not block; lesson 17 calls it
  after an error.
- Which state machines and how many instruction words are in use, and how the pins are handed
  between transmit and receive.
- The measured timings: inhibit duration used, observed request-to-first-clock delay, the
  device's clock period for host-to-device traffic, and this keyboard's reset-to-`0xAA` gap.
- What the learner's Model M did when the bus was held inhibited too long, and at what duration.
- The resend bound and the behaviour on exhaustion, and any arbitration case found.

## Optional deeper paths

- Send `0xEE` (echo) and `0xF2` (read ID) and compare what comes back against
  `docs/ps2-commands.md`. `0xF2` tells you what the keyboard thinks it is, which is a pleasant
  thing to know about a machine built before USB existed.
- Send a frame with deliberately wrong parity, watch the device NAK it, and watch your resend
  recover. It is the only easy way to exercise the `nak` path on purpose, and worth doing once
  so the code is not untested.
- Look at what `0xF3` (set typematic rate and delay) does to your frame rate, and reflect on
  lesson 08's CPU measurement, which was taken at whatever rate the keyboard defaults to.
- Work out what it would take to make the Pico *pretend to be* a PS/2 keyboard. It is the same
  sequence with the roles exchanged, and thinking it through is the fastest way to confirm you
  understand who clocks what.
