---
id: 13-your-first-keystroke
title: Your first keystroke
design_refs: [hid-contract, failure-posture]
validators: [build-ok, keystroke-delivered]
---

## Purpose

Make the host type a character your firmware chose — once per press, and then stop.

You have a device that the host believes is a keyboard, that declares an eight-byte report
and knows exactly what every bit of it means, and that has never said a single word. The
host has been politely asking it for a report every few milliseconds since lesson 11 and
getting a shrug every time. This lesson is where the device answers.

It is also the lesson with the most memorable failure in the course. A HID report is not an
event; it is a **snapshot of what is currently held down**. There is no "key up" message in
HID, and there never was. Send one report saying `A` is down and stop, and the host will
believe `A` is down forever, start its own auto-repeat, and type `aaaaaaaa...` into whatever
window has focus until you physically unplug the adapter. Everyone building one of these
does it once. Doing it deliberately, with a text editor open and your finger near the cable,
is much better than doing it by accident at two in the morning — and it teaches
`#events-vs-state` more convincingly than any paragraph can.

## Prerequisites

- Lesson 12 (`12-the-hid-report-descriptor`) complete: the report descriptor is written by
  hand, reads back off the host correctly, declares exactly eight input bytes with no report
  ID, and describes the boot keyboard layout.
- Lesson 11 (`11-descriptors-you-write-yourself`) complete: the device enumerates as a HID
  keyboard with one interrupt IN endpoint, and the learner knows the `bInterval` they chose
  and the poll rate it implies.
- Lesson 10 (`10-scan-codes-to-key-events`) complete: key events arrive as `key:` lines.
  This lesson uses one of them as a *trigger* only, and deliberately does not translate it —
  joining the two halves is lesson 14.
- Stdio on UART0 (`#debug-channel`). It matters more this lesson than any other, because
  from here on the host stops being a source of evidence; see *Theory*.
- A text editor open on the host, on a machine the learner does not mind being typed into,
  and physical access to the USB cable. If the learner took the offered `a-safety-catch`
  lesson after lesson 12, it is worth having armed.

## Learning objectives

- Explain what "interrupt" means in USB — polled, not interrupt-driven — and what that
  implies about your maximum report rate.
- Explain why the TinyUSB device task exists, where it must be called, and what happens if it
  is not.
- Explain why a report may not be sent before the host has configured the device, and how to
  tell when it has.
- Send an eight-byte boot report and check that the send succeeded.
- Explain why one keypress is **two** reports, from the definition of a report rather than
  as a rule to memorise.
- Recover from — and then prevent — a key that types forever.
- Emit `report:` lines on the debug console that later lessons' checks read.

## Theory

**"Interrupt" in USB means polled.** This is the most misleading word in the specification.
An interrupt endpoint does not interrupt the host. The host asks the device, every
`bInterval` frames, whether it has anything; the device either returns a report or NAKs.
There is no mechanism by which a device announces something. USB's one host, one initiator
model from lesson 11 has no exception for keyboards.

Two consequences, and both of them shape the rest of the course:

- Your report rate is bounded by `bInterval`. With 10 ms, the host will collect at most 100
  reports a second. A fast typist at 100 words per minute produces about eight keystrokes a
  second; each keystroke is two reports; that is 16 reports a second against a budget of
  100. Comfortable.
- **Two state changes inside one polling interval are invisible.** Whatever you queue is
  what the host collects, and anything you overwrite before it is collected never happened.
  Hold that thought — it is the entire reason lesson 14 exists, and it is why sending a
  report per PS/2 event is the wrong architecture.

**The device task.** TinyUSB is not interrupt-driven from end to end. The USB hardware
raises an interrupt and TinyUSB's ISR moves events into a queue, but the stack's state
machine — enumeration, control transfer handling, class callbacks, transfer completion —
runs in `tud_task()`, which you must call from your superloop.

The failures here are worth naming precisely, because two of them look like descriptor bugs
and will send a learner back to lesson 11:

- **Not calling it at all.** Enumeration stalls part-way, or completes and the device then
  goes dead, or the host reports a device descriptor request failure. Nothing about the
  symptom points at a missing function call.
