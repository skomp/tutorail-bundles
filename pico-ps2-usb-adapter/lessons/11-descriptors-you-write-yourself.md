---
id: 11-descriptors-you-write-yourself
title: Descriptors you write yourself
design_refs: [hid-contract]
validators: [build-ok, enumerates-as-hid]
---

## Purpose

Answer the questions a host asks a device it has never seen before, by writing the answers
by hand, in bytes, and then reading them back off the host.

Half of this adapter now works. Bytes come off the keyboard, get framed in a PIO state
machine, cross into the main loop without loss, and turn into named key events. The other
half does not exist. Plug the Pico into a computer today and the computer sees a mass
storage bootloader or nothing at all, and there is no path from a `key: down A` line to
anything a text editor would recognise.

That path starts with a conversation. When you plug any USB device into any computer, the
host interrogates it — who are you, how much current do you want, what class of thing are
you, what endpoints do you have, what should I call you in the device list — and the device
answers from a set of byte arrays it was compiled with. Those arrays are its *descriptors*.
Every USB device you have ever used has them. This lesson is where a USB device stops being
a mystery, and the only way through is to write the bytes yourself rather than copy a
header. Nothing here is checked by the compiler; a descriptor with a wrong length field
compiles perfectly and produces a device that enumerates as nothing.

## Prerequisites

- Lesson 00 (`00-first-code-and-a-window-in`) complete, and specifically: stdio goes out
  over **UART0** to the second Pico, not over USB. `#debug-channel` made that decision for
  exactly this lesson. From here to lesson 15 the USB peripheral belongs to the artefact
  under test, and a learner who put `printf` on USB loses their diagnostic channel at the
  precise moment enumeration starts failing.
- Lesson 10 (`10-scan-codes-to-key-events`) complete: key events on the console. Nothing here
  consumes them yet — the two halves are joined in lesson 14 — but the firmware must keep
  producing them while USB is added.
- `device.env` filled in from lesson 00, including the VID and PID you will use.
- A host you can plug the Pico into and do not mind experimenting with, and a build you can
  flash quickly — you will flash many times. On macOS, expect the Keyboard Setup Assistant to
  appear once the device enumerates as a keyboard; it asks you to press keys you cannot yet
  send. Dismiss it.

## Learning objectives

- Describe the USB bus model: one host, addresses, endpoints, and the four transfer types,
  and say why a keyboard uses control plus interrupt and neither of the other two.
- Walk the enumeration conversation from port reset to `SET_CONFIGURATION`, naming what the
  host asks for at each step and why in that order.
- Explain the self-describing byte-stream structure every descriptor shares, and decode the
  first two bytes of any descriptor without reference material.
- Write the device, configuration, interface, HID and endpoint descriptors by hand, and say
  what each field is for.
- Explain what `wTotalLength` covers, and why it is the field most likely to be wrong.
- Explain why string descriptor index 0 is not a string.
- State why a made-up VID is not an option for anything that leaves the bench, and what the
  pid.codes test pair is for.
- Read your own descriptors back off the host and compare them with what you wrote.

## Theory

**One host, and the device never speaks first.** A USB bus has exactly one host. Every
transfer on it is initiated by the host; a device with something to say waits to be asked.
This is not a detail — it is why a keyboard is *polled*, why your report rate will be bounded
by a number you choose in this lesson, and why lesson 14 has the problem it has. The one
exception, remote wakeup signalling in lesson 17, proves the rule: it is electrical
signalling on the bus, not a transfer.

**Addresses.** A freshly-attached device responds on address 0. The host assigns it a unique
address between 1 and 127 early in enumeration and talks to it there from then on. Hubs make
this workable by enabling one port at a time, so only one device is ever at address 0.

**Endpoints and transfer types.** An endpoint is a numbered, directional buffer in the
device. Endpoint 0 is special: it exists on every device, it is bidirectional, and it carries
the *control* transfers that enumeration is made of. Everything else you declare.

The four transfer types:

| Type | Guarantees | Used here |
|---|---|---|
| Control | delivery, with a defined request/response structure | yes — EP0, enumeration and all class requests |
| Interrupt | bounded latency, guaranteed delivery, small payloads | yes — one IN endpoint for your reports |
| Bulk | delivery, no latency guarantee, whatever bandwidth is left | no |
| Isochronous | guaranteed bandwidth, **no retry** | no |

