---
id: 12-it-was-in-the-box
title: It was in the box all along
design_refs: [handwritten-then-replaced, errors-are-values]
validators: [build, tests, dumps-basic-png, reads-text-metadata, detects-bad-crc, rejects-truncated, explains-the-repair]
---

## Purpose

Delete the buffer, the result type and the owning pointers you spent eight lessons
writing, and replace each with the standard type that was always going to do it better.

The pressure for this lesson is not that your code is wrong. It works: it lists chunks,
reads metadata, validates checksums, survives a truncated file, and does not leak. The
pressure is that it is yours alone — nobody else's code calls it, no other library
interoperates with it, and every bug left in it is a bug you will have to find yourself.
The standard library has the same three types, written once, tested by everyone, and
spelled the same way in every C++ program on earth. You could have used them in lesson 03
and learned nothing, because `std::vector`'s interface only reads as a set of answers once
you have met the questions. You have now met all of them.

## Prerequisites

Lesson `11-the-finished-tool` is complete and the inspector is finished: `dumps-basic-png`,
`reads-text-metadata`, `detects-bad-crc`, `rejects-truncated` and `tests` all pass, and the
allocation report from lesson `02-where-the-leaks-are` is still printed at exit and still
balances.

You are standing on a specific set of hand-written types, named here by what they do rather
than by what you called them: the **owning buffer** from `03-a-class-that-cleans-up`, given
copy semantics in `05-the-rule-of-three`, move semantics in `06-moving-not-copying` and a
checked element access in `07-bounds-you-cannot-skip`; the **non-owning view** of bytes,
also from `07-bounds-you-cannot-skip`; the **result type** from `09-errors-without-errno`,
carrying either a value or a failure with a byte offset; and the **owning raw pointers** to
chunk handlers from `10-chunks-without-switch`, held behind a base-class interface with a
virtual destructor. The test suite from `04-a-target-of-its-own` onwards is the instrument
this lesson is measured with, so it has to be green before you start.

## Learning objectives

- Replace the owning buffer with `std::vector` and say what it supplies that yours did not
  — and what it costs that yours did not
- Replace the owning raw pointers with `std::unique_ptr`, and explain why the virtual
  destructor from `10-chunks-without-switch` is still required afterwards
- State exactly what `std::optional` can and cannot carry, and decide where a parse
  failure's byte offset lives in C++17 as a result
- Use `std::string_view` for a `tEXt` keyword and value, and state the one rule it does not
  enforce for you
- Say in one sentence why `std::unique_ptr` is the default and what a reference count costs
- Use an unchanged test suite as evidence that a refactor changed nothing a caller could
  see, and read a test that *breaks* as information rather than as an obstacle

## Theory

### The buffer becomes `std::vector`

Open a reference page for `std::vector` and read it as a list of decisions someone made,
each of which you also had to make: a constructor taking a size, `size()` and `data()`, an
`operator[]` that does not check and an `at()` that does, a copy constructor that copies the
elements and a move constructor that does not, a destructor you never call. Every one
answers a question you were forced to answer yourself between lessons 03 and 07. That is
this lesson's whole argument; the replacements themselves are mechanical.

`std::vector<unsigned char>` owns a contiguous block of bytes, frees it in its destructor,
copies it when copied, transfers it when moved, and reports its own size. That is your
buffer's entire job description.

It obtains memory through an *allocator*, and the default allocator obtains it from
`operator new` — which is what your counting wrapper replaced in
`03-a-class-that-cleans-up`. So the counter keeps counting after the replacement, with no
change. That is worth pausing on: the evidence you built in lesson 02 does not stop working
when the thing it watches becomes standard.

What `std::vector` does that your buffer did not:

- **It grows.** `push_back`, `insert`, `resize` and `reserve` reallocate and move the
  existing elements in amortised constant time, safely even if an element's copy throws
  part-way through, and it separates `size()` (how many elements exist) from `capacity()`
  (how many fit before the next reallocation). Yours was allocated once at the size of the
  file and had only one of those numbers, because growing was work you had no reason to do.
  The restriction was invisible until something wanted it.
- **It interoperates.** Iterators mean the standard algorithms, range-based `for` and every
  library taking a pair of iterators; `data()` and `size()` mean C APIs still work.
- **Its copy and move are already correct**, self-assignment included — the thing you had
  to get right by hand in `05-the-rule-of-three` and can now stop maintaining.

