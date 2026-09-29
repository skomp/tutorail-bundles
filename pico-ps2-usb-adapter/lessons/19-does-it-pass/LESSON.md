---
id: 19-does-it-pass
title: Does it pass?
design_refs: [hid-contract, failure-posture, deliberately-unresolved]
validators: [enumerates-as-hid, no-stuck-keys, survives-abuse, finished-adapter]
---

## Purpose

Prove that the object you built is a keyboard.

Lesson 18 left you with something soldered, relieved, closed and reporting `alive`
from inside its case. That is an object, and it is not yet an answer. Everything you
know about it you learned on one machine — the one that has seen this VID/PID a
hundred times, has your console attached, and is running an operating system with a
general-purpose HID stack that will forgive a great deal. The claim the course opened
with is bigger than that: plug a Model M into the box and into **any** computer, and
it just types.

Acceptance is turning each requirement of that brief back into a test and running all
of them on a machine that has never seen this device. That includes the one test that
cannot be faked and is the reason lesson 12's report is eight bytes with no report ID:
typing in the host's firmware setup screen, where there is no operating system, no
driver, and nothing but boot protocol. It also includes running lesson 17's robustness
work again — through solder this time, with the case shut and no wire to wiggle.

The second decision `#deliberately-unresolved` left open surfaces here, and it is not
made here: you settled it back at lesson 13 by taking or declining the offered
`a-second-interface-for-debugging` lesson. What this lesson does is **confirm** that
the choice cost nothing, because the acceptance test is designed to pass either way.

## Prerequisites

- Lesson 18 (`18-off-the-breadboard-and-done`): the adapter is on a soldered board in
  a closed enclosure, strain-relieved, brought up in stages, with the debug console
  reachable without desoldering. Every test below is run on *that* object — a
  breadboard passes this list and proves nothing.
- Lesson 17 (`17-robustness-and-the-real-world`): hot-plug, resync, release-on-error,
  suspend, resume, remote wakeup and the watchdog. Several tests below are lesson 17's
  behaviours performed on the finished object, including its deliberate wedge.
- Lessons 11 (`11-descriptors-you-write-yourself`) to 15 (`15-the-lock-leds`): the
  descriptors, the eight-byte report and the lock LEDs are what is being accepted.
- Whether you took the offered `a-second-interface-for-debugging` lesson after lesson
  13. Either answer is a legitimate finished adapter; the list below does not change.
- A **second host machine** that has never had this device plugged into it, and whose
  firmware setup screen you can enter without breaking anything.
- The debug console attached to the closed object, because four of the tests are read
  off it rather than seen on the screen.

## Learning objectives

- Convert the course's original requirements into an explicit acceptance test list,
  and say for each test which requirement it stands for.
- Test in a host's firmware setup screen and explain why boot protocol is what makes
  that work — and why every other test on the list passes with a nine-byte report.
- Confirm which USB interfaces the finished adapter presents, and justify against
  `#hid-contract` why a second *interface* is compatible where a second top-level
  *collection* is not.
- Re-run `#failure-posture`'s behaviours on the soldered object, including triggering
  lesson 17's deliberate wedge and confirming the watchdog returns the adapter without
  a replug.
- Say why a host that has never seen the device, and an hour of warm typing, each
  catch a class of fault that no other test on the list can.

## Theory

### The other open decision: the vendor debug interface

`#deliberately-unresolved` leaves this one to you, and you have already taken it. If
you accepted the offered `a-second-interface-for-debugging` lesson after lesson 13,
your firmware presents a second USB interface carrying a vendor channel; if you
declined, it presents one HID interface. Either is a legitimate finished adapter, and
nothing in this lesson reopens the question — the tutor does not add the interface,
does not remove it, and does not recommend one over the other now that the object is
soldered shut.

What is **not** negotiable is `#hid-contract`: the keyboard interface stays
boot-protocol compatible — subclass 1, protocol 1, **no report ID**, an eight-byte
input report, a one-byte LED output report. A second *interface* does not touch any of
that. A second top-level *collection* on the keyboard interface does: it forces a
report ID, makes the input report nine bytes, and breaks boot protocol *silently* —
the device works perfectly on a running desktop and dies in firmware setup. That is
exactly what the acceptance test below is built to catch, and why the firmware-setup
test is not optional. **The acceptance test must pass either way**, and if it passes
with the second interface present, then the second interface is genuinely harmless —
which is the claim the offered lesson made, and this is where it is verified rather
than believed.

