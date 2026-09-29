---
id: 12-the-hid-report-descriptor
title: The HID report descriptor
design_refs: [hid-contract]
validators: [build-ok, report-descriptor-sane]
---

## Purpose

Describe the shape of your reports in a language the host can parse — a tiny stack machine
whose program you write in bytes, by hand, and which nothing in your toolchain will check for
you.

Lesson 11 told the host that a HID keyboard exists. It did not say what a report from that
keyboard would *mean*. Eight bytes are going to arrive at the host every so often, and
nothing so far says which bits are modifiers, which byte is ignored, or where the keys live.
That is what the report descriptor is for, and it is the last descriptor because it is the
only one the class driver — rather than the USB core — asks for.

The HID class is deliberately generic: one driver in the operating system serves keyboards,
mice, gamepads, graphics tablets, thermometers and uninterruptible power supplies, and it
manages that by making every device describe its own data format. The price of that
generality is a small declarative language with three item scopes, a stack, and a semantic
distinction between two kinds of field that looks arbitrary until you understand it — and
which, gotten backwards, produces a descriptor that parses cleanly, enumerates cleanly, and
is wrong.

## Prerequisites

- Lesson 11 (`11-descriptors-you-write-yourself`) complete: the device enumerates with the
  learner's own VID/PID and strings, binds as a HID keyboard, and has one interrupt IN
  endpoint of 8-byte maximum packet size. The HID class descriptor written there declares
  the length of the report descriptor you are about to write, and the two must end this
  lesson agreeing.
- Stdio still on UART0 (`#debug-channel`), and `key:` lines from lesson 10 still arriving.
- A Linux or macOS host available for the evidence step. Windows *reconstructs* a report
  descriptor from its own preparsed data rather than reading it from the device, so a
  Windows readback is at best semantically equivalent and cannot be compared byte for byte.
  This is a real constraint, not a preference; see *Theory*.

## Learning objectives

- Decode any HID report descriptor item from its prefix byte alone: tag, type and size.
- Explain the three item types — Main, Global, Local — and the difference in lifetime that
  makes the language work.
- Explain the difference between a **Variable** field and an **Array** field, and decide
  from first principles which of the two each part of a keyboard report must be.
- Compute a report's total size from Report Size and Report Count, per item, and check it
  against the eight bytes `#hid-contract` requires.
- Explain what the reserved byte is, how it is declared, and what omitting it breaks.
- Explain what a Collection is, and what a *second top-level* collection would silently do
  to this interface.
- State the difference between boot protocol and report protocol, and why the descriptor
  must describe the boot layout exactly.
- Read your own report descriptor back off the host and walk it item by item.

## Theory

**Item format.** A report descriptor is a flat sequence of *items*. Each item is one prefix
byte followed by 0, 1, 2 or 4 data bytes. The prefix packs three fields:

| Bits | Field | Meaning |
|---|---|---|
| 7–4 | `bTag` | which item this is |
| 3–2 | `bType` | 0 = Main, 1 = Global, 2 = Local |
| 1–0 | `bSize` | 0, 1, 2, 3 → 0, 1, 2, **4** data bytes |

Note the last row: a `bSize` of 3 means four data bytes, not three. That is the only
irregularity in the encoding and it is the one that trips a hand-written parser.

Decode two real prefixes:

- `0x05` is `0b0000_01_01`: tag `0b0000`, type `01` (Global), size `01` (one data byte).
  Tag 0 in the Global type is **Usage Page**. So `05 01` reads "Usage Page = 0x01", and
  usage page 1 is Generic Desktop.
- `0x09` is `0b0000_10_01`: the same tag 0, but type `10` (Local), one data byte. Tag 0 in
  the Local type is **Usage**. So `09 06` reads "Usage = 0x06", and usage 6 on the Generic
  Desktop page is Keyboard.

Those two bytes are not interchangeable even though their tags match, and that is the whole
point of `bType`. Two items you will use constantly, for practice: `0x75` is `0b0111_01_01`
— Global, tag 7, one byte: **Report Size**. `0x95` is `0b1001_01_01` — Global, tag 9, one
byte: **Report Count**.

