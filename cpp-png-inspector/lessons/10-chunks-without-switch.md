---
id: 10-chunks-without-switch
title: Chunks without a switch
design_refs: [chunk-data-vs-chunk-handlers, owning-and-borrowing]
validators: [build, tests, dumps-basic-png, no-leak-on-error-path]
---

## Purpose

Replace the `switch` over chunk type with objects the walker never names, so that
teaching the tool about a new chunk type costs one new class instead of one more case in
a function that already knows too much.

## Prerequisites

Lessons `00-write-the-c-walker` through `09-errors-without-errno` are complete. In
particular the program already has: an owning buffer whose destructor releases it
(`03-a-class-that-cleans-up`), a library target, a binary and a CTest suite
(`04-a-target-of-its-own`), copy and move that behave (`05-the-rule-of-three`,
`06-moving-not-copying`), a non-owning view of bytes with a checked read
(`07-bounds-you-cannot-skip`), a `read<T>()` that converts big-endian fields in exactly
one place (`08-templates-eat-the-macros`), and parse failures returned as values carrying
a byte offset (`09-errors-without-errno`). The allocation counter from
`02-where-the-leaks-are` is still in the program and still prints its report at exit.

Somewhere in the walker there is a `switch` (or a chain of `if`s comparing four
characters) that decides what to say about a chunk.

## Learning objectives

- Declare an abstract base class with a pure virtual function and implement it in more
  than one derived class
- Explain what `virtual` changes about a call — which function runs, when that is decided,
  and what the indirection costs
- Use `override`, and say exactly what the compiler checks when you write it
- Explain why deleting a derived object through a base pointer needs a virtual destructor,
  and show what its absence costs using the allocation counter
- Distinguish polymorphic *data* from polymorphic *interpretation*, and say why a chunk
  stays a plain value here
- Support a new chunk type by writing one new class and editing no existing function

## Theory

Look at what the walker does once it has parsed a chunk. It has an offset, a
four-character type, a length, a view of the payload and a stored CRC — and then it
branches on the type to decide what to print. Right now that branch is small. It is about
to stop being small: `11-the-finished-tool` teaches the tool to read the text out of a
`tEXt` chunk, and a format with dozens of chunk types has no shortage of further cases.

A `switch` over a type tag is the C answer, and it is less wrong than it is in the wrong
place. It puts the list of types the program cares about inside a function, so that
function is edited by everyone who adds a type, and the knowledge about `tEXt` lives in
the walker rather than in anything called `tEXt`. What you want instead is for the walker
to say *"here is a chunk, tell me about it"* to something it does not know the name of.

### Two ways to remove the switch, and only one of them is good

The obvious reading of "replace the switch with polymorphism" is: make the chunk a base
class, and derive `IhdrChunk`, `TextChunk`, `IdatChunk` from it. The walker calls
`chunk->describe()` and the right one runs. The switch is gone. It works, and it is the
wrong design — worth understanding before you write either one, because the mistake stays
invisible until two lessons later.

A parsed chunk holds the same five things whatever its type: where it starts, its type,
its length, a view of its payload, and its stored CRC. Nothing about the *data* varies by
type. What varies is what you *say* about the data. Making the data polymorphic buys you
nothing and costs you two things.

First, polymorphism in C++ works through pointers and references, not values. A derived
object assigned into a base-typed variable is *sliced*: the copy keeps the base part and
silently drops everything the derived class added, including the fact that it was ever
derived. So a list of chunks cannot be a list of chunk values any more. Every chunk in the
file has to be heap-allocated and held behind a base pointer — an allocation per chunk, in
a program whose entire subject for four lessons was that allocations are a liability.

Second, it closes a door at the end of the course. `12-it-was-in-the-box` replaces the
hand-written machinery with the standard library, and a list of plain chunk values becomes
a `std::vector` of values. A list of polymorphic chunks cannot: it becomes a vector of
owning pointers, because values would slice. The design decision is recorded in this
bundle's `DESIGN.md` under `#chunk-data-vs-chunk-handlers`, and it is the substance of
this lesson.