And two things it does *differently*, which are the interesting ones. **`at()` throws.**
`std::vector::at` reports an out-of-range index by throwing `std::out_of_range`; your
checked access reported it as a value, because this parser returns values (see
`errors-are-values`). If your parse path leans on your `at()` returning a failure, swapping
in `std::vector` turns that into an exception travelling out through your parser — a real
change in the interface, not a detail. Decide deliberately: bound-check against `size()` on
the parse path and keep `at()` for tests, or catch at one boundary. Either is defensible;
not noticing is not. And **`resize()` value-initialises** — sizing a vector to the length of
the file writes zeros over every byte before you read the file into it, where `malloc` did
not. Irrelevant for a PNG inspector, not irrelevant for a 4 GB file. Knowing that the
standard type has a cost yours did not is part of reading it honestly.

The mechanism that makes the swap survivable is a **type alias**: `using` introduces a new
name for an existing type, so the name your code already says everywhere can stay while the
type behind it becomes the standard one. That is not a trick to hide the change — it is the
tool you would use in any real migration, and it makes the replacement one edit whose
consequences arrive all at once.

### What an unchanged test suite is actually proving

The completion condition of this lesson is that **every test written in lessons 04 to 11
still passes, with its assertions untouched.** It proves that your buffer's public
interface was, in every respect a test exercised, a subset of `std::vector`'s — that the
design you arrived at under pressure, one defect at a time, converged on the answers the
standard library made.

If a test will not compile, stop before editing it and work out which of three things
happened.

1. **A name differs.** You called it `length()`, the standard calls it `size()`. This is
   nothing; note it and move on.
2. **An operation is spelled differently.** You had a method taking a byte range; the
   standard offers iterators. Slightly more interesting: your interface was shaped by
   having exactly one caller.
3. **The operation only made sense because you owned the implementation.** A method that
   handed out the raw pointer for the caller to free, or set the size without allocating,
   or reached inside for a member. This is the one worth finding: the test was not testing
   behaviour, it was testing your internals, and it was holding your implementation in
   place. **That is a defect you have just discovered**, and it is worth more than the
   refactor.

A fourth case does not fail the build. A test asserting that a moved-from buffer is empty
passed because *your* move constructor promised exactly that. `std::vector`'s moved-from
state is **valid but unspecified**: the standard guarantees only that you may destroy it or
assign to it. Every implementation leaves it empty and the test keeps passing — but it is
now asserting something the standard does not promise. Find out whether you have one.

### `std::optional`, and the thing it cannot carry

`std::optional<T>` holds either a `T` or nothing, with the `T` stored inside the optional
rather than on the heap. `has_value()` asks, `*` and `->` read, reading an empty one through
`*` is undefined behaviour and `value()` throws instead. It is the exact answer to "this
function may or may not produce a value".

Now try to replace your result type with it, and meet the wall. Your result type carried
**a value or a failure**, and the failure carried a byte offset and a message, because
`errors-are-values` says a parse failure is data the caller wants and the output contract
requires `error: <message> at offset <n>`. `std::optional` carries a value or *nothing*.
There is no room in it for the offset, and an empty optional cannot say which byte was
wrong.

This is not you failing to find the right standard type. **C++17 does not have one.** The
type that does this is `std::expected<T, E>`, which arrived in C++23: a value or an error
object of your choosing — near enough your result type with a standard name. A learner who
feels stuck here has arrived exactly where the language was in 2017, and the honest thing is
to say so rather than force `std::optional` into a job it does not do.

So the decision is yours to argue, and more than one answer is defensible. Use
`std::optional` where the absence needs no explanation and keep something that carries an
error where the offset matters. Or split the two questions: parse steps return
`std::optional<T>` for the value, and the diagnostics accumulate in a container of error
values the caller owns — a shape your tool already wants, because `rejects-truncated`
requires the chunks read before the truncation to still be listed, so failing is not the
same as stopping, and a *list* of errors is closer to what the tool does than a single one.
What is **not** defensible is setting a global, returning `-1`, or dropping the offset:
`errors-are-values` has not been repealed by this lesson, and `detects-bad-crc` and
`rejects-truncated` both read the `error:` line that carries it.

### `std::unique_ptr`, and the destructor it does not save you from