**Three scopes, and the asymmetry that matters.** The three types are not just a namespace.
They differ in *lifetime*, and getting that backwards is why a descriptor "works for the
first field and not the second".

- **Global** items set parser state that **persists** until you change it: Usage Page,
  Logical Minimum and Maximum, Report Size, Report Count, Report ID. Set Report Size to 1 and
  it stays 1 for every subsequent Main item. A Push and a Pop item save and restore the whole
  Global state, which is what makes "stack language" more than a metaphor.
- **Local** items apply only to the **next** Main item and are **discarded** afterwards:
  Usage, Usage Minimum, Usage Maximum. Declare a run of usages, emit a Main item, and the
  usages evaporate. That is a feature — it is how you say "this next field is these
  particular usages" without having to unset anything.
- **Main** items *emit* something, using whatever Global and Local state is current: Input,
  Output, Feature, Collection, End Collection.

So a descriptor reads as: accumulate state, emit a field, accumulate state, emit a field.
The Locals reset themselves; the Globals do not.

**Variable versus Array — the thing this lesson is actually about.** An Input item's data
byte is a bitfield of flags. Bit 0 is Data(0)/Constant(1). Bit 1 is **Array(0)/Variable(1)**.
Bit 2 is Absolute/Relative. The rest rarely matter here.

- **Variable** means each usage in the declared set gets its own field, in order. Declare
  *n* usages, set Report Count to *n* and Report Size to 1, and you get *n* bits, one per
  usage, every combination of which can be expressed at once. This is a **bitmap**.
- **Array** means the field does *not* correspond to a usage. It is a slot whose *value* is
  an index into the declared usage range. Report Count is then the number of values that can
  be reported **simultaneously**, and Report Size is how wide each slot is. This is a **list
  of what is currently active**.

A keyboard report has two data regions, and they use different ones. Which region gets
which is the question this lesson exists to make you answer, so answer it before reading on,
from these two numbers:

- Modifiers: there are exactly **8** possible modifier usages (`0xE0` to `0xE7` on the
  Keyboard usage page), and **all 8** can be held at once.
- Keys: there are well over **100** possible key usages, and `#hid-contract` says at most
  **6** are reported at once.

Work the arithmetic both ways. A bitmap over 8 usages costs 8 bits and can express every
combination — complete and free. A bitmap over 100-plus usages costs 100-plus bits, roughly
14 bytes, which does not fit in an 8-byte report and is not what boot protocol defines
anyway. An array of 8 slots to hold modifiers would spend 8 bytes saying what 1 byte says,
and would make "is Shift down" a search. An array of 6 one-byte slots over the key usages
costs 6 bytes and gives up the ability to report a seventh key — which is exactly the
six-key rollover `#hid-contract` chose, and which lesson 14 handles with `ErrorRollOver`.

Get it backwards and the results are instructive precisely because they are not obviously
broken. Declaring the six keys as Variable with a Usage Minimum and Maximum spanning the key
range and a Report Count of 6 gives you six *bits*, meaning the first six usages in that
range, and nothing else on the keyboard can ever be reported. Declaring the modifiers as an
Array gives you slots containing modifier indices, and the host reads your modifier byte as a
key slot. Some of these mistakes still produce a report of the right total length, which is
why a length check does not catch them and why `report-descriptor-sane` looks at the item
structure.

Two details follow. For an **Array**, Logical Minimum and Maximum bound the *values that may
appear in a slot* while Usage Minimum and Maximum give the usage range those values index —
so the keyboard array has Logical Minimum 0 and a Logical Maximum covering the usage range.
For a **Variable** bitmap, Logical Minimum is 0 and Logical Maximum is 1, because each field
is one bit meaning present or absent.

**The reserved byte.** Byte 1 of the boot keyboard report is reserved and sent as 0,
declared as one Input item with Report Count 1, Report Size 8, and the **Constant** flag set
— a Constant Input item emits padding that carries no usage and that the host ignores.

