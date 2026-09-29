---
id: a-second-interface-for-debugging
title: A second interface for debugging
design_refs: [hid-contract, debug-channel]
validators: [build-ok, second-interface-live]
optional: true
---

## Purpose

Get a debug channel through USB itself — and learn, by nearly doing it the other way, why that
channel cannot live on the keyboard interface.

Your adapter now types, and a question becomes natural: the host is already connected to this
device, so why should reading its internal state need a second Pico, a UART and a debug probe?

It need not, and the route runs straight through the most expensive mistake in `#hid-contract`.
There are two ways to add "another thing to report" to a HID device. One adds a second top-level
collection to the interface you already have, which forces a report ID, which makes your input
report nine bytes, which breaks boot protocol — **silently**, working perfectly on your desktop
and failing in the BIOS, the one place you are least likely to test. The other adds a second
**interface**, which costs a little descriptor bookkeeping and costs your boot report nothing.

Along the way you meet the constraint that shaped this whole course: a host cannot read the input
reports of a keyboard top-level collection. Not as root, not as admin, not from a browser. That
is why the course validates over a UART, and why a vendor interface is a real answer rather than
a clever workaround.

## Prerequisites

This lesson stands alone. It assumes a device that types and nothing about what you were doing
when the tutor offered it.

- Lesson 13 (`13-your-first-keystroke`) complete: a chosen character appears on the host once per
  press and stops, and `keystroke-delivered` has passed.
- Lessons 11 and 12 complete, with `enumerates-as-hid` and `report-descriptor-sane` passing — you
  will be editing the configuration descriptor you wrote by hand, and it needs to have been right
  before you started.
- The UART console still connected and working. Nothing here replaces it, and you will want it
  while the descriptors are in flux.
- A host you can run a small program on, and the ability to install a HID library or tool —
  `hidapi` and `hidapitester` on any of the three platforms, or Chrome for WebHID. Installing it
  is your work and needs the network. On Linux, either root for `/dev/hidraw*` or a udev rule
  granting your user access; writing that rule is part of the lesson.

## Learning objectives

- Describe a composite USB device as one device with several interfaces, each binding its own
  driver.
- Distinguish a second **interface** from a second **top-level collection**, state exactly what
  the latter forces, and explain why a report ID makes a boot keyboard fail in firmware setup
  while working on a running desktop.
- Write a vendor-defined HID report descriptor on a usage page in `0xFF00`–`0xFFFF`.
- Update `bNumInterfaces`, `wTotalLength`, interface numbers and endpoint addresses consistently
  when adding an interface by hand, and serve per-instance report descriptors from a HID stack
  that now has two instances.
- State why no desktop OS lets a host program read a keyboard collection's input reports, and
  name the mechanism on each of the three platforms.
- Say why this channel does not replace the UART console, with reference to `#debug-channel`.

## Theory

**A composite device is not exotic.** One device has one configuration, and that configuration can
contain any number of interfaces. The host binds a **driver per interface**, not per device. Your
keyboard interface binds the OS's HID keyboard driver; a second interface can bind something else
entirely, independently. On Windows this needs the USB composite parent driver, which loads
automatically for a device with more than one interface and `bDeviceClass` 0 — which yours
already is. No driver to install and no `.inf` to sign, and no Interface Association Descriptor
either, because each of your interfaces is standalone rather than two halves of one function.

**Two interfaces or two collections: the fork in the road.** Inside a HID interface, the report
descriptor can declare one or more **top-level collections**. That is a real feature and it is how
a keyboard-with-media-keys ships as one interface. It also has a consequence that is easy to walk
into:

> With more than one top-level collection on an interface, the host must be able to tell one
> report from another on the single interrupt IN endpoint they share. The only mechanism HID has
> for that is a **report ID** — a byte prefixed to every report on that interface.

So adding a debug collection beside the keyboard collection is not additive. It reaches back and
changes the keyboard's reports:

```
[report ID][modifiers][reserved][key 1..6]     ← nine bytes
```

