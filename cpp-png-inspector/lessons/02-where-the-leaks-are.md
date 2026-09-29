---
id: 02-where-the-leaks-are
title: Where the leaks are
design_refs: [the-allocation-counter, the-output-contract]
validators: [build, leak-is-visible, explains-the-repair]
---

## Purpose

Stop believing your program is correct and start measuring it: count every allocation and
every release, print the totals when the program exits, and read the number the error path
leaves behind.

"It probably leaks" is not a finding, and neither is "it looks fine to me". Both are opinions
about code you wrote, held by the person who wrote it. This lesson replaces them with a
number that comes out of the program on every run, for the rest of the course — it is the
evidence for five later lessons, and in `10-chunks-without-switch` it is the only thing that
catches a defect with no other visible symptom.

## Prerequisites

`01-not-a-superset` is complete: the walker builds as C++17 and still lists the chunks of
`assets/basic.png` correctly. Memory is still obtained with `malloc` and released with `free`,
and there are no classes and no destructors in the program.

## Learning objectives

- Route every allocation and release through one pair of counting functions, so no call site
  can be forgotten
- Print the allocation report in the contract's exact shape, once, on every way the program
  can end
- Run the tool against the file that sends it down its error path, and say what the number
  means
- Point at the exact line that returns while holding memory, and name what it costs
- State what a counter can see and what it cannot, so you do not over-trust the evidence you
  just built

## Theory

**Ownership is a countable property.** Every call to `malloc` is a promise that something will
call `free` exactly once with that pointer. The promise is not attached to anything the
compiler checks; it lives in your head and in the shape of the code. But it is countable: at
any moment, the number of promises made minus the number kept is the number of live
allocations, and when a program is about to exit that difference should be zero. Counting does
not prove the program is correct. It measures one specific thing precisely, which is a great
deal more than you have now.

**Why a counter and not a sanitizer** (see `#the-allocation-counter`). The professional answer
to "does this leak" is a tool: AddressSanitizer's leak detector, or valgrind. This course does
not use them, for a blunt practical reason and a better teaching one. The practical reason is
coverage: LeakSanitizer does not detect leaks on macOS, and valgrind does not run on Apple
silicon, so on a large share of learners' machines the check for this lesson would pass while
finding nothing at all — the worst possible failure for a lesson whose entire job is to make a
leak visible. The teaching reason is that counting allocations *is* the ownership discipline
being taught. You will carry the counter to the end of the course, and it is what proves each
later repair actually repaired something. A sanitizer is a fine thing to reach for at work;
learn it after this course, not instead of it.

**The wrapper.** Two functions: one that calls `malloc`, increments a count and returns the
pointer, and one that calls `free` and increments another count. Two counters with internal
linkage beside them, in one translation unit. Then change every allocation site in your program
to go through them.

The point of the wrapper is not that it is cleverer than incrementing a counter by hand — it is
that it removes the opportunity to forget. A count maintained at call sites is only as good as
your discipline at every future call site, and there will be more of them; a count maintained
inside the only function that allocates is a fact about the program. This is the same argument
the entire course makes about destructors, made one lesson early and in a form you can write in
ten minutes.

Three details to decide deliberately rather than by accident. `free(nullptr)` is legal and does
nothing — decide whether it counts as a release, and be consistent, because a wrapper that
counts null frees will drift away from reality as soon as your code starts releasing
conditionally. `realloc` is the awkward one: it is an allocation *and* a release in a single
call, and sometimes neither, because it may extend the block in place. If your program uses it
anywhere, work out what it should do to your two counters and be able to defend the answer. And
if you allocate anywhere else in the program — a copy of a filename, a small scratch buffer —
that call has to go through the wrapper too, or the report is telling you about part of your
program while sounding like it is telling you about all of it.

**Where the report is printed is the substance of this lesson.** The contract fixes the line's
shape (see `#the-output-contract`):

```
allocations: <n> frees: <m> outstanding: <k>
```

Single spaces, decimal numbers, at the start of the line, exactly once per run — the check
reads it with a pattern, and two copies of the line confuse it as thoroughly as none. It must
be printed *at exit*.

Which is where the question hides, and it is worth stopping on before you write a line of code:
how many ways can your program end? There is the run that works, and there is the run where the
file would not open, and the run where the signature was wrong, and the run where a chunk did
not fit in what was left of the file. Before you run anything, predict which of those reaches
the line you are about to write. Then write it, and go and find out.

