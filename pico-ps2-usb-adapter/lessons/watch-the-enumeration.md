---
id: watch-the-enumeration
title: Watch the enumeration
design_refs: [hid-contract]
validators: [enumeration-captured]
optional: true
---

## Purpose

See the enumeration conversation as packets, in order, with your own descriptor bytes in the
data stages — instead of inferring that it happened from the fact that your device appeared.

**This lesson needs a Linux or Windows host. USB packet capture does not work on macOS.**
Verified on macOS 26.6.2 with SIP enabled: no `XHC*` capture interface exists, and although
`AppleUSBHostPacketFilter.kext` is present and loads, it never instantiates. The only documented
route is disabling SIP from Recovery, which this course will not ask for. If your only machine
is a Mac, decline now — or read *Optional deeper paths*, where a third Pico does the job without
the host's cooperation. Nothing on the main path depends on any of it.

In lesson 11 you wrote every descriptor byte by hand and proved they were right by reading them
back off the host. That is a proof by result: the answers were correct, so the questions must
have been asked. You never saw the questions, their order, or what happened between them.

That gap matters the next time enumeration fails. A device that does not appear gives you
nothing to read back, and "it did not enumerate" is the absence of a diagnosis rather than one.
A capture turns it into one: the host got eight bytes of the device descriptor and gave up; it
assigned an address and nothing answered at it; it asked for string index 0 and got a stall.
This lesson gets you the tool while your device is *working*, which is the only sensible time to
learn an instrument.

## Prerequisites

This lesson stands alone. It assumes a device that already enumerates and nothing about what you
were doing when the tutor offered it.

- Lesson 11 (`11-descriptors-you-write-yourself`) complete: the host enumerates your device with
  your own VID/PID (the pid.codes development pair `1209:0001`, per `#hid-contract`) and your own
  strings, and `enumerates-as-hid` passes.
- A **Linux or Windows** host you can install a capture tool on, with administrative rights —
  root or the `usbmon` group on Linux, an administrator account and a reboot on Windows — and
  Wireshark installed. Installing it is your work and needs the network.
- The ability to unplug and replug the adapter: the capture must be running before the device
  appears.
- The UART debug console still connected. Not the subject here, but it tells you
  the firmware is alive while the host says nothing.

## Learning objectives

- Describe a USB transaction as token, optional data and handshake, and decode an 8-byte SETUP
  packet field by field into the request it represents.
- Name the enumeration sequence in order, and say why the device descriptor and the
  configuration descriptor are each fetched twice.
- Start a capture before the event, and explain why one started afterwards is empty of everything
  interesting; identify your own device in a capture of a whole bus, by the bytes you wrote.
- State plainly what a keyboard-bus capture records about your own typing, and take the
  precautions that follow.
- Distinguish a kernel-level URB capture from a wire-level one, and name what the former cannot
  show.

## Theory

**USB is a bus the host drives.** A device never speaks unprompted. Every exchange begins with a
**token** packet from the host naming an address, an endpoint and a direction; most then carry a
**data** packet and end with a **handshake** — `ACK` if the data arrived, `NAK` if the device had
nothing or was not ready, `STALL` if it is refusing. A device with nothing to say `NAK`s every
`IN` token, tens of thousands of times an hour, which is why an idle keyboard is not an idle bus.

**Control transfers have three stages,** and all of enumeration is control transfers on endpoint
0: a **setup stage** (a `SETUP` token and exactly eight bytes of request), an optional **data
stage** carrying the payload — for `GET_DESCRIPTOR`, the descriptor itself — and a **status
stage**, a zero-length packet in the opposite direction, which is how the device says "done" or,
by stalling, "no".

**The eight bytes of SETUP** are the sentence the host speaks, and are worth reading without a
dissector:

| Offset | Field | Meaning |
|---|---|---|
| 0 | `bmRequestType` | direction (bit 7), type (standard/class/vendor), recipient |
| 1 | `bRequest` | `0x06` `GET_DESCRIPTOR`, `0x05` `SET_ADDRESS`, `0x09` `SET_CONFIGURATION` |
| 2–3 | `wValue` | for `GET_DESCRIPTOR`, descriptor type in the high byte, index in the low |
| 4–5 | `wIndex` | interface or endpoint number, or a language ID for string descriptors |
| 6–7 | `wLength` | how many bytes the host will accept in the data stage |

So `80 06 00 01 00 00 40 00` reads: device-to-host, standard, recipient device;
`GET_DESCRIPTOR`; type `0x01` (device), index 0; no language ID; up to 64 bytes. You will see
that exact request, and you should recognise it before Wireshark tells you what it is.