Omitting it is one of this lesson's named failures and it has the `#hid-contract` signature:
it fails silently, in the one place you will not test. Without the reserved byte your report
is seven bytes and the key array starts one byte early. On a running desktop the host is in
**report protocol**, parses your descriptor, believes you, and reads a seven-byte report
correctly — everything works. In a BIOS the host is in **boot protocol**, parses nothing, and
reads byte 2 onward as the key array, which in your report is the *second* key slot. The
device works on the desk and fails in firmware setup, with no error anywhere.

**The arithmetic, done per item.** Report Size × Report Count is the number of bits an Input
item contributes. Modifiers: 1 × 8 = 8 bits. Reserved: 8 × 1 = 8 bits. Keys: 8 × 6 = 48 bits.
64 bits, 8 bytes. Do this addition explicitly every time you change an item — a total that is
not 64 gives the host a report buffer of a different size from the one your firmware writes,
and the mismatch shows up as truncation or padding rather than as an error.

**The output report.** The host needs to tell the keyboard about the lock LEDs — lesson 15's
subject, but its descriptor belongs here. It is an Output item on the LED usage page with
five usages (Num Lock, Caps Lock, Scroll Lock, Compose, Kana) as a Variable bitmap: Report
Size 1, Report Count 5. That is 5 bits, and a report is byte-aligned, so a second Output item
of Report Size 3, Report Count 1, Constant supplies the padding. Forget the padding and you
have declared a 5-bit output report where boot protocol defines a one-byte one.

**Collections.** A Collection item groups things and carries a type: Application, Logical,
Physical. A keyboard is one **Application** collection, opened with Usage Page (Generic
Desktop), Usage (Keyboard), Collection (Application) and closed with End Collection. Every
Input and Output item above lives inside it.

Adding a **second top-level** Application collection to this interface is the failure
`#hid-contract` was written to prevent. HID cannot tell two top-level collections' reports
apart without a Report ID, so the moment you add one, report IDs become mandatory — and a
Report ID is a byte prepended to every report, so your eight-byte report becomes nine. Boot
protocol has no concept of a report ID at all. Once again the device works perfectly on a
running desktop and fails in a BIOS. This is why a debug or vendor channel on this adapter
goes on a **separate interface** and never in this collection, which is exactly what the
offered `a-second-interface-for-debugging` lesson does.

**Boot protocol versus report protocol.** A HID keyboard interface declaring subclass 1
supports two protocols, selected by the host with `SET_PROTOCOL`. In **report protocol** the
host fetches your report descriptor, parses it, and interprets your reports according to it —
what a running operating system does. In **boot protocol** the host fetches and parses
nothing: it assumes the fixed 8-byte layout defined in the HID specification's Appendix B —
modifier byte, reserved byte, six key codes — and reads your report as that. A BIOS, a
bootloader and a UEFI setup screen all do this, because a full HID parser is more than they
want to carry.

The consequence for you: **your report descriptor must describe exactly the boot layout.**
Not a compatible one, not a superset — exactly it. If the two disagree the device behaves one
way before the operating system loads and another way after, which is the hardest class of
bug in this course to reason about. TinyUSB will tell you which protocol is currently active
if you ask; it is worth printing on a freeform console line while you experiment.

**Reading it back off the host.** This is the lesson's evidence, and the platforms are not
equivalent. On **Linux**, `/sys/class/hidraw/hidrawN/device/report_descriptor` gives the raw
bytes exactly as the device sent them; on **macOS**, `ioreg -c IOHIDDevice -r -l` exposes
`ReportDescriptor` as raw bytes with no root required. Both are faithful, as is
`hidapitester --get-report-descriptor` cross-platform. On **Windows** the descriptor you can
obtain is **reconstructed** from HID's preparsed data rather than read from the device — it
is semantically close and not byte-identical, and USBTreeView's own documentation notes that
report-descriptor requests usually fail. A Windows learner should borrow a Linux or macOS
host for the byte-for-byte comparison, or accept a semantic comparison and know that is what
it is.

