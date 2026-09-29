---
id: 10-scan-codes-to-key-events
title: Scan codes to key events
design_refs: [wire-format, events-vs-state]
validators: [build-ok, key-events-decoded]
---

## Purpose

Turn the byte stream your receiver produces into key-down and key-up events for every
physical key on your Model M — including the two keys that do not play by the rules.

Everything so far has been about getting bytes off a wire intact. You have them: framed,
parity-checked, queued, popped in the main loop, and arriving through a PIO state machine
that costs the CPU almost nothing. What you do not have is any idea what they *mean*. A
`frame: 1c ok` line tells you a byte arrived. It does not tell you a key went down, and it
certainly does not tell you which one, because a single keypress on this keyboard can be
one byte long, two bytes, four bytes, or eight.

The pressure comes from the other end. In three lessons the USB side will need to answer
the question "which keys are down right now". That question cannot be answered from a byte
stream. It can only be answered from a set of *events* applied to a piece of *state*, and
this lesson builds the event half. It is also the lesson where the temptation to trust a
table you found on the internet is strongest and most expensive, because roughly half of
the scan-code tables on the web describe a different scan code set than the one your
keyboard is sending, and the resulting decoder is wrong in a way that looks right.

## Prerequisites

- Lesson 08 (`08-ps2-receive-in-pio`) complete: bytes arrive through the PIO backend and
  through the interrupt backend, both behind the one receive interface from
  `#rx-interface`, and `frame:` lines appear on the debug console for keys you press.
- Lesson 06 (`06-handing-data-to-the-main-loop`) complete: the main loop pops bytes
  non-blockingly from the ring buffer, and the drop counter stays at zero under fast
  typing. This lesson's decoder lives on the main-loop side of that queue, never in the
  ISR or in the PIO IRQ path.
- Lesson 03 (`03-see-the-protocol-before-you-decode-it`) complete: you can capture a keypress
  on the logic analyser and read the bytes out of the trace. You will need that skill again,
  because for two keys the console is harder to read than the trace.
- Lesson 00 (`00-first-code-and-a-window-in`) complete: the debug console on UART0 works and
  `checks/_console.py` can read it. This lesson adds a new line key to it.
- Useful but not required: lesson 09 (`09-talking-back-in-pio`), because you have seen the
  keyboard's response bytes and will need to keep them out of the decoder.

## Learning objectives

- Explain what a scan code is — a position in the keyboard's matrix — and why it is
  neither a character nor a HID usage.
- State the difference between scan code set 1 and scan code set 2, and say exactly what a
  set-2 break code looks like.
- Decode the `0xF0` break prefix and the `0xE0` extended prefix, in the correct order, as
  states in a state machine rather than as keys.
- Handle the two fixed sequences that do not follow the make/break rule at all: Pause and
  Print Screen.
- Recognise typematic repeat and suppress it, rather than emitting a stream of new presses.
- Derive about ten scan codes from your own keyboard, by pressing keys and reading your own
  console — and know why the course hands you the rest instead of asking you to type them.
- Emit `key:` lines on the debug console that the `key-events-decoded` check can read.

## Theory

**A scan code is a position, not a letter.** The Model M's controller does not know what is
printed on its keycaps. It scans a matrix of rows and columns, finds the intersection that
closed, and sends the number of that intersection. The key labelled `A` on a US Model M
sends `0x1C`; on a German board with the same controller that position is still `0x1C` and
only the legends moved. This is the same principle that governs USB HID three lessons from
now, where the host — not your firmware — decides what a position means. Your decoder's job
is to name positions consistently, not to produce characters.

`#wire-format` fixed the rest at the beginning: the keyboard stays in **scan code set 2**
and the adapter never asks it to switch. Set 2 is what a PS/2 keyboard sends at power-on,
and asking for set 1 or set 3 would mean a command exchange, a failure path and a second
table, for nothing.

**Make and break.** In set 2, pressing a key sends its **make code**. Releasing it sends
`0xF0` followed by the *same* make code. Press `A`, and the wire carries `1C`. Release it,
and the wire carries `F0 1C`. That is the whole rule for most of the board.

**The rule that is not the rule, and why it costs you half the keyboard.** A great many
scan-code references — books, wiki pages, forum answers, and a large fraction of the code
you will find on the internet — state that a break code is the make code with bit 7 set.
That is **scan code set 1**, the set the original IBM PC/XT used and the set your PC's
legacy keyboard controller translates *to*. In set 1 the break of `A` (make `0x1E`) is
`0x9E`. In set 2 it is not.

A decoder built on that assumption does not fail cleanly. It fails partially, which is
worse:

- Every `0xF0` is consumed as if it were a key, so most keys never produce an up event at
  all, and the host — once you get there — believes everything you ever pressed is still
  held down.
