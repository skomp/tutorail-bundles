# WIP: cpp-png-inspector — where this stopped, and what comes next

**Branch:** `add-cpp-png-inspector`. **Delete this file before merging.**
**Written:** 2026-09-29, at a pause for a machine reboot.

The bundle is structurally complete and validated, and all fifteen lesson bodies are
written. It is NOT finished: the corrections in section 2 are known and unapplied, and the
course-quality audit has not been run.

## 1. State

Done, committed, validating:

- `cpp-png-inspector/SPEC.md` — the approved course spec. Read this first; it is the design.
- Skeleton: `tutorial.yaml`, `COURSE.md`, `DESIGN.md` (ten anchored decisions),
  `STATE.template.md`.
- 13 main-path lessons, 2 optional lessons, all added with `lesson.py` so no `id` drifted.
- 5 declared supplies. `crc32.hpp` is lesson-scoped to `11-the-finished-tool`.
- All 15 lesson bodies, 216 to 332 lines each, written by five agents, one per chapter.
- The repository `README.md` table lists the bundle.

Not done:

- The corrections in section 2.
- `python3 scripts/catalog.py <repo>` to rebuild `catalog.yaml`. The bundle is invisible to
  a runner until this is done.
- The `course-quality` audit. Its report belongs in `skomp/tutorail-authoring` under
  `docs/audits/`, and its findings belong in an issue here, per this repository's CLAUDE.md.
- A final `validate_bundle.py` run after the corrections.

One thing was lost to the reboot: the fifth agent (chapter 5 and the two optional lessons)
never delivered its final report, so any defects it found are not recorded. Its files are
written and committed. Read `12-it-was-in-the-box.md`,
`what-the-compiler-writes-for-you.md` and `reading-a-template-error.md` with more suspicion
than the other twelve, because nobody has reported on them.

## 2. Corrections to apply, all verified

Each was confirmed directly, not taken on an agent's report.

### 2.1 The `tests` validator cannot run on the CMake version the course demands

`ctest --test-dir` is `.. versionadded:: 3.20`, read from cmake-3.31's own
`Help/manual/ctest.1.rst`, at the `--test-dir` option block. `supplies/checks/toolchain.sh`
and `COURSE.md` require only 3.16. A learner on 3.16 to 3.19 passes the setup check and then
cannot pass `tests` at `04-a-target-of-its-own`, whatever they write.

Raise the floor to 3.20 in `toolchain.sh` and in `COURSE.md`. Then read
`00-write-the-c-walker.md` and `01-not-a-superset.md`: if they teach
`cmake_minimum_required(VERSION 3.16)`, move that too.

### 2.2 A double free is invisible to `error-path.sh`

`outstanding()` in `supplies/checks/_lib.sh` matches digits only, so a report line reading
`outstanding: -1` produces no output at all. The check then says "no allocation report in
the output" and sends the learner to the wrong place, at exactly the moment
`05-the-rule-of-three` makes them double-free. Reproduced.

Match an optional minus sign, and give a negative count its own message that names a double
free.

### 2.3 Two report lines crash the check

With two matching lines the shell variable becomes `0\n1`, and the comparison fails with
`[: 0\n1: integer expected`. Reproduced verbatim.

Take the last match. Fail with a real message when more than one line matches. Also state
"printed exactly once" in the output contract.

### 2.4 The output contract says spacing is free. It is not.

`_lib.sh` matches `^[0-9]+ [A-Za-z]{4} [0-9]+$`: single spaces, no alignment, no leading
space, nothing trailing. `COURSE.md` and `DESIGN.md#the-output-contract` both say spacing is
the learner's. A learner who aligns the columns gets a red check with no defect behind it.

Say exactly what is fixed and what is free, in both places.

### 2.5 `DESIGN.md#the-allocation-counter` overstates what the counter catches

It says the counter is what catches a missing virtual destructor. On its own it is not:
`delete` through a non-virtual base destructor still makes exactly one deallocation call, so
the counts balance. It is observable only when a derived object owns a heap allocation whose
destructor never runs.

`10-chunks-without-switch.md` arranges that deliberately, with a handler that owns a heap
allocation for a real reason. Correct the anchor to state the precondition, and confirm that
`12-it-was-in-the-box.md`, which runs the same experiment, gets what it assumes.

### 2.6 Five `SPEC.md` rows are wrong and the lessons already diverge from them

The bundle is right and the spec is stale in each case. Update the spec, do not change the
lessons.

- **Lesson 05** — completion says "a test copies a buffer and passes", but the same row
  offers `= delete` as a legitimate answer, under which nothing can copy it. The lesson
  writes it as a fork: a copy-and-count test, or an `is_copy_constructible_v` test plus a
  borrowed-use test.
- **Lesson 06** — "a test proves a returned buffer allocated once" passes vacuously. C++17
  guaranteed copy elision satisfies it on a prvalue return even with no move constructor at
  all. The lesson adds a second test on a case elision cannot cover.
- **Lesson 07** — the instructive failure says returning a non-`const` reference from a
  `const` method "compiles nowhere useful". With a raw pointer member it compiles everywhere
  and works, because `const` is shallow. That is the sharper failure and is what got taught.
- **Lesson 10** — "adding a chunk type touches one new class and no existing function"
  cannot include registering the handler. The lesson names the registration entry as the
  honest exception: it is data, not a branch.
- **Lesson 00** — "never terminating because `IEND` was not special-cased" does not
  reproduce on `basic.png`; a bounds-checked loop terminates anyway. It bites only on
  `truncated.png`. The lesson poses termination as a real choice between two stopping rules.

## 3. Checked and deliberately not acted on

- **iostreams inflating the counter.** Chapter 2 suspected that replacing global
  `operator new` makes `std::cout`'s startup allocation appear as `outstanding: 1`. Probed
  on this machine, libc++ and Apple clang: zero outstanding with both `printf` and
  `std::cout`. Not reproduced. It may still occur on libstdc++, so the lessons' advice to
  stay on `printf` remains as cheap insurance, but do not record the problem as real.
- **Lesson length.** 216 to 332 lines against a briefing figure of 120 to 250. The byte
  sizes sit inside the range of this repository's existing lessons. Do not trim teaching to
  hit a number.
- **`crc32.hpp` and `PNG-FORMAT.md` disclose the CRC range** before lesson 11's trap can
  spring. Keep it. A supplied file that hides its own contract is worse than a survivable
  trap, and the failure is in what the learner passes, not in what they can read.

## 4. Things already verified, so do not redo them

- The four PNG assets are real, with correct CRCs. `basic.png` is `8 IHDR 13`, `33 IDAT 108`,
  `153 IEND 0`, 165 bytes. `text.png` is `8 IHDR 13`, `33 tEXt 30`, `75 IDAT 108`,
  `195 IEND 0`, 207 bytes. `truncated.png` is 95 bytes and cuts mid-IDAT with IHDR intact.
  `badcrc.png` is `basic.png` with one bit flipped in IHDR's stored CRC.
- All four `dump.sh` cases pass against a correct implementation, and `error-path.sh` was
  confirmed in both directions: `expect-leak` fails on a clean tool and passes on a leaky
  one. This was done with a throwaway reference inspector, deliberately not kept in the
  bundle.
- `toolchain.sh` passes on this machine.