So: **the chunk stays a plain value. The polymorphism goes in the handler** — an object
whose job is to interpret a chunk it is given and report on it. There is one handler class
per kind of interpretation, the walker holds them behind a base pointer, and the mapping
from a four-character type to a handler is data, not control flow.

### What a virtual function actually is

You have written this in C: a struct of function pointers, one set per "kind", every
instance pointing at the right set. That is a vtable built by hand, and C++ writes it for
you. A class with at least one virtual function gets a hidden pointer added to each
object, pointing at a per-class table of function addresses; a call through a base pointer
loads the address from that table and calls it.

The distinction that matters at the call site is *when the function is chosen*. A
non-virtual call is resolved by the compiler from the **static** type — the type written
in the source. A virtual call is resolved at run time from the **dynamic** type, what the
object actually is. Same syntax, two different rules; this is the one place in C++ where
you cannot tell which function runs by reading the call. It is not free either: one
pointer of size per object, and one indirect call the optimiser usually cannot inline
through. For a handler invoked once per chunk that is noise — but a C programmer's
instinct that "objects are slow" is exactly this cost, and it is worth being able to say
how large it is.

A **pure virtual** function is declared with `= 0`:

```cpp
virtual void handle(const Chunk& c) = 0;
```

It has no implementation in the base, and a class that has one cannot be instantiated —
it is an **abstract base class**, a description of what a handler must be able to do. That
is the kind of inheritance this course uses: inheritance of an *interface*, not of an
implementation. The base holds no data and supplies no shared behaviour. If you find
yourself putting a member variable in the base for the derived classes to use, stop and
ask whether it is still an interface.

### `override`, and the function you defined by accident

Writing `override` on a derived function tells the compiler *I intend this to replace a
virtual function from a base class*, and the compiler then checks it. To override, the
derived function must have the same name, the same parameter types, the same
const-qualification and a compatible return type. Differ in any of them and you have
overridden nothing: you have declared a **new** function that happens to share a name, the
base's version stays in the vtable, and calls through a base pointer go on reaching the
base for the rest of the program's life.

One `const` is the difference that catches people, because both spellings look right in
isolation:

```cpp
void handle(const Chunk& c);         // in the base
void handle(Chunk& c);               // in the derived: a different function entirely
```

Without `override`, that compiles and does nothing. With `override`, it is a compile
error. You will be asked to produce this error on purpose, because recognising the message
once is worth more than being warned about it.

### The virtual destructor

Now the one that costs memory. `delete p`, where `p` is a base pointer, has to run a
destructor, and the compiler picks it the same way it picks any other member function:
from the **static** type, unless the destructor is virtual. If the base's destructor is
not virtual, the derived destructor never runs. The language calls that undefined
behaviour; what you observe is nothing at all — no crash, no warning, no diagnostic, and a
program that keeps working.

Except that whatever the derived object owned is never released. If a handler holds a
member whose destructor frees something — the owning buffer from
`03-a-class-that-cleans-up`, say — that release never happens, and the leak four lessons
made unwriteable is back, reintroduced by a missing keyword in a base class.

The fix is one line in the base:

```cpp
virtual ~Handler() = default;
```

and the rule behind it: **a class intended to be deleted through a pointer to it needs a
virtual destructor.**

Be precise about what the counter can see, because it decides how the experiment has to
be set up. The counter counts calls: one allocation for the handler object, one
deallocation when it is deleted — and those balance whether or not the right destructor
ran. What it catches is the allocation the derived object's *own member* is holding and
never gets to release. So the omission is observable only if at least one of your handlers
owns something on the heap. That is a constraint on this exercise, and not an artificial
one: a handler that accumulates something across a file — how many `IDAT` chunks it saw
and how many bytes they carried — has a real reason to own storage.

### What "the switch is gone" has to mean