**The sequence.** A freshly plugged device answers at **address 0**, the well-known address every
unconfigured device responds to. The host resets the port; asks for the **device descriptor**,
needing only its first eight bytes because byte 7 is `bMaxPacketSize0` and no longer conversation
is correct without it; resets again on many hosts, which is legal and is why your firmware must
not treat a reset as a fault; sends **`SET_ADDRESS`** — whose status stage completes at the *old*
address, and only then does the device move; re-reads the **full device descriptor** at the new
address; asks for the **configuration descriptor** twice, nine bytes to learn `wTotalLength` and
then that many; asks for **string descriptors**, index 0 first, which is not a string but the
list of language IDs; sends **`SET_CONFIGURATION (1)`**, at which point the endpoints come alive;
then the HID class driver takes over with `GET_DESCRIPTOR (Report)`, usually `SET_IDLE` and
`SET_PROTOCOL`; and finally polls your interrupt IN endpoint at the `bInterval` you declared,
collecting `NAK`s until you have a keystroke.

Every failure lesson 11 warned about is a specific break in that list. A wrong `wTotalLength`
shows as the second configuration request returning fewer bytes than the descriptors need; a
missing language-ID descriptor at index 0 as a stall where the strings should be; a
`bInterfaceClass` no driver claims as a sequence that completes perfectly and is followed by
silence.

**The failure you will meet first: capturing too late.** Enumeration is over in about a tenth of
a second and happens **once**. Plug the device in and then start capturing, and you get an
uninterrupted stream of `IN` tokens and `NAK`s and no descriptors at all, and conclude the tool
is broken. It is not. **Start the capture, then plug the device in.** If it is already plugged
in, unplug and replug, or unbind and rebind it on the host so the port is reset.

**The hazard, stated plainly: a keyboard-bus capture is a keylogger.** Once your adapter is
typing, its interrupt IN reports carry the HID usage code of every key you press, and a capture
writes them to a file. This is not theoretical and it is not a joke. On Windows, USBPcap attaches
to a **root hub** and captures every device below it — usually including the keyboard you
actually type on; on Linux, `usbmon0` captures **all buses at once**, with the same result. A
password typed while a capture runs is in the pcap, in the clear, trivially decodable. So:
capture the **specific bus your adapter is on**; stop as soon as you have the enumeration, which
needs about a second of traffic; type nothing you would not publish while it runs; and **delete
the pcap afterwards** rather than pasting it into a chat, an issue or a gist.

**Route: Linux, usbmon.** A kernel facility exposing USB traffic as capture interfaces. Load it
with `modprobe usbmon`; Wireshark then lists `usbmon1`, `usbmon2` and so on, one per bus, plus
`usbmon0` for all of them — the one you must not use. `lsusb` tells you which bus your device is
on, though you must plug it in once to find out and unplug it again before capturing. Non-root
capture needs your user in the group your distribution puts on `/dev/usbmon*`, or a `setcap` on
dumpcap; running Wireshark as root is the wrong answer and it will say so.

**Route: Windows, USBPcap.** It installs a kernel filter driver and appears in Wireshark's
interface list as the root hubs it can attach to. Two real warnings. **It is old and it is a
kernel driver** — last released in 2020, with an open bug-check report against Windows 11 25H2,
and a kernel filter driver that faults takes the machine with it. And **it attaches at the root
hub, not the device**, so pick the hub your real keyboard is not on; if everything hangs off one
hub, use a different machine.

**What your tool actually shows you.** Both capture **URBs** — the kernel's requests to its own
USB stack — not electrical packets. You will see setup, data and status stages; you will not see
token packets, `NAK`s, start-of-frame markers, bit stuffing, or the retries the host controller
performed for you. Same shape of limitation as the analyser's fixed threshold: **the instrument
has already decided what is visible.** For enumeration the URB view is exactly right, because
the request sequence is what you came for.

## Concepts to teach

- Host-driven polling; an idle device `NAK`s continuously; transactions as token / data /
  handshake; the three stages of a control transfer, including the zero-length status stage.
- The 8-byte SETUP packet decoded field by field, with `GET_DESCRIPTOR`, `SET_ADDRESS` and
  `SET_CONFIGURATION` worked through.
- Address 0; that `SET_ADDRESS`'s status stage completes at the old address; why the device
  descriptor is read twice (`bMaxPacketSize0`) and the configuration descriptor twice
  (`wTotalLength`); string descriptor index 0 as a language-ID list rather than text.
- Enumeration failures as specific breaks in the sequence, tied back to lesson 11; and capture
  ordering, because the capture must precede the plug-in and enumeration happens once.
- **The keylogger hazard** of capturing a bus carrying a keyboard, and the concrete precautions.
- usbmon and USBPcap: how each attaches, what scope it captures, what privilege it needs, and
  USBPcap's age and stability risk. URB capture versus wire capture, and what each cannot show.

## Constraints

- Capture only **your own machine's** USB traffic, on the bus your adapter is on. Never
  `usbmon0`, and on Windows never the root hub carrying the keyboard you type on. Delete the
  capture file when the lesson is finished, unless it was deliberately taken on a machine set
  aside for the purpose.
- The firmware does not change here, and neither does any descriptor. If reading the capture
  reveals a mistake, that is a fix in lesson 11's files and it must leave `enumerates-as-hid` and
  `report-descriptor-sane` passing.
- The capture must be of **your own device**, with your VID/PID and your strings. A capture of a
  commercial keyboard is a different and easier exercise and does not complete this lesson.