Bulk is wrong because it has no latency bound: your keystroke would arrive eventually, behind
a file copy. Isochronous is wrong for a reason worth sitting with — it does not retry a
failed transfer, because it is built for audio and video where a late packet is worthless. A
dropped keystroke is not worthless; it is a bug. Interrupt is the only type offering both a
latency bound and retry, which is why every keyboard, mouse and gamepad uses one.

**Full speed, frames, and `bInterval`.** The Pico's USB is full speed, 12 Mbit/s, and a
full-speed bus is divided into 1 ms *frames*. For a full-speed interrupt endpoint,
`bInterval` is expressed directly in frames, 1 to 255 — so 10 means "poll me as often as
every 10 ms". This is where a high-speed habit bites: on high speed, `bInterval` is an
exponent and the period is 2^(bInterval−1) × 125 µs, so the same numeral means something
completely different. A `bInterval` that contradicts the transfer type and speed is one of
this lesson's named failures, and the symptom is a device that works at a rate you did not
choose.

**The enumeration conversation.** Roughly, and in this order:

1. The host detects the attachment electrically and resets the port.
2. `GET_DESCRIPTOR(Device)` — only the first 8 bytes, because the host does not yet know how
   large this device's control transfers may be, and byte 7 is `bMaxPacketSize0`.
3. A second port reset, then `SET_ADDRESS` — the device moves off address 0.
4. `GET_DESCRIPTOR(Device)`, all 18 bytes this time.
5. `GET_DESCRIPTOR(Configuration)` — the first 9 bytes, to learn `wTotalLength`.
6. `GET_DESCRIPTOR(Configuration)` again, for `wTotalLength` bytes: this returns the
   configuration descriptor *and everything under it* as one blob.
7. String descriptors, for whichever indices the previous descriptors referenced.
8. `SET_CONFIGURATION` — the device becomes configured and its non-zero endpoints come alive.
9. The class driver binds and asks its own questions. For HID that means
   `GET_DESCRIPTOR(Report)`, which is lesson 12's entire subject.

Notice that every step depends on a length or an index from the step before. That is why a
wrong length field does not produce a wrong field — it derails the conversation.

**Descriptors are a self-describing byte stream.** Every descriptor, of every kind, starts
the same way: byte 0 is `bLength`, the total length of this descriptor in bytes, and byte 1
is `bDescriptorType`. A parser walks the blob by reading `bLength` and stepping forward.
That is the entire structural rule, and it means you can decode any descriptor you are
handed, from any device, with nothing but the type numbers. Type 1 is Device, 2 is
Configuration, 3 is String, 4 is Interface, 5 is Endpoint, and the HID class adds 0x21 for
its own descriptor and 0x22 for the report descriptor.

**The device descriptor**, 18 bytes, one per device. `bcdUSB` is the version claimed, as
binary-coded decimal. `bMaxPacketSize0` is the control endpoint's packet size — 64 on the
RP2040. `bcdDevice` is your own version number. `iManufacturer`, `iProduct` and
`iSerialNumber` are *indices* into the string descriptors, not strings, with 0 meaning "no
string". `bNumConfigurations` is 1.

The field to think hardest about is `bDeviceClass`, with its subclass and protocol: **set all
three to 0**, meaning "the class is defined at the interface level". Putting 3 (HID) here is
a common mistake and a meaningful one — HID is an *interface* class and is not defined at the
device level at all.

**The configuration descriptor and the blob.** The configuration descriptor is 9 bytes, but
`GET_DESCRIPTOR(Configuration)` does not return 9 bytes. It returns the configuration
descriptor followed by every interface, class and endpoint descriptor beneath it,
concatenated. `wTotalLength` is the length of that **whole blob**, not of the configuration
descriptor.

This is the field most likely to be wrong, and its failure mode is instructive. Too small,
and the host stops reading before it reaches your endpoint descriptor: the device enumerates,
the interface appears, and it has no endpoints, so the class driver has nothing to bind to.
Too large, and the host asks for bytes you do not have, and the control transfer stalls or
returns rubbish. In both cases the device is *present* and useless, which is far more
confusing than a device that does not appear. Compute the value from the sizes of the
structures you are concatenating — never by counting on paper — and remember the descriptor
lengths are spec constants: configuration 9, interface 9, HID 9, endpoint 7.

