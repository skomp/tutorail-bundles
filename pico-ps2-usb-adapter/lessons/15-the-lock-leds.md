---
id: 15-the-lock-leds
title: The lock LEDs
design_refs: [hid-contract, wire-format]
validators: [build-ok, leds-follow-host]
---

## Purpose

Every byte that has crossed your adapter so far has gone one way, and this lesson turns the
arrow round: the host tells the keyboard something, and the keyboard obeys.

It is tempting to read the lock LEDs as decoration — the last five per cent before the
soldering. They are not. They are the only place in this project where the adapter is a
*consumer* of the host's state rather than a producer of its own, and getting them right
forces you to understand something about Caps Lock that most people have wrong: the lock state
does not live in the keyboard, it lives in the host. Your Caps Lock key is an ordinary key
sending an ordinary make code; the host decides what it means, keeps the flag, and tells every
attached keyboard what to light. That is why toggling Caps Lock on one keyboard lights the LED
on another, and it is why this lesson's acceptance test involves a second keyboard.

Two things make it worth teaching rather than worth ten minutes. The bit order the host sends
is **not** the bit order PS/2 wants, and both are three low bits of one byte, so a wrong
mapping does not crash — it lights the wrong LED, which you notice only by looking at the
keyboard. And the PS/2 write is slow: two frames and two acknowledgements, milliseconds of it,
arriving inside a USB callback that must not take milliseconds. That is lesson 06's discipline
again, in a place you will not expect it.

## Prerequisites

- `09-talking-back-in-pio` — you can send a byte to the keyboard and read its acknowledgement,
  and `docs/ps2-commands.md` has been in your workspace since that lesson.
- `12-the-hid-report-descriptor` — you declared a one-byte LED output item yourself, in an
  order you chose. You will go and read exactly what you wrote.
- `13-your-first-keystroke` — the device enumerates, is configured, and `tud_task()` runs on
  every pass of the main loop.
- `14-events-to-state` — the adapter types correctly from a state model, and you have the habit
  of acting only when something actually changed.
- `06-handing-data-to-the-main-loop` — moving slow work out of a context that must stay fast,
  with a flag and a shared variable. It applies here with only the context renamed.

## Learning objectives

- Explain where lock state lives in a USB keyboard system, and why the keyboard is not the
  owner.
- Locate the output item in your own report descriptor and state each bit's meaning from what
  you declared, not from memory.
- Receive a HID output report in the right TinyUSB callback, and name the callbacks it is
  confused with and what each is actually for.
- Explain why a boot keyboard receives its LED byte as a `SET_REPORT` control transfer on
  endpoint 0 rather than on an OUT endpoint.
- Translate a HID LED bitmap into the argument byte of a PS/2 `0xED` command, having read both
  orders rather than assumed they match.
- Perform the `0xED` exchange as two frames with two acknowledgements, and survive a NAK or a
  silent keyboard without spinning.
- Move multi-millisecond work out of a USB callback, and say what stalls if you do not.
- Apply "only act when it changed" in the host-to-device direction.

## Theory

### The lock state belongs to the host

A PS/2 keyboard's Caps Lock key sends a make code and a break sequence and nothing more. It
has no idea whether caps is on. The LED is not wired to the key; it is wired to a command
register, and the only thing that writes it is a host sending `0xED`.

USB works the same way and is more explicit about it. The keyboard sends the Caps Lock usage
in an input report like any other key. The host's keyboard driver owns the lock flags, applies
them to its interpretation of later keystrokes, and pushes the resulting LED state back down to
**every** attached keyboard — which is why two keyboards on one machine always agree, and why
the LED on a keyboard you have not touched changes when you press Caps Lock on the other.

Your adapter decides nothing here. It receives the host's decision and relays it to a 1986
keyboard that speaks a different dialect.

### The output report you already declared

In lesson 12 you wrote an output item: Usage Page 0x08 (LEDs), five usages, report size 1,
report count 5, then a three-bit constant pad to fill the byte. The five usages, in the order
the HID usage tables give them, are Num Lock, Caps Lock, Scroll Lock, Compose and Kana.

Bit *n* of the byte is the *n*th usage **in the order you listed them**. Say that slowly: the
answer to "which bit is Caps Lock?" is in your own file, not in your memory and not in a forum
post. Go and read your descriptor. If you declared the usages in ascending order, which is the
conventional thing to do, then:

| bit | usage |
|---|---|
| 0 | Num Lock |
| 1 | Caps Lock |
| 2 | Scroll Lock |
| 3 | Compose |
| 4 | Kana |
| 5–7 | constant padding, always zero |

The report is one byte with no report ID in front of it, because `#hid-contract` says this
interface has none. Adding one to get a tidier callback signature breaks boot protocol.

### How the byte reaches you

A boot keyboard normally declares one endpoint: interrupt IN. With no interrupt OUT endpoint
the host has nowhere to push an output report asynchronously, so it uses the control pipe — a
`SET_REPORT` request on endpoint 0, report type Output. Every host does this, and it is why a
boot keyboard can be a one-endpoint device.

TinyUSB surfaces it as **`tud_hid_set_report_cb`**. Three neighbouring callbacks are routinely
mistaken for it, and knowing which is which is half this lesson:

- `tud_hid_get_report_cb` is the host *asking you* for a report over the control pipe — the
  other direction, and it will never carry an LED byte.
- `tud_hid_report_complete_cb` fires when an input report you sent has been collected. It is
  about your own traffic.
- `tud_hid_set_protocol_cb` says the host switched between boot and report protocol. It
  matters; it is not this.

Two details inside the right callback will bite. The `instance` argument identifies **which HID
interface** the request is for: with one interface it is always zero, and code that ignores it
works — until the offered `a-second-interface-for-debugging` lesson adds a second interface and
the debug channel's traffic starts setting your keyboard's LEDs. Check it. Check `report_type`
too, since the same callback carries feature reports, and check the buffer length: a short
buffer is a host or a stack you were not expecting, and reading past it is a fault.

If you *did* declare an interrupt OUT endpoint in lesson 11, the host may use it instead, and a
declared endpoint nothing services leaves the host waiting. Either service it or do not declare
it.

### The trap: two byte orders that are not the same

Here is the fact this lesson exists to make you meet. `docs/ps2-commands.md`, supplied back in
lesson 09, documents the `0xED` argument byte and the HID LED bitmap beside it, and says in as
many words that **they are not in the same order.**

PS/2's `0xED` argument is:

| bit | LED |
|---|---|
| 0 | Scroll Lock |
| 1 | Num Lock |
| 2 | Caps Lock |

Set that beside the HID table above and the problem is obvious in hindsight and invisible in
advance. Both are three consecutive low bits in one byte; both use the same three names.
Passing the host's byte straight through to `0xED` compiles, runs, and lights a lamp — the
wrong lamp. Press Caps Lock on the host and Num Lock lights on the Model M.

Nothing catches this. Not the compiler, not TinyUSB, not the keyboard, which acknowledges your
command cheerfully because it was a perfectly valid command. The only thing that catches it is
a person looking at a keyboard, which is exactly why `leds-follow-host` is a manual check and
why pretending otherwise would be dishonest. It is also why this lesson insists you press more
than one lock key: a mapping can be wrong in a way that happens to look right for one of three.

### The `0xED` exchange, and how long it takes

Setting the LEDs is two frames, not one, and each needs its acknowledgement:

1. Host sends `0xED`. Device replies `0xFA` (ACK).
2. Host sends the LED argument byte. Device replies `0xFA` (ACK).

Each host-to-device frame is the sequence you built in lesson 09: inhibit the clock for at
least 100 µs, pull data low to request to send, release the clock, and let the **device** clock
your eleven bits out of you — because per `#wire-format` the keyboard generates the clock in
both directions and samples your data on the rising edge. Then read its acknowledgement bit,
then wait for its `0xFA` response frame.

Add it up: two request-to-send sequences, twenty-two clocked bits at a clock rate in the low
tens of kilohertz, two response frames, plus the inhibit times. It is comfortably over a
millisecond and can be several. If the keyboard is mid-transmission when you start — because
someone is typing — you must wait for the line to go idle or handle the collision, which adds
more.

A NAK (`0xFE`) means resend. Silence means the bus is broken or the keyboard is gone. Neither
may become an unbounded loop: `#failure-posture` wants an adapter that survives a keyboard
being unplugged, and a retry that never gives up is a wedge.