- `#hid-contract` is not up for renegotiation. This lesson observes the enumeration of the single
  boot-protocol HID interface; it does not add one.

## Suggested progression

1. State the goal in one line: lesson 11 proved the answers, and now you watch the questions.
2. Confirm which host you are using, and that it is not a Mac. If it is, stop and either decline
   or read the deeper path about the Pico sniffer.
3. Install Wireshark and the capture back end — a kernel module you load on Linux, an installer
   and a reboot on Windows.
4. Read the hazard section back, and say out loud which bus or hub carries the keyboard you type
   on and which one you will capture instead.
5. Plug the adapter in once to find its bus and device number, then unplug it.
6. Select the capture interface for that bus only, start the capture with the adapter
   **unplugged**, plug it in, wait two seconds, stop.
7. Find your device. Not by address, which you do not yet know — search for your VID and PID, or
   a string you chose, and work outwards from the packet you find.
8. Locate the first `GET_DESCRIPTOR` for the device descriptor and read its eight setup bytes **by
   hand** before looking at Wireshark's decode. Then check yourself against it.
9. Note that request's `wLength` and the bytes actually returned, find `bMaxPacketSize0` in them,
   and say why the host wanted it before anything else.
10. Find `SET_ADDRESS`, read the address out of `wValue`, and confirm that transfers after it use
    that address and transfers before it use 0.
11. Find the two configuration-descriptor requests. Read `wTotalLength` from the first response
    and confirm the second asks for exactly that many bytes — lesson 11's field, doing its job.
12. Find the string requests. Confirm index 0 returns a language ID and not text, then find your
    product string in UTF-16LE and read it.
13. Find `SET_CONFIGURATION` — everything after it is the device working — and then the HID class
    requests that follow, noting their different `bmRequestType`.
14. Find the first `IN` transactions on your interrupt endpoint, measure the interval, and compare
    it with the `bInterval` you declared.
15. Meet the failure deliberately: start a fresh capture with the device already plugged in and
    look at what you get. Say why in one sentence, then say what you would do if the device were
    soldered into something you could not unplug.
16. Walk the whole sequence back in order from your notes, and for each step say what a failure
    there would look like from the host's side.
17. Stop the capture, close Wireshark, delete the file.

## Completion conditions

- The learner presents a capture **of their own device** — identifiable by the VID/PID and strings
  from lesson 11 — taken on a Linux or Windows host, containing the enumeration and not merely
  steady-state traffic.
- The learner walks the request sequence in order, naming the first truncated device-descriptor
  request, `SET_ADDRESS`, the full device descriptor, both configuration-descriptor requests, the
  string descriptors including index 0, and `SET_CONFIGURATION`.
- The learner decodes at least one `SETUP` packet **by hand**, field by field, and agrees with the
  dissector.
- The learner explains why the device descriptor is requested twice (`bMaxPacketSize0`) and the
  configuration descriptor twice (`wTotalLength`), and points at the address in `SET_ADDRESS`,
  showing transfers before and after it using different device addresses.
- The learner can state, having seen it, what a capture started after plug-in contains and why,
  and names at least one thing their tool cannot show because it captures URBs, not wire packets.
- The learner states the keylogger hazard in their own words, names which bus or hub they
  deliberately avoided, and confirms the capture file is deleted.
- The `enumeration-captured` check passes. It is manual: the tutor looks at the capture and hears
  the walkthrough.

## On completion, persist

Record in the instance's `DESIGN.md`/`STATE.md`:

- That USB capture is available to this learner, on which host and with which tool, so a later
  lesson can suggest reaching for it — and that the learner can read a `SETUP` packet unaided.
- The device address the host assigned, and the polling interval actually observed, compared with
  the declared `bInterval`. Useful if the offered latency lesson is taken later, where the polling
  interval must be held constant.
- That the capture file was deleted; or, if one was deliberately kept, where it is, so it can be
  dealt with at the end of the course.

## Optional deeper paths

- **A third Pico as a passive sniffer.** The route that works on any host, macOS included,
  because it needs no cooperation from the host: a third Pico sits across the D+/D− pair of a
  full-speed link, decodes it in PIO, and emits a pcap. Conspicuously on-theme — the peripheral
  from lesson 07 reading the bus from lesson 11 — and unlike usbmon it sees the wire, so tokens,
  `NAK`s and start-of-frame markers all appear. The course does not assume a third Pico, so this
  is a path and not a requirement.
- **Break something on purpose.** In a scratch copy of the firmware, set `wTotalLength` wrong and
  capture again; watching a host react to a malformed descriptor is the fastest way to learn what
  that failure looks like. Then watch a real keyboard enumerate on a bus that is not carrying
  your typing — commercial keyboards are frequently composite devices, which is good preparation
  for the offered `a-second-interface-for-debugging` lesson. Or sleep the host with the adapter
  attached and capture the suspend and resume, which is the traffic lesson 17 makes your firmware
  handle. USB 2.0 chapter 9 defines every request you have watched and is unusually readable with
  a capture open beside it.