Once you have the bytes, walk them: read the prefix, split it into tag, type and size, take
that many data bytes, name the item, step. Doing it by hand once for the whole descriptor is
the exercise; after that a parser such as `hidrd-convert`, or any of the online HID
descriptor tools, will do it for you and you will be able to tell when it is wrong.

**One thing you must not do.** TinyUSB ships a macro that emits an entire keyboard report
descriptor for you, and using it would hand you the answer to this lesson. Write the items.
Afterwards, by all means expand the macro and compare — any difference is a question worth
answering.

## Concepts to teach

- Item prefix encoding: `bTag`, `bType`, `bSize`, and the 3-means-4 irregularity.
- Main, Global and Local item types, their different lifetimes, and Push/Pop.
- Usage Page and Usage; the Generic Desktop, Keyboard and LED pages.
- Logical Minimum and Maximum, and how their meaning differs between Variable and Array;
  Usage Minimum and Usage Maximum as a Local range.
- Report Size and Report Count, and per-item bit arithmetic.
- The Input item flag byte, and Variable versus Array as the central distinction.
- Constant items as padding; the reserved byte; the LED output bitmap and its padding.
- Collections, collection types, and the second-top-level-collection trap.
- Report IDs: what they are, why this device has none, and what forces one.
- Boot protocol versus report protocol, `SET_PROTOCOL`, and Appendix B's fixed layout.
- The HID class descriptor's report-descriptor length as a promise from lesson 11.
- Platform differences in reading a descriptor back, and Windows' reconstruction.

## Constraints

- Exactly **one** top-level Application collection on this interface.
- **No Report ID item** anywhere in the descriptor.
- The input report is exactly 8 bytes: an 8-bit modifier bitmap, one reserved byte, and six
  one-byte key slots, in that order, per `#hid-contract`.
- The reserved byte must be present and declared as a Constant Input item.
- The modifier region and the key region must use the correct one of Variable and Array
  each; the learner must justify both choices before the lesson completes.
- The output report is exactly 1 byte: five LED bits as a Variable bitmap plus three bits of
  Constant padding.
- The report descriptor must describe exactly the boot keyboard layout, so that boot
  protocol and report protocol see the same thing.
- The descriptor length declared in the HID class descriptor from lesson 11 must equal the
  actual length of the report descriptor, and must be derived from it rather than typed in
  twice.
- The learner writes the items. TinyUSB's ready-made keyboard report descriptor macro must
  not be used to produce the shipped descriptor.
- Stdio stays on UART0, and the lesson 10 `key:` lines keep flowing.
- Still nothing is sent to the host. Sending is lesson 13.

## Suggested progression

1. Establish what is missing: the host knows a keyboard is there and has no idea what its
   bytes mean. Note that this is the only descriptor the *class driver* asks for, not the
   USB core, and that it arrives after `SET_CONFIGURATION`.
2. Before writing anything, dump the report descriptor of an existing USB keyboard or mouse
   on the host, and decode the first three or four items by hand from the prefix rules. Do
   not use a parser yet.
3. Teach the three item types by example from those bytes: point at a Global that is still
   in force several items later, and a Local that was consumed by the next Main item.
4. Pose the Variable/Array question directly, with the two counts — 8 modifiers all of which
   can be held, 100-plus keys of which 6 are reported. Have the learner decide which region
   is which and justify it with arithmetic, before being told.
5. Write the collection open: Usage Page, Usage, Collection (Application). Write End
   Collection immediately so it is never forgotten.
6. Write the modifier item: usage page, usage range, logical bounds, report size, report
   count, Input with the correct flags. Add up its bits out loud.
7. Write the reserved byte item as Constant, and have the learner say what it is for before
   being told. Add up the running total.
8. Write the key array item: logical bounds, usage range, report size, report count, Input
   with the correct flags. Add up the total and confirm 64 bits.