- **Calling it once, at startup.** Same thing, slightly later.
- **Blocking inside it, or inside a callback it dispatches.** A `sleep_ms` in a HID callback
  stalls the endpoint. USB has timeouts and the host will eventually decide the device is
  broken. This is the same discipline as "do not do slow work in an ISR" from lesson 04,
  applied to a different kind of callback, and lesson 15 meets it again for real when a
  multi-millisecond PS/2 write is tempting to do inside a USB callback.

The rule is: call it every time round the loop, unconditionally, and do no slow work in
anything it calls.

**Do not speak before you are configured.** A device is not usable until the host has issued
`SET_CONFIGURATION`, and until then its non-zero endpoints do not exist. TinyUSB exposes a
"mounted" predicate for this. It also exposes a "ready" predicate for the HID interface,
which is true when the previous report has been collected and the endpoint is free to accept
another.

Both matter, and the instructive failure is not checking either. The send call will simply
return false, your report will vanish, and — because you were not looking at the return
value — you will conclude that your report descriptor is wrong and spend an hour in lesson
12's territory. **Check the return value of every report send.** A `false` is not an error to
suppress; it is the stack telling you something true about the bus state.

**A report is a snapshot, and that is why a keypress is two of them.** The eight bytes you
send say "these modifiers are currently held, and these up-to-six keys are currently held".
They do not say "a key was pressed". There is no HID message that says a key was released,
because a release is expressed as the key's *absence* from the next snapshot.

So typing one character is:

1. a report with the key's usage in a slot, and
2. a report with that slot empty.

Send only the first and the host's state machine says: the key is still down. After the
host's repeat delay it will start its own auto-repeat — the operating system's, not the
keyboard's — and type the character into whatever has focus. Your own keyboard will not
help; the stuck key is in the host's model of *your* device. The only recovery is to unplug
the adapter.

This is worth doing on purpose, once, with a text editor focused, a hand on the cable, and
no unsaved work anywhere. It makes `#events-vs-state` concrete: reports are snapshots, the
snapshot must be correct at every instant, and any design where the snapshot is assembled
incrementally from events is a design that can leave a key held.

**And `#failure-posture` says: never leave a key held.** Beyond sending the release report,
the host's view of your device can be reset out from under you — the host reboots, the bus
resets, the device is unmounted and remounted. Whatever your firmware believes is down, the
host now believes nothing is. Send an all-zero report when the device mounts, so the two
agree from the first moment. TinyUSB gives you mount and unmount callbacks for this. Lesson
17 makes the rest of the posture real; this is the first instalment, and it costs three
lines.

**A modifier goes in the same report, not a separate one.** If the character you chose is a
capital letter, the report that carries the letter's usage must *also* have the shift bit set
in the modifier byte. Sending shift in one report and the letter in the next is a different
thing entirely — it is two snapshots, and at 10 ms apart the host may well see them as
"shift pressed, then shift released and a letter pressed". Modifiers are part of the same
snapshot as the keys they modify.

**A usage is a position, not a character.** The usage for the key labelled `A` on a US
layout is `0x04`. It is `0x04` on a French AZERTY host too, where it types `q`, because the
host's layout decides what the position means. This is exactly the point lesson 10 made about
scan codes, arriving at the far end of the pipeline. Choose the character you want to see in
your editor, look up the usage for the *position* that produces it on your host's layout, and
be unsurprised when a colleague with a different layout sees something else.

**From here, the host stops being evidence.** This is the boundary the course was designed
around, and it is worth stating plainly at the moment it takes effect. You cannot read your
own keyboard's input reports back from the host:

- Windows' Raw Input Manager opens keyboard top-level collections exclusively, at any
  privilege level.
- macOS gates them behind Input Monitoring *and* a non-exclusive open.
- Chrome's WebHID strips their reports, prunes the collection, and drops the device from
  `requestDevice()` altogether.

So there is no host-side tool that will show you the bytes you sent. Descriptors are
different and stay readable — that is what lessons 11 and 12 did — but reports are not. From
now on the evidence is a human watching a text editor, and the **debug UART**. That is why
`keystroke-delivered` is a manual check, and why every check after it reads the console.

**The `report:` line.** Print every report you send, as eight bytes in hex, space-separated,
exactly as sent:

```
report: 00 00 04 00 00 00 00 00
report: 00 00 00 00 00 00 00 00
```

