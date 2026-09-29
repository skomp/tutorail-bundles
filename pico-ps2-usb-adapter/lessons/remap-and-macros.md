---
id: remap-and-macros
title: Remap and macros
design_refs: [events-vs-state]
validators: [build-ok, keymap-applied]
optional: true
---

## Purpose

Make the layout yours: swap what a key sends, and teach one key to send a whole sequence.

A Model M has no Windows key, its Caps Lock sits where a great many people would rather have
Control, and it has keys most modern software never asks for. Remapping is the first thing
most owners want from an adapter, and it is a genuinely small change — three lines in the
right place. The interest is entirely in *which* place.

Your firmware has four layers between the wire and the host: raw PS/2 bytes, decoded key
events, the key-state bitmap, and the HID report built from it. A remap can be inserted into
any of them, and three of the four choices are wrong, each in a different and instructive way.
`DESIGN.md` `#events-vs-state` already told you where the boundary between "events" and
"state" falls, and the right answer falls straight out of it. The wrong answer that feels most
natural — remapping the scan code as it comes off the wire, where the table is smallest — is
the one that leaves your arrow keys behaving differently from your letters, and it takes an
evening to understand.

## Prerequisites

This lesson stands alone and assumes a finished, working adapter.

- Lesson 10 (`10-scan-codes-to-key-events`) complete: the `0xE0` extended prefix and the
  `0xF0` break prefix are handled in the decoder, Pause and Print Screen included, and every
  physical key produces a named down and up event.
- Lesson 13 (`13-your-first-keystroke`) complete: you know what the eight-byte report looks
  like and how a keypress is two reports rather than one.
- Lesson 14 (`14-events-to-state`) complete: the key-state bitmap is the single source of
  truth, and HID reports are snapshots of it sent only on change. The console prints
  `key: <down|up> <key name>`, `report: <eight bytes in hex>` and `held: <n>`.
- You know your endpoint's polling interval from the descriptor you wrote in lesson 11. The
  macro half of this lesson depends on it.
- Lesson 15 is the offer point rather than a requirement; nothing here touches the LEDs.

## Learning objectives

- Name the four layers between the PS/2 wire and the HID report, and say what each one's
  values mean.
- Place a keymap at the key-event layer and explain why the scan-code layer cannot express the
  same mapping, and why report-build time can produce a stuck key.
- Choose between compile-time and runtime keymap configuration and defend the choice on RAM,
  reflash cost, persistence and recovery grounds.
- Implement a macro as a scheduled sequence of state changes rather than a burst of reports,
  and say why the host's polling interval forces that.
- Show, from the console, that a remapped key and a macro both preserve the one-down-one-up
  invariant.

## Theory

**The four layers, and what a value means in each.**

1. **Scan-code bytes.** What arrives from the receive backend: `0x1C`, `0xF0`, `0xE0`. A
   single byte is not a key. `0x75` is the keypad `8`; `0xE0 0x75` is the up arrow. `0xF0` is
   not a key at all, it is the announcement that the next code is a release. Pause is eight
   bytes long and has no break sequence whatsoever.
2. **Key events.** What the lesson 10 decoder produces: a key *identity* plus a direction.
   Extended and non-extended keys are distinct identities here, prefixes have been consumed,
   and every key on the board is representable exactly once.
3. **The key-state bitmap.** One bit per key identity, mutated by events. The single source
   of truth of `#events-vs-state`.
4. **The HID report.** A snapshot built from the bitmap: modifier bitmap, reserved byte,
   six-key array.

**Why the scan-code layer is the wrong place — the failure to walk into.** A table keyed on
one byte cannot distinguish `0x75` from `0xE0 0x75`, so a remap written there hits the keypad
key and leaves the arrow key alone (or, if you keyed on the second byte of an extended pair,
the other way round). Half your keyboard obeys the map and half ignores it, and the half that
ignores it is exactly the half — arrows, navigation cluster, right Control and Alt, the
keypad's Enter and slash — that people most want to remap. Worse, `0xF0` and `0xE0` are
themselves byte values in the same space, so a sloppy table can remap a *prefix* and turn
every following key into something else. And Pause cannot be expressed as a byte substitution
at all. This is `#events-vs-state` restated from the other side: PS/2 produces events, and a
byte is not yet an event.

**Why the key-event layer is the right place.** After the decoder, a keymap is a pure function
from key identity to HID usage, total over every key on the board, one entry per key. Extended
keys need no special case because the decoder already dealt with the prefix, and Pause and
Print Screen are single identities by the time they get here, so they remap like anything
else. The decoder stays the only code that knows `0xE0` and `0xF0` exist, which is exactly the
separation lesson 10 was for.