`std::unique_ptr<T>` owns one heap object and deletes it in its destructor. It is
move-only: copying is deleted, which is the type system stating that two owners of one
object is not a thing that happens. `std::make_unique<T>(args...)` allocates and constructs
in one step; `get()` borrows without giving up ownership, `release()` gives up ownership,
`reset()` deletes early. It is the rule of five from `06-moving-not-copying` applied to a
pointer, written once by someone else — and with the default deleter it is zero-overhead:
the size of a raw pointer, compiling to the same instructions plus the `delete` you were
going to write anyway. Your handler list from `10-chunks-without-switch` is where it goes,
and a container of `std::unique_ptr<Handler>` says all of that in the type.

Say the next part out loud, because it is the most common wrong conclusion:
**`std::unique_ptr` does not remove the need for the virtual destructor.** When a
`unique_ptr<Base>` with the default deleter destroys the object it calls `delete` on a
`Base*`. If `Base`'s destructor is not virtual that is undefined behaviour and, in
practice, the derived part is never destroyed — the same leak lesson 10 caught with the
allocation counter, now hidden behind a type whose name suggests it was handled. Remove the
`virtual` after the refactor, run the tool, and read the counter.

Keep the chunk *values* as values. `chunk-data-vs-chunk-handlers` puts polymorphism in the
handlers and nowhere else, and one reason is visible only now: a chunk that is a plain value
goes into a `std::vector` of values, one allocation for the lot, while a polymorphic chunk
would force a container of pointers and an allocation per chunk. That decision was made two
lessons ago and this is where it pays.

### `std::shared_ptr`, in one paragraph

`std::shared_ptr<T>` is for ownership that is genuinely shared, where no single scope can
say when the object dies. It keeps a reference count in a separately allocated control
block; copying increments it, destruction decrements it, and the object is deleted at zero.
That count is atomic, because a shared pointer may be copied on one thread and destroyed on
another, so every copy and every destruction is a synchronised read-modify-write even in a
single-threaded program; the control block is a second allocation unless you use
`make_shared`; the pointer is twice the size of a raw one; and two objects holding shared
pointers to each other never reach zero and never die. `unique_ptr` is the default because
single ownership is the common case, costs nothing, and says something definite. Reach for
`shared_ptr` only when you can name the second owner and say why its lifetime cannot nest
inside the first — and nothing in this program can. This course does not teach it further.

### `std::string_view` for text that was never a C string

`std::string_view` is a pointer and a length over characters someone else owns. It copies
freely, frees nothing, and must not outlive what it points into — the contract of the view
you wrote in `07-bounds-you-cannot-skip`, which is why you can read it without explanation.

It is the right type for a `tEXt` chunk specifically because **the value is not
NUL-terminated**: it runs to the end of the chunk, and its length is whatever the chunk
length leaves over after the keyword and its NUL. A `std::string_view` carries that length
with it, so the trap `11-the-finished-tool` is built around cannot be sprung — there is no
terminator to look for, and nothing invites you to look for one. In exchange you get `find`, `substr`,
comparison against string literals, and printing to a stream with the right length.

Two details. Your bytes are `unsigned char` and `std::string_view` is over `char`, so the
conversion at that boundary is a `reinterpret_cast` and belongs in one place. And
`string_view::data()` is **not** guaranteed to be NUL-terminated, so handing it to anything
expecting a C string reintroduces the exact bug the view removed. The dangling rule is
unchanged and unenforced: a view into the buffer is valid only while the buffer is alive,
and the standard type will not warn you.

## Concepts to teach

`std::vector` as an owning, growable, contiguous sequence: `size()` versus `capacity()`,
`data()`, `at()` versus `operator[]`, iterators, value-initialisation on `resize`, and the
default allocator routing through `operator new` so the lesson-02 counter still sees it.
Type aliases as the tool that makes a type replacement local. `std::optional` as "a value or
nothing", and the explicit limit that it carries no error payload — with `std::expected`
(C++23) named as what fills the gap. `std::unique_ptr`: single ownership in the type,
move-only, `make_unique`, `get`/`release`/`reset`, zero overhead, and that it still requires
a virtual destructor when it owns through a base pointer. `std::shared_ptr` and reference
counting to one paragraph only: the control block, the atomic count, cycles, and why
`unique_ptr` is the default. `std::string_view` as a borrowed, non-NUL-terminated character
range, and the lifetime rule it does not enforce. And a refactor whose evidence is an
unchanged test suite, with the three reasons a test might break.

## Constraints

- Behaviour must not change. The output contract from `the-output-contract` is fixed: the
  chunk lines, the `error:` lines with their offsets, and the allocation report at exit are
  all still printed in the same shapes.
- The allocation counter stays in the program and must still balance. It is the evidence,
  and this lesson is not an excuse to retire it.