Print it at the point of *sending*, not at the point of deciding to send, and only when the
send succeeded — the line is meant to be evidence of what went onto the wire. This lesson's
own validator does not read it, but `no-stuck-keys` in lesson 14 does, and it is much easier
to add now than to retrofit.

One honest note: that line is about 24 characters, which at 115200 baud takes roughly two
milliseconds to push out. Inside a 10 ms polling interval that is affordable, and it is also
the first time in this course that your instrumentation costs a measurable fraction of the
thing being measured. Lesson 16 names this properly. Keep it in mind if you later add more
printing and the timing goes strange.

**Something has to cause the keystroke.** The PS/2 side and the USB side are not connected
yet, and connecting them is lesson 14's job. The trigger is yours to choose, but choose one
that a human can cause on demand, because "once per press, and stops" is only observable if
there is a press. The most satisfying option is to use a key *event* from lesson 10 purely as
a trigger — any key down sends your one chosen usage, any key up sends the empty report —
without translating the key. That proves both halves of the adapter are alive in the same
firmware, takes about five lines, and pointedly does not build the translation layer.

## Concepts to teach

- Interrupt transfers as polling; `bInterval` as an upper bound on report rate.
- Why two state changes inside one polling interval are invisible, and the foreshadowing of
  lesson 14.
- The TinyUSB device task: what it does, where it is called, and the three ways to get it
  wrong.
- Not blocking inside the device task or any callback it dispatches.
- Mounted versus ready, and checking the return value of a send.
- A HID report as a snapshot of currently-held state; the absence of any release message.
- A keypress as two reports, derived from the snapshot definition.
- The stuck-key failure, its symptom, and its only recovery.
- Sending a zeroed report on mount, as the first instalment of `#failure-posture`.
- Modifiers as part of the same snapshot as the keys they modify.
- HID usages as positions, and the host's layout as the thing that assigns meaning.
- Why the host cannot show you your own input reports, and what replaces it.
- The `report:` console line and the observer effect of printing it.

## Constraints

- Every report sent is exactly 8 bytes, with no report ID, per `#hid-contract`.
- `tud_task()` is called unconditionally every pass of the superloop, and nothing called from
  it blocks. No `sleep_ms`, no busy wait, no PS/2 transaction inside a USB callback.
- No report is sent before the device is mounted, and the return value of every send is
  checked and acted on.
- A keypress must produce two reports: one with the key present and one with it absent. A
  build that sends only the first must not be left in place at the end of the lesson.
- A zeroed report is sent when the device mounts, so the host's view and the firmware's agree
  from the start.
- If the chosen character needs a modifier, the modifier bit is in the *same* report as the
  key, not a preceding one.
- Every successfully sent report is printed as a `report:` line, eight space-separated hex
  bytes, in the order sent.
- Stdio stays on UART0. The `key:` and `alive:` lines keep flowing.
- No translation from scan codes to HID usages in this lesson. The key event is a trigger and
  nothing more; the translation table and the state model are lesson 14.
- Do not migrate the TinyUSB integration to `hid_composite` in search of an easier API. It
  adds a report ID and a ninth byte.

## Suggested progression

1. Restate the situation: the host has been polling an endpoint that always NAKs since
   lesson 11. Ask what the device would have to do to answer, and establish that it is one
   eight-byte write.
2. Add `tud_task()` to the superloop first, before any report is sent, and confirm the device
   still enumerates and the console still runs. Then *remove* it, flash, and watch what the
   host does — enumeration misbehaving in a way that looks like a descriptor bug. Put it
   back. This inoculation is worth the two minutes.
3. Add the mount and unmount callbacks, printing a freeform line each. Plug and unplug and
   watch them fire. Establish when the device becomes usable.
4. Choose the character. Look up its HID usage for the *position* on the learner's host
   layout, and have the learner say why the usage is a position rather than a character.
5. Choose the trigger — a key event from lesson 10 is recommended — and wire it so a key down
   causes exactly one send attempt.
6. Write the send: build the eight bytes, check mounted and ready, send, check the return
   value, print the `report:` line on success. Do **not** send the release report yet.
7. Open a text editor on the host, focus it, put a hand near the USB cable, and press the
   trigger key once. Watch the character appear and then repeat forever. Let it run for a
   few seconds. Unplug.