### Why that cannot happen inside the callback

`tud_hid_set_report_cb` is called from inside `tud_task()`, on the same thread as everything
else USB does in this firmware. While you are in it the stack processes nothing else: not the
control transfer you are answering, not your interrupt IN endpoint, not the next SETUP packet.
Sit there for four milliseconds and you have stalled the transfer the host is waiting on,
delayed every input report that was ready, and — on an unlucky host — earned a request timeout
and a reset.

The symptom is not a crash. It is typing that stutters every time a lock key is pressed, which
is a lovely bug to chase if you do not already know where it comes from.

The shape of the fix is lesson 06's, and naming it that way is the point: **the callback does
the minimum and the main loop does the work.** Validate the instance, the report type and the
length; store the byte where the main loop can see it, with `volatile` or whatever discipline
your ISR/main-loop boundary already uses; set a flag; return. The main loop notices the flag on
its next pass and performs the `0xED` exchange there, where four milliseconds cost four
milliseconds and nothing else.

Expect one consequence and do not be alarmed by it: while you hold the bus inhibited to send,
the keyboard cannot send you anything. It buffers a keystroke or two internally and you will see
them arrive slightly late. That is what the protocol is, and one more reason not to do this
more often than necessary.

### Only when it changed, and remembering what it was

Hosts send `SET_REPORT` more often than you would guess — at configuration, on focus changes,
on resume, sometimes repeatedly with a value that has not moved. Each one is milliseconds of
bus inhibition if you act on it blindly.

So apply lesson 14's discipline in the other direction: keep the last bitmap you actually wrote
to the keyboard, compare, and do nothing when it is the same. Keep the last bitmap the *host*
sent as well — it is what the `leds` console key prints, and lesson 17 will want it, because a
keyboard that has been unplugged and replugged comes back with its LEDs dark and the host will
not spontaneously tell you again.

Print `leds` as the bitmap **the host sent**, in hex, in HID order, before your translation.
That is the honest thing to log: it is the input to the mapping you are most likely to have got
wrong, and printing the translated value would hide the very bug this lesson is about.

## Concepts to teach

- Where lock state lives in a USB keyboard system, and why the keyboard is not the owner.
- The HID LED output report, its five usages, its padding bits, and bit order as a consequence
  of the learner's own declaration order.
- `SET_REPORT` as a control transfer, and why a one-endpoint boot keyboard receives its LED
  byte on endpoint 0.
- `tud_hid_set_report_cb`, the three callbacks it is confused with, and validating `instance`,
  `report_type` and length inside a USB callback.
- The PS/2 `0xED` command: two frames, two acknowledgements, and the NAK path.
- The two incompatible LED bit orders, and `docs/ps2-commands.md` as where both are written
  down.
- The cost of blocking inside `tud_task()`, and lesson 06's flag-plus-main-loop pattern applied
  to a USB callback.
- Bus inhibition during a host-to-device write, and what the keyboard does with keystrokes
  meanwhile.
- Acting only on change, in the host-to-device direction.

## Constraints

- The OUT report MUST be handled in the callback that actually receives output reports, on the
  correct HID interface instance, with report type and buffer length checked before the byte is
  read.
- The HID LED bitmap MUST be translated to the PS/2 order. A pass-through is a defect even when
  it lights something.
- No PS/2 transaction may be performed inside a USB callback. The callback stores and flags; the
  main loop transacts.
- The `0xED` exchange must handle a NAK and a non-responding keyboard without looping
  unboundedly, per `#failure-posture`.
- The keyboard must not be written to when the LED state has not changed.
- The last LED bitmap the host sent must be retained, so it can be reapplied later.
- Print `leds` as that bitmap, in hex, in HID bit order.
- Nothing here may add a report ID, a second top-level collection or a second interface to the
  keyboard interface, per `#hid-contract`.
- The eight-byte input report and everything lesson 14 built must keep working while the LEDs
  are being set.

## Suggested progression

1. Open your report descriptor from lesson 12, find the output item, and write down what each
   of the eight bits means in the order you declared the usages. Look nothing else up yet.
2. Predict, before writing code, which bit will change when you press Caps Lock on the host.
3. Find the TinyUSB callback that receives an output report. Name the three callbacks near it
   in the header and say what each is really for.