**The file that matters is `assets/truncated.png`.** It is `basic.png` cut off at 95 bytes,
part-way through the `IDAT` payload: the `IHDR` chunk at offset 8 is intact, and the `IDAT`
header at offset 33 announces 108 bytes of data when only 50 remain. Your walker meets that in
`00-write-the-c-walker`'s bounds check, cannot go further, and stops — which is the correct
thing to do and also the run on which your program is holding a heap buffer it allocated and
has not yet released. A valid file exercises none of this. It is the only run in the course
where a whole file's worth of memory is live at the moment the program gives up, and it is
therefore the only run whose number is interesting.

**This lesson's check passes when your program is broken, and that is deliberate.** The
`leak-is-visible` validator runs your tool against `assets/truncated.png` and passes only when
the report says `outstanding:` is greater than zero. It is the one check in the entire course
that rewards a defect, so read what it is buying: a leak detector that has never once reported
a leak is not a leak detector you have any reason to trust. This run is the calibration. From
`03-a-class-that-cleans-up` onward the same script is run in its other mode against the same
file and requires `outstanding: 0`, and every ownership lesson after that leans on it.

So do not fix the leak in this lesson. You would be fixing it by hand, on the path you happened
to think of, with a `free` you have to remember to keep — and the next lesson's argument is
that remembering is the wrong mechanism. Find it, measure it, name it, and leave it.

**If your number comes out zero**, there are exactly two explanations and they are easy to tell
apart. Either the counter is not seeing every allocation — check that every `malloc` in the
program goes through the wrapper, and that the report is not being printed before the parse
runs — or your program genuinely does release the buffer on that path, because you wrote the
`free` before the early `return`. The second is not cheating and it is not wrong; it is a C
programmer being careful. It still has to be demonstrated rather than asserted, so take that
one `free` out, watch the counter report the loss, and leave it out for this lesson. It is
sitting in exactly the place `03-a-class-that-cleans-up` deletes anyway, and the point of that
lesson is that the correctness must stop depending on you remembering to put it there.

**What the counter can and cannot see.** It sees a leak — memory allocated and never released —
and it sees a double release, as a `frees` count that runs ahead of `allocations`. Note what
that does to the report line: `outstanding` in the contract's shape is a non-negative decimal
number, and a program that has freed more than it allocated has no honest way to print one, so
say so on a line of your own rather than printing a wrapped-around unsigned value. Keep the
counters in a signed type, or compute the difference carefully, so this stays a choice rather
than a surprise; `05-the-rule-of-three` is where you will need it. What the counter cannot see
at all is a use-after-free: the counts balance perfectly while the program reads memory it has
handed back. It is a measure of one property, not a verdict on the program.

## Concepts to teach

Allocation as a promise and release as its discharge; outstanding allocations as the countable
difference. Why every exit from a function is an exit path, and why error returns are where
releases are lost. Counting wrappers around `malloc` and `free`, static counters in one
translation unit, and why counting at the allocation site beats counting at call sites.
`free(nullptr)`, and `realloc` as a release and an allocation in one call. The report line's
exact shape, printed once, at exit (`#the-output-contract`). The difference between a program
that ends and a function that returns. `assets/truncated.png` and why it is the interesting
run. Why the course counts rather than using a sanitizer, including where sanitizers do not
work (`#the-allocation-counter`). What a counter detects — leaks, double releases — and what it
is blind to, namely use-after-free. Calibration: a detector that has never fired is not known
to work.

## Constraints

- Do not fix the leak. No new `free`, no cleanup label, no rearranging the error path so the
  release happens. Measuring is the whole task.
- Do not add a class, a constructor or a destructor. `03-a-class-that-cleans-up` is next and it
  needs the problem intact.
- Keep `malloc` and `free` underneath the wrappers. Not `new`, not `std::vector`.
- Every allocation and every release in the program goes through the wrappers — not most of
  them.
- The report line matches the contract exactly, is printed exactly once per run, and is printed
  however the program ends.
- The tool must not crash on `assets/truncated.png`. Reporting a malformed file is the job;
  dying on one is not, and a run killed by a signal fails the check before it can read anything.
- `assets/basic.png` must still list correctly and exit 0, with no line beginning with `error:`.
  Adding the report line must not disturb it.
- Do not report the truncation in the contract's `error:` shape yet, and do not start keeping
  already-listed chunks across a failure. That is `07-bounds-you-cannot-skip`.