### Acceptance: turning the brief back into tests

The course opened with a promise: plug a Model M into the box and into any computer,
and it just types — no driver, working in a BIOS, lock LEDs lit, and not giving up the
first time something is unplugged. Here is that promise as a test list. A build that
passes all of it is finished.

| # | Requirement | Test |
|---|---|---|
| 1 | works on a machine that has never seen it | plug into the second host, cold, and type |
| 2 | needs no driver | nothing installed, nothing prompted for, working within seconds |
| 3 | is a keyboard, not something claiming to be one | enumerates with your VID/PID and strings, as a boot keyboard |
| 4 | **works in firmware setup** | enter the host's BIOS/UEFI setup and navigate and type in it |
| 5 | types correctly | a paragraph of real text, character for character, capitals and punctuation |
| 6 | lock LEDs follow the host | toggle Caps and Num Lock from the host and from the Model M |
| 7 | starts with no keyboard | power it up with nothing attached, then attach the keyboard |
| 8 | survives keyboard replug | unplug and replug the keyboard, mid-press at least once |
| 9 | survives its own replug | unplug and replug the adapter while typing |
| 10 | survives suspend and resume | suspend the host, wake it **with a keypress**, type immediately |
| 11 | **recovers from a wedge on its own** | trigger lesson 17's deliberate wedge; the watchdog resets it, it comes back typing with neither cable touched, and it says on the console that the watchdog caused the boot |
| 12 | never sticks a key | after every test, `held` is zero and the last report is all zeroes |
| 13 | is stable warm | an hour of real typing, then check `resync` and the dropped counter |

Four deserve a note. **Test 1 is not a formality**: your development machine has seen
this VID/PID, may have cached descriptors, and on some platforms has remembered
decisions about the device — a host that has never seen it is the only honest test of
enumeration.

**Test 4 is the one that cannot be faked, and it is why the whole HID chapter was
shaped as it was.** In firmware setup there is no operating system and no
general-purpose HID stack: the platform uses the **boot protocol**, issuing
`SET_PROTOCOL` with the boot value and then reading a fixed eight-byte report whose
shape it already knows, without parsing your report descriptor at all. This works if
and only if your interface declares subclass 1 and protocol 1 and your input report is
the eight bytes `#hid-contract` specifies, with no report ID. **Every other test on
this list passes with a nine-byte report. This one does not**, and that asymmetry is
why lesson 12's trap was called the central conceptual trap of the chapter. Navigate
with the arrows, use Enter and Escape, and type into a text field — taking care which
field: do not set a firmware password you will not remember.

**Test 11 was proved once already and has to be proved again**, because what lesson 17
proved was that the *firmware* recovers, with the board open, a console in front of
you and a power lead within reach. On the finished object the question is different:
the case is shut, nobody is watching, and the only acceptable recovery is one that
happens without a human unplugging anything. So trigger the same deliberate wedge you
built in lesson 17, hands off both cables, and watch the adapter come back and resume
typing — then read the console and find the watchdog-caused boot reported there,
because a reset nobody can see is indistinguishable from a hang that ended. Test 6 is
the other half of the same check: hammering Caps Lock drives the lesson 15 LED write,
the longest blocking operation the watchdog period was sized against, and if the
period was chosen badly the adapter resets every time a lock key is pressed.

**Test 13 is the one that catches the cold joint**, which is why it is on the list
rather than in a footnote: an hour of typing warms the board, and a `resync` counter
that was zero cold and is not zero warm is a temperature-dependent connection. Lesson
18's cold baseline is the number you compare against, and the console you kept a way
into is how you read it.

## Concepts to teach

- Acceptance testing as converting a brief into a checklist: every requirement becomes
  a test, and a partial run is not an acceptance test.
- Why a fresh host is a different test from a working one — cached descriptors,
  remembered decisions, and a driver stack that may have been doing you favours.
