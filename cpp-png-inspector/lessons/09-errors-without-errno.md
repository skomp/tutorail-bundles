---
id: 09-errors-without-errno
title: Errors without errno
design_refs: [errors-are-values, owning-and-borrowing]
validators: [build, tests, rejects-truncated, no-leak-on-error-path, explains-the-repair]
---

## Purpose

Your parse functions report failure by returning `-1` and printing, so the caller learns that
something went wrong and nothing about what or where.

`07-bounds-you-cannot-skip` left you with detection that works and reporting that does not.
Somewhere deep in the parser a function knows the exact byte offset at which the file ran
out; by the time control reaches the code that prints, that offset has become a `-1`, or a
global, or a line printed on the spot by a function whose job was to read bytes. This lesson
replaces all three with a value carrying the failure and its offset out to the caller — and
teaches the mechanism this course has been avoiding on the way, because the argument for not
using exceptions is worthless from someone who cannot explain them.

## Prerequisites

Lesson `08-templates-eat-the-macros` is complete: `read<T>` exists as a function template in a
header and you have met instantiation, deduction and the reason a template's definition is
visible to its callers. The owning buffer has a working move constructor and move assignment
from `06-moving-not-copying`, and a destructor from `03-a-class-that-cleans-up`. The
allocation counter from `02-where-the-leaks-are` is still running.

## Learning objectives

- Write a class template holding either a value or an error, and say what instantiation means
  for a type rather than a function
- Make the invalid state unaskable: no path on which a caller reads a value that was never
  produced
- Carry a byte offset from the function that detects a failure to the function that reports it
- Explain what an exception is, what stack unwinding does, and why an exception thrown through
  a function holding an owning buffer does not leak
- State why this program returns errors as values anyway, and argue the other side
- Say which special member function makes a result holding a buffer returnable at all

## Theory

### What `-1` costs you

A C parse function has one return value and has to make it carry a result and a verdict. The
usual answers fail in the same way. Returning `-1` works only while no legitimate result can
be `-1`, and a chunk length or a byte offset has no spare value to give away. Setting a global
— `errno`, or your own — makes the failure and the notification two separate events, so the
discipline of checking before the next call falls on the caller, and stale state is
indistinguishable from fresh. Printing at the point of detection is worst, because it puts the
program's user interface inside a function that reads bytes: the message goes out whether the
caller wanted it or not, cannot be suppressed, and cannot be tested.

All three share one defect. The failure is not *data*. It cannot be stored, passed, compared
or returned; it can only be signalled. And the single most useful fact about a parse failure
in this program — the byte offset it happened at — has nowhere to live at all.

### A class template

`08-templates-eat-the-macros` parameterised a function by a type. The same mechanism
parameterises a type:

```cpp
template <typename T>
class Result { /* ... */ };
```

`Result` is not a type. `Result<std::uint32_t>` is, and so is `Result<Buffer>`, and they are
unrelated types generated from one pattern when you name them. Everything from the previous
lesson carries over: the code exists once in a header, the compiler generates what each use
needs, there is no run-time cost, and the definition must be visible wherever it is used —
including the member functions, which are instantiated only when something calls them, so a
member that would not compile for some `T` causes no trouble until a program calls it.

### Holding either a value or an error, and not both

The shape is a value, an error, and something that says which one is real. The error is a
small plain type of its own: a message and the byte offset that caused it, which matches the
`error: <message> at offset <n>` line the output contract fixes.

The instructive mistake is easy to make and hard to see. The obvious implementation gives the
class a `T` member and an error member, fills in whichever applies, and offers accessors for
both. Now every error result also contains a fully constructed `T` — a zero, an empty buffer,
a plausible chunk length — and a caller who forgets to check gets valid-looking garbage with
no symptom: you have replaced a `-1` that at least stood out with a `0` that does not, and the
trouble surfaces far away, because a length of 0 walks the parser forward twelve bytes and
produces a second, different error.

So make the invalid state unaskable. The caller must be forced to ask which state the result
is in before it can extract anything, and reading a value out of a failed result should be a
programming error that is detected rather than a value that is returned. An assertion is
enough here — the point is that it must not silently succeed.

Name the price of the simple design honestly, because the learner will meet it: a plain `T`
member means every `Result<T>` must construct a `T` even when it holds an error, so `T` needs
a default constructor and one is built on the error path for nothing. The standard library
solves that with storage it constructs into only when there is something to construct, which
is what `12-it-was-in-the-box` is about. If the learner asks about `std::optional`, answer
directly: C++17 has it, it holds a value or nothing, and it carries no error payload — exactly
the gap this `Result` fills. `std::expected` is the right tool and arrived in C++23, so it is
out of reach here. Do not adopt either now, and do not treat the question as premature.