`#hid-contract` is explicit about the cost. Boot protocol specifies an 8-byte report with **no
report ID**; a BIOS does not parse your report descriptor at all — it sends `SET_PROTOCOL(boot)`
and reads eight raw bytes in a fixed layout. Give it nine with an ID in front and it reads your
modifier byte as the report ID, your reserved byte as the modifiers, and your keys shifted by one
— or, more often, simply does not work.

**Why that failure is the worst kind.** A running desktop uses *report* protocol: it parsed your
descriptor, knows about the report ID, and handles it correctly. So the device works on your
development machine, passes every test you thought to run, and fails in firmware setup — which you
next visit in lesson 18, days later, and which offers no error message of any kind.

**The answer: a second interface.** Interface 1 gets its own report descriptor, its own interrupt
IN endpoint, and optionally an interrupt OUT for host-to-device commands. Report IDs stay off
interface 0 entirely, and the keyboard's report descriptor is byte-for-byte what lesson 12
produced — so `report-descriptor-sane` keeps passing unchanged, which is the check to watch,
because it is the one that tells you whether you have quietly broken the contract.

**Vendor-defined usage pages.** HID usage pages `0xFF00` to `0xFFFF` are vendor-defined: the
specification deliberately declines to say what they mean. No operating system ships a class
driver for them, and that is exactly the property you want — **nothing claims the interface**, so a
userspace program can open it. The descriptor is short:

```
USAGE_PAGE (Vendor Defined 0xFF00)
USAGE      (0x01)
COLLECTION (Application)
    USAGE           (0x02)
    LOGICAL_MINIMUM (0)
    LOGICAL_MAXIMUM (255)
    REPORT_SIZE     (8)
    REPORT_COUNT    (N)          ← N bytes of device state, host-bound
    INPUT           (Data, Var, Abs)
    ...                          ← optionally an OUTPUT item for host-to-device commands
END_COLLECTION
```

`REPORT_SIZE (8)` with `REPORT_COUNT (N)` is N opaque bytes. You decide what they mean and nothing
in the host's stack cares, which is the whole appeal.

**The other instructive failure: you cannot read the keyboard interface.** Before reaching for a
second interface, the obvious idea is to read the keyboard's own input reports from a host program
and skip all of this. It does not work, on any desktop OS. Verified 2026-09-29:

- **Windows.** The Raw Input Manager opens keyboard top-level collections **exclusively**, at every
  privilege level. An administrator's `CreateFile` on that collection fails with a sharing
  violation. There is no flag, and elevation does not help.
- **macOS.** Keyboard collections are gated behind the Input Monitoring privacy permission *and*
  require a non-exclusive open; without both, `IOHIDManager` will not deliver their input values.
- **Chrome WebHID.** It strips reports from keyboard top-level collections, prunes the collection
  from the device it hands you, and — if that collection is all the device has — drops the device
  from `requestDevice()` entirely, so the user is never offered it.

This is not an obstacle to route around; it is why the course validates through the debug UART
rather than the host, and why the vendor interface is a genuine engineering answer. A vendor usage
page has none of those protections applied, because none of it is the OS's business.

**This does not replace the UART, and `#debug-channel` still stands.** A debug channel running over
USB lives *inside the artefact under test*. When enumeration is broken — exactly when you most want
to see inside — the USB debug channel is broken too, and so is every check that reads it. The UART
console is outside the experiment, which is the entire reason lesson 00 chose it. What the second
interface buys you is a channel that works **in the field**, on a finished adapter plugged into
someone else's computer with no debug probe anywhere near it.

**The bookkeeping you have to get right.** `bNumInterfaces` goes from 1 to 2. `wTotalLength` must
now cover *everything* following the configuration descriptor — both interface descriptors, both
HID descriptors, all endpoint descriptors — and it is wrong more often on the second edit than the
first. The new interface takes `bInterfaceNumber` 1, class 3, and **subclass 0 and protocol 0**,
because it is not a boot device. Endpoint addresses must not collide: keyboard IN stays `0x81`,
vendor IN goes to `0x82`, a vendor OUT to `0x02`. Its HID descriptor declares the length of *its*
report descriptor, not the keyboard's. And in TinyUSB, `CFG_TUD_HID` becomes 2 and the
report-descriptor callback is handed an **instance index** — returning the keyboard's descriptor
for both instances is the most common bug here, and it produces a device with two keyboard
interfaces, one of which does nothing, which looks almost right and is not.

