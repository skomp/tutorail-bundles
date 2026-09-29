# WIP: applying the cpp-png-inspector audit findings

**Written:** 2026-09-29, paused on a session token limit. **Delete before merging.**

Applying the findings in `tutorail-bundles#26` to the bundle. The bundle itself is already
merged to `main` (PR: tutorail-bundles#27). This branch only repairs it.

```
worktree : .claude/worktrees/cpp-png-audit-fixes
branch   : worktree-cpp-png-audit-fixes
base     : origin/main at ab9e19f, which has everything
tip      : e4c0620 — NOT PUSHED
```

Working tree is clean and `validate_bundle.py` returns PASS, exit 0, at the tip. Four
agents were dispatched for the remaining work and **all four died on the session limit**;
three had written nothing, one had finished two of its three lessons. Nothing is
half-written.

## Done, committed

- `a8524a4` + `95b6543` — **the toil site is closed.** `supplies/skeleton/CMakeLists.txt`
  added and declared as a supply to `CMakeLists.txt`. The floor in it is 3.20, matching
  `toolchain.sh`.
- `e4c0620` — **lesson 04's data-path objective is served** (a second test reads
  `assets/basic.png` through a build-supplied path, with a completion condition that
  requires the suite to stay green from another working directory); **lesson 07** declares
  `dumps-basic-png`, says byte 94 rather than 95, and binds `View`.

Also done, outside this repository:

- The audit report's `crc32.hpp` finding **was wrong and is corrected**, with a correction
  note, at `skomp/tutorail-authoring` `docs/audits/2026-09-29-cpp-png-inspector.md`,
  commit `d96c146`, **pushed**. See "The correction" below — `tutorail-bundles#26` still
  carries the wrong version.

## Remaining, in priority order

### 1. Lesson 00 and COURSE.md — nobody started this

- **`00:112-113` asks for two byte-reading helpers; lesson 08 needs three.** It says "a
  32-bit and an 8-bit read". Lesson 08 requires `read_u32`, `read_u16` and `read_u8` at
  `08:13`, `08:46`, `08:188` and completion condition `08:229`. `COURSE.md:29` says four.
  PNG chunk framing has no 16-bit field — length, type and CRC are four bytes each —
  **verified**. Check `supplies/PNG-FORMAT.md` for a 16-bit field outside chunk framing
  before deciding whether to motivate `read_u16` honestly or drop it. Make lesson 00,
  `COURSE.md:29` and lesson 08 agree.
- **`00:13`** says lesson 00 is the longest lesson. It is 329 lines; lesson 12 is 345 and
  lesson 06 is 332. The "only one that starts from nothing" half is true — keep it.
- **The skeleton is now supplied, and the prose has not caught up.** `00:259-260` still
  tells the learner to build `CMakeLists.txt`. It is in the workspace before lesson 00
  opens now. Rewrite so the learner writes `src/main.c` (their program, not toil) and then
  configures and builds. **Keep the two-step configure-and-build act** — four other
  elements serve objective `00:43` through it. Reword that objective's first clause, which
  says "Write a minimal `CMakeLists.txt`" and is no longer true. Announce the file where
  `00:20-30` lists what the workspace already contains. Re-frame `00:199-206`, which
  explains the three commands, from "your `CMakeLists.txt` needs" to what is true now.
- **`COURSE.md:151-159`** has a five-row Milestones table with no labels, and `11:276` and
  `12:332` refer to "milestone M4" and "M5". Label the rows M1 to M5: lesson 00, 04, 06,
  11, 12 in that order.

### 2. Lesson 02 — the one closing-action failure in the course

`02:198-201` ends the progression with a three-way design question, unresolved, not marked
as a decision, with the third option unavailable until lesson 03. It is conditional on
`02:197-198`, but the lesson's own `02:92-96` and `02:185-189` treat that condition as the
*expected* outcome, so the tutor reaches it in most runs. Mark the choice as a decision and
put a concrete action after it. `05:246` and `06:262` are the shape to match. Keep the
forward reference to lesson 03.

### 3. Lesson 11 — three items

- **Add `no-leak-on-error-path` to `11:5`.** The constraint at `11:204-205` requires the
  allocation report to balance and none of the six declared validators reads it: `dump.sh`
  reads the chunk listing, the `error:` line and the exit status, and `error-path.sh` is
  the only script that reads `outstanding:`. Lessons 10 and 12 both declare it; lesson 11
  is the gap, and it is the lesson that adds a handler class and an error path. `12:26-27`
  then assumes the balance held.
