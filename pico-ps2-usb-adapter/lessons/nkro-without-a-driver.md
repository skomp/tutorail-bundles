---
id: nkro-without-a-driver
title: More than six keys, without a driver
design_refs: [hid-contract]
validators: [build-ok, nkro-reports]
optional: true
---

## Purpose

Report more than six simultaneous keys to a host that has no driver for your device, and
understand exactly what that costs you.

Lesson 12 built an eight-byte report with a six-slot key array, and lesson 14 made it
overflow honestly with `ErrorRollOver` when a seventh key went down. That is not a bug and
not a limitation of USB — it is the boot keyboard report, whose shape is fixed by the HID
specification precisely so a BIOS can understand a keyboard it has never seen without parsing
anything. Six is the number that shape can hold.

The way past it is not to make the boot report bigger. It is to describe a *second*,
differently-shaped report and let the running operating system use that one, while the boot
report stays exactly as lesson 12 left it. `DESIGN.md` `#hid-contract` is normative about
where that second report may live, and the reason is worth stating up front: put it in the
wrong place and your adapter keeps working perfectly on your desk and silently stops working
in firmware setup — the one place you are least likely to test, and the one place the whole
course promised it would work.

## Prerequisites

This lesson stands alone and assumes only a finished, working adapter.

- Lesson 11 (`11-descriptors-you-write-yourself`) complete: you wrote the device,
  configuration, interface and endpoint descriptors by hand and can read them back off the
  host.
- Lesson 12 (`12-the-hid-report-descriptor`) complete: you can walk your report descriptor
  item by item, and you know why the six keys are an **array** and the modifiers are a
  **bitmap**.
- Lesson 14 (`14-events-to-state`) complete: the key-state bitmap is the single source of
  truth, reports are snapshots of it, and seven keys currently produce `ErrorRollOver`. The
  console prints `held: <n>` and `report: <eight bytes in hex>`.
- A host you can reboot into firmware setup, because the BIOS test is not optional here.
- The offered `a-second-interface-for-debugging` lesson is **not** required. If you took it,
  the composite-descriptor mechanics will already be familiar.

## Learning objectives

- Explain the difference between an array field and a bitmap (variable) field in a HID
  report, and say which one rollover limits and why.
- Write a report descriptor fragment declaring a key bitmap covering far more than six usages.
- Distinguish boot protocol from report protocol, and name which one a BIOS uses and which one
  a booted desktop uses.
- State where an NKRO report may live in this device and why it may not live on the boot
  interface.
- Decide which interface reports a given keypress at a given moment, and avoid the
  double-typing bug that follows from getting it wrong.
- Separate the firmware's rollover limit from the Model M's own matrix limit, with evidence
  for which one you have hit.

## Theory

**Why six.** The boot keyboard input report is eight bytes: a modifier bitmap, a reserved
byte, and six bytes of key *array*. An array field says "here are up to N usages that are
currently active", one usage value per slot. Six slots, six keys. A bitmap — a *variable*
field in HID terms — says instead "here is one bit per usage, set if that usage is active".
Bits are cheap: 120 usages cost fifteen bytes and have no cap at all. That is the whole
trick, and it is the exact mirror image of lesson 12's central trap. There you were told that
declaring the six keys as a bitmap was wrong; here, declaring the NKRO field as an array
would be wrong. The items are the same items. What changed is what the report means.

**A bitmap input report, in report-descriptor terms.** `Usage Page (Keyboard)`, a
`Usage Minimum` and `Usage Maximum` spanning the range you want to cover,
`Logical Minimum (0)` and `Logical Maximum (1)`, `Report Size (1)`, a `Report Count` equal to
the number of usages in that range, and an `Input (Data, Variable, Absolute)`. Two details
bite. The count must round the field out to a whole number of bytes, so add a padding
`Input (Constant)` if your range is not a multiple of eight. And usages `0x00` to `0x03` are
the error codes — `ErrorRollOver` lives at `0x01` — so a range starting at `0x00` spends four
bits describing states a bitmap cannot meaningfully be in. Keep the modifiers as their own
eight-bit variable field; they were already a bitmap and nothing about them changes.

**Boot protocol versus report protocol.** A HID interface declaring
`bInterfaceSubClass = 1` and `bInterfaceProtocol = 1` — as yours does, per `#hid-contract` —
promises it can speak boot protocol. In boot protocol the host does not read your report
descriptor at all: it assumes the fixed eight-byte layout. That is how a BIOS, with no HID
parser and a few kilobytes to play with, drives a keyboard it has never seen. A booted desktop
instead reads the descriptor and uses whatever you declared; that is report protocol, and it
is a HID interface's default state after enumeration. The host moves an interface between the
two with `SET_PROTOCOL`, and TinyUSB will tell you which mode an interface is in.