- The tests written in lessons 04 to 11 keep their assertions. If one will not compile,
  diagnose it and record why before changing a character of it.
- No new features, and one replacement at a time with the full check set green in between.
  A new output mode, flag or chunk type in the same change as a type replacement leaves you
  unable to tell which one broke a check.
- No `std::shared_ptr` anywhere in this program, and no exception escaping the parser's
  interface — if you use `at()` on a parse path, that is a decision made explicitly.
- Chunks stay plain values; a container of pointers to chunks contradicts
  `chunk-data-vs-chunk-handlers`. `std::string_view` and any byte view must not outlive the
  buffer they point into.

## Suggested progression

Before changing anything, run every check the tool passes today and write down the
allocation report for each asset. That is the baseline; without it, "the counter still
balances" is an opinion.

Start with the buffer. Introduce an alias so its name survives, point it at
`std::vector<unsigned char>`, and delete your class — all of it, including the destructor,
the copy constructor, the copy assignment operator, the move pair and the checked access.
Build, read what breaks, and sort each failure into the three categories above before fixing
any of them. Get the suite green, then run all four behavioural checks and compare the
allocation report against the baseline.

Then the owning pointers: convert the handler list to `std::unique_ptr` and remove every
`delete` it made unnecessary. Then run the experiment — make the base destructor
non-virtual, run the tool, read the counter, restore it, and be able to say what you saw.

Then the result type. Work out first, on paper, which of your returns need to carry an
offset and which only need to say "nothing here"; replace the second kind with
`std::optional` and argue the choice for the first. Whatever you choose, the `error:` lines
must still carry their offsets and `rejects-truncated` must still list the `IHDR` read
before the truncation.

Then the text: replace the hand-rolled keyword and value handling with `std::string_view`,
keeping the `unsigned char` to `char` conversion in one place.

Finally go back through the diff and write the sentence this lesson is for, once per
replacement: *what does the standard type do that mine did not?* If you cannot answer for
one of them, that is the reference page to go and read.

## Completion conditions

- `build` and `tests` pass, and `dumps-basic-png`, `reads-text-metadata`, `detects-bad-crc`
  and `rejects-truncated` all pass — the same four behavioural checks the tool passed before
  the refactor, still passing after it.
- The tests written in lessons 04 to 11 pass with their assertions unchanged. Any test that
  had to be edited is accounted for by name, with which of the three reasons applied; an
  edit for reason 3 is recorded as a defect the refactor found.
- No hand-written owning buffer and no owning raw pointer remains. The allocation report
  still appears at exit and still shows `outstanding: 0` on every asset, including
  `assets/truncated.png`.
- `explains-the-repair`: the learner states, per replacement, what the standard type does
  that theirs did not — specifically that `std::vector` grows and separates size from
  capacity, that `std::unique_ptr` puts single ownership in the type while still requiring
  the virtual destructor, and that `std::string_view` is the right type for a value that has
  a length rather than a terminator.
- The learner can say what `std::optional` could not carry, name `std::expected` and the
  standard it arrived in, and justify where a parse failure's byte offset lives now.
- The learner can say, in one sentence each, why `std::unique_ptr` is the default and what a
  reference count costs.

## On completion, persist

In the instance's `DESIGN.md`, record each replacement as a decision: which hand-written
type went, which standard type replaced it, and the one-sentence answer to what the standard
type does that theirs did not. Record the error-carrying decision explicitly — where a parse
failure's byte offset lives now, and why — because that is the one place this lesson leaves a
genuine choice. If a test had to change, record which one and why. If the learner proposed a
second output mode, note it against `json-output`, which is deliberately unresolved.

In `STATE.md`, record that the inspector now stands on the standard library with nothing
hand-rolled left in it, that milestone M5 is reached, and that the main path is finished.

## Optional deeper paths

Measure what `reserve` is worth: watch the counter while a `std::vector` grows without it.
Read why `std::vector<bool>` is not a vector of bools, and why it is the standard library's
most-regretted specialisation. Look at `std::span` (C++20) as the standard spelling of the
byte view from `07-bounds-you-cannot-skip`, and at `std::variant` and `std::visit` as the
C++17 way to hold a
value *or* an error in one object — then decide whether it is clearer than what was chosen
here. Read `std::unique_ptr`'s second template parameter, the deleter, and what changes
about the pointer's size when it is not the default. And take the tool further: a second
output mode is the natural next step, and it is the pressure that argues the lesson-10
handler interface a second time.