- Boot protocol as what makes the firmware-setup test pass: `SET_PROTOCOL(0)`, a fixed
  eight-byte report, no report descriptor parsed, and why that test alone catches a
  nine-byte report.
- The vendor debug interface as a choice already made, and why a second *interface* is
  compatible with `#hid-contract` where a second top-level *collection* is not.
- `#failure-posture` re-verified through solder: start with no keyboard, resynchronise
  rather than latch, release held keys on every error path, wake the host with a
  keypress.
- The watchdog as an acceptance property and not only a firmware feature: recovery
  with the case shut, no replug, and the reset reported rather than silent — and the
  lock-LED write as the misfire it must *not* produce.
- Faults that only appear warm, and the `resync` counter as the way a cold joint
  announces itself over an hour rather than over a keystroke.
- What the evidence is for each test: the host's screen, the `leds`, `usb`, `ps2`,
  `held`, `report` and `resync` records on the console, and your own eyes on a
  paragraph of text.

## Constraints

- **The firmware is not modified in this lesson.** If a test fails, the fault is in
  the construction or in something an earlier lesson left wrong — find out which
  before changing code, and go back to the lesson that owns it.
- `#hid-contract` is untouched: no report ID, eight bytes, boot subclass and protocol.
  Nothing here changes the descriptors.
- The vendor-interface question is **not reopened**. `#deliberately-unresolved` made it
  the learner's, it was settled at lesson 13, and the tutor neither decides it nor
  treats either answer as the better build. This lesson only confirms that whatever
  the adapter presents, it still passes.
- The acceptance list is run **in full**, on a host that has never seen the device. A
  partial run is not an acceptance test, and a test skipped because "that one already
  worked on the breadboard" is the one most worth running.
- Every test is performed by the learner on the physical object. The tutor reads
  evidence and asks questions; it does not assert a result the learner did not observe.
- Test 11's wedge is triggered deliberately and with both cables left alone. A
  recovery that needed a replug is a failed test, not a passed one with an asterisk.
- The debug console stays reachable with the case closed. If reading `resync` means
  opening the enclosure, lesson 18 is not finished.
- The known non-compliance stands: `#failure-posture` records that the adapter draws
  more than the USB suspend budget because it keeps the Model M alive. Test 10 checks
  that a keypress wakes the host, not that the current is legal.

## Suggested progression

1. Build the list before running it. Have the learner state the course's original
   promise from memory and turn each clause of it into a test they could fail, then
   compare their list with the table above and account for every difference — the
   tests they missed are usually the ones that only fail on a fresh host or when warm.
2. Move to the **second host**, which has never seen this device, and run tests 1, 2,
   3 and 5: cold plug-in, no driver, correct identity, a paragraph checked character
   by character. The `enumerates-as-hid` check reads the identity for test 3; the
   paragraph is read by the learner.
3. **The firmware setup test.** Enter the host's BIOS/UEFI setup with the adapter as
   the only keyboard, navigate with the arrows, use Enter and Escape, and type into a
   text field — avoiding anything that sets a password. Have the learner explain while
   they are in there why it works: `SET_PROTOCOL(0)`, a fixed eight-byte report, no
   report descriptor parsed, and what a ninth byte would do.
4. Run lesson 17's robustness tests on the finished object — tests 7 to 10: boot with
   no keyboard then attach it; unplug the keyboard mid-press and confirm nothing
   sticks; unplug and replug the adapter while typing; suspend the host and wake it
   with a keypress. Each was verified on a breadboard and is now verified through
   solder, with `ps2`, `usb` and `held` on the console as the evidence and
   `survives-abuse` reading it.
5. **Test 11, the wedge.** Trigger lesson 17's deliberate wedge on the closed object,
   touch neither cable, and watch it reset, come back and resume typing. Then find the
   watchdog-caused boot reported on the console and have the learner say what the
   report is for: a recovery nobody can see is a hang as far as the user is concerned.
6. Check the lock LEDs both ways — toggled from the host and from the Model M — and
   treat repeated toggling as the watchdog's misfire test: the LED write is the
   longest blocking operation, and it must not reset the board.
