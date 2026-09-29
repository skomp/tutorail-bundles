---
id: 14-events-to-state
title: "Events to state: joining the two halves"
design_refs: [events-vs-state, hid-contract]
validators: [build-ok, no-stuck-keys]
supplies:
  - from: lessons/14-events-to-state/ps2_set2_to_hid.h
    to: include/ps2_set2_to_hid.h
    describe: The complete scan code set 2 to HID usage translation table; lesson 10 had you derive a handful yourself, and this is the rest
---

## Purpose

You have two working halves that have never been introduced, and the obvious way to join
them is wrong in a way your bench will not show you.

Lesson 10 left you with key events on the console — `key: down A`, one line per thing that
happened on the wire. Lesson 13 left you with a host that types a character your firmware
chose, delivered as an eight-byte report the host asks for on a schedule you do not control.
Both halves work. Wiring an event straight to a report compiles, runs, and types correctly at
the speed a person types while watching to see whether it works.

Then someone types properly, and a key sticks. Not always, and not on a key you can name. The
report that would have released it was overwritten before the host collected it, and because
that report described a *change* rather than a *situation*, the change is gone and nothing
will put it back. The host believes the key is held because the last thing you told it was
"this key went down", and you never got to say the other half.

This lesson is the conceptual hinge of the course, and the fix is one sentence: the adapter
holds a key-state bitmap as its single source of truth, and every HID report is a snapshot
built from that bitmap at the moment it is sent. What makes it worth a whole lesson is the
argument under the sentence — why a stream of snapshots survives losing one and a stream of
deltas does not. That argument is not about keyboards, and you will meet it again wherever an
event source faces a state consumer.

## Prerequisites

- `10-scan-codes-to-key-events` — named key-down and key-up events from scan code set 2, with
  the `0xE0` and `0xF0` prefixes handled and typematic repeat recognised for what it is.
- `12-the-hid-report-descriptor` — you wrote the descriptor and can say why the modifiers are
  a bitmap and the six keys are an array, not the other way round.
- `13-your-first-keystroke` — a character arrives on the host, once per press, and stops. You
  know where `tud_task()` is called and what happens when it is not.
- `06-handing-data-to-the-main-loop` — slow work in the main loop, the minimum in interrupt
  context. You use it here unchanged.
- Both receive backends still build, per `#rx-interface`. Nothing here touches either.

## Learning objectives

- Explain the difference between an event protocol and a state protocol, and say which side of
  the adapter is which.
- Explain why a stream of state snapshots tolerates a lost message and a stream of deltas does
  not, without appealing to keyboards.
- Design a key-state bitmap: choose its index space and size, and justify both.
- Derive the modifier bitmap and the six-key array from that bitmap when a report is built,
  rather than accumulating either as events arrive.
- Send a report only on change, and say why "it changed" and "the last send succeeded" are two
  separate conditions.
- Report `ErrorRollOver` on overflow rather than dropping a key in silence.
- Tell your firmware's rollover limit apart from the Model M's own matrix limits, using console
  evidence rather than guesswork.
- Turn an intermittent race into a reproducible one by widening the window it lives in.

## Theory

### Two protocols that disagree about what a message is

PS/2 is an **event** protocol. The keyboard tells you about transitions and nothing else: a
make code means "this key just went down", a break sequence means "this key just came up".
There is no message meaning "these keys are down now". Miss a byte and you have missed a fact
that will never be repeated.

USB HID boot keyboard is a **state** protocol. The eight-byte input report is not a message
about a change; it is a photograph of the keyboard at the instant you built it. Modifier
bitmap, reserved byte, six key slots — a description of a situation. Every report you send
replaces the host's entire picture of your keyboard. The host does not accumulate your
reports; it believes the most recent one.

A device between these two is a transducer, and a transducer needs somewhere to keep the thing
it is transducing. That is the key-state bitmap, which `#events-vs-state` makes the single
source of truth: PS/2 events mutate it, HID reports are snapshots of it, and nothing downstream
of the decoder ever sees a PS/2 event again.

### Why one report per event fails, and why it fails late

The host polls your interrupt IN endpoint every `bInterval` milliseconds — a number you chose
in lesson 11. Between two polls you have one report buffer. Hand TinyUSB a second report
before the host has collected the first and, depending on how you called it, either the call
fails and you throw the report away or the buffered report is replaced and the first is never
seen by anybody.