### Returning a result that owns something

`Result<Buffer>` is where the earlier chapter is paid back. Returning it by value must move
the buffer, not copy it — and if you deleted the copy in `05-the-rule-of-three`, a `Result`
that cannot move will not compile at all, which is the good outcome. The bad outcome is a
`Result` that compiles and copies, or one whose special members were suppressed by accident:
declare a destructor on `Result` and the compiler stops writing the move constructor and move
assignment, and everything silently goes back to copying. `Result` owns nothing itself, so it
needs no destructor — let the compiler write all six special members and they will move the
members for you. That is the rule from `07-bounds-you-cannot-skip` again: types that own need
the rule of five, types that do not should keep their hands off it.

### Exceptions, properly

A C programmer's picture of exceptions is usually "an expensive non-local goto that other
languages made a mess with", and correcting it is half this lesson.

`throw expr` constructs an exception object and abandons the current function. Control does
not return to the caller normally: the runtime walks back up the call stack looking for a
`try` block whose `catch` clause matches the thrown type, and transfers control there. Each
function frame abandoned on the way is *unwound*: every automatic object in it that was fully
constructed has its destructor run, in reverse order of construction, exactly as if the scope
had been exited normally. If no matching handler is found anywhere up the stack,
`std::terminate` is called and the program ends.

The middle sentence is the whole point of teaching this here. **An exception thrown through a
function that holds an owning buffer does not leak that buffer, because unwinding runs the
destructor written in `03-a-class-that-cleans-up`.** Nothing else in the program had to be
changed, no handler had to know the buffer existed, and no cleanup label had to be maintained.
Compare with C: `longjmp` runs nothing at all, and the equivalent discipline is a chain of
`goto cleanup` labels that each new early return has to be added to correctly.

This is the strongest argument for RAII available anywhere in the course, and it lands now
because the learner can already see both halves. It also inverts the usual framing: a
destructor is not a convenience that saves typing `free`, it is the thing that makes a
language with exceptions survivable at all. Every standard-library type works this way, which
is why `std::vector` can be used in code that throws without anybody thinking about it.

It is worth demonstrating rather than asserting, and the allocation counter makes that
possible: a test that constructs a buffer inside a scope, throws through it, catches outside,
and then checks that the outstanding count came back to where it started. That test is proof,
it takes ten lines, and it is the memorable part of the lesson.

Two more pieces belong here. The `noexcept` from `06-moving-not-copying` is a promise that a
function throws nothing, and it matters because the library changes its behaviour around
functions that can throw. And *exception safety* names what a function guarantees when
something it calls throws: the basic guarantee (nothing leaks, invariants hold), the strong
guarantee (it completes or leaves everything as it was), and the nothrow guarantee. Those
names are worth having; the course does not examine them further.

### Why this program returns values anyway

Teaching exceptions and then not using them is the decision, not an omission — see
`#errors-are-values`. The reasons are specific and a learner should be able to weigh them:

- **The error is data the caller wants.** The byte offset is not a signal, it is a number
  that gets printed. Something that must be stored, passed and formatted is more naturally a
  return value than a control-flow event.
- **The control flow is visible at every call site.** In a parser, "this call can fail" is the
  most important thing about most lines, and a returned result puts it in the code.
- **A malformed file is expected input, not an exceptional condition.** This tool's *job* is
  reading broken files. Failures are ordinary here in a way that a failed allocation is not.

And the other side, which the learner should also be able to argue: exceptions cannot be
ignored by omission, whereas an unchecked returned result compiles; they keep the error path
out of every intermediate function that has nothing to do with it; and a constructor has no
return value, so a type whose construction can fail has no alternative. This course does not
have that last problem, because the buffer's construction is done where a result can be
returned.

The rule that follows for the code: nothing in the parser throws. Detecting a failure produces
a value that travels outward, printing happens in one place near the top, and that place is
what writes the `error:` line and sets the exit status.

### What this buys the truncated file

With errors as values, the reporting for `assets/truncated.png` becomes ordinary code rather
than a special case: the walker lists each chunk it reads, one read fails with an offset
attached, the loop stops, the top level prints the error line and exits non-zero. Note what
must *not* happen — the chunks already listed are not withdrawn, because a result carrying an
error is a report about one read, not a verdict on the file. `rejects-truncated` still checks
that `8 IHDR 13` is listed, and it is there for that reason.

## Concepts to teach

