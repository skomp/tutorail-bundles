---
id: 07-bounds-you-cannot-skip
title: Bounds you cannot skip
design_refs: [owning-and-borrowing]
validators: [build, tests, dumps-basic-png, rejects-truncated, no-leak-on-error-path]
---

## Purpose

Your parser reads bytes without ever establishing that they exist, and one of the supplied
files is short enough to prove it.

The buffer you have spent four lessons on owns its memory correctly on every path, and still
hands that memory to anyone who asks, at any index — while the parser asks for indices it
computed from a length field it read out of the file itself. `assets/truncated.png` is 95
bytes long and holds a chunk claiming 108 bytes of payload, so something in your program
reads bytes 95 through 152 of a 95-byte buffer, and whether that crashes, prints rubbish or
appears to work is luck. This lesson is also where the second half of the ownership story
arrives: you have a type that owns bytes, and now you need one that deliberately does not.

## Prerequisites

Lesson `06-moving-not-copying` is complete: your owning buffer type has a destructor, a copy
that is either correct or deleted, and a move that transfers the pointer and leaves the
source safe to destroy. The project is split into a library, the `pngdump` binary and a test
executable, as of `04-a-target-of-its-own`, and `ctest` runs the tests. The allocation
counter from `02-where-the-leaks-are` is still in the program and still balances on the error
path.

## Learning objectives

- Say, for any read in the parser, which bytes it touches and what establishes that those
  bytes are inside the file
- Write an unchecked `operator[]` and a checked accessor on the same type, and choose between
  them deliberately at each call site
- Write a non-owning view of pointer and length: copied freely, passed by value, freeing
  nothing
- Explain that `const` is part of a type, write `const` member functions, and say why a raw
  pointer member does not make its pointee `const` for you
- Name the lifetime rule a view must obey and point at what guarantees it in your program
- Report a truncated file while still reporting every chunk read before it

## Theory

### The read that nobody checked

Walk `assets/truncated.png` by hand before you run anything. The signature occupies bytes 0
to 7. At offset 8 there is a length field that says 13, a type field that says `IHDR`, 13
bytes of payload and a 4-byte CRC: bytes 8 to 32 inclusive, all present. At offset 33 there
is a length field that says 108, and a type field that says `IDAT`. That chunk therefore
claims bytes 33 through 33 + 12 + 108 − 1 = 152. The file stops at byte 94.

Your parser almost certainly computes `offset + 12 + length` somewhere and compares it to the
file size, because something makes it take the error path on this file — that is what
`02-where-the-leaks-are` measured. What it probably does not do is check every *other* read.
Reading the 8 bytes of a chunk header needs 8 bytes present; copying a payload needs the
payload present. Each is a separate read, and in C each needs its own hand-written
comparison, written by a programmer who remembered.

That is the actual defect, and it is not that a particular `if` is missing. It is that the
check and the read are two unrelated statements. Nothing in the language ties them together,
so the day you add a fifth read you will write it without its check and the program will
compile, link, run and be wrong. The repair is not to add the missing comparisons. It is to
put the bytes behind something that cannot be read without the bounds being consulted.

### Two ways to reach a byte, and why both exist

C++ lets you give your own type the subscript syntax. A member function named `operator[]`
is called when someone writes `buf[i]`, and it is an ordinary function apart from its
spelling:

```cpp
unsigned char& operator[](std::size_t i);        // buf[i] = x;  and  x = buf[i];
```

The return type is a *reference* — from `01-not-a-superset` — which is what makes
`buf[i] = 0x89` work: the caller is handed the byte itself, not a copy. This function checks
nothing and compiles to the pointer arithmetic you would have written in C. That is not a
flaw but the contract: `operator[]` is for reads already proved in range, and it costs
nothing, which is why the standard containers spell it the same way.

Beside it goes a checked accessor, conventionally called `at`. It compares the index against
the length and, when the index is out of range, does something the caller cannot ignore.
*What* it does is the interesting question, and this course constrains it. The standard
library's `at` throws an exception; exceptions are taught in `09-errors-without-errno`, and
this program's parser is not going to throw in any case. A sentinel that quietly returns zero
for an out-of-range byte is worse than no check at all, because zero is a plausible byte and
the truncation disappears into the data.

So the constraint is behavioural, not syntactic: **an out-of-range read must be impossible to
perform without the caller finding out.** Two shapes satisfy that with what you have built.
One returns a pointer that is null when the range is bad. The other answers a question first
— "are there `n` bytes at offset `k`?" — and hands back a usable view only when there are.
Either is fine, and `09-errors-without-errno` replaces whichever you pick with something that
carries the offset too. Pick one and use it everywhere.