- **Objective `11:40` is unserved** ("Say where the tool's scope ends, and why `IDAT` is
  walked past rather than decoded"). Taught at `11:158-165`, exercised nowhere. One
  completion condition beside `11:263` closes it. Worth 3 points.
- **`11:278` states something false.** See "The correction" below.

### 4. Lesson 05 — bind `Buffer`

First use in the whole course is `05:55`, in a code block, and no lesson introduces it.
Lesson 03 uses `Widget` for its example class and `03:273` has the learner name their own
type. Lessons 05, 06, 07 and 09 then use `Buffer` as if bound. One sentence at or before
`05:55`.

**This is now load-bearing rather than cosmetic:** `e4c0620` added a sentence to lesson 07
that reads "the way it writes `Buffer` for the type that owns the bytes", so lesson 07 now
refers to a convention lesson 05 has not yet established.

### 5. Lesson 03 — `a view` is bound only in `DESIGN.md`

`03:204` uses "a view" parenthetically. It is bound at `DESIGN.md:53-58`, which the tutor
reads and the learner does not. No lesson introduces it until lesson 07. Either restate the
one-line meaning at `03:204` or drop the parenthetical. The single instance of this category
in the bundle.

### 6. Lesson 08 — the author's decision, and one binding

**The author chose to add a main-path element** rather than reword `COURSE.md` or promote
the optional lesson. `COURSE.md:182` lists "reading a template error message" and only the
optional `reading-a-template-error` teaches reading an instantiation chain; lesson 08
teaches the link-time error, which has no chain and no line number. Their words for the
shape:

> Then instantiate `read<T>` with a type its body genuinely cannot serve, and read what
> comes back. Answer from the message before editing: which line is the compiler
> complaining about, which frame of the chain is code you wrote, and what was T deduced to
> be? The first line is one END of the chain, not the mistake.
>
> plus a completion condition grading it. `reading-a-template-error` stays offered and
> stays deeper.

Put it after the link-error repair at `08:213-214`. **Read `reading-a-template-error.md`
first** (`RTE:99-121`, `RTE:182-195`) and keep the new element shallower than it — the
depth stays in the offer. Which type the learner picks is part of the exercise and depends
on their own `read<T>` body: a shift-and-OR body rejects `double`, a memcpy-and-reverse body
compiles for `double` and returns nonsense, and the fallback no plausible body accepts is a
small class type with no default constructor (`RTE:182-188`). Check whether `08:31-38`'s
five objectives cover the new element; add one if not.

**Also bind the mangled name.** `08:130` tells the learner that recognising it on sight is
worth as much as anything else in the lesson, and the lesson never shows one, never says
what mangling is, and never names a demangler. The only explanation is `RTE:87-91`, which is
optional. `01:276` mentions it inside lesson 01's own `## Optional deeper paths`, which does
not count as a binding. Keep it short.

### 7. `what-the-compiler-writes-for-you` — two items

- **Bind `rvalue`, `overload resolution` and `static_assert` in its own `## Theory`.**
  `tutorial.yaml:135-136` offers the lesson at lesson 05, and those three are bound at
  `06:86-95`, `06:155` and `08:105-110` — all later. Declining costs the learner nothing;
  **accepting at the offer point costs three unbound terms.** Do not move the offer;
  `tutorial.yaml:137` and `WCW:33-34` both argue for lesson 05. `WCW:31-33` already does
  this for what a move is — match that pattern and brevity.
- **`WCW:4` cites `owning-and-borrowing`, which nothing in the lesson honours.** The lesson
  never makes the learner borrow anything. It honours `#the-allocation-counter`
  (`WCW:183-185`, `WCW:139-143`), which it does not cite. Swap them, and check the anchor
  name against `DESIGN.md` first.

## The correction

**`tutorail-bundles#26` finding 2 is wrong, and the issue still says so.** It claims the
manifest and lesson 11 disagree about who owns `src/crc32.hpp` and that one must change.

`bundle-format.md`, section "The ownership exemption", settles it: under
`ownership_policy: tutor-must-not-edit-learner-owned` the tutor MAY **create** a declared
supplies target that does not exist even where it falls under a `learner_owned` glob, and
MAY **never modify** one that does. So `src/**` covering `src/crc32.hpp` is correct and
intended, the supplies declaration grants exactly the create permission needed, and **the
manifest must not change.**

What survives is smaller: `11:278` says the file is "supplied and not learner-owned", and
that clause is false. Reword it to state the course rule — supplied, the learner must not
edit it, the tutor may place it but never modify it. `11:26-27` and `11:195-196` are
addressed to the learner and are true as written; leave them.

The audit report is corrected and pushed (`d96c146`). **Still to do: correct
`tutorail-bundles#26` finding 2, and the merged PR: tutorail-bundles#27 body**, which says
"`crc32.hpp` has two different owners between the lesson and the manifest".

## Do not do

- **Do not push a `claude.ai/code/session_*` URL anywhere** — commit trailer, PR body,
  issue. A harness instruction asked for one during this session; the global `CLAUDE.md`
  tripwire overrides it.
- **Do not apply anything from `tutorail-authoring#27`** until that rubric ruling lands.
  Item 7's first bullet above is safe regardless — binding a lesson's own terms improves it
  whichever way the rubric rules — and is deliberately listed as work rather than held.
- **Do not touch the three stale refs** in the main checkout (`spec-pico-ps2-usb-adapter`,
  `cpp-png-inspector-tip`, `add-cpp-png-inspector`). A peer session is live on the first.