7. Confirm test 12 across everything run so far: `held` at zero, the last `report` all
   zeroes, and the `no-stuck-keys` check agreeing.
8. **Soak.** An hour of real typing, real work if possible, then read `resync` and the
   dropped counter against lesson 18's cold baseline. A counter that was zero cold and
   is not warm sends you back to the joints with a specific suspicion rather than a
   general worry.
9. Confirm the vendor-interface question: have the learner say which interfaces their
   adapter presents and point at the test that would have caught a mistake. If the
   vendor interface is present, the point to make explicit is that the firmware-setup
   test passed *with it present*, and why a second interface is compatible with
   `#hid-contract` where a second collection would not be.
10. Close the course: have the learner trace one keypress end to end out loud — the
    open-drain falling edge, the shifter, the PIO state machine, eleven bits, parity,
    the ring buffer, the scan-code decoder, the key-state bitmap, the eight-byte
    report, the interrupt IN endpoint, the host's poll. If they can do that in front of
    the object they built, they are finished.

## Completion conditions

- The learner produced the acceptance list themselves, from the brief, before running
  it, and can say which requirement each test stands for.
- **All thirteen acceptance tests pass**, run in full on a host that has never seen the
  device. In particular: it enumerates cold with the learner's own VID/PID and strings
  with nothing installed or prompted for, and `enumerates-as-hid` agrees; it types a
  paragraph correctly; the lock LEDs follow the host toggled from both ends; and
  `#failure-posture`'s behaviours hold through solder, including **a keypress waking a
  suspended host**, with `survives-abuse` passing on the finished object.
- **It types in the host's firmware setup screen** — arrows, Enter, Escape and a text
  field — and the learner can explain why boot protocol makes that work and what a
  report ID would have done to it.
- **The deliberate wedge is recovered from with neither cable touched**: the adapter
  resets, comes back and types again on its own, and the watchdog-caused boot is
  reported on the console. Repeated lock-key toggling causes no reset.
- `held` is zero and the last `report` is all zeroes after the whole run, with
  `no-stuck-keys` passing.
- After an hour of typing, `resync` and the dropped counter are compared against lesson
  18's cold baseline, and any rise is investigated rather than noted.
- The learner can state which interfaces the finished adapter presents and why that
  choice is compatible with `#hid-contract`; if the vendor interface is present,
  **every test passed with it present**, the firmware-setup test included.
- The `finished-adapter` validator is satisfied. It is a **manual** check — obviously:
  no script can look at a soldered board in a case and tell you it is trustworthy.

## On completion, persist

Record in the instance's `DESIGN.md`/`STATE.md`:

- The acceptance results: which host, which firmware setup screen, the date, which
  tests needed a second attempt and what fixed them.
- Whether the vendor debug interface is present in the shipped firmware, and that the
  firmware-setup test passed with it.
- The wedge result: how the wedge was triggered, how long the adapter took to come
  back, and the watchdog period it was sized against — the three numbers a future
  reboot loop will be read against.
- The `resync` and dropped-byte counters after the soak, beside lesson 18's cold
  baseline, as the reference a future intermittent fault is compared against.
- Any known non-compliance — the USB suspend current from lesson 17 in particular — so
  the limits are written down rather than rediscovered.
- Anything the acceptance list should have contained and did not, discovered by running
  it. That is the list a second build starts from.

## Optional deeper paths

- **A third host, deliberately different.** A different operating system, a different
  USB controller, a KVM switch or a USB hub in the path. The faults that survive this
  list tend to live in the combinations nobody tried.
- **Leave it plugged in for a month** and then read the counters. The failures lesson
  18 is about take weeks, and time is the only way to know you avoided them.
- **Powering the keyboard through a switch.** Lesson 17 noted the adapter cannot meet
  the USB suspend current budget. A high-side switch on the keyboard's 5 V, opened on
  suspend, is the real answer — and it needs re-probing on resume, which your presence
  state machine already knows how to do.
- **Hand it to somebody else** for a week without telling them what to watch for. An
  acceptance list written by the person who built the object has a blind spot exactly
  where their assumptions are, and a stranger finds it in a day.