8. Debrief before fixing: ask what the host believes, and why the learner's own keyboard
   could not stop it. Arrive at "a report is a snapshot" from the observed behaviour rather
   than from the lesson text.
9. Add the release report on key up. Flash. Repeat the editor test: one character per press,
   and it stops.
10. Read the console: confirm two `report:` lines per press, the second all zeros, and
    confirm the hex matches the character's usage in the expected byte position — which is
    byte 2, because of the reserved byte from lesson 12.
11. Add the zeroed report on mount. Test it by unplugging mid-press and replugging: the host
    must come back believing nothing is held.
12. If the chosen character is a capital, add the modifier bit to the same report and confirm
    the case. Then deliberately send the modifier in a separate preceding report and observe
    that it does not reliably work — a short, cheap demonstration of why the snapshot is
    atomic.
13. Press the trigger key rapidly and watch the `report:` lines. Note whether any send
    returned false and what the learner did about it.
14. Ask the learner to predict what would happen if two different keys went down within one
    polling interval, given that only one report can be collected per interval. Do not solve
    it. Name it as lesson 14's subject and move on.

## Completion conditions

- A character the learner chose appears in a text editor on the host, once per press of the
  trigger, and stops when released. Repeated presses produce repeated single characters.
- The learner has deliberately produced the stuck-key failure, watched the host auto-repeat,
  recovered by unplugging, and can explain in their own words why the host behaved that way
  and why no key on any keyboard could have stopped it.
- Two `report:` lines appear per press on the debug console, eight space-separated hex bytes
  each, the second all zeros, and the learner can point at the byte carrying the usage and
  say why it is in that position.
- `tud_task()` is called every pass of the superloop, and nothing reachable from it blocks.
- No report is sent before mount; every send's return value is checked; a zeroed report is
  sent on mount.
- The learner can state what "interrupt" means in USB, and can compute the maximum number of
  reports per second implied by the `bInterval` they chose in lesson 11.
- The learner can state why the host cannot be used to inspect the reports being sent, and
  what is used instead.
- The `key:` and `alive:` lines are still arriving with USB active.
- The `build-ok` check passes.
- The `keystroke-delivered` check passes: it is a manual check, and the human evidence is the
  character appearing once per press in an editor, with the matching pair of `report:` lines
  on the console.

## On completion, persist

Record in the instance's `DESIGN.md`/`STATE.md`:

- The character chosen, its HID usage, and the host layout it was chosen against.
- The trigger used, and the explicit note that it is a trigger only and that no scan-code to
  usage translation exists yet.
- Where `tud_task()` is called, and the rule that nothing reachable from it may block —
  lesson 15 will be tempted to break this.
- That every send's return value is checked, and what the firmware does on a `false`.
- That a zeroed report is sent on mount, as the first instalment of `#failure-posture`; the
  rest arrives in lesson 17.
- That the `report:` console line is now emitted, its exact format, and that `no-stuck-keys`
  in lesson 14 reads it.
- That the host cannot read this device's input reports back, on any desktop OS, so all
  evidence from here on comes from the debug UART and from a human watching.
- The open question left deliberately unanswered: what happens when two key events occur
  inside one polling interval. Lesson 14 answers it.

## Optional deeper paths

- What the host actually does with a NAK on an interrupt IN endpoint, and how little
  bandwidth an idle keyboard costs a full-speed bus.
- Where the host's auto-repeat lives — it is the operating system's, driven by the state your
  reports establish, and it is configurable per host. Good grounding for why lesson 10
  suppresses typematic repeat rather than forwarding it.
- The offered `a-safety-catch` lesson, which the tutor raises at the start of this one: a
  firmware gate that suppresses HID output until an enable pin is grounded, which makes the
  failure you just produced deliberately harmless to produce accidentally.
- The offered `measure-your-latency` lesson, which instruments this path with a GPIO marker
  and puts a number on keypress-to-report — and shows how easy it is to measure the firmware's
  internal time and call it end-to-end latency.
- `SET_IDLE` and `GET_IDLE`: the HID requests that ask a device to resend its report
  periodically even when nothing changed, why a keyboard is normally set to idle-infinite,
  and what a BIOS sometimes does instead.