### A type that owns nothing on purpose

Every parsing function takes the whole buffer, because that is the only handle you have. None
of them needs it: a function that reads a chunk header needs to see some bytes, not the right
to free them, copy them, or outlive them.

What it needs is a *view*: a pointer to the first byte and a count. That is the whole type,
and what you call it is yours — the course writes `View` for whatever you name it, the way it
writes `Buffer` for the type that owns the bytes. It has no destructor, because it releases
nothing, and no copy constructor you have to write, because copying two scalars is exactly
what the compiler's default copy does — the first type in this course where that default is
right. Compare `05-the-rule-of-three`, where the default
copy duplicated a pointer and the second destructor freed it again: the rule of three and the
rule of five are rules about classes that *own* something, and a view owns nothing.

Because copying is two scalars, a view is passed **by value**; passing it by reference buys
nothing and costs an indirection. That is a genuine reversal from the rest of the course —
the owning buffer is passed by reference or moved, never copied; the view is copied
everywhere — and the difference is ownership.

Bounds live in the view. Its size is always at hand to whoever holds it, and a function that
takes a view cannot be handed a bare pointer without a length, which is the C signature that
made this bug possible.

### `const` is part of the type

In C, `const` is a hint you can cast away and mostly do. In C++ it is part of a type and it
participates in overload resolution: the compiler uses it to decide which function you called.
A member function can be marked `const` after its parameter list:

```cpp
std::size_t size() const;    // promises not to modify the object
```

That mark changes the type of the hidden `this` parameter from `Buffer*` to `const Buffer*`.
Two consequences follow. First, a `const Buffer&` — what a function takes when it only reads
— permits exactly the member functions marked `const` and nothing else; forget to mark
`size()` and no `const` handle can ask how big the buffer is, with the error pointing at the
call rather than at the missing mark.

Second, the trap: `const` on the object does **not** propagate through a raw pointer member.
Inside a `const` member function, a member declared `unsigned char* data_` has type
`unsigned char* const` — the pointer is const, the bytes are not. So this compiles:

```cpp
unsigned char& operator[](std::size_t i) const { return data_[i]; }   // compiles. Wrong.
```

The compiler does not complain, and a caller holding a `const Buffer&` can write through it.
Const-correctness with a raw pointer member is something you assert, not something you are
given: the `const` overload returns `const unsigned char&` only because you wrote it that
way. Provide both overloads and the compiler picks by the constness of the object.

Then work outward: every function that only reads takes a `const` handle or a view of `const`
bytes, and each either compiles at once or tells you it was modifying something you did not
think it modified. The second case is the value of the exercise.

### Dangling: the bug ownership was supposed to end

A view is a pointer and a length, and the bytes stay alive only because something else owns
them. Nothing in the type says so. If the buffer is destroyed, reassigned, or moved out of and
then destroyed, every view into it points at freed memory and looks exactly as healthy as it
did a moment ago. That is the double-free of `05-the-rule-of-three` arriving from the other
direction: you introduced a non-owning type on purpose, and its price is that lifetimes are
your problem again in one place. Three ways to write it, all of which compile:

- a function that constructs a buffer, returns a view of it, and lets the buffer die at the
  closing brace;
- a struct storing a view beside something whose lifetime is not tied to the buffer;
- a view taken before the buffer is moved from or reassigned, and used after.

The allocation counter catches none of them: it counts allocations and frees, and a
use-after-free reads memory that was correctly freed, so the counts balance perfectly while
the program prints nonsense. Naming that limit is part of this lesson.

The rule is simple and unenforced: **a view must not outlive the buffer it points into.** In
this program that is easy to guarantee, because the buffer is created once near the top and
every view is derived from it and used further down the same call stack. Pointing at that
structure and saying why it is safe is the objective — not a mechanism that proves it,
because C++17 has none.

### Reporting truncation without throwing away what you read

The check is strict about one thing. When your program reaches a chunk that runs off the end
of the file it must report a problem and exit non-zero — and must still have listed
`8 IHDR 13`, the chunk it read correctly before the trouble started. A parser that abandons
everything on the first error is a worse tool than one that says the file is good to byte 94
and broken after. Detecting a failure and discarding your results are two decisions, and the
second is not implied by the first. The error line keeps the contract's shape,
`error: <message> at offset <n>`, where `<n>` is the offset of the chunk that claims more
bytes than remain. Carrying that offset from the place that notices to the place that prints
is awkward with what you have today; that awkwardness is the subject of
`09-errors-without-errno` and you are not expected to solve it elegantly here.

## Concepts to teach

