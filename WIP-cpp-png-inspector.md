# WIP: cpp-png-inspector — where this stopped, and what comes next

**Branch: read section 0 first — this work is NOT on `add-cpp-png-inspector`.**
**Delete this file before merging.**
**Written:** 2026-09-29. Updated 2026-09-29 after the corrections were applied.

The bundle is structurally complete, validating, catalogued, and all ten known
corrections are applied. What remains is the course-quality audit and the merge.

## 0. Where this work lives now

**This bundle is developed in a worktree**, per the rule in the repository `CLAUDE.md`.

```
worktree : .claude/worktrees/cpp-png-inspector
branch   : worktree-cpp-png-inspector
tip      : 34 commits ahead of main, all mine, nothing of anyone else's
```

That branch is authoritative. Work on the bundle there, not in the main checkout.

### How it got untangled

Two sessions had shared the main checkout. A peer created and checked out
`spec-pico-ps2-usb-adapter` from my HEAD part-way through my work, and because branches are
per-checkout, my later commits landed on their branch — one peer commit (`d3074a0`, a
458-line `pico-ps2-usb-adapter/SPEC.md`) sandwiched between mine.

The worktree branch was built additively and rewrote nothing shared: it starts at `64bfc72`
(my last pre-peer commit) and replays `d3074a0..cpp-png-inspector-tip` on top, which brings
my commits over and skips the peer's. Verified by diffing the two tips: the single change is
the deletion of the peer's `SPEC.md`, nothing else. `validate_bundle.py` passes here, exit 0.

### Stale refs left behind in the main checkout

All three still exist, none were moved, and none is where the work is:

| ref | at | what it is |
|---|---|---|
| `spec-pico-ps2-usb-adapter` | `d727074` | the peer's branch. Carries their commit AND a copy of my pre-worktree history. |
| `cpp-png-inspector-tip` | `d727074` | the safety ref made while the work hung off the peer's branch. Superseded. |
| `add-cpp-png-inspector` | `64bfc72` | the original feature branch, stranded before the lesson bodies were written. **Do not resume from this one.** |

They are kept deliberately rather than deleted: the old commits stay reachable, so nothing
about the untangling is irreversible. Robert decides when they go.

**Nothing is pushed.** A worktree branches from `origin/<default-branch>` by default, so any
further worktree made from this repository will not see any of this work. Say so, or push.

**`rebase.updateRefs` is `true` in the global config**, so a rebase over `d3074a0` in the
main checkout would force-move every branch pointing into that range. Replaying commits one
at a time does not.

## 1. State

Done, committed, validating:

- `cpp-png-inspector/SPEC.md` — the approved course spec, now matching the built course.
- Skeleton: `tutorial.yaml`, `COURSE.md`, `DESIGN.md` (ten anchored decisions),
  `STATE.template.md`.
- 13 main-path lessons, 2 optional lessons, all added with `lesson.py` so no `id` drifted.
- 5 declared supplies. `crc32.hpp` is lesson-scoped to `11-the-finished-tool`.
- All 15 lesson bodies, 216 to 332 lines each.
- The repository `README.md` table lists the bundle.
- **All ten corrections from the previous section 2 are applied.** Commits `f2f9c8f`
  (check scripts), `73c4e91` (SPEC.md's eight stale cells), `ae06b0b` (lessons),
  `c58becd` (COURSE.md and DESIGN.md).
- **`catalog.yaml` is rebuilt** — commit `ee88ec5`. The bundle is discoverable now; it
  was not before, which is the one thing that had made it invisible to a runner.
- `validate_bundle.py` returns `PASS - every applicable check ran and found nothing`,
  exit 0, at `ee88ec5`. Confirmed by running it.

### One defect found while applying the corrections, and fixed

Worth recording because the handover's own section 2.5 got it half right. Lessons 10 and
12 both ran the missing-virtual-destructor experiment over `assets/truncated.png`, which
is the one file where it cannot fire: that file ends 54 bytes into the first `IDAT`'s
payload (header at offset 33, length 108, file 95 bytes — measured), so no complete chunk
ever reaches a handler and the handler's owned allocation never happens. The learner
removed `virtual`, saw `outstanding: 0`, and would have concluded the keyword does not
matter. Lesson 10's test for it was vacuous for the same reason.

In lesson 12 it was guaranteed rather than learner-dependent: after the refactor the
record is a `std::vector`, which allocates nothing until something is put in it.

Both now run it over `assets/basic.png`. Lesson 12 gained a constraint that at least one
handler must still own heap state afterwards, because lesson 10 guaranteed that through
the owning buffer type and `std::vector` silently does not.

## 2. What remains

**Only the merge.** Nothing is pushed. See section 0. Delete this file before merging.

The `course-quality` audit is done. Total 371 — 377 across fifteen lessons, less two
unserved objectives at -3 each. No `required_for` gates, and the completability invariant
holds and is planned for at `08:248`.

- Report: `skomp/tutorail-authoring`, `docs/audits/2026-09-29-cpp-png-inspector.md`,
  commit `88f3463`. **Local and unpushed in that checkout.**
- Findings: `tutorail-bundles#26`.
- Three rulings the rubric owes, filed where they will be fixed: `tutorail-authoring#27`.
  No session held that repository at the time.

Nothing in the audit has been applied — an audit proposes and never changes a bundle. The
four findings worth doing first are in `tutorail-bundles#26`: lesson 00 asks for two byte
helpers where lesson 08 needs three; `src/crc32.hpp` has two different owners; lesson 11
asserts the allocation balance and no validator checks it; lesson 07 needs a validator it
does not declare.

**One finding is blocked on `tutorail-authoring#27`** and must not be repaired before the
rubric rules: whether `what-the-compiler-writes-for-you` has to bind `rvalue`,
`overload resolution` and `static_assert` in its own theory, given that the manifest offers
it at lesson 05 and the main path binds those three in lessons 06 and 08.

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