- The counter stays in the program for the rest of the course. Write it somewhere you are happy
  to keep.

## Suggested progression

Start with the prediction, in writing: list every way your program can end, and mark which of
them you expect to reach the report line. Also predict the two numbers for `assets/basic.png`
and for `assets/truncated.png` before either has ever been printed.

Write the two wrappers and the two counters, and change your allocation site to use them. Add
the report line in the contract's shape and run the tool on `assets/basic.png` first: the
listing must be unchanged, the exit status still 0, and the numbers should balance. If the
listing check now fails, the report line is landing somewhere it interferes.

Now run the tool on `assets/truncated.png` and compare what you see against the prediction you
made. There are three interesting outcomes and each says something different: a report with a
non-zero `outstanding`, which is the leak; a report with zero, which sends you to the two
explanations above; and *no report at all*, which means the run that loses memory is precisely
the run that never reaches your report — the most instructive of the three, and the reason this
lesson asks for the prediction first.

Once the report prints on every path, run the `leak-is-visible` check and read its output. Then
do the part that is not automatic: open your source, put your finger on the `return` that
leaves the function while the buffer is live, and say how many bytes that run lost. Follow it
with the harder question — how many other places in this program could grow the same defect
later, and what would have to be true for you to notice?

Placing the report on every path is where this gets awkward, and that awkwardness is worth a
minute's thought before you engineer around it. Two answers are available to you today: C's
`atexit` registers a function to run when the program exits normally, and a single exit point
that all the error paths funnel to. Decide between them deliberately, and write down the
reason before you implement either — the answer the course is heading towards is that scope
exit should be doing this work for you, and that one is not available until next lesson. Then
run the tool on `assets/basic.png`, on `assets/truncated.png`, and on a file that does not
exist, confirm the report line appears exactly once on each of the three runs, and re-run
`leak-is-visible`.

## Completion conditions

- The `build` validator passes.
- The `leak-is-visible` validator passes: run against `assets/truncated.png`, the tool exits
  without dying on a signal, prints the allocation report in the contract's shape, and that
  report shows `outstanding:` greater than zero.
- The report line appears exactly once per run and on every way the program can end, including
  the early returns. The learner can demonstrate this by running the tool on a path that fails
  before parsing — a file that does not exist, or one that is not a PNG — and seeing the report.
- `assets/basic.png` still lists correctly with exit status 0 (re-running the earlier
  `dumps-basic-png` check is the quickest way to be sure).
- Every allocation site in the program goes through the wrapper. The learner can say how they
  know there is no unwrapped one left.
- `explains-the-repair`: the learner points at the specific `return` that abandons the buffer,
  says how many bytes are lost on that run, explains why a valid file never reveals it, and
  says why `leak-is-visible` requiring a leak is a check worth having rather than a mistake.
- The learner can state what this counter would fail to notice — a use-after-free — and what a
  `frees` count exceeding `allocations` would mean.

## On completion, persist

In the instance's `STATE.md`: that the allocation counter exists, where it lives in the source
and what the wrappers are called; the decisions taken about `free(nullptr)` and `realloc`; where
the report line is printed from; the measured numbers for `assets/basic.png` and
`assets/truncated.png`; and the exact `return` identified as the one that abandons the buffer,
because `03-a-class-that-cleans-up` starts from it. If the learner had to remove a `free` to
make the leak visible, record that, so the next lesson does not read it as a fresh defect.

In the instance's `DESIGN.md`: the allocation counter as an adopted, permanent part of the
program (`#the-allocation-counter`), including the note that it will move from wrapping
`malloc`/`free` to wrapping `operator new`/`operator delete` when the program stops using
`malloc`, and the note that it is blind to use-after-free.

## Optional deeper paths

Find out what your platform's own tools would say: `leaks` on macOS, `valgrind --leak-check=full`
on Linux x86-64, or a build with `-fsanitize=address`. Compare their output with your counter's
and notice what each sees that the other does not — and whether the tool is even available on
the machine you are sitting at, which is the argument for the counter in one line. Add the peak
outstanding count and the total bytes allocated to your own bookkeeping, as extra output beside
the contract line. Look up how `operator new` can be replaced globally in C++, which is where
this counter goes next. Read about `atexit`, and about what it does *not* run after: `_exit`,
`abort`, and a crash — and ask which of those your program could take.