**Why the state and report layers are wrong.** Rewriting the bitmap as it is mutated means
rewriting the source of truth, and it is then indexed by something that is neither physical
key nor sent usage — you lose the ability to say what is actually held. Applying the map when
the report is built is worse, and the reason is the strongest argument in this lesson: a
keypress lives across *two* report builds, one when it goes down and one when it comes up. If
the map is consulted at build time and anything about it differs between those two moments — a
runtime change, a layer toggle, a conditional — the key goes down as usage X and comes up as
usage Y, usage X is never released, and you have a key typing forever into whatever has focus.
So the invariant is one line: **map once, at the event, and the whole down/up lifetime of that
press uses the mapped usage.**

**What the console should say.** Print the **mapped** usage in your `key:` lines, because that
is what leaves the adapter, and because the pairing invariant the check enforces — every
`down` matched by an `up` — then covers precisely the identity that remapping can break. If
you also want the physical key name, print it on a free-form line of your own; lines that do
not match the log format are ignored by every check.

**Compile-time versus runtime.** A `const` table in flash costs no RAM, no code and no failure
modes, and changing your layout means editing a file and reflashing. A table in RAM can be
changed while the adapter runs — from the debug console, from a key combination, from a vendor
report if you took the offered `a-second-interface-for-debugging` lesson — and costs RAM, a
persistence story and a recovery story. Persistence is possible on this chip and is fiddly,
because your code executes in place out of the same flash you would be writing to; the
optional deeper path at the end of this lesson is where that is covered. Recovery is quieter
and bites harder: a runtime map that
remaps the key you need in order to fix the map leaves you reflashing anyway. Compile-time is
the right default here. Whichever you pick, be able to say why.

**Macros, and the polling interval.** A macro is one key event expanding into a *sequence* of
host-visible states. To type `abc` the host must observe six distinct reports: `a` down,
nothing, `b` down, nothing, `c` down, nothing. The empty reports are not decoration — without
one between two presses of the same letter, `aa` arrives as a single `a`, because the host
sees no change.

The failure is to emit all six as fast as the CPU can. The host does not read your reports; it
*polls*, once per `bInterval`, and sees only the state in the endpoint buffer at the moment the
IN token arrives. Push six reports in ten microseconds and the host observes one or two.
Intermediate states you never gave the bus time to carry simply did not happen, and the macro
types a fragment of itself, differently each run. Nor can you fix it by spinning: a busy-wait
inside the event handler blocks the USB task and the receive path, turning a cosmetic bug into
a stuck-key bug.

The shape that works keeps `#events-vs-state` intact. Hold the macro as a small queue of
pending state changes and advance it by **at most one step per report opportunity** — one step
per completed IN transfer, or one step per polling interval from the main loop on a timer.
Each step mutates the key-state bitmap; the report is still a snapshot of it, still sent on
change. The macro is a virtual typist pressing keys, not a special path that writes reports.

Two more details cost an evening each. Modifiers must be sequenced — shift down, key down, key
up, shift up — because releasing the modifier in the same report as the key it modified is a
race the host may resolve either way. And a macro still running when the user presses a real
key has to decide what happens; the simplest defensible rule is that the macro owns the report
stream until it finishes and real events queue behind it.

## Concepts to teach

- The four layers between wire and report, and what a value means in each.
- Why a scan-code-layer remap splits the keyboard into obedient and disobedient halves, via
  `0xE0`, `0xF0` and the Pause sequence.
- The key-event layer as a total, one-entry-per-key function from identity to HID usage.
- The down/up lifetime argument: map once at the event, or risk a key that goes down as one
  usage and up as another.
- `#events-vs-state`: the bitmap is still the single source of truth and reports are still
  snapshots of it, after remapping and after macros alike.
- Compile-time versus runtime configuration: RAM, reflash cost, and recovery from a bad map.
- The polling interval as the rate limit on host-visible state changes, and why a repeated
  character needs an intervening empty report.
- Macros as a scheduled queue advanced one step per report opportunity, never a busy-wait;
  modifier sequencing; and what happens when a real key arrives mid-macro.

## Constraints

- The keymap is applied at the key-event layer. The decoder remains the only code that knows
  about `0xE0` and `0xF0`, and the scan-code stream is not rewritten.
- A key's down and up use the same mapped usage for the whole lifetime of that press,
  regardless of anything that changes in between.
- The key-state bitmap stays the single source of truth per `#events-vs-state`. Macros mutate
  it; they do not write reports directly.
- The keymap is total: every physical key on the board has exactly one entry, extended keys,
  Pause and Print Screen included. An unmapped key is a bug, not a default.
