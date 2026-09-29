# WIP: cpp-png-inspector — where this stopped, and what comes next

**Branch: read section 0 first — this work is NOT on `add-cpp-png-inspector`.**
**Delete this file before merging.**
**Written:** 2026-09-29, at a pause for a machine reboot.

The bundle is structurally complete and validated, and all fifteen lesson bodies are
written. It is NOT finished: the corrections in section 2 are known and unapplied, and the
course-quality audit has not been run.

## 0. Branch collision — read this before anything else

Two sessions shared this checkout. A peer session created and checked out
`spec-pico-ps2-usb-adapter` from my HEAD at `64bfc72`, part-way through my work. Branches
are per-checkout, so from that moment **my commits went onto their branch.** Nothing was
lost and nobody staged anyone else's files, but the history is interleaved:

```
main
 └─ d6ed53b .. 64bfc72   mine   skeleton, 15 lesson adds, failure mode
     └─ d3074a0          PEER'S pico-ps2-usb-adapter/SPEC.md (458 lines, one file)
         └─ 7a93281 .. cd8baa1   mine   supplies, all lesson bodies, this handover
```

- `add-cpp-png-inspector` is stranded at **`64bfc72`** and does NOT contain the lesson
  bodies, the supplies declarations or this file.
- `cpp-png-inspector-tip` -> **`cd8baa1`** is a ref I added purely so my later commits stay
  reachable from something I own. It rewrites nothing.
- `spec-pico-ps2-usb-adapter` -> `cd8baa1` is the peer's branch and currently HEAD.

**The tip of my work is `cd8baa1`.** Untangling it means separating one peer commit from
nine of mine, which is a history rewrite in a shared checkout — Robert's call, not a thing
to do unattended. The peer said it intends to cherry-pick only `d3074a0` onto a fresh
branch off `main` and leave my commits alone; cherry-picking does not move refs, so that
plan is safe for me.

**One hazard if anyone rebases instead.** `rebase.updateRefs` is `true` in the global git
config, so a rebase over `d3074a0` force-moves every branch pointing into the rewritten
range. `git for-each-ref --contains d3074a0` lists both `cpp-png-inspector-tip` and
`spec-pico-ps2-usb-adapter` — which is to say the backup would be moved off the commits it
exists to preserve. Pass `--no-update-refs`, or re-point the ref afterwards and verify it.
Nothing here is pushed, so the safety ref is local only and is not yet a real backup.

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

All five agents reported. `validate_bundle.py` returns PASS, exit 0, at the last commit —
confirmed by running it, not assumed.

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

### 2.7 `SPEC.md` lesson 12 asks for something C++17 cannot give

"No hand-written result type remains" cannot hold alongside `#errors-are-values` and the
`error: <message> at offset <n>` contract. `std::optional` carries no error payload and
`std::expected` is C++23. The lesson turns this into its designed decision point:
`std::optional` where absence needs no explanation, and for failures that must carry an
offset, a choice the learner argues — a diagnostics container the caller owns, which the
tool already wants because `rejects-truncated` requires chunks read before the truncation to
still be listed, or a justified two-field result. The non-negotiables stay: no global, no
`-1`, offsets survive. Soften the spec cell to match.

### 2.8 Lesson 12's validator list cannot check its own closing claim

Its completion says the allocation counter still balances, but `dump.sh` ignores the
allocation report and `error-path.sh` is the only script that reads `outstanding:` — and
`no-leak-on-error-path` is not in lesson 12's validator list. The condition is currently
tutor-verified. Adding `no-leak-on-error-path` to that lesson makes the course's closing
claim machine-checked, for one word of change. Worth doing.

### 2.9 The optional lesson's type-trait mechanism is subtly wrong

`SPEC.md` suggests `static_assert` on type traits for
`what-the-compiler-writes-for-you`. `std::is_move_constructible_v<T>` is `true` for a
copy-only type, because the copy constructor's `const T&` binds to an rvalue — so a naive
assertion would *confirm* a wrong prediction about the learner's own buffer. The lesson
makes that trap its sharpest point and uses a behavioural probe (construct from an rvalue
with the counter watching) for the move questions, keeping traits where they genuinely
answer. The spec's suggested mechanism should say so.

### 2.10 `reading-a-template-error`'s compile-time case is implementation-dependent

`read<double>` fails only if the template body shifts and ORs; a memcpy-and-reverse body
compiles for `double` and silently returns nonsense. The lesson makes choosing the type part
of the exercise and gives a fallback (a small class type with no default constructor) that
no plausible body accepts. It also surfaces a secondary point worth keeping: an
unconstrained `read<T>` accepts types it should not.

## 3. Checked and deliberately not acted on

- **iostreams inflating the counter.** Chapter 2 suspected that replacing global
  `operator new` makes `std::cout`'s startup allocation appear as `outstanding: 1`. Probed
  on this machine, libc++ and Apple clang: zero outstanding with both `printf` and
  `std::cout`. Not reproduced. It may still occur on libstdc++, so the lessons' advice to
  stay on `printf` remains as cheap insurance, but do not record the problem as real.
- **Lesson length.** 216 to 332 lines against a briefing figure of 120 to 250. The byte
  sizes sit inside the range of this repository's existing lessons. Do not trim teaching to
  hit a number.
- **A reported missing supply that is not missing.** The fifth agent reported that
  `tutorial.yaml` has no entry handing `crc32.hpp` to `src/crc32.hpp`. It is declared, and
  correctly: the entry is LESSON-scoped, so it lives in the frontmatter of
  `lessons/11-the-finished-tool/LESSON.md`, which is where the format requires a
  lesson-scope `from` to be. Confirmed by reading the file. No action.
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