Operator overloading, and `operator[]` as an ordinary member function with unusual syntax.
Returning a reference from an accessor. Unchecked versus checked access as a deliberate pair,
not a safe one and a fast one. A non-owning view: pointer plus length, copied by value, frees
nothing, and its compiler-written special members are correct precisely because it owns
nothing — contrast `05-the-rule-of-three`. `const` as part of a type; `const` member
functions and what they do to `this`; `const` and non-`const` overloads; shallow const through
a raw pointer member. Dangling and lifetime: a view must not outlive what it points into,
nothing checks this, and the allocation counter cannot see a use-after-free. Reporting a
failure without discarding what was established. See `#owning-and-borrowing` for why exactly
one type here owns bytes.

## Constraints

- Exactly one type owns bytes. The view holds a pointer and a length, has no destructor, and
  never frees or takes responsibility for anything.
- The view is passed by value; the owning buffer is not copied into parsing functions.
- Every read goes through either an index already proved in range or the checked accessor,
  and no parsing function receives a bare pointer without a length.
- The checked accessor must not throw, and must not silently substitute a value for an
  out-of-range byte — zero is a plausible byte and would hide the truncation.
- Read-only operations must compile against a `const` handle, and the `const` path must not
  hand out a mutable reference to the bytes.
- On `assets/truncated.png`: an `error:` line naming the byte offset, a non-zero exit, no
  death by signal, and `8 IHDR 13` still listed.
- `assets/basic.png` and `assets/text.png` are still listed exactly as before — bounds
  checking that rejects a valid file is not a fix — and the counter still balances.

## Suggested progression

Start by predicting: given the numbers above, name every read your parser performs for
`assets/truncated.png` and say, for each, what proves the bytes are there. Then run it and
compare — including the possibility that it appeared to work, the most instructive outcome
and the least reassuring.

Introduce the view type next, before touching any bounds check: a pointer, a length, its size
and an unchecked `operator[]`. Change one parsing function to take it instead of the buffer
and notice what the new signature says that the old one could not. Add the checked accessor
and make one deliberately out-of-range read through it in a test, so
the test names the behaviour you chose rather than the one you assumed. Convert the remaining
parsing functions one at a time until every read is either proved in range or checked — the
chunk header read and the payload read are separate reads and both need it. Then do the
`const` pass: mark every member function that does not modify the object, take `const` handles
in every function that only reads, follow the errors, add the `const` overload of
`operator[]`, and confirm by trying it that a `const` handle cannot write a byte.

Finally make `truncated.png` report properly — chunks listed up to the trouble, one `error:`
line with the offset, non-zero exit — then run `rejects-truncated`, `dumps-basic-png` and the
test suite, so that a bounds check which rejects valid files is caught here. Leave time for
the dangling exercise: write a function that returns a view of a buffer local to it, use the
view, see what happens, then delete it. It may print the right answer, which is the point.

## Completion conditions

- `build` passes and `tests` passes.
- `rejects-truncated` passes: on `assets/truncated.png` the program prints an `error:` line
  naming a byte offset, exits non-zero, does not die on a signal, and `8 IHDR 13` is still
  among the chunk lines.
- `dumps-basic-png` still passes — this lesson lists it because a bounds check that rejects
  valid files is the commonest way to pass the truncation check for the wrong reason.
- A test exercises an out-of-range read through the checked accessor and asserts the chosen
  behaviour; a test that only reads in range does not satisfy this.
- At least one read-only function takes a `const` handle, and writing a byte through that
  handle demonstrably does not compile.
- The learner can state, for a read they point at in their own parser, what establishes that
  the bytes exist; can say why the view needs no destructor, copy constructor or move
  constructor in terms of what it owns while the buffer needed all three; and can state the
  lifetime rule for a view, name what satisfies it in their program, and explain why the
  allocation counter would not catch a violation.

## On completion, persist

Record in the instance's `STATE.md` the name of the non-owning view and what its checked
accessor does when a read is out of range — `09-errors-without-errno` replaces that choice,
so it has to be written down. Record that parsing functions now take the view by value, and
any place where a read is left unchecked because the code proves the range some other way.

## Optional deeper paths

If the learner asks what the standard library calls this type, answer straight:
`std::string_view` and, from C++20, `std::span` are the same idea, and `12-it-was-in-the-box`
is where they arrive — do not adopt either now.

For the keen: give the two `operator[]` overloads different bodies temporarily and observe
which runs for which handle; look up `mutable`, the one thing that opts a member out of a
`const` member function's promise; ask what a view of `const unsigned char` buys over a view
of `unsigned char`, and whether the parser ever needs the mutable one; and read about
lifetime annotations in other languages to see what C++17 would need to catch dangling.