- No busy-wait and no blocking delay anywhere in the event or report path, and a macro
  advances at most one host-visible state change per report opportunity.
- `key:` lines report the mapped usage. Any physical-key annotation goes on the learner's own
  free-form lines.
- Nothing from lesson 14 regresses: typing a paragraph produces exactly the right text, no key
  sticks, and releasing everything leaves `held: 0`.
- The learner states, for each change they made, which layer it belongs in and why.

## Suggested progression

1. Have the learner name the four layers in their own firmware and point at the code that
   implements each boundary.
2. Pick the first remap out loud — Caps Lock to Control is the usual one — and ask where it
   should go, before any of the theory.
3. If the answer is the scan-code layer, implement it there. It will work for Caps Lock.
4. Now remap an extended key with it: the right Control, an arrow, or the keypad Enter. Watch
   half the keyboard ignore the map, and read the `key:` lines to see why.
5. Diagnose it against `#events-vs-state`: a byte is not an event, and the prefix is the
   proof.
6. Move the map to the key-event layer, keyed on key identity. Confirm the extended key now
   obeys it and the decoder did not change.
7. Make the map total. Walk every key on the board and check each one produces exactly one
   `down` and one `up` under its mapped name.
8. Discuss compile-time versus runtime. Have the learner choose, write down the reason, and
   name how they would recover from a map that remapped the key they need.
9. Instructive probe: apply the map at report-build time instead, then change the map while a
   key is held. Watch the key stick, and connect it back to the two-report lifetime.
10. Design the first macro on paper as a sequence of key-state snapshots, including the empty
    ones, and count how many reports the host must observe.
11. Implement it the naive way — emit every report in one pass — and watch the host receive a
    fragment, differently each time.
12. Work out from `bInterval` how many host-visible states per second are actually available,
    and compare with how fast the naive version emitted them.
13. Rewrite the macro as a queue advanced one step per report opportunity. Confirm from the
    `report:` lines that every intended state appears, in order, including the empty ones.
14. Add a modifier to the macro and get the sequencing right: modifier down, key down, key up,
    modifier up.
15. Start the macro and press a real key while it runs. State the rule the firmware follows
    and show it does not leave a key held.
16. Re-run lesson 14's evidence — type a paragraph, check the text, check `held: 0` at rest —
    and have the learner state which layer each of their changes belongs in.

## Completion conditions

- A remapped key works: pressing one physical key produces a different, intended character or
  usage on the host, and the `key:` lines show the mapped usage on both the down and the up.
- The remap is applied at the key-event layer, and the learner can show that an **extended**
  key remaps identically to a non-extended one, naming why a scan-code-layer map would not.
- A multi-key macro works: one key press produces the full intended sequence on the host,
  every time, including any repeated character, and the `report:` lines show each intended
  state with the empty reports between them.
- The learner states, for the remap and for the macro separately, **which layer** the change
  belongs in and why the adjacent layers are wrong — specifically, why report-build time risks
  a stuck key — and states whether the keymap is compile-time or runtime, why, and how a bad
  map is recovered from.
- The macro advances at most one host-visible state per report opportunity, with no busy-wait
  in the event or report path, and the learner can relate that rate to their `bInterval`.
- Nothing regresses: a typed paragraph is correct, no key sticks, `held: 0` at rest, every
  `down` on the console is matched by an `up`, and the `build-ok` and `keymap-applied` checks
  pass.

## On completion, persist

Record in the instance's `DESIGN.md`/`STATE.md`:

- That the keymap lives at the key-event layer, with the one-line reason, so a later change is
  not made at the wrong boundary; and the map-once-at-the-event invariant with the stuck-key
  failure it prevents.
- Whether the keymap is compile-time or runtime, and if runtime, how it is changed, where it
  persists and how it is recovered.
- The macro scheduling rule — one state change per report opportunity — the polling interval
  it is tied to, and the rule for a real keypress arriving during a macro.
- The current remappings, so the finished adapter of lesson 18 is accepted against the layout
  it actually has.

## Optional deeper paths

- Add a layer key in the QMK sense: a held key that selects a second keymap. Work out where
  the layer state lives, and how the map-once invariant keeps a key released under the layer
  it was pressed in.
- Persist a runtime keymap to the RP2040's flash and read it back at boot, dealing properly
  with XIP being disabled during the write and with the second core and interrupts.
- Give the Model M its missing keys: map the two keys modern software ignores to the ones it
  wants, and check the result in the host's firmware setup as well as on the desktop.
- Add tap-versus-hold behaviour to one key, and discover why it needs a timeout, what that
  timeout costs in perceived latency, and how it interacts with typematic repeat.