- Set 2 has make codes that already have bit 7 set. `F7` is `0x83`. A decoder that reads
  bit 7 as "this is a release" will never report `F7` going down, and will instead report
  an up event for whatever key it thinks `0x03` is — which on a set-2 keyboard is `F5`.
- Bit 7 is also set on bytes that are not scan codes at all. The keyboard answers commands
  with `0xFA` (acknowledge), `0xFE` (resend) and `0xAA` (self-test passed, which you saw in
  lesson 09). A decoder that masks bit 7 and looks up the remainder will happily invent key
  events out of a power-on self test.

So you will meet this failure if you reach for the familiar rule, and the symptom will be
"most of it works". Test the release path deliberately.

**The `0xE0` extended prefix.** The original AT keyboard's code space filled up, and the
keys added afterwards — the right-hand modifiers, the arrow cluster, the navigation cluster,
the keypad's `Enter` and `/`, and the GUI keys — were given codes prefixed with `0xE0`. The
byte after the prefix deliberately collides with an existing unprefixed key:

| Bytes on the wire | Key |
|---|---|
| `14` | Left Control |
| `E0 14` | Right Control |
| `75` | Keypad 8 |
| `E0 75` | Up arrow |
| `5A` | Enter |
| `E0 5A` | Keypad Enter |

`0xE0` is **not a key**. It is a modifier on the *next* code, and in your decoder it is a
state, not a table lookup. A decoder that emits `key: down E0` has made the mistake this
lesson is built to make you meet.

**Prefix order on a break.** Releasing an extended key sends `E0 F0 <code>` — extended
prefix first, then break prefix, then the code. Not `F0 E0 <code>`. A decoder whose state
machine accepts the two prefixes in either order will appear to work and will mis-handle
one of the two arrangements for a key that never actually sends it; a decoder that assumes
the wrong one will lose every extended key's release. Read the order off your own capture
rather than believing this paragraph.

**Pause, which sends no break at all.** Pause is a fixed eight-byte sequence with its own
prefix:

```
E1 14 77 E1 F0 14 F0 77
```

It arrives in one burst the moment the key goes down, and releasing the key sends nothing.
Two things follow. First, `0xE1` is a third prefix and a third state in your machine.
Second, if you ignore `0xE1` and let the rest fall through your normal path, the sequence
contains `14` (Left Control) and `77` (Num Lock) and their breaks — so an incomplete decoder
reports a phantom Control press and a phantom Num Lock press every time Pause is touched.
For a correctly-behaved key event, your decoder has to *synthesise* the up event, because
the keyboard will never send one.

**Print Screen, which pretends to be Shift.** Print Screen's make is `E0 12 E0 7C` and its
break is `E0 F0 7C E0 F0 12`. The `12` is Left Shift's make code, and it is there for
compatibility with a decades-old convention about `Shift+PrtSc`. A decoder that processes
the sequence one prefixed code at a time reports a Left Shift press and release around every
Print Screen. Worse, the sequence *changes* when a modifier is already held: with Control
down, or with Alt down (where the key is labelled SysReq), your keyboard sends something
shorter and different. Capture what *your* Model M actually does in each case rather than
taking a table's word for it — this is the single strongest argument in the course for
deriving from the hardware in front of you.

**Typematic repeat.** Hold a key down and the keyboard, after about half a second, begins
resending the make code roughly eleven times a second until you let go. There is no `0xF0`
between them. On the wire, a repeat is indistinguishable from a new press — because at the
scan-code layer it *is* a new press.

It is not a new key event, though, and this is where `#events-vs-state` first bites. If you
emit `key: down A` eleven times a second with no `up` between them, the `key-events-decoded`
check will see ten unmatched downs and fail, and it will be right to. The fix is that your
decoder already has to know which keys are currently down, so that a make code for a key
that is already down is recognised as a repeat and produces nothing.

That "which keys are currently down" set is the seed of the key-state bitmap that
`#events-vs-state` names as the single source of truth for the whole adapter — you are
building the first version of it here, and lesson 14 makes it authoritative. Do not pass
repeats through to a later layer "in case it wants them": the host generates its own
auto-repeat from the state you report to it, and a repeat that reaches the host as a fresh
press produces doubled characters.

**The shape of the thing you are writing.** A small state machine, fed one byte at a time
from the receive interface, with states along the lines of idle, saw-`E0`, saw-`F0`,
saw-`E0`-then-`F0`, and a short buffer for the `E1` sequence; plus a set of currently-held
keys; plus a table mapping (prefix, code) to a name. Perhaps a hundred lines. It must not
block, must not allocate, and must live on the main-loop side of the ring buffer.

**Names, and what the check actually checks.** Print one line per event:

```
key: down LeftShift
key: up LeftShift
```

