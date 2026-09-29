#!/usr/bin/env python3
"""The checks that read evidence off your debug console. One subcommand per lesson.

WHAT THIS CHECKS
    Whatever the first argument names:

        alive       lesson 00  the firmware is running and printing
        edges       lesson 04  the ISR sees clock edges, at the right rate
        frames      lesson 05  bytes assemble, parity is checked, framing resyncs
        queue       lesson 06  the ISR-to-main-loop handover loses nothing
        pio         lesson 07  a PIO state machine runs while the CPU does not
        pio-frames  lesson 08  the PIO backend produces the same bytes, measurably cheaper
        ack         lesson 09  the keyboard acknowledged a command you sent it
        events      lesson 10  scan codes became balanced key-down/key-up events
        reports     lesson 14  HID reports are 8 bytes, and no key is ever left stuck
        robustness  lesson 17  hot-plug, resync, held-key release, suspend and wakeup
        safety      offered    the enable gate blocks output until it is grounded

WHAT EVIDENCE IT READS
    The `key: value` lines your firmware prints on UART0, through checks/_console.py.
    Nothing else: not the host, not your source, not your word for it. Lines that do
    not match the contract are ignored, so your own printf debugging cannot affect a
    result either way.

    Several of these need a human to make something happen -- a keypress, an unplug,
    a deliberate glitch. Those print an instruction and wait for Enter. The tutor
    reads the instruction out to the learner: the machine reads the evidence, a human
    causes it. Do not type the keys yourself and then tell the check it happened.

WHAT A FAILURE HERE MEANS
    Almost always your firmware, and the message says which part. Two failures are
    not about your firmware and say so: "no such records arrived" can mean you have
    not printed that key yet (each lesson says which keys it needs, spelled exactly),
    and anything reported as CANNOT CHECK is the port or the environment, not the code.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _console import (  # noqa: E402
    EXIT_OK,
    EXIT_SETUP,
    by_key,
    collect,
    collect_while,
    counter_delta,
    describe_traffic,
    fail,
    last,
    note,
    ok,
    open_console,
    require_records,
)

COMMANDS = {}


def command(name):
    def register(function):
        COMMANDS[name] = function
        return function
    return register


# ---------------------------------------------------------------------------
# small parsers over the vocabulary
# ---------------------------------------------------------------------------

class Frame:
    def __init__(self, record):
        parts = record.fields()
        self.t = record.t
        self.raw = record.raw
        self.byte = None
        self.status = parts[1] if len(parts) > 1 else ""
        if parts:
            try:
                self.byte = int(parts[0], 16)
            except ValueError:
                self.byte = None

    @property
    def is_ok(self):
        return self.status == "ok" and self.byte is not None


def frames_of(records):
    return [Frame(r) for r in by_key(records, "frame")]


def malformed(frames):
    return [f for f in frames if f.byte is None or f.status not in
            ("ok", "parity-error", "framing-error")]


def report_bytes(record):
    """`report: 01 00 04 00 00 00 00 00` -> [1, 0, 4, 0, 0, 0, 0, 0], or None."""
    parts = record.fields()
    try:
        return [int(p, 16) for p in parts]
    except ValueError:
        return None


def key_events(records):
    """[(direction, name)] from `key: down A` lines, skipping malformed ones."""
    events = []
    for record in by_key(records, "key"):
        parts = record.fields()
        if len(parts) < 2 or parts[0] not in ("down", "up"):
            continue
        events.append((parts[0], " ".join(parts[1:])))
    return events


def balance(events):
    """(unbalanced_names, double_downs, counts). A key left down at the end is the
    bug lesson 14 is named after; a second down with no up between is typematic
    repeat being read as a new press."""
    held = {}
    doubles = []
    counts = {}
    for direction, name in events:
        counts[name] = counts.get(name, 0) + 1
        if direction == "down":
            if held.get(name):
                doubles.append(name)
            held[name] = True
        else:
            held[name] = False
    return sorted(n for n, down in held.items() if down), doubles, counts


def distinct_names(events):
    seen = []
    for _direction, name in events:
        if name not in seen:
            seen.append(name)
    return seen


SUSPICIOUS_NAMES = {"e0", "f0", "0xe0", "0xf0", "e0)", "unknown", "?", "??", "none",
                    "0", "00", "0x00", "null"}


# ---------------------------------------------------------------------------
# lesson 00 -- firmware-alive
# ---------------------------------------------------------------------------

@command("alive")
def cmd_alive(handle):
    records = collect(6.0, handle=handle)
    alive = require_records(
        records, "alive",
        "Lesson 00 asks your firmware to print `alive: <counter>` about once a\n"
        "second, where the counter goes up every time. That one line is how every\n"
        "later check knows the chip is running at all.")
    values = [r.as_int() for r in alive]
    if any(v is None for v in values):
        fail("some `alive:` lines do not carry a number:",
             *["    " + r.raw for r in alive if r.as_int() is None],
             "",
             "The value must be a counter and nothing else -- `alive: 12`, not",
             "`alive: tick 12` and not `alive: still here`. A check that cannot read",
             "it cannot tell a running counter from a stuck one.")
    if len(values) < 2:
        fail("only one `alive:` line arrived in six seconds (%r)." % alive[0].raw,
             "",
             "One line could be a board that printed once and then hung -- which is",
             "exactly what a blocking call in your main loop looks like. The counter",
             "should be printed about once a second, so this check wants to see it",
             "move. Check that your loop really loops, and that nothing in it blocks",
             "forever waiting for hardware that is not there yet.")
    if values[-1] < values[0]:
        fail("the `alive` counter went backwards: %d then %d." % (values[0], values[-1]),
             "",
             "The counter restarting means the chip reset in the middle of this check.",
             "A reset loop on the RP2040 is usually a hard fault or a watchdog you",
             "armed and are not feeding. Lesson 16 is where you learn to catch it in",
             "gdb; for now, look for a fault in whatever ran just before the restart.")
    if len(set(values)) == 1:
        fail("the `alive` counter printed %d times and never changed (always %d)."
             % (len(values), values[0]),
             "",
             "The line is being printed but the number is not moving. Either the",
             "counter is reset every pass through the loop, or the thing you are",
             "printing is not the counter you are incrementing.")
    span = alive[-1].t - alive[0].t
    rate = (len(values) - 1) / span if span > 0 else 0
    ok("the firmware is running and printing on the debug console.",
       "%d `alive` records in %.1fs, counter %d -> %d, about %.1f per second."
       % (len(values), span, values[0], values[-1], rate),
       "The console route works, which is what lesson 00 is for: a window into the",
       "chip that USB cannot take away from you in lesson 11.")


# ---------------------------------------------------------------------------
# lesson 04 -- edges-counted
# ---------------------------------------------------------------------------

@command("edges")
def cmd_edges(handle):
    records = collect_while(
        "Press and release the A key five times, slowly -- about one press a second.\n"
        "Then press Enter here.", handle=handle)
    edges = require_records(
        records, "edges",
        "Lesson 04 asks your firmware to print `edges: <total>` whenever the count\n"
        "of clock edges seen since boot changes.")
    if len(edges) < 2:
        fail("only one `edges:` line arrived for five keypresses: %s" % edges[0].raw,
             "",
             "The count is printed on change, so one line means the count changed",
             "once -- or that it is printed once and never again. Either way there is",
             "nothing here to compare. Check that the print really is driven by the",
             "count changing, and press the key again while the check is recording.")
    first, final, delta = counter_delta(records, "edges")
    if first is None:
        fail("the `edges:` lines carry no number this check could read.",
             describe_traffic(records))
    if delta == 0:
        fail("the edge count did not move while five keys were pressed (stuck at %d)." % final,
             "",
             "Either the interrupt is not firing or the counter is not surviving the",
             "trip out of the ISR. Three things cause this, in the order they bite:",
             "  1. the IRQ was enabled before the pin was configured, or on the wrong",
             "     pin -- clock is GP2, data is GP3;",
             "  2. the callback is registered for the wrong edge, or for no edge;",
             "  3. the counter is not `volatile`, so the compiler cached it in a",
             "     register for your main loop and never reloaded it. This one is",
             "     the classic: the ISR is running perfectly and you cannot see it.")
    if delta < 0:
        fail("the edge count went backwards (%d then %d) -- the board reset mid-check."
             % (first, final))

    per_press = delta / 5.0
    arithmetic = [
        "%d edges over five press-and-releases: %.1f per press, %.1f frames' worth"
        % (delta, per_press, delta / 11.0),
        "One PS/2 frame is eleven clock edges: start, eight data, parity, stop.",
        "A press and a release is at least two frames (make, then F0 + make).",
    ]
    if delta < 11:
        fail("only %d edges arrived for five keypresses." % delta, "",
             *(arithmetic + [
                 "", "Fewer than one frame's worth. The interrupt is firing, but on",
                 "far fewer edges than the wire carries -- a noisy trigger condition,",
                 "or an interrupt that is being disabled and not re-enabled."]))
    if delta < 40:
        fail("only %d edges arrived for five keypresses, which is too few." % delta, "",
             *(arithmetic + [
                 "",
                 "If your number is close to five, you are counting frames or keys and",
                 "calling them edges. If it is close to eleven times five, you are",
                 "seeing the make codes and missing the break codes -- check that you",
                 "are still counting while the key is being released."]))
    note(*arithmetic)
    remainder = delta % 11
    if remainder:
        note("%d is not a whole number of eleven-edge frames (%d left over). That is"
             % (delta, remainder),
             "not a failure -- a bounce or a stray edge does it -- but if the leftover",
             "is large your trigger is picking up noise as well as clock.")
    ok("the ISR is counting clock edges off the wire.",
       "count %d -> %d, delta %d, which is %.1f frames' worth for five keypresses."
       % (first, final, delta, delta / 11.0),
       "Make sure the learner can say why eleven: start bit, eight data bits, one",
       "parity bit, one stop bit, clocked by the keyboard.")


# ---------------------------------------------------------------------------
# lesson 05 -- frames-received
# ---------------------------------------------------------------------------

@command("frames")
def cmd_frames(handle):
    first_pass = collect_while(
        "Press and release the A key five times.\n"
        "Then press Enter here.", handle=handle)
    require_records(
        first_pass, "frame",
        "Lesson 05 asks your firmware to print one `frame: <hex byte> <ok|parity-error|\n"
        "framing-error>` line per assembled byte -- for example `frame: 1c ok`.")

    frames = frames_of(first_pass)
    bad_shape = malformed(frames)
    if bad_shape:
        fail("%d `frame:` lines are not in the contract's shape:" % len(bad_shape),
             *["    " + f.raw for f in bad_shape[:8]],
             "",
             "The shape is `frame: <hex byte> <status>`, where status is exactly one",
             "of ok, parity-error or framing-error. The hex byte has no 0x prefix.",
             "Anything else this check has to treat as noise.")

    good = [f for f in frames if f.is_ok]
    errors = [f for f in frames if not f.is_ok]
    if len(good) < 5:
        fail("only %d of %d frames came through as `ok` for five keypresses."
             % (len(good), len(frames)),
             "",
             "Frames are arriving but most of them are wrong, which is a decoding bug",
             "and not a wiring one. In order of how often each is the cause:",
             "  1. sampling data on the wrong clock edge. The keyboard puts data on",
             "     the line on the rising edge and it is valid on the FALLING edge;",
             "  2. assembling the byte MSB-first. PS/2 sends the least significant",
             "     bit first, so a shift in the wrong direction gives you a mirrored",
             "     byte that fails parity about half the time;",
             "  3. parity computed over the wrong bits -- it is odd parity over the",
             "     eight data bits, and the parity bit itself is not part of the sum.",
             "",
             "Statuses seen: " + ", ".join(sorted({f.status for f in frames})))

    counts = {}
    for frame in good:
        counts[frame.byte] = counts.get(frame.byte, 0) + 1
    common = sorted(counts.items(), key=lambda kv: -kv[1])
    if not common or common[0][1] < 5:
        fail("no single byte value repeated five times across five presses of one key.",
             "",
             "Bytes seen: " + ", ".join("%02x x%d" % (b, n) for b, n in common[:12]),
             "",
             "Pressing the same key five times must give the same make code five",
             "times. Values that differ each press mean the frame boundary is",
             "drifting -- usually no idle timeout, so one glitch leaves the receiver",
             "permanently one bit out of step and every byte after it is garbage.")
    note("%d frames, %d ok, %d with an error status." % (len(frames), len(good), len(errors)))
    note("Most common byte: %02x, seen %d times -- that is the A key's make code."
         % (common[0][0], common[0][1]))

    second_pass = collect_while(
        "Now break it on purpose, and watch it recover.\n"
        "Briefly touch the PS/2 CLOCK line to ground while typing -- or unplug and\n"
        "replug the keyboard. Then press the A key twice more.\n"
        "Then press Enter here.", handle=handle)

    all_records = first_pass + second_pass
    _f, _l, resync_delta = counter_delta(all_records, "resync")
    glitch_frames = frames_of(second_pass)
    detected = [f for f in glitch_frames if not f.is_ok]

    if not resync_delta and not detected:
        fail("the deliberate glitch produced no evidence that anything noticed it.",
             "",
             "No `resync:` counter moved and no frame came back with an error status.",
             "Either the glitch did not land -- try again, shorting clock to ground",
             "for a moment mid-frame -- or your receiver has no way to notice a",
             "truncated frame at all. A state machine with no idle timeout does not",
             "resynchronise: it waits forever for bits that already went past, and",
             "every byte from then on is off by one. That is the failure this lesson",
             "exists to make you meet.")

    recovered = []
    if detected:
        marker = detected[-1].t
        recovered = [f for f in glitch_frames if f.is_ok and f.t > marker]
    else:
        recovered = [f for f in glitch_frames if f.is_ok]
    if len(recovered) < 2:
        fail("the receiver noticed the glitch but did not come back from it.",
             "",
             "resync moved by %s and %d frames reported an error, but only %d good"
             % (resync_delta, len(detected), len(recovered)),
             "frames arrived afterwards -- and two more keypresses were asked for.",
             "",
             "This is latching: one bad frame and the receiver stays wedged. Treat a",
             "framing or parity error as a reason to drop the partial byte and go back",
             "to waiting for a start bit, not as a fatal condition. An idle timeout --",
             "no clock edge for longer than about 100 microseconds means the frame is",
             "over, finished or not -- is what makes recovery automatic.")

    ok("frames assemble correctly, and the receiver recovers from a deliberate glitch.",
       "Clean run: %d frames, %d ok, make code %02x seen %d times."
       % (len(frames), len(good), common[0][0], common[0][1]),
       "After the glitch: resync moved by %s, %d error frames, %d good frames after."
       % (resync_delta, len(detected), len(recovered)))


# ---------------------------------------------------------------------------
# lesson 06 -- queue-lossless
# ---------------------------------------------------------------------------

@command("queue")
def cmd_queue(handle):
    records = collect_while(
        "Type as fast as you can for about five seconds -- mash a sentence out of\n"
        "the Model M, both hands, no care for accuracy. The point is to produce\n"
        "bytes faster than the main loop is comfortable with.\n"
        "Then press Enter here.", handle=handle)
    queue = require_records(
        records, "queue",
        "Lesson 06 asks your firmware to print `queue: <popped> <dropped>` from the\n"
        "MAIN LOOP -- total bytes taken out of the ring buffer, and total bytes the\n"
        "ISR had to throw away because the buffer was full.")

    parsed = [(r, r.int_at(0), r.int_at(1)) for r in queue]
    broken = [r for r, popped, dropped in parsed if popped is None or dropped is None]
    if broken:
        fail("%d `queue:` lines do not carry two numbers:" % len(broken),
             *["    " + r.raw for r in broken[:6]],
             "",
             "The shape is `queue: <popped> <dropped>`, both decimal, both totals",
             "since boot rather than deltas.")

    if len(parsed) < 2:
        fail("only one `queue:` line arrived during five seconds of fast typing: %s"
             % queue[0].raw,
             "",
             "One line gives nothing to compare against. Print the counters from the",
             "main loop on a regular tick -- roughly with `alive` is fine -- so the",
             "check can see them move rather than take a single snapshot on trust.")

    popped = [p for _r, p, _d in parsed]
    dropped = [d for _r, _p, d in parsed]
    popped_delta = popped[-1] - popped[0]
    dropped_delta = dropped[-1] - dropped[0]

    if dropped[-1] or dropped_delta:
        fail("the buffer dropped %d byte%s during that burst (total dropped is now %d)."
             % (dropped_delta, "" if dropped_delta == 1 else "s", dropped[-1]),
             "",
             "The completion condition for this lesson is a drop counter that stays at",
             "zero through fast typing, and it is achievable: a Model M at full speed",
             "produces a few hundred bytes a second and the main loop has microseconds",
             "of slack. A non-zero drop count means one of:",
             "  * the ring buffer is too small for the worst burst -- but before you",
             "    grow it, ask what the main loop is doing that takes so long;",
             "  * slow work is being done between pops -- a printf per byte at 115200",
             "    baud costs about a millisecond, which is enough on its own;",
             "  * the consumer only pops one byte per loop iteration while the",
             "    producer can deliver several in that time.",
             "",
             "Growing the buffer hides this. Find out which of the three it is first.")

    if popped_delta < 40:
        fail("only %d bytes were popped by the main loop during five seconds of fast typing."
             % popped_delta,
             "",
             "Frames seen on the console in the same window: %d." % len(frames_of(records)),
             "",
             "Bytes are being received but not making it out of the ring buffer. The",
             "usual cause is shared state that the compiler is allowed to assume",
             "nobody else touches: a head or tail index that is not `volatile` is read",
             "once into a register and never re-read, so the consumer sees an empty",
             "buffer forever while the producer fills it. The second usual cause is a",
             "wrap condition that is wrong in one direction -- full and empty look the",
             "same when head == tail unless you have decided which one that means.")

    if popped[-1] < popped[0]:
        fail("the popped counter went backwards (%d then %d): the board reset mid-check."
             % (popped[0], popped[-1]))

    frame_count = len([f for f in frames_of(records) if f.is_ok])
    if frame_count and popped_delta + 5 < frame_count:
        note("%d good frames were logged but only %d bytes were popped. If those two"
             % (frame_count, popped_delta),
             "diverge over a long run, the consumer is falling behind the producer.")

    ok("the ISR-to-main-loop handover lost nothing under a fast burst.",
       "popped %d -> %d (%d bytes), dropped %d throughout."
       % (popped[0], popped[-1], popped_delta, dropped[-1]),
       "That is a lock-free single-producer single-consumer ring buffer doing its job:",
       "one writer in interrupt context, one reader in thread context, no lock between",
       "them and no byte lost.")


# ---------------------------------------------------------------------------
# lesson 07 -- pio-runs
# ---------------------------------------------------------------------------

@command("pio")
def cmd_pio(handle):
    print("Watching the console for eight seconds. The PIO program should keep")
    print("running -- and `alive` should keep ticking -- with no help from you.")
    records = collect(8.0, handle=handle)
    pio = require_records(
        records, "pio",
        "Lesson 07 asks your firmware to print `pio: <sm> <freeform>` -- the state\n"
        "machine index, then whatever the lesson has you report about it (the pin,\n"
        "the divider, the rate you predicted).")

    def sm_index(record):
        value = record.int_at(0)
        return value if value is not None and 0 <= value <= 3 else None

    bad = [r for r in pio if sm_index(r) is None]
    if bad:
        fail("%d `pio:` lines do not start with a state machine index of 0 to 3:" % len(bad),
             *["    " + r.raw for r in bad[:6]],
             "",
             "Each RP2040 PIO block has exactly four state machines, numbered 0 to 3.",
             "The first field says which one this line is about.")

    thin = [r for r in pio if len(r.fields()) < 2]
    if thin:
        fail("%d `pio:` lines carry a state machine index and nothing else:" % len(thin),
             *["    " + r.raw for r in thin[:6]],
             "",
             "The second field is yours to choose, but it has to say something -- the",
             "pin being toggled, the clock divider, the rate you calculated. A bare",
             "index is not evidence that the program is doing what you predicted.")

    if len(pio) < 3:
        fail("only %d `pio:` line%s in eight seconds."
             % (len(pio), "" if len(pio) == 1 else "s"),
             "",
             "The point of this lesson is that the state machine keeps running on its",
             "own. A single line could be printed by setup code that ran once and then",
             "stopped. Print it repeatedly so this check can see it continuing.")

    span = pio[-1].t - pio[0].t
    if span < 2.0:
        fail("all %d `pio:` lines arrived within %.1f seconds and then stopped."
             % (len(pio), span),
             "",
             "The state machine stopped, or your reporting did. A PIO program keeps",
             "executing after main() moves on -- that independence is the whole point",
             "of the lesson -- so if the reports stop, look at what stopped: the",
             "state machine being disabled, the FIFO filling and stalling the program,",
             "or a `pull` with no data behind it.")

    alive = by_key(records, "alive")
    if len(alive) < 2:
        fail("the PIO program is reporting, but the CPU stopped: only %d `alive` lines"
             % len(alive),
             "arrived in the same eight seconds.",
             "",
             "The claim this lesson makes is that PIO runs WHILE the CPU is busy",
             "elsewhere. A CPU that has hung -- most likely blocked on a FIFO that",
             "never fills -- does not demonstrate that. Do not block the main loop on",
             "PIO output unless you mean to.")

    ok("a PIO state machine is running independently of the CPU.",
       "%d `pio` reports over %.1fs, and %d `alive` ticks in the same window."
       % (len(pio), span, len(alive)),
       "Ask the learner what rate they predicted and how the clock divider produces",
       "it: sys_clk / divider, one instruction per cycle unless a delay says otherwise.",
       "Last report: " + pio[-1].raw)


# ---------------------------------------------------------------------------
# lesson 08 -- pio-frames-received
# ---------------------------------------------------------------------------

@command("pio-frames")
def cmd_pio_frames(handle):
    records = collect_while(
        "Reset the adapter Pico first (its RUN button, or replug it) so its startup\n"
        "lines land inside this recording. Then press and release the A key five\n"
        "times.\n"
        "Then press Enter here.", handle=handle)
    backend = require_records(
        records, "backend",
        "Lesson 08 asks your firmware to print `backend: interrupt` or `backend: pio`\n"
        "at startup, saying which receive backend this build selected. Keeping both\n"
        "and choosing between them is the lesson: the interrupt version is the known-\n"
        "good reference the PIO version is debugged against.\n"
        "\n"
        "If you are sure the line is printed: it is printed ONCE, at startup, so the\n"
        "board has to be reset while this check is recording. Reset it and run the\n"
        "check again.")

    which = backend[-1].value.strip()
    if which != "pio":
        fail("this build selected the `%s` backend, not `pio`." % which,
             "",
             "The interrupt backend is the reference and it should stay in the tree --",
             "deleting it is one of the failures this lesson warns about. But this",
             "check is the evidence for the PIO receiver, so it needs a build with the",
             "PIO backend selected. Switch the build option, reflash, and run it again.",
             "",
             "Both backends are expected to pass the `frames-received` check as well.",
             "If the interrupt build passes and the PIO build does not, you have the",
             "known-good reference you need to find out why.")

    frames = frames_of(records)
    good = [f for f in frames if f.is_ok]
    if len(good) < 5:
        fail("the PIO backend produced only %d good frames from five keypresses (%d frames total)."
             % (len(good), len(frames)),
             "",
             "The same bytes that came out of the interrupt backend in lesson 06 must",
             "come out of this one. The three things that go wrong in the PIO version",
             "and not in the interrupt version:",
             "  * sampling on the wrong clock edge -- `wait 0 pin` then `in pins, 1`",
             "    is not the same instant as `wait 1 pin` then `in pins, 1`;",
             "  * an autopush threshold that counts the start and stop bits in, or",
             "    leaves the parity bit out, so the word you pop is shifted;",
             "  * forgetting that the ISR shift register fills from the top when",
             "    shifting right: the byte arrives in the high bits of the 32-bit FIFO",
             "    word and needs shifting down, and it is LSB-first within that.",
             "",
             "Statuses seen: " + ", ".join(sorted({f.status for f in frames}) or ["none"]))

    counts = {}
    for frame in good:
        counts[frame.byte] = counts.get(frame.byte, 0) + 1
    common = sorted(counts.items(), key=lambda kv: -kv[1])
    if common[0][1] < 5:
        fail("no byte value repeated five times for five presses of one key.",
             "Bytes seen: " + ", ".join("%02x x%d" % (b, n) for b, n in common[:12]),
             "",
             "Compare this against what the interrupt backend gives you for the same",
             "key. Two different answers from the same wire is the most useful bug",
             "report you can have, and it is why the reference backend stays.")

    cpu = by_key(records, "cpu")
    if not cpu:
        fail("no `cpu:` record arrived, so the check has no measurement of what the "
             "offload bought.",
             "",
             "Lesson 08 asks for `cpu: <microseconds per 1000 frames>` -- the measured",
             "receive cost, not an estimate. Measure the same way for both backends",
             "and the difference is the answer. A claim without a number is not one of",
             "this course's completion conditions.")
    value = cpu[-1].as_int()
    if value is None:
        try:
            value = float(cpu[-1].value.split()[0])
        except (ValueError, IndexError):
            fail("the `cpu:` record does not start with a number: " + cpu[-1].raw,
                 "It should be microseconds of CPU time per 1000 received frames.")

    ok("the PIO backend receives the same bytes, and the cost is measured.",
       "backend %s, %d frames, %d ok, make code %02x seen %d times."
       % (which, len(frames), len(good), common[0][0], common[0][1]),
       "Measured receive cost: %s microseconds per 1000 frames." % value,
       "Ask the learner for the same number from the interrupt build, and what the",
       "difference is made of -- it is ISR entry and exit, not the framing logic.")


# ---------------------------------------------------------------------------
# lesson 09 -- keyboard-acks-command
# ---------------------------------------------------------------------------

@command("ack")
def cmd_ack(handle):
    records = collect_while(
        "Make the firmware send the keyboard a reset: press the RUN button on the\n"
        "adapter Pico, or unplug and replug it, so the startup code sends 0xFF.\n"
        "Watch the Model M: its three LEDs should flash as it runs its self test.\n"
        "Then press Enter here.", handle=handle)
    tx = require_records(
        records, "tx",
        "Lesson 09 asks your firmware to print `tx: <hex byte sent> <ack|nak|timeout>`\n"
        "for every byte it sends to the keyboard -- for example `tx: ff ack`.")

    resets = [r for r in tx if (r.fields() or [""])[0].lower() in ("ff", "0xff")]
    if not resets:
        fail("no `tx:` line reported sending 0xFF.",
             "",
             "Bytes this firmware said it sent: " +
             ", ".join(sorted({(r.fields() or ["?"])[0] for r in tx})),
             "",
             "0xFF is Reset. It is the command lesson 09 asks for because its effect",
             "is visible from across the room: the keyboard runs its power-on self",
             "test and flashes its LEDs.")

    final = resets[-1]
    status = (final.fields() + ["", ""])[1]
    if status == "timeout":
        fail("the keyboard never acknowledged the 0xFF you sent (`%s`)." % final.raw,
             "",
             "A timeout means the device never clocked your byte out of you. The",
             "host-to-device sequence is fussy and the order is the whole trick:",
             "  1. pull CLOCK low for at least 100us -- this is Inhibit, and it tells",
             "     the keyboard to stop talking;",
             "  2. pull DATA low -- this is the Request-to-Send, and it must happen",
             "     while clock is still held low;",
             "  3. RELEASE CLOCK, and only then. The device now generates every clock",
             "     edge for the transfer, including the ones for your data bits.",
             "Releasing clock before data is down is the usual bug: the keyboard sees",
             "an idle bus, decides nothing was asked of it, and goes back to sleep.",
             "",
             "Also check the direction change: your GPIO must actually let go of the",
             "line (open-drain, input with the pull-up doing the work), not drive it",
             "high. Driving high against the keyboard's low is what the level shifter",
             "is there to survive, but it stops the bus working.")
    if status == "nak":
        fail("the keyboard rejected the byte you sent (`%s`)." % final.raw,
             "",
             "A NAK -- the device pulling DATA high at the ack bit -- means it clocked",
             "your bits in and did not like them. Almost always parity: host-to-device",
             "uses the same ODD parity as device-to-host, over the eight data bits.",
             "Check also that you are sending least significant bit first, and that",
             "you release DATA before the stop bit so the device can drive the ack.")
    if status != "ack":
        fail("the `tx:` line for 0xFF has status %r, which is not one of ack, nak or timeout: %s"
             % (status, final.raw))

    after = [f for f in frames_of(records) if f.t >= final.t and f.is_ok]
    sequence = [f.byte for f in after]
    if 0xFA not in sequence:
        fail("the keyboard acknowledged the 0xFF bit-by-bit, but never sent 0xFA back.",
             "",
             "Bytes received after the command: " +
             (", ".join("%02x" % b for b in sequence[:12]) or "(none)"),
             "",
             "Two different things are both called an acknowledgement here, and this",
             "is the moment to keep them apart. The ACK BIT is the twelfth bit of a",
             "host-to-device frame, driven by the device, and your `tx: ff ack` says",
             "you got it. 0xFA is the ACKNOWLEDGE BYTE, a whole device-to-host frame",
             "sent afterwards to say the command was understood. You have the first",
             "and not the second, so the receiver is probably still inhibited or still",
             "in transmit direction -- turn the line back around and start listening",
             "again as soon as the stop bit is out.")
    index = sequence.index(0xFA)
    rest = sequence[index + 1:]
    if 0xAA not in rest:
        fail("the keyboard acknowledged the reset with 0xFA but never reported a passed self test.",
             "",
             "Bytes after the 0xFA: " + (", ".join("%02x" % b for b in rest[:12]) or "(none)"),
             "",
             "After 0xFA the keyboard runs its Basic Assurance Test and answers 0xAA",
             "if it passed, or 0xFC if it failed. 0xFC is a real answer and means the",
             "keyboard is unhappy, not your code. Nothing at all usually means the",
             "self test takes longer than you waited -- a Model M can take the better",
             "part of a second -- or that you stopped listening after the 0xFA.")

    ok("the keyboard took a command from you and answered it.",
       "%s, then 0xFA (acknowledge), then 0xAA (self test passed)." % final.raw,
       "That is bidirectional traffic on a single open-drain wire that the DEVICE",
       "clocks in both directions. Confirm the learner saw the Model M's LEDs flash.")


# ---------------------------------------------------------------------------
# lesson 10 -- key-events-decoded
# ---------------------------------------------------------------------------

@command("events")
def cmd_events(handle):
    first_pass = collect_while(
        "Press and release the A key five times, slowly, letting it come fully up\n"
        "between presses. Do not hold it down.\n"
        "Then press Enter here.", handle=handle)
    require_records(
        first_pass, "key",
        "Lesson 10 asks your firmware to print `key: <down|up> <name>` for each key\n"
        "event -- for example `key: down LeftShift`. The names are yours, from the\n"
        "table you built; this check reads the direction and the balance, not the\n"
        "spelling.")

    events = key_events(first_pass)
    if not events:
        fail("`key:` lines arrived but none of them parse as an event.",
             *["    " + r.raw for r in by_key(first_pass, "key")[:6]],
             "",
             "The shape is `key: down <name>` or `key: up <name>`. The direction is",
             "the first field and it is spelled `down` or `up`, nothing else.")

    unbalanced, doubles, counts = balance(events)
    names = distinct_names(events)
    downs = [n for d, n in events if d == "down"]
    ups = [n for d, n in events if d == "up"]

    if len(names) > 2:
        fail("five presses of one key produced %d different key names: %s"
             % (len(names), ", ".join(names[:10])),
             "",
             "The prefixes are being decoded as keys in their own right. 0xE0 is not a",
             "key: it says the NEXT byte belongs to the extended set. 0xF0 is not a",
             "key either: it says the next byte is a release. Both must be consumed as",
             "state by the decoder and never emitted.")
    if len(downs) != 5 or len(ups) != 5:
        if len(downs) > len(ups):
            diagnosis = [
                "More downs than ups means the break code is not being decoded. In scan",
                "code set 2 a release is the TWO bytes F0 <make>. It is not the make",
                "code with bit 7 set -- that rule belongs to set 1, it is what most web",
                "pages show first, and it is the single most common way this lesson",
                "goes wrong. The keyboard is speaking set 2 unless you asked it not to.",
                "",
                "Many more downs than ups also means typematic repeat is being read as",
                "new presses: a held key repeats its make code about ten times a second,",
                "and that is the same key still down, not a second press.",
            ]
        else:
            diagnosis = [
                "More ups than downs means a release is being emitted for something",
                "that was never pressed. Look at the extended-key path: an extended",
                "release is the THREE bytes E0 F0 <make>, and decoding the F0 without",
                "having consumed the E0 produces an event for the wrong key.",
            ]
        fail("five presses produced %d down events and %d up events, not five of each."
             % (len(downs), len(ups)),
             "",
             "Counts per name: " + ", ".join("%s x%d" % (n, counts[n]) for n in names),
             "",
             *diagnosis)
    if doubles:
        fail("a key went down twice with no release in between: " +
             ", ".join(sorted(set(doubles))),
             "",
             "That is typematic repeat being read as a new press, or a make code",
             "arriving while your state says the key is already down. Either way the",
             "decoder has to notice: a repeat of a make code for a key that is already",
             "held is a repeat, not an event.")
    if unbalanced:
        fail("these keys were still down when the check ended: " + ", ".join(unbalanced),
             "A key with no matching up event is a stuck key, and lesson 14 depends on",
             "this being right before it starts.")

    second_pass = collect_while(
        "Now press and release EVERY key on the keyboard once, working across the\n"
        "board left to right, top to bottom. Include the whole keypad, both shifts,\n"
        "and -- specifically -- Print Screen and Pause, which do not behave like the\n"
        "others on this wire.\n"
        "Then press Enter here.", handle=handle)

    events2 = key_events(second_pass)
    unbalanced2, doubles2, counts2 = balance(events2)
    names2 = distinct_names(events2)

    suspicious = [n for n in names2 if n.strip().lower() in SUSPICIOUS_NAMES]
    if suspicious:
        fail("these came out as key names and are not keys: " + ", ".join(suspicious),
             "",
             "E0 and F0 are prefixes, not keys. Seeing one as a name means the decoder",
             "emitted an event while it should have been waiting for the byte the",
             "prefix introduces.")
    if unbalanced2:
        fail("%d key%s left down at the end of the sweep: %s"
             % (len(unbalanced2), "" if len(unbalanced2) == 1 else "s",
                ", ".join(unbalanced2[:12])),
             "",
             "Every key was pressed and released, so every down must have an up.",
             "Pause is the one that catches people: it sends a fixed eight-byte",
             "sequence with NO break code at all, so its release has to be synthesised",
             "by your decoder. Print Screen is the other: E0 12 E0 7C going down and",
             "E0 F0 7C E0 F0 12 coming up, which is easy to decode as two keys.")
    if doubles2:
        note("%d key%s repeated without an intervening release (%s). Held a little"
             % (len(set(doubles2)), "" if len(set(doubles2)) == 1 else "s",
                ", ".join(sorted(set(doubles2))[:8])),
             "long during the sweep is enough to do that, so it is not a failure here --",
             "but check the repeat is being suppressed and not re-emitted.")
    if len(names2) < 80:
        fail("the sweep produced only %d distinct key names." % len(names2),
             "",
             "A Model M has 101 or 102 keys and the completion condition for this",
             "lesson is that every physical key produces one distinct, correctly-named",
             "event. Fewer distinct names than keys pressed means several keys are",
             "landing on the same name -- usually the extended set colliding with the",
             "base set, because E0 1C and 1C are different keys and must not decode",
             "to the same thing.",
             "",
             "Names seen (%d): %s" % (len(names2), ", ".join(names2[:40])))

    interesting = [n for n in names2 if "pause" in n.lower() or "print" in n.lower()]
    if interesting:
        note("Names that look like the awkward two: " + ", ".join(interesting))
    else:
        note("Nothing in the names looks like Pause or Print Screen. This check does",
             "not police your spelling, so that may be fine -- but confirm with the",
             "learner that both keys produced an event, since they are the two that",
             "do not follow the normal make/break rules.")

    ok("scan codes are decoding to balanced, distinct key events.",
       "Five presses of one key: 5 down, 5 up, one name (%s)." % names[0],
       "Full sweep: %d events, %d distinct names, every down matched by an up."
       % (len(events2), len(names2)))


# ---------------------------------------------------------------------------
# lesson 14 -- no-stuck-keys
# ---------------------------------------------------------------------------

def check_reports(records, where):
    reports = by_key(records, "report")
    if not reports:
        return []
    parsed = []
    for record in reports:
        values = report_bytes(record)
        if values is None:
            fail("a `report:` line in %s is not eight hex bytes: %s" % (where, record.raw),
                 "",
                 "The shape is `report: 00 00 04 00 00 00 00 00` -- eight values, hex,",
                 "space separated, exactly as sent to the host.")
        if len(values) != 8:
            fail("a `report:` line in %s carries %d bytes, not eight: %s"
                 % (where, len(values), record.raw),
                 "",
                 "Nine bytes is the signature of a report ID having crept in, and a",
                 "report ID breaks boot protocol -- the BIOS reads a fixed eight-byte",
                 "layout with no ID and will not understand a ninth byte. The usual",
                 "cause is a second top-level collection on this interface, which",
                 "forces IDs on every report. A debug or vendor channel belongs on a",
                 "SEPARATE interface, which is exactly what the offered lesson does.",
                 "",
                 "Fewer than eight bytes means the report is not the boot layout at",
                 "all: modifier bitmap, reserved byte, six key slots.")
        parsed.append((record, values))
    return parsed


@command("reports")
def cmd_reports(handle):
    typing = collect_while(
        "Type this sentence on the Model M at your normal speed, then take your\n"
        "hands off the keyboard completely:\n"
        "    the quick brown fox jumps over the lazy dog\n"
        "Then press Enter here.", handle=handle)
    require_records(
        typing, "report",
        "Lesson 14 asks your firmware to print `report: <eight bytes in hex>` for\n"
        "every HID report it sends to the host, and `held: <n>` for the number of\n"
        "keys the state bitmap currently has down.")

    parsed = check_reports(typing, "the typing run")
    if len(parsed) < 8:
        fail("only %d reports were sent while a whole sentence was typed." % len(parsed),
             "",
             "Each key produces at least two reports: one with the key in a slot, one",
             "with it gone. A sentence should be dozens. Too few means reports are",
             "being built but not sent -- or that the change detection thinks nothing",
             "changed. Check that you compare the WHOLE eight bytes, including the",
             "modifier byte, when you decide whether to send.")

    for record, values in parsed:
        if values[1] != 0x00:
            fail("a report has a non-zero reserved byte: %s" % record.raw,
                 "",
                 "Byte 1 of the boot keyboard report is reserved and must always be",
                 "zero. It is not a seventh key slot and it is not spare space. A host",
                 "in boot protocol reads a fixed layout: byte 0 modifiers, byte 1",
                 "reserved, bytes 2 to 7 the six key slots. Putting anything in byte 1",
                 "shifts the meaning of everything a BIOS reads.")
        for slot, value in enumerate(values[2:], start=2):
            if 0xE0 <= value <= 0xE7:
                fail("a modifier usage (0x%02x) is in key slot %d: %s"
                     % (value, slot - 1, record.raw),
                     "",
                     "0xE0 to 0xE7 are the modifier usages -- the control, shift, alt",
                     "and GUI keys -- and in this report they belong in the BITMAP in",
                     "byte 0, one bit each, not in the six-key array. Putting them in",
                     "the array is the same conceptual mistake as declaring them as an",
                     "array in the report descriptor, and the host will honour the",
                     "descriptor rather than your intent: it reads byte 0 for shift and",
                     "finds nothing, so capital letters never arrive.")

    duplicates = 0
    for index in range(1, len(parsed)):
        if parsed[index][1] == parsed[index - 1][1]:
            duplicates += 1
    if duplicates > len(parsed) // 4:
        note("%d of %d reports are identical to the one before them. The design says"
             % (duplicates, len(parsed)),
             "reports are sent ON CHANGE, not per PS/2 event. That is not failed here,",
             "but a stream of identical reports means the state bitmap is the source of",
             "truth in name only.")

    final_record, final_values = parsed[-1]
    if any(final_values):
        fail("the last report sent was not empty: %s" % final_record.raw,
             "",
             "Every key was released before Enter was pressed, so the last thing the",
             "host should have been told is all zeros: no modifiers, no keys. A",
             "non-empty final report is a stuck key -- on a real host it types that",
             "character forever and the only way out is unplugging the adapter.",
             "",
             "The cause is nearly always sending one report per PS/2 EVENT instead of",
             "one per STATE CHANGE: when two events land between polls, the host sees",
             "only the last one, and a release that shared a poll with a press is lost.")

    held = last(typing, "held")
    if held is None:
        fail("no `held:` record arrived.",
             "Lesson 14 asks for `held: <n>`, the number of keys the state bitmap has",
             "down. It is what makes 'no key is stuck' checkable rather than asserted.")
    if held.as_int() != 0:
        fail("the firmware still believes %s key(s) are held after everything was released."
             % held.value,
             "",
             "The reports went empty but the state bitmap did not, so the two have",
             "diverged -- which means the reports are not being built from the bitmap.",
             "The bitmap is meant to be the single source of truth: PS/2 events mutate",
             "it, HID reports are snapshots of it. Anything else and they drift.")

    rollover = collect_while(
        "Now press and hold SEVEN keys at once -- use both hands, and pick keys far\n"
        "apart on the board so the keyboard's own matrix can see them all. Hold for\n"
        "about two seconds, then release everything.\n"
        "Then press Enter here.", handle=handle)
    rollover_parsed = check_reports(rollover, "the rollover run")
    if not rollover_parsed:
        fail("no reports at all arrived while seven keys were pressed.",
             "Either nothing was pressed, or the report path stopped. Try again.")

    overflow = [r for r, v in rollover_parsed if all(b == 0x01 for b in v[2:])]
    max_keys = max(len([b for b in v[2:] if b]) for _r, v in rollover_parsed)
    if not overflow:
        fail("seven keys were pressed and no ErrorRollOver report was sent.",
             "",
             "The most keys seen in one report was %d." % max_keys,
             "",
             "The boot report has six key slots. When a seventh key goes down the",
             "specification's answer is not to drop it silently: it is to fill all six",
             "slots with 0x01, ErrorRollOver, which tells the host 'more keys are down",
             "than I can describe'. Silently losing the seventh is worse than useless,",
             "because the typist gets a missing character with no indication why.",
             "",
             "If the report never showed more than %d keys, the Model M's own matrix"
             % max_keys,
             "may be the limit rather than your firmware -- a membrane keyboard ghosts",
             "and blocks. Pick keys in different rows and columns and try again; if it",
             "still caps below six, that is the keyboard, and worth saying out loud.")

    tail = last(rollover, "held")
    if tail is not None and tail.as_int() not in (0, None):
        fail("after releasing all seven keys the firmware still holds %s." % tail.value,
             "Releases under rollover are where a state bitmap earns its keep: the",
             "seventh key's release must clear its bit even though it was never in a",
             "report.")

    ok("reports are well-formed, state-driven, and no key is left stuck.",
       "%d reports while typing, reserved byte zero throughout, no modifier in a key slot."
       % len(parsed),
       "Final report all zeros and `held: 0`.",
       "Seven keys produced %d ErrorRollOver report(s), and the release cleared them."
       % len(overflow))


# ---------------------------------------------------------------------------
# lesson 17 -- survives-abuse
# ---------------------------------------------------------------------------

@command("robustness")
def cmd_robustness(handle):
    problems = []
    findings = []

    # 1. boots with nothing attached
    phase1 = collect_while(
        "Unplug the KEYBOARD from the adapter, leaving the adapter powered.\n"
        "Now reset the adapter Pico (its RUN button, or replug its USB).\n"
        "Wait about five seconds for it to boot with no keyboard present.\n"
        "Then press Enter here.", handle=handle, min_seconds=3.0)
    alive1 = by_key(phase1, "alive")
    ps2_1 = [r.value.strip() for r in by_key(phase1, "ps2")]
    if len(alive1) < 2:
        problems.append((
            "boot with no keyboard", [
                "only %d `alive` line(s) arrived after a reset with no keyboard attached."
                % len(alive1),
                "The firmware wedged waiting for hardware that is not there. This is the",
                "state the finished object will most often start in -- plugged into a PC",
                "that powers up before the keyboard is connected -- so it has to be the",
                "normal case, not the error case. Look for a blocking wait in startup:",
                "a loop waiting for a first clock edge, or a reset command that waits",
                "forever for an 0xFA that will never come."]))
    if "absent" not in ps2_1:
        problems.append((
            "absent keyboard reported", [
                "no `ps2: absent` record arrived while the keyboard was unplugged.",
                "ps2 records seen: " + (", ".join(ps2_1) or "(none)"),
                "Lesson 17 asks the firmware to say what it believes about the keyboard:",
                "absent, present or reset-ok. Knowing the difference between 'no keyboard'",
                "and 'keyboard saying nothing' is what makes hot-plug possible."]))
    else:
        findings.append("booted with no keyboard, stayed alive, reported `ps2: absent`")

    # 2. picks it up when plugged in
    phase2 = collect_while(
        "Now plug the keyboard back into the adapter. Wait two seconds, then type\n"
        "a few keys.\n"
        "Then press Enter here.", handle=handle, min_seconds=2.0)
    ps2_2 = [r.value.strip() for r in by_key(phase2, "ps2")]
    good2 = [f for f in frames_of(phase2) if f.is_ok]
    if not ({"present", "reset-ok"} & set(ps2_2)):
        problems.append((
            "hot-plug detection", [
                "the keyboard was plugged in and no `ps2: present` or `ps2: reset-ok`",
                "record followed. ps2 records seen: " + (", ".join(ps2_2) or "(none)"),
                "Nothing tells the firmware a keyboard appeared; it has to notice. The",
                "Model M announces itself -- it runs its self test on power-up and sends",
                "0xAA -- and beyond that, the arrival of any valid frame after a silence",
                "is evidence. Detecting it at boot only is the failure this phase looks for."]))
    if len(good2) < 2:
        problems.append((
            "traffic after hot-plug", [
                "only %d good frame(s) arrived after the keyboard was plugged back in."
                % len(good2),
                "The receiver did not come back. Re-arming after an absence usually means",
                "clearing the framing state machine and any partial byte before the first",
                "new edge arrives -- a half-assembled byte from before the unplug will",
                "swallow the first bits of the first new frame."]))
    else:
        findings.append("picked the keyboard up on hot-plug and resumed receiving")

    # 3. no key left held when it is unplugged mid-press
    phase3 = collect_while(
        "Now press and HOLD a letter key, and while it is still held down, unplug\n"
        "the keyboard from the adapter.\n"
        "Then press Enter here.", handle=handle, min_seconds=2.0)
    held3 = last(phase3, "held")
    reports3 = [report_bytes(r) for r in by_key(phase3, "report")]
    reports3 = [v for v in reports3 if v and len(v) == 8]
    if held3 is None or held3.as_int() not in (0,):
        problems.append((
            "held keys released on unplug", [
                "after the keyboard was pulled out mid-press the firmware reports %s."
                % (("`held: " + held3.value + "`") if held3 else "no `held` record at all"),
                "A key that was down when the wire went away is down forever: no break",
                "code is ever coming. The host is still being told that key is pressed,",
                "and on a real machine it repeats that character until the adapter is",
                "unplugged too. Losing the device must release everything it was holding."]))
    elif reports3 and any(reports3[-1]):
        problems.append((
            "final report after unplug", [
                "the last report after the unplug was not empty: " +
                " ".join("%02x" % b for b in reports3[-1]),
                "`held` reached zero but the host was never told. Clearing the state",
                "bitmap has to produce a report, or the host keeps the last one it saw."]))
    else:
        findings.append("released every held key when the keyboard was pulled out mid-press")

    # 4. resync rather than latch
    phase4 = collect_while(
        "Plug the keyboard back in. Now induce a framing error on purpose: briefly\n"
        "touch the PS/2 CLOCK line to ground while typing. Then keep typing for a\n"
        "few more seconds.\n"
        "Then press Enter here.", handle=handle, min_seconds=2.0)
    _f, _l, resync_delta = counter_delta(phase4, "resync")
    frames4 = frames_of(phase4)
    bad4 = [f for f in frames4 if not f.is_ok]
    if bad4:
        recovered4 = [f for f in frames4 if f.is_ok and f.t > bad4[-1].t]
    else:
        recovered4 = [f for f in frames4 if f.is_ok]
    if not resync_delta and not bad4:
        problems.append((
            "error detection", [
                "no resync and no bad frame: the induced error was not noticed.",
                "Either the glitch did not land, or a truncated frame leaves no trace.",
                "Try again with a cleaner short of clock to ground mid-frame; if it is",
                "still silent, the receiver has no idle timeout and does not know a",
                "frame was cut short."]))
    elif len(recovered4) < 2:
        problems.append((
            "recovery from a framing error", [
                "the error was noticed (resync moved by %s, %d bad frame(s)) but only %d"
                % (resync_delta, len(bad4), len(recovered4)),
                "good frame(s) followed. The receiver latched. One parity error must",
                "cost you one byte, not the session: drop the partial byte, return to",
                "waiting for a start bit, carry on."]))
    else:
        findings.append("resynchronised after an induced framing error (resync +%s, %d good frames after)"
                        % (resync_delta, len(recovered4)))

    # 5. USB suspend, resume and remote wakeup
    phase5 = collect_while(
        "Last one, and it takes a minute. Put the HOST to sleep -- close the lid, or\n"
        "use its sleep command -- with the adapter plugged into it. Wait until it is\n"
        "properly asleep. Then wake it by pressing a key on the Model M, not by\n"
        "touching the host.\n"
        "Then press Enter here.", handle=handle, min_seconds=3.0)
    usb5 = [r.value.strip() for r in by_key(phase5, "usb")]
    missing = [want for want in ("suspended", "wakeup-sent", "resumed") if want not in usb5]
    if missing:
        problems.append((
            "suspend, wakeup and resume", [
                "these USB states were never reported: " + ", ".join(missing),
                "usb records seen: " + (", ".join(usb5) or "(none)"),
                "",
                "An ordinary keyboard wakes the machine it is plugged into, and that is",
                "not automatic: the device must set the remote-wakeup bit in its",
                "configuration descriptor, the host must then grant it, and the device",
                "must signal resume on the bus when it has something to say. Missing",
                "`suspended` means the suspend callback is not wired up (or the host",
                "never suspended -- some hosts keep the bus alive on mains power, so try",
                "on battery). Missing `wakeup-sent` means the key was seen but the",
                "wakeup was never requested. Missing `resumed` with the others present",
                "means the host ignored the request, which is what happens when the",
                "descriptor never claimed the capability."]))
    else:
        findings.append("suspended, sent a remote wakeup on a keypress, and resumed")

    if problems:
        lines = ["the adapter did not survive %d of the five things lesson 17 asks of it."
                 % len(problems), ""]
        for name, detail in problems:
            lines.append("  [%s]" % name)
            lines += ["    " + line for line in detail]
            lines.append("")
        if findings:
            lines.append("  What did work:")
            lines += ["    * " + f for f in findings]
        fail(*lines)

    ok("the adapter behaves when things are not ideal.",
       *["  * " + f for f in findings])


# ---------------------------------------------------------------------------
# offered lesson -- safety-catch-works
# ---------------------------------------------------------------------------

@command("safety")
def cmd_safety(handle):
    blocked = collect_while(
        "Leave the enable pin (GP4) completely unconnected -- floating, nothing\n"
        "touching it. Now type several keys on the Model M, including a few letters\n"
        "you would notice if they escaped.\n"
        "Then press Enter here.", handle=handle, min_seconds=2.0)
    states = [r.value.strip() for r in by_key(blocked, "safety")]
    if not states:
        fail("no `safety:` records arrived.",
             "",
             "This lesson asks the firmware to print `safety: armed` or",
             "`safety: blocked` so the gate's state is observable. A gate you cannot",
             "see the state of is a gate you have to trust, and the whole point of the",
             "exercise is not having to.",
             describe_traffic(blocked))
    if "armed" in states:
        fail("the safety catch reported `armed` with the enable pin left floating.",
             "",
             "safety records seen: " + ", ".join(states),
             "",
             "This is the failure the lesson is named for: failing OPEN. A floating",
             "input on the RP2040 is not low and not high -- it is whatever the last",
             "charge and the nearby traces make it, and it will read as enabled",
             "sometimes and not others. Enable the internal pull-up and make the",
             "DISARMED state the one a disconnected pin produces; grounding the pin is",
             "then a positive, deliberate act.")
    if "blocked" not in states:
        fail("the safety catch never reported `blocked` with the pin floating.",
             "safety records seen: " + ", ".join(states))

    sent = [v for v in (report_bytes(r) for r in by_key(blocked, "report")) if v]
    leaked = [v for v in sent if any(v)]
    if leaked:
        fail("%d non-empty HID report%s was sent to the host while the catch was blocked."
             % (len(leaked), "" if len(leaked) == 1 else "s"),
             *["    " + " ".join("%02x" % b for b in v) for v in leaked[:6]],
             "",
             "The gate is in the wrong place. It has to sit BEFORE the report is",
             "queued, not after -- a report that has been handed to the USB stack is",
             "already the host's, and suppressing the next one does not recall it.",
             "Gate the send, not the sending.")

    armed = collect_while(
        "Now connect the enable pin (GP4) to ground, and type a few keys again.\n"
        "Then press Enter here.", handle=handle, min_seconds=2.0)
    states2 = [r.value.strip() for r in by_key(armed, "safety")]
    if "armed" not in states2:
        fail("grounding the enable pin did not arm the catch.",
             "safety records seen: " + (", ".join(states2) or "(none)"),
             "",
             "Blocked in both states is safe and useless. Check which way round the",
             "test is: with a pull-up, the pin reads HIGH when floating (blocked) and",
             "LOW when grounded (armed).")
    sent2 = [v for v in (report_bytes(r) for r in by_key(armed, "report")) if v]
    live = [v for v in sent2 if any(v)]
    if not live:
        fail("the catch armed, but no report with a key in it followed.",
             "%d report(s) were sent and all of them were empty." % len(sent2),
             "",
             "Arming has to restore normal service, not merely stop blocking. If the",
             "gate drops events while disarmed rather than suppressing reports, the",
             "key state your reports are built from is now wrong as well.")

    ok("the safety catch fails safe and arms deliberately.",
       "Pin floating: `blocked`, and %d report(s) sent, none carrying a key." % len(sent),
       "Pin grounded: `armed`, and %d report(s) carrying keys." % len(live),
       "Confirm with the learner that this was tested against a build they know is",
       "misbehaving -- a catch only proves itself in front of firmware that would",
       "otherwise type into whatever has focus.")


# ---------------------------------------------------------------------------

def usage():
    print(__doc__.strip().splitlines()[0])
    print("")
    print("usage: python3 checks/console.py <subcommand>")
    print("")
    print("subcommands: " + ", ".join(sorted(COMMANDS)))


def main(argv):
    if len(argv) != 2 or argv[1] in ("-h", "--help", "help"):
        usage()
        return EXIT_SETUP if len(argv) != 2 else EXIT_OK
    name = argv[1]
    if name not in COMMANDS:
        print("CANNOT CHECK: there is no console check called %r." % name, file=sys.stderr)
        print("      Known checks: " + ", ".join(sorted(COMMANDS)), file=sys.stderr)
        return EXIT_SETUP
    handle = open_console()
    try:
        COMMANDS[name](handle)
    finally:
        try:
            handle.close()
        except Exception:
            pass
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv))