9. Write the LED output items, including the padding. Confirm one byte.
10. Wire the descriptor into the HID class descriptor's length field from lesson 11, derived
    from the array's size rather than typed twice.
11. Flash, plug in, and read the descriptor back off the host. Compare byte for byte with the
    source. On Windows, note explicitly that this comparison is semantic.
12. Walk the retrieved bytes item by item, by hand, out loud. Then run them through a parser
    and compare the two readings.
13. Deliberately delete the reserved byte item, flash, read back, and count the report's
    declared size. Discuss why the desktop would still work and the BIOS would not. Restore
    it.
14. Deliberately swap Variable for Array on one of the two regions, flash, read back, and
    walk a parser's output to see what the host now believes the report means. Restore it.
15. Discuss the second-top-level-collection trap explicitly, without building it: what would
    be forced, what the report length would become, and where it would fail. Note that the
    offered `a-second-interface-for-debugging` lesson is the correct way to want that.
16. Ask TinyUSB which protocol is currently active and print it on a freeform console line.
    Observe that a running desktop has selected report protocol.

## Completion conditions

- The learner reads their report descriptor back off the host and it matches, byte for byte,
  the bytes they wrote — or, on Windows only, matches semantically, with the learner able to
  say why the qualifier is there.
- The learner walks the retrieved descriptor item by item, unaided, naming tag, type, size
  and meaning for each, and their reading agrees with a parser's output.
- The declared input report is exactly 8 bytes and the output report exactly 1 byte, and the
  learner can show the Report Size × Report Count arithmetic for each Input item.
- The modifier region is a Variable bitmap and the key region is an Array, and the learner
  can justify each choice from the counts of possible usages and simultaneous values, without
  reference to this lesson.
- The reserved byte is present, declared Constant, and the learner can say what omitting it
  does and specifically why the failure would not show up on their desktop.
- There is exactly one top-level Application collection and no Report ID item, and the
  learner can state what a second top-level collection would force and what it would break.
- The learner can state the difference between boot protocol and report protocol and why the
  descriptor must describe the boot layout exactly.
- The report-descriptor length declared in the HID class descriptor matches the actual
  descriptor and is derived rather than duplicated.
- The `build-ok` check passes, and the `report-descriptor-sane` check passes: it reads the
  descriptor off the host and confirms the collection structure, the absence of a report ID,
  the field kinds, and the 8-byte input and 1-byte output totals.

## On completion, persist

Record in the instance's `DESIGN.md`/`STATE.md`:

- The final report layout, byte by byte: modifier bitmap, reserved byte, six-slot key array;
  and the one-byte LED output report.
- That the modifier region is Variable and the key region is Array, with the one-line reason
  for each, so a later lesson does not "tidy" one into the other.
- That there is no Report ID and exactly one top-level collection, and that any debug or
  vendor channel must go on a separate interface.
- The report descriptor's length, and that the HID class descriptor derives it.
- That the descriptor describes exactly the boot keyboard layout, and that lesson 18's BIOS
  test is the acceptance test for that claim.
- Which host and which tool were used to read the descriptor back, and whether the comparison
  was byte-for-byte or semantic.

## Optional deeper paths

- Expand TinyUSB's ready-made keyboard report descriptor macro and diff it against the
  hand-written one. Any difference is a question worth answering, and some are historical
  rather than necessary.
- The HID Usage Tables document: how large the usage space is, what a vendor-defined usage
  page is for, and why the offered `a-second-interface-for-debugging` lesson uses one.
- Feature reports — the third kind of Main item — and what `GET_REPORT`/`SET_REPORT` on a
  Feature is used for in real devices. And Push/Pop in a descriptor with several dissimilar
  fields, where saving and restoring the Global state genuinely earns its keep.
- The offered `nkro-without-a-driver` lesson, which adds a bitmap input report for more than
  six keys — and the reason it *adds* rather than replaces: a device that drops boot
  compatibility stops working in a BIOS.