4. Implement the callback with nothing in it but validation and a print of `leds`. No keyboard
   involvement at all yet.
5. Press Caps Lock on the host and confirm a `leds` line appears with the bit you predicted.
6. Press Num Lock and Scroll Lock and confirm the other two bits. Reconcile any surprise with
   what you wrote down in step 1.
7. Observe how often your host sends the report — at configuration, on a focus change, on
   resume — and whether it ever sends an unchanged value.
8. Now relay the byte to the keyboard the naive way: straight through as the `0xED` argument,
   performed right there in the callback. Build and run it.
9. Press Caps Lock and look at the keyboard, not at the console. Note which LED lit.
10. Hold a key so it is repeating and toggle Caps Lock repeatedly. Note what happens to your
    typing while the exchange runs.
11. Measure the callback: timestamp on entry and exit, print the difference. Write the number
    down; it is the argument for the next step.
12. Move the PS/2 work out — the callback validates, stores, flags and returns; the main loop
    performs the exchange. Re-measure the callback and compare.
13. Repeat step 10 and confirm the typing stutter is gone.
14. Go to `docs/ps2-commands.md` and read the `0xED` argument's bit order beside the HID one.
15. Write the translation down as a table in the tutorial's `DESIGN.md` before you write the
    code for it.
16. Verify all three locks independently: each must light its own LED and no other.
17. Add acknowledgement handling — `0xED` acknowledged, argument byte acknowledged, bounded
    retry on `0xFE` — and confirm both ACKs with your lesson 09 `tx:` lines.
18. Add the change filter, and confirm from the `tx:` lines that a repeated identical
    `SET_REPORT` produces no bus traffic at all.
19. Attach a second keyboard to the same host, toggle Caps Lock on it, and confirm the Model M's
    LED follows without the Model M's own Caps Lock key being touched.
20. Toggle Caps Lock back from the Model M and confirm the other keyboard's LED follows too.
21. Type with Caps Lock on and confirm the host produces capitals — the lock state is applied by
    the host, and your input report is unchanged by it.
22. Run the `build-ok` check, then the `leds-follow-host` check, which needs a human to look at a
    lit LED.

## Completion conditions

- Pressing Caps Lock on the host lights the Caps Lock LED on the Model M, and pressing it again
  puts it out.
- Num Lock and Scroll Lock each light their own LED and only their own, demonstrated
  independently.
- The state survives a host-side toggle from another keyboard: toggling Caps Lock on a second
  keyboard on the same host changes the Model M's LED without the Model M being touched.
- A `leds` line appears for each `SET_REPORT` the host sends, in hex, in HID bit order, and
  matches the bit the learner predicted from their own descriptor.
- The learner can state both bit orders from the supplied reference and say which lamp a
  pass-through would have lit.
- The USB callback's measured duration is microseconds, not milliseconds, and the learner has
  the before and after numbers.
- Typing does not stutter while the LEDs are being set.
- An identical repeated `SET_REPORT` produces no PS/2 bus traffic, shown by the absence of `tx:`
  lines.
- A keyboard that NAKs or does not answer does not wedge the firmware.
- The `build-ok` and `leds-follow-host` checks pass.

## On completion, persist

- The LED bit-order translation, as a table, both orders side by side.
- Which TinyUSB callback receives the output report, and the instance and report-type checks
  applied to it.
- The measured callback duration before and after moving the PS/2 work to the main loop.
- Where the last host LED bitmap is stored, with the note that lesson 17 will reapply it after a
  keyboard hot-plug or reset.
- The retry policy for a NAK or a silent keyboard, and its bound.

## Optional deeper paths

- What Compose and Kana are, why they are in the usage table, and what a host does with them.
- Why the host and not the keyboard owns the lock flags, and what changed between the PC/AT
  keyboard controller and USB HID to make that the natural design.
- `GET_REPORT` on the control pipe: what a host can ask your device for, and why a keyboard
  rarely has anything interesting to answer.
- Declaring an interrupt OUT endpoint instead: what it costs, what it buys, and why boot
  keyboards do not.
- The offered `remap-and-macros` lesson, which adds a keymap layer and makes you decide which
  layer a change belongs in — the same layering question the LED path just asked in reverse.