**What to send.** Anything the console already knows: frames received, the `resync` count, queue
drops, the compiled-in receive backend, keys held, the raw key-state bitmap. Aim for something
that **changes while you type**, which is what makes it evidence rather than a snapshot.

## Concepts to teach

- Composite devices: one configuration, several interfaces, one driver binding per interface;
  `bDeviceClass` 0 and the Windows composite parent; why no IAD is needed here.
- HID hierarchy: interface → report descriptor → top-level collection(s) → reports, and the
  report-ID consequence — more than one top-level collection forces a report ID onto **every**
  report on that interface, so boot protocol's fixed 8-byte, no-report-ID contract is broken and
  fails in firmware setup while working on a desktop: the silent failure of `#hid-contract`.
- Vendor-defined usage pages `0xFF00`–`0xFFFF`, that no OS claims them, and how to write one:
  usage page, usage, application collection, logical min/max, report size and count, INPUT and
  optional OUTPUT items.
- Descriptor bookkeeping across two interfaces: `bNumInterfaces`, `wTotalLength`,
  `bInterfaceNumber`, class/subclass/protocol on a non-boot interface, endpoint allocation, and
  per-instance callbacks in a HID stack with two instances.
- Why a host cannot read a keyboard collection's input reports, with the mechanism named on
  Windows, macOS and Chrome WebHID — and why this channel is therefore additive to the UART
  console rather than a replacement for it (`#debug-channel`).

## Constraints

- **Interface 0 does not change.** It stays the boot-protocol keyboard: class 3, subclass 1,
  protocol 1, no report ID, 8-byte input report, 1-byte LED output report.
  `report-descriptor-sane` must keep passing on exactly the bytes lesson 12 produced.
- The debug channel goes on a **second interface**, never a second top-level collection on
  interface 0. If your keyboard input report is nine bytes at any point, stop and go back.
- The new interface uses a **vendor-defined usage page** and declares subclass 0 and protocol 0; a
  standard usage page invites a class driver to claim the interface. Endpoint addresses must be
  unique across both interfaces.
- The UART console stays, keeps printing everything it printed before, and remains the channel
  every existing check reads. No PS/2 or key-handling behaviour changes; the device types exactly
  as before.
- Nothing on the main path may come to depend on this interface. The design leaves it deliberately
  unresolved whether the finished adapter carries it, and lesson 18's acceptance test must pass
  either way.
- If the offered `a-safety-catch` gate is present, the new interface must not become a way around
  it. The gate guards keyboard output; the vendor interface must not carry keystrokes.

## Suggested progression

1. State the goal in one line: a channel the host can read, on an interface of its own, with the
   boot report left exactly as it is.
2. Before writing any descriptor, try the obvious thing and let it fail. Install a HID tool and
   attempt to open your **keyboard** interface and read its input reports. Note precisely what your
   OS does — a sharing violation, a permission prompt, a device not even offered — and connect it
   to the mechanism named above for your platform.
3. Now try the other shortcut on paper only: sketch the keyboard report descriptor with a second
   top-level collection added, and count the bytes of the resulting input report. Nine. Say out
   loud which host would notice and which would not.
4. Decide the payload: pick the state values worth sending and fix their byte layout. Write the
   layout down before writing the descriptor — you need it on the host side and the two must agree.
5. Write the vendor report descriptor: vendor usage page, a usage, an application collection, an
   INPUT item of the right size and count. Add an OUTPUT item only if you want host-to-device
   commands.
6. Add the second interface descriptor, its HID descriptor and its endpoint descriptor(s) to your
   configuration descriptor, by hand, as in lesson 11.
7. Fix the bookkeeping: `bNumInterfaces` to 2, `bInterfaceNumber` 1, subclass and protocol 0,
   non-colliding endpoint addresses. Recompute `wTotalLength` and check it against the actual
   number of bytes you return — by counting, not by trusting last time's macro.