**Where the NKRO report may live — this is the normative part.** `#hid-contract` says: one
HID interface, boot-protocol compatible, **no report ID**, an eight-byte input report. Adding
a second top-level collection to *that* interface forces report IDs onto it. The moment a
report ID exists, every report on the interface gains a leading ID byte, the input report
becomes nine bytes, and boot protocol is broken. It breaks *silently* — the desktop still
types, because the desktop parses your descriptor and copes — and it fails in firmware setup,
where nothing parses anything and the eight-byte assumption is all there is.

So the NKRO report goes on a **separate interface**, with its own HID descriptor, its own
interrupt IN endpoint and its own report descriptor containing the bitmap collection. The
boot interface's descriptors do not change by a single byte. Two HID interfaces in one
configuration are two independent functions; nothing needs to group them. This is what
commercial NKRO keyboards do, and it is why "a second report descriptor" is the usual answer
rather than a clever trick.

**The bug that follows: everything types twice.** You now have two interfaces that can both
report the letter `A`, and an operating system that happily reads both will insert two `A`s.
The rule that fixes it is one line long: **at any moment, exactly one interface reports a
given keypress.** The natural gate is the boot interface's protocol state — when the host has
put it into boot protocol, the boot interface carries the keys and the NKRO interface stays
quiet; otherwise the NKRO interface carries them and the boot interface sends nothing but
empty reports. Note the consequence before committing: a host that reads neither receives
nothing at all. Decide the rule, write it down, and test both halves.

Nothing here changes `#events-vs-state`. The key-state bitmap is still the single source of
truth, both reports are snapshots built from it at the moment of sending, and both are still
sent only on change. You are adding a second *projection* of the same state, not a second
state.

**The Model M will disappoint you, and that is not your bug.** Its matrix has no per-key
diodes, and its controller blocks combinations it cannot distinguish, so for many
three-and-more-key combinations the keyboard never emits the make code at all — there is
nothing on the wire for your firmware to be good or bad at. Your firmware can be flawlessly
NKRO and you will still fail to get twenty arbitrary keys out of this keyboard. Keys spread
across different rows and columns fare much better than keys clustered together. The console
tells you which limit you have hit: watch the `key:` lines while you hold the combination. If
the `down` events are not arriving, the keyboard stopped them; if they arrive and `held:`
rises past six while the host still sees six, the firmware stopped them. Find a combination
the keyboard will actually deliver before you conclude anything about your descriptor.

**What you give up.** A second interrupt IN endpoint out of a limited budget, a larger
`wTotalLength` and more descriptor to get right, more bus bandwidth per poll for a
fifteen-byte report than for an eight-byte one, the double-typing hazard above, and a device
that now appears in the host's device list as two keyboards. NKRO is not free, and for a
Model M — whose matrix caps you well before six becomes a problem in ordinary typing — it is
mostly a thing you do because you want to know how.

## Concepts to teach

- Array fields versus variable (bitmap) fields in a HID report, which one has a rollover
  limit, and why this is the mirror of lesson 12's trap.
- Report-descriptor items for a bitmap: `Usage Minimum`/`Usage Maximum`, `Logical Minimum`
  and `Logical Maximum` of 0 and 1, `Report Size (1)`, `Report Count`, `Input (Data, Var,
  Abs)`, byte padding, and why the error-code usages `0x00`–`0x03` are excluded.
- Boot protocol versus report protocol: who selects which, what a BIOS does, what a desktop
  does, and how the firmware asks which mode it is in.
- `#hid-contract`: why a second top-level collection on the boot interface forces a report
  ID, makes the input report nine bytes, and breaks boot protocol silently — and why a
  separate interface is therefore the answer.
- The one-reporter-at-a-time rule and the double-typing bug that violating it produces.
- The Model M's matrix limit as distinct from the firmware's rollover limit, and how the
  console tells the two apart.
- The costs: endpoints, descriptor size, bandwidth, and a device that looks like two
  keyboards.

## Constraints

- The boot interface's device, configuration, interface, endpoint and report descriptors are
  **unchanged**, byte for byte, from lesson 12. No report ID appears on it and its input
  report stays eight bytes. The NKRO work adds; it does not edit.
- The NKRO report lives on its own interface with its own endpoint and its own report
  descriptor. It is not a second top-level collection on the boot interface.
- Exactly one interface reports a given keypress at a given moment. The learner states the
  rule they used and demonstrates that nothing types twice.