A dispatch table is easy to fake. If the walker looks a handler up and then still asks
"but which one is it?" anywhere, you have moved the switch rather than removed it. The
completion condition is behavioural: **adding a chunk type touches one new class and no
existing function.** Registering the handler is one more entry in a list of pairs — data —
and that is the honest exception. A new `case`, a new `if`, or a new branch inside an
existing handler is not.

The `default:` arm of the old switch — list the chunk by name and length, say nothing more
— becomes a handler too: the fallback the table returns for a type it holds nothing for.
Most chunks in a real PNG go through it, and that is correct; a parser that walks chunks
properly does not need to know what `gAMA` means.

One boundary to keep from `#owning-and-borrowing`: a handler is handed a chunk whose
payload is a **view** into the one buffer that owns the file. The handler reads through
that view and must not copy the bytes out or take ownership of them. Its lifetime is
shorter than the buffer's; it borrows. State the handler computes for itself is a
different thing and may be owned.

## Concepts to teach

Interface inheritance versus implementation inheritance. Abstract base class; pure virtual
function (`= 0`) and why such a class cannot be instantiated. Static type versus dynamic
type; virtual dispatch and when the function is chosen; the vtable as the C struct-of-
function-pointers the compiler writes for you, and its cost in space and indirection.
Non-virtual calls resolved at compile time. `override` and exactly what it makes the
compiler check — name, parameter types, const-qualification, return type — and the new
function you define silently without it. The virtual destructor, deletion through a base
pointer, and what is not released when it is missing. Object slicing, and why polymorphism
needs pointers or references. The reason the chunk is a value and the handler is the
polymorphic thing (`#chunk-data-vs-chunk-handlers`), including what it buys in
`12-it-was-in-the-box`. Handlers borrow the payload and do not own it
(`#owning-and-borrowing`); the table owns the handlers.

## Constraints

- The parsed chunk stays a **plain value**: no base class, no virtual functions, no
  per-chunk heap allocation. The parser keeps returning values.
- The handler base class is abstract — at least one pure virtual function — holds no data
  members, and is used only through base pointers or references.
- Every function in a derived handler that implements the interface carries `override`.
- At least one handler owns a heap allocation of its own, through the owning type written
  in `03-a-class-that-cleans-up`, so that a missing virtual destructor is observable
  rather than theoretical.
- The table owns its handlers and releases them. It may hold owning raw pointers for now;
  `12-it-was-in-the-box` is where that becomes `std::unique_ptr`. The hand-written buffer
  and result type stay hand-written (`#handwritten-then-replaced`).
- After the change, no `switch` or `if`/`else if` chain on a chunk type remains anywhere
  outside the table lookup itself.
- Handlers read the payload through the borrowed view. No handler copies the payload into
  storage it owns.
- The output contract is unchanged (`#the-output-contract`): the chunk lines for
  `assets/basic.png` must be byte-for-byte what they were before this lesson, and the
  allocation report still prints at exit.
- Whatever prints the allocation report must run **after** the handler table has been
  destroyed. A report printed while the handlers are still alive counts them as
  outstanding and the check fails for a reason that is not a leak.
- `assets/basic.png` and `assets/truncated.png` behave exactly as they did at the end of
  `09-errors-without-errno`: the valid file lists cleanly and exits 0, the truncated file
  still lists `8 IHDR 13`, reports an `error:` line and exits non-zero.

## Suggested progression

Start by reading the branch you are about to delete: count its arms and say what each one
contributes. Then look ahead — `11-the-finished-tool` adds reading the text out of a `tEXt`
chunk, and validating a CRC. Predict which of the two becomes a new arm of this switch and
which does not; they are not the same kind of thing, and the answer says what the handler
interface is for.

Before writing any handler, try the tempting design on paper: a `Chunk` base class with
`IhdrChunk` and `TextChunk` derived from it. Work out what the walker's list of chunks has
to become, and what happens when a derived chunk is assigned to a base-typed variable — a
three-line scratch program outside `src/` shows slicing rather than asking you to take it
on faith. Then set that design aside.