**Deltas.** Say each report describes what just happened: report one is "A is down", report
two is "nothing is down". Lose report two and the host's last word from you is "A is down". A
types forever. Nothing in the protocol will correct it, because no future message means
"actually, about that earlier one". The only repair is another event — the user pressing and
releasing A again, and hoping that one gets through.

**Snapshots.** Say each report describes the whole situation. Lose report one and the host goes
from "nothing" to "nothing": the keystroke is missing, which is bad but bounded, and the user
retypes. Lose report two and the *next* report you send — and you will send one the moment
anything else changes — also says "nothing down", because it is built fresh from a bitmap in
which A's bit is clear. The error heals itself.

That asymmetry is the whole lesson. A snapshot stream is self-correcting under loss because
every message carries the complete truth; a delta stream is not, because every message is only
meaningful relative to one you may not have received. The fix is therefore not "queue more
carefully" or "make the buffer bigger" — those only reduce how often you lose one. Snapshots
make losing one survivable.

### Making the race reproducible

The failure needs two events inside one polling interval, which needs fast typing, which nobody
does while watching for bugs. It is intermittent by construction — and that suggests a general
technique, worth more than the specific bug. A race that needs two things inside a window is
intermittent because the window is narrow. Widen the window and it stops being a race.

Your polling interval *is* that window, and it is a number in a descriptor you wrote.
Temporarily setting it to tens of milliseconds puts several events inside one interval every
time. The intermittent bug becomes one you can demonstrate on request, explain, fix, and then
demonstrate the absence of. Put the interval back afterwards; a real keyboard does not poll
that slowly.

### The key-state bitmap

One bit per key, indexed by **HID usage ID** and not by scan code. The decoder is the last
place a PS/2 scan code exists; past it the adapter speaks HID. That is what keeps the two
receive backends interchangeable and what will make the offered remapping lesson a change in
one layer instead of two.

The keyboard usage page runs `0x00` to `0xE7` — 232 bits, 29 bytes, round it to 32 and index
with a shift and a mask. That is the obvious representation, not the only one, and you should
be able to say why you chose yours: an array of held usages is smaller and makes report
building trivial, at the cost of a search on every event. Either way the operations are the
same three: set on down, clear on up, read when building a report.

Notice what falls out for free. **Typematic repeat becomes a non-event.** The Model M repeats a
held key by resending its make code several times a second with no break in between. In an
event-per-report design that is a flood of identical reports. In a state design, setting a bit
that is already set changes nothing, so no report is built — and the host does its own
auto-repeat, at the rate its user configured, which is what it wanted all along.

The `held` console key is the population count of that bitmap, and a deceptively strong
diagnostic: type a paragraph, take your hands off, and `held` must be zero. If it is not, a
key's down was recorded and its up was not, and you have found the bug *in your own state*
rather than in the host's — a far better place to find it.

### Deriving the report, every time

The report is built, not maintained. Every field comes from the bitmap at the moment of
building.

- **Byte 0, the modifier bitmap.** The eight modifier usages are `0xE0` to `0xE7` — left
  control, shift, alt, GUI, then the four right-hand ones in the same order. Bit *n* is the
  state of usage `0xE0 + n`. That contiguity is not a coincidence; HID laid the usages out so
  this derivation is a subtraction.
- **Byte 1 is reserved and always zero.** It is not a seventh key slot and it is not yours.
- **Bytes 2 to 7, the six-key array.** Scan the bitmap for set bits *outside* `0xE0`–`0xE7`
  and place up to six. Modifiers must never appear here: a host that sees LeftShift in the
  modifier byte and in the array has been told shift is held twice by two mechanisms with
  different meanings, and you have spent a slot saying what byte 0 already said.

Scan in a fixed order — lowest usage first, say. The array's order is not significant to the
host, but *stability* is significant to you: if one set of held keys can produce two different
orderings, your change detection fires on a difference that is not a change and you send
reports that say nothing.

### Send only on change, and only commit what was sent

Build the eight bytes into a scratch buffer and compare them with the last report you actually
delivered. Identical means do nothing at all — not a duplicate, not a shortened report,
nothing. An unchanged state is not news.

The subtle half is the second condition. "The report changed" and "the report was sent" are
different facts, and you need both before updating your record of what the host believes. If
the send fails because the previous report has not been collected and you update the record
anyway, your next comparison finds no difference and you never send that state again. The host
is permanently stale — and since the lost state was probably a release, you are back to a stuck
key by another route. Record what went out, not what you meant to send.

Where does this run? In the main loop, on the pass that drains the receive queue and services
`tud_task()`. Not in the ISR, not inside the decoder. Draining every available byte and then
building one report is not a shortcut: intermediate states that lasted two hundred microseconds
were never observable by a host polling every millisecond, and collapsing them is exactly what
a state model is for.