- The key-state bitmap remains the single source of truth, per `#events-vs-state`. Both
  reports are snapshots of it, sent on change.
- The adapter is tested in the host's firmware setup screen. "It works on the desktop" is not
  evidence about boot protocol.
- The `held:` and `report:` console lines keep their lesson 14 meanings, and no key sticks:
  holding more than six keys and releasing them must leave `held: 0`.

## Suggested progression

1. Re-establish where six comes from: walk the eight-byte report and identify the array
   field. Have the learner say what would have to change for a seventh key to fit.
2. Have the learner propose a change. If the proposal is "make the array longer" or "add a
   collection to this interface", follow it on paper as far as the report ID, and let
   `#hid-contract` land.
3. Read `#hid-contract` together and extract the rule in the learner's own words: where an
   NKRO report may live, and what breaks if it lives anywhere else.
4. Design the bitmap field on paper: which usage range, how many bits, how much padding, how
   many bytes the whole report is. Do this before writing any descriptor bytes.
5. Write the second report descriptor. Have the learner walk it item by item as they did in
   lesson 12.
6. Add the second HID interface: its interface descriptor, its HID descriptor, its interrupt
   IN endpoint, and the corrected `wTotalLength`. Rebuild.
7. Enumerate and read **both** report descriptors back off the host. Confirm the boot
   interface's is byte-identical to lesson 12's.
8. Send the bitmap report: build it from the key-state bitmap at send time, not accumulated
   from events.
9. Type one letter. If it appears twice, the one-reporter rule is not in place yet — this is
   the moment to discover the bug rather than be warned about it.
10. Decide the gate before writing it: which interface reports a keypress at a given moment,
    keyed on the boot interface's protocol state. Have the learner state the rule in one
    sentence, and say what a host that reads neither interface would then receive.
11. Implement the decided rule, and type the same letter again. It appears once.
12. Find a combination the Model M will actually deliver: hold candidate sets and watch the
    `key:` and `held:` lines to see whether seven or more downs reach the firmware at all.
13. With a combination that works, press more than six keys at once into a text editor on the
    host and check every one appears while `held:` shows the same count. Release everything
    and confirm `held: 0` and no stuck key.
14. Reboot into firmware setup and type. The boot interface must still work there, with the
    NKRO interface idle.
15. Have the learner write down what NKRO cost them — endpoints, bytes, the second device
    entry, the gate — and whether they would keep it in the finished adapter.

## Completion conditions

- More than six simultaneous keys are reported to the host and all of them appear in a text
  editor from a single simultaneous press, with `held:` showing the same count the host
  received.
- The boot interface still works: the learner boots into the host's firmware setup and types
  correctly there with the NKRO interface idle.
- The boot interface's report descriptor, read back off the host, is byte-identical to the one
  lesson 12 produced, carries no report ID, and its input report is still eight bytes.
- The learner can state where the NKRO report lives and give the `#hid-contract` reason it may
  not live on the boot interface, naming the nine-byte consequence.
- Nothing types twice. The learner states the rule deciding which interface reports a keypress
  and demonstrates it in both protocol states.
- The learner distinguishes, with console evidence, a combination the Model M's matrix refuses
  to emit from one the firmware failed to report, and names at least one of each.
- Releasing every key leaves `held: 0` and no key stuck, and the `build-ok` and `nkro-reports`
  checks pass.

## On completion, persist

Record in the instance's `DESIGN.md`/`STATE.md`:

- That the device is now composite, with the interface numbers and endpoint addresses of both
  HID interfaces, and the note that the boot interface is unchanged from lesson 12.
- The usage range and report size of the NKRO bitmap report, and the rule deciding which
  interface reports a keypress along with the protocol state it keys off.
- Which key combinations the Model M's matrix will and will not deliver, so a later lesson
  does not rediscover the matrix as a firmware bug.
- Whether the finished adapter of lesson 18 keeps the NKRO interface. Lesson 18's acceptance
  test must pass either way.

## Optional deeper paths

- Work out why the modifiers were already a bitmap in the boot report and therefore never had
  a rollover problem at all.
- Investigate how operating systems actually consume a two-interface keyboard: which one
  claims the device name, what the second looks like in the host's device list, and what
  happens if you unplug while one is active.
- Read about the single-interface variant: declare only the bitmap on the existing interface
  and rely on the BIOS ignoring the descriptor while the firmware sends boot-shaped bytes in
  boot mode. Work out which promise it breaks — the descriptor read back off the host no
  longer describes what boot mode sends — and why some commercial keyboards accept the trade.
- With the offered `measure-your-latency` instrumentation in place, see whether a fifteen-byte
  report at your polling interval changes anything the typist can feel.