The names are the HID usage names, spelled as you will spell them in your own table — `A`,
`Enter`, `LeftShift`, `KeypadPlus`, `PrintScreen`, `Pause`. The `key-events-decoded` check
does **not** validate your spelling against a list; it checks that every `down` is matched by
a corresponding `up`, that the counts are right, and that distinct keys produce distinct
names. What it punishes is *inconsistency*: a key that goes down as `LeftShift` and comes up
as `Lshift` reads as one stuck key and one phantom release. Choose a convention and hold it.

**About ten entries, and no more.** Derive roughly ten codes yourself, by pressing keys and
reading your own console. Ten is enough to meet every structural case the format has, and
deriving them is where the method is learnt. The remaining hundred-odd entries are
transcription, they teach nothing, and **the bundle ships them for you**: the complete set-2
to HID translation table arrives as `include/ps2_set2_to_hid.h` at lesson 14, the first
lesson that needs all of it. Do not go and type the rest now — you will have spent an evening
on work the course was always going to hand you. Ten well-chosen keys cover everything: an
ordinary letter; `Enter`; `Space`; Left Shift and Right Shift (Right Shift is `0x59` and is
*not* extended, which surprises people); Left Control and Right Control as the
unprefixed/prefixed pair; a keypad key and the navigation key that collides with it; and
then Pause and Print Screen.

## Concepts to teach

- Scan code as matrix position; the distinction between scan code, character and HID usage.
- Scan code set 1 versus set 2, and specifically that break-equals-make-with-bit-7 is set 1.
- Make codes and `0xF0` break codes.
- The `0xE0` extended prefix, the collisions it creates, and prefix ordering on a break.
- The `0xE1` Pause sequence and the absence of a break for it.
- The Print Screen sequence and its embedded phantom Shift.
- Typematic repeat: delay, rate, and why it is invisible on the wire.
- A prefix state machine as the correct structure, versus a lookup with special cases.
- The held-key set, and its relationship to the key-state bitmap of `#events-vs-state`.
- Keyboard response bytes (`0xFA`, `0xFE`, `0xAA`, `0x00`) that must not reach the table.
- The console line contract for `key:`.

## Constraints

- The decoder consumes bytes only through the receive interface's non-blocking pop, as
  defined in `#rx-interface`. It must not reach into either backend's internals, and it
  must work unchanged with the interrupt backend selected as well as the PIO one.
- The decoder runs in the main loop. No decoding in an ISR or in a PIO IRQ handler.
- `0xE0`, `0xF0` and `0xE1` must never be emitted as key events, and must never appear as
  entries in the translation table.
- Exactly one `key: down <name>` per physical press and exactly one `key: up <name>` per
  physical release, for every key on the board, Pause and Print Screen included.
- Typematic repeats produce **no** event. Holding a key produces exactly one `down`.
- Pause's up event is synthesised by your firmware, because the keyboard sends no break.
- Print Screen produces one `PrintScreen` event pair and no phantom `LeftShift` events.
- Names must be identical between the `down` and the `up` for a given key.
- The firmware must not ask the keyboard to change scan code set. `#wire-format` fixed set 2
  and the adapter never sends `0xF0` as a command.
- An unrecognised scan code must not produce a key event, must not wedge the decoder, and
  must not desynchronise the prefix state. Print it on a freeform line of your own if you
  want to see it — any line that is not `key: value` is ignored by every check.
- The table you write yourself holds roughly ten entries. Do not transcribe a full table
  from anywhere; the complete one is supplied at lesson 14.
- The `frame:` and `queue:` lines from earlier lessons keep working. This lesson adds a
  channel, it does not replace one.

## Suggested progression

1. Restate where the bytes come from: the main loop pops them one at a time from the ring
   buffer, and until now it has printed them. Establish that this lesson puts a decoder
   between the pop and the print, and keeps the print.
2. Press and release a single letter key, and read the bytes off the console. Name the make
   code. Name the two bytes of the break. Have the learner state the rule they just
   observed, in their own words, before any code is written.
3. Ask what a break code would be if it were "the make code with bit 7 set", compute that
   value for the key they just pressed, and compare it with what the console actually
   showed. This is the moment the set 1 / set 2 distinction becomes concrete rather than
   trivia.
4. Press `F7` and read its make code. Ask what a bit-7 decoder would do with it. Then press
   `F5` and observe that the two are exactly the pair that decoder would confuse.
5. Write the first version of the decoder: idle and saw-`F0` states only, a table of two or
   three unprefixed keys, and `key:` lines out. Confirm one `down` and one `up` per press on
   the console.
6. Press Right Control and observe three bytes where two were expected. Add the saw-`E0`
   state. Press Right Control's release and read the prefix order off the console — do not
   state it for the learner in advance.