8. Set the HID stack to two instances and make the report-descriptor callback return the right
   descriptor for each. Verify by enumeration rather than by reading your own code: a device whose
   second interface serves the keyboard descriptor enumerates successfully and is wrong.
9. Build and enumerate. Confirm the host shows **two** HID interfaces on one device, that the
   keyboard still types, and that interface 0's report descriptor is unchanged, its input report
   eight bytes, with no report ID anywhere on it.
10. Send something on the vendor endpoint, periodically or on change, from your main loop — not
    from an interrupt and not from a USB callback.
11. Write or run a host-side reader that opens the **vendor** interface, filtering by usage page
    rather than interface number, which is more portable. On Linux this is where you write the
    udev rule.
12. Confirm the numbers change as you type and agree with the same values on the UART console. Two
    independent channels reporting the same state is a stronger claim than either alone.
13. Break it once on purpose: return the keyboard's report descriptor for instance 1 and see what
    the host makes of the device. Then put it back. This is the bug you would otherwise spend an
    evening on later.
14. Test boot protocol for real: reboot the host into firmware setup with the adapter attached and
    type. If it works, the second interface has cost you nothing, which was the objective. If it
    does not, a report ID crept in somewhere.
15. Decide and record whether this interface stays in the build you take to lesson 18.

## Completion conditions

- The `build-ok` check passes, and the device enumerates with **two** interfaces: interface 0 the
  boot keyboard, interface 1 a vendor-defined HID interface with its own endpoint.
- The learner reads **live, changing device state** over interface 1 from a host program or tool,
  and the values change as they type and agree with the same values on the UART console.
- Interface 0 is unchanged: class 3, subclass 1, protocol 1, **no report ID**, an 8-byte input
  report. `report-descriptor-sane` passes on the same bytes as before, `enumerates-as-hid` still
  passes, and the adapter types exactly as it did.
- The learner states what a second top-level collection on interface 0 would have forced, how many
  bytes the input report would have become, and **which host would have failed and which would
  not** — ideally having confirmed the good case by typing in firmware setup.
- The learner names, for their own platform, the specific mechanism that prevented them reading the
  keyboard interface's input reports from the host.
- The learner can say why the UART console remains the course's validation channel, in terms of the
  debug channel living inside or outside the artefact under test.
- The `second-interface-live` check passes, finding the vendor interface on the host and reading a
  report from it.

## On completion, persist

Record in the instance's `DESIGN.md`/`STATE.md`:

- That this instance's firmware carries a **second, vendor-defined HID interface**, with its usage
  page, interface number, endpoint addresses and the byte layout of its report. Any later lesson
  touching the configuration descriptor must keep `wTotalLength` and `bNumInterfaces` right, and
  needs that layout written down.
- That interface 0 remains boot-protocol clean and carries no report ID — stated explicitly,
  because this is the invariant every later change risks, and the BIOS test is what catches a
  regression in it.
- That the deliberately unresolved choice is settled for this instance one way or the other: whether the
  finished adapter in lesson 18 carries this interface. Lesson 18's acceptance test must pass
  regardless. The UART console remains the validation channel; the vendor interface is an addition
  for field diagnostics.

## Optional deeper paths

- **Make it bidirectional.** Add an interrupt OUT endpoint and an OUTPUT item, and accept commands
  from the host: dump the key-state bitmap, reset the drop counters, switch receive backends at run
  time. Note where the handler must run — the same rule as lesson 15's LED report, that slow work
  does not happen inside a USB callback.
- **A WebHID page.** Chrome will open a vendor usage page from an ordinary web page with a user
  gesture, which means a diagnostics dashboard with no installed software — and the same page
  cannot see your keyboard collection, by design. While you are there, dump the descriptors of a
  gaming keyboard and find its vendor interface; most of them have one.
- **Report IDs done properly.** Write a scratch build that *does* use two top-level collections with
  report IDs, purely to watch the mechanism work, then test it in firmware setup so you have
  witnessed the failure rather than been told about it. Keep it out of the firmware you care about.