Define the handler interface: an abstract base with one pure virtual function taking a
parsed chunk. Write two handlers against it, one for `IHDR` and one for `IDAT`, and give
the `IDAT` handler a job that needs memory — a record of every `IDAT` chunk it has been
given, owned through your buffer type, so it can report the count and total payload size
at the end of the run. Then build a table mapping a type to a handler, have the walker
look up and call, and delete the handlers when the table goes away.

Now run `build` and `no-leak-on-error-path`, then run the tool yourself over
`assets/basic.png` and read what the counter says there. The second run is the one that
shows this: `assets/truncated.png` ends 54 bytes into the first `IDAT`'s payload, so no
complete chunk ever reaches that handler, it never allocated on that path, and its counts
balance whether the destructor is virtual or not. If the number is not zero, do not reach for the answer: find out which
allocation is outstanding, which destructor was supposed to release it, and why that
destructor did not run when the handler was deleted through a base pointer.

With that fixed, do the `override` experiment on purpose. Take one derived handler, change
its parameter or its const-qualification so the signature no longer matches the base, and
build it twice: once with `override` on the function and once without. The build without
is the interesting one — it succeeds, and the handler is never called again.

Then finish the job: move the old `default:` behaviour into a fallback handler, delete the
switch, and confirm nothing branches on a chunk type any more. Prove the claim by adding a
handler for a type that does not appear in the test files at all — `gAMA` or `pHYs` — and
counting the existing functions you had to edit. The answer should be zero.

Add tests: that a call through a base pointer reaches the derived handler; that
constructing a handler, giving it a chunk to record, and deleting it through a base pointer
leaves the counter balanced — give it the chunk, or the test passes with the destructor
having had nothing to release; that the table returns the fallback for an unregistered
type. Finish with `build`, `tests`, `dumps-basic-png` and `no-leak-on-error-path`.

## Completion conditions

- `build`, `tests`, `dumps-basic-png` and `no-leak-on-error-path` all pass.
- The chunk listing for `assets/basic.png` is unchanged from before this lesson, and the
  allocation report shows `outstanding: 0` on the truncated file.
- No `switch` or `if`/`else if` chain on chunk type remains outside the table lookup, and
  the parsed chunk has no virtual functions.
- A handler exists whose destructor releases a heap allocation, and the learner can say —
  from having watched the counter go non-zero — what the missing virtual destructor failed
  to release and why nothing crashed.
- The learner can state which function a call through a base pointer runs and what would
  have run instead had it not been virtual, say what `override` made the compiler check,
  and describe the function they defined by accident without it.
- The learner can explain why the chunk is a value rather than a base class, naming both
  costs of the alternative: an allocation per chunk, and a list that cannot hold values.
- Adding a handler for a new chunk type required exactly one new class and one registration
  entry, with no existing function edited — demonstrated, not asserted.

## On completion, persist

Record in the instance's `DESIGN.md`: the handler interface (the base class name and its
pure virtual function), the decision that a parsed chunk is a plain value with polymorphism
in the handlers, how the table maps a type to a handler and what it does with an
unregistered type, which handler owns heap state and what it owns, and that the table owns
its handlers through a raw pointer pending `12-it-was-in-the-box`.

Record in `STATE.md` that abstract base classes, pure virtual functions, virtual dispatch,
`override` and the virtual destructor have been demonstrated, with the allocation-counter
reading observed before and after the virtual destructor was added — that number is the
evidence.

## Optional deeper paths

Print `sizeof` a handler before and after its first virtual function and watch it grow by
a pointer. Ask why a constructor cannot be virtual, and what a virtual call made *during*
construction dispatches to — the answer surprises most people and explains a class of real
bugs. Read about `final`, on a class and on a function, and what it lets the optimiser do.
Look at the non-virtual interface idiom, where a public non-virtual function in the base
calls a private virtual one so the base keeps control of what happens around the override.
Ask what `dynamic_cast` is for, and notice that a design where the table chooses the
handler never needs it — needing it usually means the interface is missing a function.
Finally, compare this design with a table of function pointers or `std::function` values,
and work out at what point a handler that remembers something across chunks makes the
class the better answer.