7. Add the saw-`E0`-then-`F0` state and confirm extended keys now produce matched pairs.
   Extend the table to cover the unprefixed/prefixed collision pair (Left and Right Control,
   or Keypad 8 and Up arrow) so the collision is visible in the table itself.
8. Hold a key down for two seconds and watch the console. Count the `down` lines. This is
   typematic repeat, and it is the failure the `key-events-decoded` check will catch.
   Introduce the held-key set and suppress the repeats. Confirm that holding a key now
   produces exactly one `down`, and releasing it exactly one `up`.
9. Press Pause. Read what arrives. Point out the `14` and the `77` inside it and the
   phantom events a naive decoder emits. Add the `0xE1` sequence handling, and have the
   learner decide where the synthesised `up` goes and why there is no other option.
10. Press Print Screen and read the sequence. Find the `12` and name it. Add the handling.
    Then press `Ctrl+PrintScreen` and `Alt+PrintScreen` and observe that the sequences
    differ — capture whichever ones the learner's board actually sends, on the analyser if
    the console is hard to read at that speed.
11. Reset the keyboard with the lesson 09 command path, or replug it, and watch `0xAA`
    arrive. Confirm it does not produce a key event. Do the same for the `0xFA` that
    follows a command.
12. Round the table out to roughly ten entries covering the cases named in *Theory*: a
    letter, `Enter`, `Space`, both Shifts, both Controls, a keypad/navigation collision
    pair, Pause and Print Screen. Stop there, and say out loud that the rest arrives at
    lesson 14.
13. Rebuild with the interrupt backend selected and confirm the decoder is unchanged and
    the events are identical. This is the `#rx-interface` promise being cashed.
14. Type a short burst at full speed and confirm every `down` has its `up`, the drop counter
    is still zero, and nothing is left held.

## Completion conditions

- Every physical key on the learner's Model M that is in their table produces exactly one
  `key: down <name>` when pressed and exactly one `key: up <name>` when released, with the
  same name in both lines.
- Pause produces one `down` and one `up`, with the `up` synthesised by the firmware, and no
  phantom Control or Num Lock events.
- Print Screen produces one `down` and one `up` and no phantom Left Shift events.
- Holding any key for several seconds produces exactly one `down` line, not a stream of
  them.
- No `key:` line ever names `E0`, `F0` or `E1`, and no response byte from the keyboard
  (`0xAA`, `0xFA`, `0xFE`) produces a key event.
- The learner can state, unprompted, why break-equals-make-with-bit-7-set describes set 1
  and what it does to a set 2 keyboard — naming at least one key it would silently break.
- The learner can state the byte order of an extended key's break sequence, having read it
  off their own console rather than from this lesson.
- The translation table the learner wrote holds roughly ten entries derived from their own
  keyboard, and the learner can say why the remaining entries are not their work.
- The decoder produces identical events with either receive backend selected.
- The `build-ok` check passes.
- The `key-events-decoded` check passes: it will ask for a specific sequence of presses and
  releases and will confirm every `down` is matched and the counts are right.

## On completion, persist

Record in the instance's `DESIGN.md`/`STATE.md`:

- The scan code set in use is set 2, fixed by `#wire-format`, and the adapter never asks the
  keyboard to change it.
- The decoder's states and where the decoder runs — main loop, behind the receive
  interface's pop, never in interrupt context.
- The naming convention chosen for key names, and the roughly ten entries derived, with
  their codes. Later lessons must not contradict these names.
- That `0xE0`, `0xF0` and `0xE1` are decoder states and never table entries.
- That Pause's release event is synthesised, and Print Screen's embedded `0x12` is
  swallowed, with the exact sequences observed on this learner's keyboard.
- That typematic repeat is suppressed by the held-key set, and that this set is the first
  version of the key-state bitmap `#events-vs-state` makes authoritative in lesson 14.
- A note that the complete translation table arrives as a supplied file at lesson 14, so a
  later session does not assign the transcription.

## Optional deeper paths

- Scan code set 3, the only set with a genuinely regular structure — every key a single
  unprefixed code, with per-key programmable make/break/typematic behaviour — and the reason
  nobody uses it: patchy keyboard support, so the adapter would need a detect-and-fall-back
  path for no gain.
- The `0xF3` command (set typematic rate and delay), using the transmit path from lesson 09
  and the supplied `docs/ps2-commands.md`. Watching the repeat interval change on the console
  is a satisfying five minutes, and a good argument for leaving it alone.
- Where the translation actually happens on a legacy PC: the 8042-compatible keyboard
  controller converts set 2 to set 1 on the fly, which is why so much documentation describes
  set 1 as if it came off the keyboard.
- The Model M's own matrix: why some three-key combinations do not register at all, and why
  that is a property of the keyboard rather than of your firmware. Lesson 14's rollover
  discussion assumes it.