Two other fields deserve thought. In `bmAttributes`, bit 7 must be set (a historical
requirement) and bit 5 is remote wakeup, which `#failure-posture` requires and lesson 17
makes work — deciding now whether to claim it is reasonable. `bMaxPower` is in **2 mA units**
and is not a formality here: the Model M is powered from VBUS, so your adapter really does
draw the keyboard's current through this port, and you measured it in lesson 01. Declare
enough to cover it; the maximum expressible is 250, meaning 500 mA.

**The interface descriptor** is where `#hid-contract` becomes bytes: `bInterfaceClass` 3
(HID), `bInterfaceSubClass` 1 (boot), `bInterfaceProtocol` 1 (keyboard), `bNumEndpoints` 1.

Get `bInterfaceClass` wrong — leave it 0, or make it 0xFF for vendor-specific — and **no
driver binds**. The device enumerates perfectly, appears in the host's USB tree with your
strings and VID/PID, and does absolutely nothing. The host offers no error, because from its
point of view nothing went wrong: a device with no matching class driver is a normal thing to
have on a bus. This is the failure that sends people back to check their wiring.

**The HID descriptor** sits between the interface and endpoint descriptors: class-specific, 9
bytes, type 0x21, declaring `bcdHID`, a country code (0 for "not localized"), and — the field
that matters — the type and **length of the report descriptor** the host should ask for next.
Lesson 12 writes that descriptor; here you declare how long it will be, and the two must
agree. A mismatch makes the host request the wrong number of bytes, and the parse fails
downstream as a device with no usable collections.

**The endpoint descriptor**, 7 bytes: `bEndpointAddress` with the direction bit set for IN,
`bmAttributes` saying interrupt, `wMaxPacketSize` — 8, because `#hid-contract` fixes an
8-byte report — and `bInterval`.

**String descriptors, and the one that is not a string.** Index 0 is special: it is not text
but a list of 16-bit language identifiers the device supports (0x0409 for US English). Every
other index is a string in **UTF-16LE**, preceded by the usual `bLength` and
`bDescriptorType`, with no NUL terminator. Two failures live here. First, providing indices
1, 2 and 3 but no index 0: hosts differ in how they react, and the symptom is "my names do
not show up" rather than anything pointing at index 0. Second, `bLength` counts **bytes**,
not characters, so *n* characters means `bLength` of 2*n* + 2 — being out by a factor of two
truncates your product name in a way that looks like a firmware bug.

**Your VID and PID, and why you may not invent one.** A vendor ID is assigned by the USB
Implementers Forum to an organisation, for money. It is an identity claim on a shared bus.
Making one up does three bad things: it collides with a real vendor's, so a host may apply
that vendor's quirks to your device; it makes your device indistinguishable from theirs in
every bug report and driver database; and it is, straightforwardly, using someone else's
name. `#hid-contract` therefore fixes the development pair as **pid.codes `1209:0001`**,
allocated explicitly for exactly this and explicitly not for distribution. If this adapter
ever leaves your bench, pid.codes will allocate a real product ID under VID 0x1209 for an
open-source project — that is the route, and it is free. Put whichever pair you are using in
`device.env`; the `enumerates-as-hid` check reads it from there.

**TinyUSB's shape.** TinyUSB does not generate your descriptors. It calls back into your code
and asks for them: one callback returns the device descriptor, one the configuration blob,
one a string descriptor by index and language. You provide the byte arrays. Add the TinyUSB
device library and a `tusb_config.h` to your build, and initialise the stack. Base this on
the **`hid_boot_interface`** example and not on `hid_composite`: `hid_composite` carries a
report ID, which makes the input report nine bytes where `#hid-contract` says eight, and
lesson 12 would then be counting a different number than the one you have.

One thing you are *not* doing yet is sending anything. At the end of this lesson the host has
a keyboard on the bus that has never said a word, and sits there polling an endpoint that
always NAKs. That is the correct state.

**Reading your descriptors back.** This is the lesson's evidence, and a host hands a device's
descriptors over freely. It is also the last time the host is a rich source of evidence:
reading a keyboard's *input reports* back is blocked on every desktop OS, which is why every
check from lesson 13 onward reads the debug UART instead. Descriptors remain readable.