### Six keys, and two different reasons you will see fewer

Boot protocol gives you six slots — a property of the eight-byte report, not of your firmware,
and the reason `#hid-contract` exists: a BIOS understands boot protocol and nothing else.

When a seventh non-modifier key goes down, the honest answer is **not** to drop one. HID
defines usage `0x01`, `ErrorRollOver`, for this: put `0x01` in **all six** array slots and send
that. The modifier byte stays valid, since modifiers are a bitmap and do not compete for slots.
The host then knows your device has more keys down than it can describe, which is true, rather
than believing a particular six are held, which is not. Silently dropping the seventh is worse
than useless: it looks like your firmware works, and it loses a keystroke.

You will also meet a second, unrelated limit, and confusing the two will cost you an evening.
**The Model M's matrix blocks some combinations before your firmware ever hears about them.**
It is a scanned matrix without a diode per key, so certain three-key combinations produce
ghosting, which the keyboard's own controller suppresses by refusing to report. The symptom is
that pressing a key produces no `key:` line at all.

So use the console rather than guessing. If the `key: down` line is there and the usage is
missing from your report, the firmware is at fault. If the line never appeared, the keyboard
never sent it and there is nothing to fix — that is a 1986 matrix doing what it was designed to
do, and it is outside this course's scope by explicit decision.

### The rest of the translation table arrives now

`include/ps2_set2_to_hid.h` is in your workspace. The bundle ships it as
`ps2_set2_to_hid.h` beside this lesson, and the runner places it when this lesson opens. It is the complete scan code set 2 to HID
usage translation — every plain make code and every `0xE0`-extended one, with the HID usage ID
and the usage name for each.

It arrives here and not at lesson 10 for a reason worth stating. Lesson 10 had you derive
roughly ten entries from your own captures, because deriving them is where the method is
learnt: what a make code is, what the prefixes mean, how to get from a byte on a wire to a
named key. The remaining hundred-odd entries teach nothing the first ten did not — they are
transcription, which is not this course's subject, so the bundle ships them. This is the first
lesson that needs the whole board. Compare the header against your own handful before you wire
it in: a disagreement is either an error in your derivation or a real difference in your
keyboard, and both are worth knowing.

## Concepts to teach

- Event protocols versus state protocols, and the transducer between them.
- Why a snapshot stream is self-healing under message loss and a delta stream is not — argued
  in general, then applied to this adapter.
- The key-state bitmap as the single source of truth (`#events-vs-state`), indexed by HID usage
  rather than scan code, and what that buys downstream.
- Derivation versus accumulation: the modifier bitmap and the six-key array are computed at
  report-build time, from usages `0xE0`–`0xE7` and from everything outside that range.
- The reserved byte, and why it is not a seventh slot.
- Change detection, the separate condition that the previous report was delivered, and the
  spurious reports an unstable array order produces.
- Typematic repeat as a state no-op, and host-side auto-repeat.
- Six-key rollover and `ErrorRollOver` (`0x01`) in all six slots.
- Matrix ghosting and blocking in the Model M, and telling it apart from a firmware bug using
  the `key:` stream.
- Widening a timing window to make an intermittent race reproducible.

## Constraints

- The key-state bitmap is the single source of truth. Nothing downstream of the decoder may
  consume a PS/2 scan code, and nothing may hold a parallel idea of what is held.
- The modifier bitmap and the six-key array MUST be derived from the bitmap when a report is
  built. Neither may be accumulated as events arrive.
- Byte 1 of the report is always zero, and no modifier usage may appear in bytes 2 to 7.
- No report may be sent when the state it describes is identical to the last report delivered.
- The record of what the host believes may only be updated when a send actually succeeded.
- On overflow, all six array slots carry `0x01` (`ErrorRollOver`). A key is never dropped
  silently.
- The report is built and sent from main-loop context, never from an ISR and never from inside
  the decode path.
- The report stays eight bytes with no report ID, per `#hid-contract`. Nothing here is a reason
  to add a collection or an interface.
- Print `report` as the eight bytes in hex, space-separated, exactly as sent — and only for
  reports that were actually sent. A `report` line for a report the host never received is a
  lie to the check and to you.
- Print `held` as the number of keys currently down in the state bitmap.
- Both receive backends must still build. The interrupt backend is not deleted.

## Suggested progression

1. State in one sentence each what kind of message PS/2 sends and what kind a HID input report
   is. Do not move on until the two sentences disagree with each other.