Why `-1`, `errno`-style globals and printing at the point of detection each fail, and that
the common defect is that the failure is not data. Class templates; one template instantiated
into distinct types; member functions instantiated on use; why the definition lives in a
header. A result as a discriminated pair of value and error, with the invalid state
unreachable rather than discouraged, and an error carrying a message and a byte offset. Why
the value member must not be readable on the error path, and what a default-constructed `T`
there costs. Returning a result that owns something: move construction, and how declaring a
destructor suppresses the implicit moves. Exceptions:
`throw`, `try`/`catch`, matching by type, stack unwinding, destructors running during
unwinding, `std::terminate` when unhandled. The RAII argument — an exception through a
function holding an owning buffer does not leak, demonstrated with the counter. `noexcept`,
and the names of the three exception-safety guarantees. Why this program returns values
anyway, and the honest case for the other choice (`#errors-are-values`).

## Constraints

- No parse function returns `-1`, `0`/`1` or any other sentinel to mean failure, and none sets
  a global or file-scope error variable.
- Every failure carries the byte offset that caused it, all the way out to where it is printed.
- Parse functions do not print. The `error:` line is written in one place, from a returned
  error, and that place sets the exit status.
- The result type is a class template, defined in a header the library and the tests both
  include, and it owns nothing itself.
- There is no path on which a caller can read the value of a failed result and get a
  plausible-looking answer.
- The parser throws no exceptions. A `throw` may appear only in a test written to demonstrate
  unwinding.
- `assets/basic.png` and `assets/text.png` still list exactly as before; on
  `assets/truncated.png` the chunks read before the failure are still listed, an `error:` line
  names the offset, the exit status is non-zero, and the counter still balances.

## Suggested progression

Start by finding every place the current code signals a failure and writing down, for each,
what the caller can learn from it and what the detecting function knew but could not say. The
byte offset will be in the second column every time.

Design the error type first — two fields, and the part the output contract constrains. Then
write the class template around it, with the value and the discriminator, deciding before you
write the accessors what happens when someone asks a failed result for its value. Write a test
for that decision immediately; it is the part most likely to be quietly weakened later.

Convert the deepest parse function first, then its caller, then upward. Converting from the
bottom keeps the program compiling and makes each step small. When you reach a function
returning `Result<Buffer>`, watch what the compiler says if the buffer's move is missing or
suppressed, and connect the message to `06-moving-not-copying`.

Then do the exception experiment, in a test and never in `src/` parsing code: allocate a
buffer inside a scope, throw through it, catch outside, and assert on the counter that nothing
was lost. Do it a second time with a raw `new` and no owning type to see the counter register
the leak. That pair is the evidence for the whole argument, and it is worth keeping in the
suite.

Finish by moving all printing of failures to one place, running `rejects-truncated`, and then
`dumps-basic-png` to confirm the valid files are unaffected.

## Completion conditions

- `build`, `tests` and `rejects-truncated` pass. On `assets/truncated.png`: `8 IHDR 13` is
  still listed, one `error:` line names the offset, the exit status is non-zero, and the
  program does not die on a signal.
- No sentinel return and no global error state remains anywhere in the parser, and no parse
  function prints.
- A test shows that a failed result cannot be read as a successful one — an assertion fires, a
  null is returned, or the call does not compile — and a test shows an error's offset arriving
  at the caller with the value the detecting function saw.
- A test demonstrates that an exception thrown through a scope holding an owning buffer leaves
  the allocation counter balanced.
- `explains-the-repair`: in their own words, the learner can
  - describe what happens between `throw` and `catch`, and say why the buffer's destructor
    runs;
  - give the course's three reasons for returning errors as values, and one good argument for
    exceptions that this program does not happen to need;
  - explain why a result whose value is always readable is worse than the `-1` it replaced;
  - name the special member function that makes `Result<Buffer>` returnable, and say what
    declaring a destructor on `Result` would have cost.

## On completion, persist

Record in the instance's `STATE.md` the name of the result type and its header, the shape of
the error type (message plus byte offset), and the single place where failures are printed —
`10-chunks-without-switch` and `11-the-finished-tool` both add failure paths and must use it.
Record in the instance's `DESIGN.md` that exceptions were taught and deliberately not used,
with the learner's own statement of why, so that a later lesson does not reopen a decision
already made. Note whether the unwinding test is in the suite, since it is the evidence for
`#owning-and-borrowing` that the rest of the course refers back to.

## Optional deeper paths

If the learner wants to know what the standard library would do here, answer plainly rather
than deferring: `std::optional<T>` is in C++17 and models "a value or nothing" with no room
for an error; `std::variant` can hold either alternative; `std::expected<T, E>` is exactly this
`Result` and arrived in C++23, out of reach for this course. `12-it-was-in-the-box` replaces
the hand-written type, and doing it now costs the exercise.

For the curious: find out what `throw` costs when nothing is thrown, what happens when a
destructor throws during unwinding and why destructors are implicitly `noexcept`, and read
about `std::error_code`, the standard library's own value-based error channel. Then consider
what the result type would become if a failure could carry more than one error — the shape a
validating parser eventually grows into.