On **Linux**, `lsusb -v -d <vid>:<pid>`, or the `descriptors` file in the device's sysfs
directory for the raw bytes. On **Windows**, Device Manager for the basics and USBTreeView
for the descriptors. On **macOS**, `system_profiler SPUSBHostDataType` — note the name;
`SPUSBDataType` returns an empty array on macOS 26 and is absent from `-listDataTypes`
entirely, so if you find it in a blog post, the blog post is old.

## Concepts to teach

- USB bus topology: one host, hubs, host-initiated transfers only; address 0 and
  `SET_ADDRESS`.
- Endpoints as directional numbered buffers; endpoint 0 as the mandatory control endpoint.
- The four transfer types, and the reasoning that excludes bulk and isochronous here.
- Full speed, 1 ms frames, and `bInterval` in frames rather than microframes.
- The enumeration sequence, and why each step needs the one before it.
- `bLength` / `bDescriptorType` as the universal descriptor header.
- The device descriptor field by field, including why `bDeviceClass` is 0.
- The configuration blob and `wTotalLength`; `bmAttributes`, and `bMaxPower` as a real
  current declaration for this project.
- Interface class, subclass and protocol, and what a wrong class does.
- The HID class descriptor and its report-descriptor length field.
- Endpoint direction, attributes, packet size and interval.
- String descriptors, UTF-16LE, byte-counted lengths, and index 0 as a language list.
- VID/PID as an identity claim, and pid.codes.
- TinyUSB's descriptor callbacks, and `hid_boot_interface` as the reference example.

## Constraints

- Stdio stays on UART0. Do **not** enable USB stdio in the build. `#debug-channel` is not
  negotiable and the console-reading checks depend on it.
- Exactly one configuration, one interface, one interrupt IN endpoint. No second interface
  on the main path; the offered `a-second-interface-for-debugging` lesson adds one properly.
- `bDeviceClass`, `bDeviceSubClass` and `bDeviceProtocol` are 0.
- `bInterfaceClass` 3, `bInterfaceSubClass` 1, `bInterfaceProtocol` 1, per `#hid-contract`.
- `wMaxPacketSize` on the IN endpoint is 8. No report ID anywhere.
- `wTotalLength` must be derived from the sizes of the descriptors actually in the blob, not
  hand-counted into a literal.
- `bMaxPower` must cover the current measured in lesson 01 for the keyboard plus the Pico.
- VID/PID must be the pair recorded in `device.env`. A VID invented by the learner is not
  acceptable even temporarily.
- A language-ID descriptor must exist at string index 0.
- The descriptors are written by the learner. Do not copy a descriptor header from an
  example project and edit the strings.
- Base the TinyUSB integration on `hid_boot_interface`, not `hid_composite`.
- The lesson 10 decoder keeps running and keeps printing `key:` lines throughout. Adding USB
  must not cost the console.

## Suggested progression

1. Establish the goal precisely: at the end of this lesson the host lists a keyboard with
   the learner's own name on it, and that keyboard has never sent a byte. Sending is lesson
   13.
2. Before any code: plug in some existing USB device and dump its descriptors with the
   host tool for the learner's OS. Walk one descriptor by `bLength` and
   `bDescriptorType` and find the next one. The structure should be concrete before they
   write any.
3. Add TinyUSB to the build: the device library, a `tusb_config.h`, stack initialisation.
   Confirm the firmware still boots and the `alive:` and `key:` lines still appear on UART.
   A build that enumerates nothing but still talks on the console is the right checkpoint.
4. Write the device descriptor. Discuss `bDeviceClass` = 0 explicitly — ask what 3 there
   would mean, and let the learner find that it means nothing defined.
5. Fill in VID/PID from `device.env`, and have the learner say in their own words why they
   may not pick their own numbers. Cover what pid.codes is and what `1209:0001` is for.
6. Write the string descriptors, including index 0. Get the `bLength` arithmetic right by
   reasoning about bytes versus characters rather than by trial.
7. Flash and plug in. The device should appear on the host with its VID/PID, though very
   possibly with no strings or no function yet. Read it back with the host tool.
8. Write the configuration, interface, HID and endpoint descriptors as one blob, with
   `wTotalLength` computed from the structure sizes.