2. Open `include/ps2_set2_to_hid.h`, now in the workspace, and compare the entries you derived
   in lesson 10 against it, one by one.
3. Resolve any disagreement before wiring anything up, and say which side was wrong and how you
   know.
4. Point your decoder at the full table. Confirm that every physical key — keypad, navigation
   cluster, both shifts, Pause, Print Screen — produces a distinct, correctly named `key:` line.
5. Choose the shape of the key-state bitmap. Say its index space, its size in bytes and why,
   before writing it.
6. Implement set-on-down and clear-on-up, and nothing else. No reports yet.
7. Print `held` as the population count. Type a paragraph, take your hands off, and confirm
   `held` returns to zero. Fix this before building a single report: a bitmap that does not
   settle at zero produces stuck keys however good your report builder is.
8. Hold a key until typematic repeat starts and confirm `held` does not climb. Say why.
9. Now build the wrong thing deliberately, because it is what you would otherwise build by
   accident: one report per key event, describing that event. Type slowly and satisfy yourself
   that it works.
10. Widen the window — temporarily raise the endpoint's polling interval in the descriptor to
    something generous, rebuild, and type at your real speed.
11. Watch the `report` lines while you do. Find the report that should have released a key and
    did not go out, or went out and was overwritten. Write down what you saw.
12. Leave the widened interval in place for now. It is a test fixture, not a bug.
13. Rebuild the output path as a snapshot: a scratch eight-byte buffer filled from the bitmap
    every time, modifier byte derived from `0xE0`–`0xE7`, byte 1 zero, up to six non-modifier
    usages in a fixed order.
14. Add change detection against the last report delivered, updating that record only on a
    successful send. Say out loud what breaks if it is updated unconditionally.
15. Print `report` for sent reports only.
16. Repeat step 10's experiment at the same widened interval. Keys must not stick; explain why
    not, in terms of what one lost report now costs you.
17. Restore the polling interval to the value you chose in lesson 11 and rebuild.
18. Add the overflow path: a seventh non-modifier key down means `0x01` in all six slots.
19. Press seven keys at once and read the `report` line. If fewer arrive than you pressed, look
    at the `key:` lines first and decide whether it is your rollover limit or the matrix.
20. Find a three-key combination your keyboard refuses to report, and name the layer refusing.
21. Type a full paragraph into a text editor on the host and compare it character for character
    with what you intended, capitals and punctuation included.
22. Take your hands off and confirm `held` is zero and the last `report` line is eight zeroes.
23. Run the `build-ok` and `no-stuck-keys` checks.

## Completion conditions

- Typing a paragraph on the Model M produces exactly that paragraph on the host, character for
  character, shifted characters and punctuation included.
- No key ever sticks, at the learner's real typing speed, over a sustained paragraph.
- After typing stops, `held` reads zero and the last `report` line is eight zero bytes.
- Pressing seven non-modifier keys produces a `report` line whose six array slots are all
  `0x01`, rather than one that silently omits a key.
- Holding a key through typematic repeat produces no repeated reports, and the learner can say
  why the host still auto-repeats.
- The learner can state the difference between a stuck key from a lost delta and a missing
  character from a lost snapshot, and say which their design can still suffer.
- The learner can point at a combination their keyboard refuses to report and show, from the
  `key:` lines, that the matrix and not the firmware is refusing.
- The `build-ok` and `no-stuck-keys` checks pass, and both receive backends still build.

## On completion, persist

- The shape of the key-state bitmap: index space, size, and the reason for the choice.
- Where in the main loop the report is built and sent, and what else runs on that pass.
- The polling interval in use, with a note that it was temporarily widened as a test fixture
  and restored.
- The `ErrorRollOver` behaviour, recorded as a decision rather than a detail.
- Any entry where the learner's lesson 10 table disagreed with the supplied header, and how it
  was resolved.
- Any combination the learner's Model M refuses to report, so a later lesson does not chase it
  as a firmware bug.

## Optional deeper paths

- What a host does with `ErrorRollOver` in practice, and why implementations differ.
- Why the modifiers are a bitmap and the six keys an array, revisited now that you have built
  both — and what the report would look like the other way round.
- Ghosting and blocking in a scanned matrix: what a diode per key buys, and why the Model M has
  none.
- Keeping the six-key array in press order rather than usage order, and why some firmwares do.
- The offered `measure-your-latency` lesson, which puts a number on the path you just
  completed, and `nkro-without-a-driver`, which reports more than six keys without losing the
  boot interface.