9. Flash and plug in again. Read the whole configuration blob back off the host and compare
   it field by field with what was written, including `wTotalLength`.
10. Deliberately break `wTotalLength` — make it short by 7 bytes, exactly losing the endpoint
    descriptor — flash, and observe what the host reports: an interface with no endpoints and
    no error message anywhere. Restore it. This is the most valuable five minutes of the
    lesson.
11. Deliberately set `bInterfaceClass` to 0xFF, flash, and observe that the device enumerates
    completely and binds nothing. Note that the host's device list looks *fine*. Restore it.
12. Check `bMaxPower` against the lesson 01 measurement and adjust if it was guessed.
13. Confirm on the host that the device now appears as a HID keyboard, with the learner's
    manufacturer and product strings, and that macOS's Keyboard Setup Assistant (if it
    appeared) can be dismissed.
14. Read the full descriptor set back one last time and have the learner narrate it,
    descriptor by descriptor, without looking at their source.

## Completion conditions

- The host enumerates the device with the VID/PID from `device.env` and with the learner's
  own manufacturer, product and serial strings visible in the host's device listing.
- The device binds as a HID keyboard: `bInterfaceClass` 3, `bInterfaceSubClass` 1,
  `bInterfaceProtocol` 1, with one interrupt IN endpoint of 8-byte maximum packet size.
- The learner reads the complete configuration blob back off the host and matches it,
  descriptor by descriptor, against the bytes they wrote — including `wTotalLength`.
- The learner can explain what `wTotalLength` covers and can describe, from having seen it,
  what a short `wTotalLength` does to the host's view of the device.
- The learner can explain what a wrong `bInterfaceClass` does, and why it produces no error.
- A language-ID descriptor exists at string index 0, and the learner can say why it is not a
  string.
- The learner can state why a made-up VID is unacceptable for anything distributed, and what
  `1209:0001` is for.
- The learner can say what an endpoint is — a numbered, directional buffer in the device — what
  makes endpoint 0 different from the ones they declared, and what a device's address is,
  including what it is before the host assigns one.
- The learner can say why a keyboard uses control plus interrupt transfers and neither of the
  other two: bulk carries no latency bound, so a keystroke arrives behind whatever else is on
  the bus; isochronous does not retry a failed transfer, and a dropped keystroke is a bug rather
  than a late video frame; interrupt is the only type that offers a latency bound and delivery
  together.
- The `key:` and `alive:` lines are still arriving on the UART console with USB attached.
- The `build-ok` check passes.
- The `enumerates-as-hid` check passes: it finds the device on the host by the VID/PID in
  `device.env` and confirms the interface class, subclass, protocol and endpoint.

## On completion, persist

Record in the instance's `DESIGN.md`/`STATE.md`:

- The VID/PID in use and where it came from, with the note that it is a development pair and
  not for distribution; and the manufacturer, product and serial strings chosen.
- The endpoint address, transfer type, packet size and `bInterval` chosen, and the resulting
  poll rate in hertz — lesson 13 and lesson 14 both reason about that number.
- The declared `bMaxPower` and the lesson 01 measurement it is based on.
- That `wTotalLength` is computed from structure sizes, so a later lesson adding a descriptor
  does not have to remember to update a literal.
- That the report descriptor's declared length in the HID descriptor is a promise lesson 12
  must keep.
- That stdio is on UART0 and must stay there, and that the TinyUSB integration is based on
  `hid_boot_interface` and must not be migrated to `hid_composite`.

## Optional deeper paths

- The offered `watch-the-enumeration` lesson, which shows this conversation as packets rather
  than inferred from its results. USB packet capture does not work on macOS with SIP enabled,
  so it needs a Linux or Windows host, or the third-Pico sniffer route that lesson describes.
- Composite devices and `bNumInterfaces` greater than 1: interface association descriptors,
  and why a debug channel is a second *interface* and never a second collection. The offered
  `a-second-interface-for-debugging` lesson builds it.
- Bus-powered versus self-powered devices, what happens when a hub's current budget is
  exceeded, and why a Model M on a passive hub is a real risk.
- USB 2.0 chapter 9: more readable than its reputation, and section 9.6 is the descriptor
  definitions you have just been writing from memory.
