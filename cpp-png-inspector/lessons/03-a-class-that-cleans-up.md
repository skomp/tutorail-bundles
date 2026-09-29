---
id: 03-a-class-that-cleans-up
title: A class that cleans up after itself
design_refs: [owning-and-borrowing, the-allocation-counter]
validators: [build, dumps-basic-png, no-leak-on-error-path]
---

## Purpose

Stop fixing the leak and make it unwriteable, by handing the file bytes to an object whose
cleanup the compiler calls on every exit path — including the early returns that
`02-where-the-leaks-are` measured.

The previous lesson put a number on the loss. The obvious repair is to add the missing
`free` to the error path, and it works until the next error path is added. This lesson
takes the choice away from you.

## Prerequisites

`00-write-the-c-walker`, `01-not-a-superset` and `02-where-the-leaks-are` are complete. The
program builds as C++17, walks `assets/basic.png` correctly, and prints the allocation
report line. On `assets/truncated.png` the report shows outstanding allocations, and you
can point at the `return` statement that skips the `free`.

## Learning objectives

- Write a class with a constructor that acquires a resource and a destructor that releases it
- Say exactly when a destructor runs, and name the exit paths on which it runs that a
  hand-written `free` did not cover
- Explain why a `destroy()` method you call yourself is not the same thing, and what the
  checks show when you use one
- Write a destructor that is correct for an object whose allocation never happened
- Pair `new` with `delete` and `new[]` with `delete[]`, and say why mixing them with
  `malloc`/`free` is not allowed
- Move the allocation counter from `malloc`/`free` to `operator new`/`operator delete` and
  explain what changed about what it sees

## Theory

In C, freeing memory is a discipline: for every allocation somewhere there is a matching
release, and keeping them matched is your job on every path through the function. You
proved in the last lesson that the discipline had already failed — not because you are
careless, but because an early `return` is an exit path that does not look like one. Add a
third error case next week and the same hole opens again.

C++ does not offer a better discipline. It offers a different mechanism: it moves the
release out of your control flow and attaches it to the **lifetime of an object**.

### A class is a struct whose functions came with it

A `struct` in C++ is a `class` whose members are public by default; those are the only
differences worth your attention today. Either one may contain functions as well as data,
and a function declared inside gets an implicit first parameter — a pointer to the object
it was called on, spelled `this`. Writing `b.size()` calls a function with `b`'s address
already in hand. That is all a member function is; you have written the same thing in C as
`buffer_size(&b)`.

Two member functions are special because the compiler calls them for you.

A **constructor** has the class's name and no return type. It runs when an object comes
into existence, and its job is to leave the object in a state every other member function
can rely on:

```cpp
struct Widget {
    Widget(std::size_t n);   // runs when a Widget comes into existence
    ~Widget();               // runs when its lifetime ends
};
```

Members are best set in a **member initialiser list**, between the parameter list and the
body:

```cpp
Widget::Widget(std::size_t n) : data_(nullptr), size_(0) { /* body runs after this */ }
```

The distinction is not cosmetic. Members are initialised in the order they are declared in
the class, and they are initialised *before* the constructor body starts. Assigning to them
in the body is therefore a second write over an already-initialised member. For a pointer
and a length that is merely wasteful; for a `const` member or a reference member it does not
compile at all. Get into the habit now.

A **destructor** is written `~Widget()`, takes no parameters and returns nothing. It runs
when the object's lifetime ends. For a local object that is when control leaves the scope it
was declared in — and here is the whole lesson: **on every path out of that scope**. Falling
off the end of the function, a `return` in the middle, a `break` out of the loop, a `return`
buried in an error branch you add six months from now. You do not write the call. You cannot
forget the call, because there is no call for you to write.

This pattern — acquire the resource in the constructor, release it in the destructor, and
let scope be the unit of lifetime — is the single most important idea in C++, and it has an
ugly name: RAII, for *resource acquisition is initialisation*. The name describes the first
half. The half that matters to your program is the second: release is destruction.

### `new` and `delete` are not `malloc` and `free` with a coat of paint

C++ allocates with `new` and releases with `delete`. Three practical differences:

- `new T` returns a `T*`, not a `void*`. There is no cast, which matters because
  `01-not-a-superset` made you write those casts and think about what each one asserted.
- `new` and `delete` run constructors and destructors; `malloc` and `free` only move memory
  around.
- Arrays have their own spelling. `new unsigned char[n]` must be released with `delete[]`,
  never plain `delete`. `delete` on an array pointer and `delete[]` on a single object are
  both undefined behaviour, and on most platforms they will not even crash promptly.

The pairing rule is absolute and there are three pairs, not one: `new` with `delete`,
`new[]` with `delete[]`, `malloc` with `free`. Memory from one may never be released by
another's partner. If part of your program still calls `malloc`, the buffer it produced must
still reach `free`; the cleanest way through this lesson is to move the file bytes to
`new[]`/`delete[]` entirely rather than leave the program with two allocation styles in it.

One small mercy you already know from C: `free(NULL)` is defined to do nothing, and
`delete` and `delete[]` on a null pointer are defined the same way. That fact is what makes
the next paragraph work.

### A destructor runs for objects that never got what they wanted

The destructor runs for every object whose constructor completed — whatever happened inside
that constructor. If the file was empty, if the length was zero, if you decided not to
allocate, the object still exists and its destructor still runs. So every path through your
constructor has to leave the members meaningful, which in practice means: the pointer is
either a live allocation or null, and the length agrees with it. Initialise both in the
member initialiser list before anything can go wrong, and the destructor's job becomes a
single unconditional release that does nothing when there was nothing.

The failure this prevents is a destructor that releases a member that was never set, on an
object built from a zero-length or unreadable file. It is easy to write, and it is not
reliably fatal, which is worse. (One exception, worth knowing and not worth exercising here:
if a constructor throws, the object never came into existence and its destructor does not
run. Exceptions arrive in `09-errors-without-errno`.)

### The trap: calling cleanup yourself

The instinctive first move for a C programmer is to give the class a `destroy()` — or
`release()`, or `close()` — and call it where the `free` used to be. It compiles, the happy
path is clean, and the code looks object-oriented.

It is C with classes, and it has changed nothing. The call is still yours to remember, the
early return still skips it, and the leak is still there on exactly the run that matters.
Run `no-leak-on-error-path` against that version before you decide whether it is finished;
the truncated asset is the run that takes the error path, and the check reads the number
your own counter printed.

### What the counter counts now

`#the-allocation-counter` says the counter stays in the program for the whole course, and
from this lesson it wraps `operator new` and `operator delete` rather than `malloc` and
`free`.

Those are real, ordinary functions, and this is the part that surprises people: `new` is an
*expression*, and the memory it hands out comes from a function named `operator new(std::size_t)`
that the standard library defines and that **your program may replace** simply by defining
its own at global scope. Same for `operator delete(void*)`, and separately for the array
forms `operator new[]` and `operator delete[]`. Define them, count in them, forward the real
work to `std::malloc` and `std::free`, and every `new` anywhere in your program passes
through your counter without a single call site changing.

Two consequences to be ready for:

- You are now counting **every** allocation the process makes through `new`, including ones
  the standard library makes on your behalf. That is honest — it is the truth about your
  process — but it means the report is only zero at exit if nothing else is still holding
  memory. On some standard libraries the first use of `std::cout` allocates once at startup
  and releases it after your report has already printed, which shows up as a stubborn
  outstanding count of one or two that does not respond to anything you change in your own
  code. If you meet that, printing with `std::printf` (which is what your C version already
  used, and which does not allocate through `new`) is the cheapest way out, and it keeps the
  output contract identical.
- The report must still be printed on **every** exit path, which is the lesson you already
  paid for in `02-where-the-leaks-are`. The run that leaks is the run that returns early.

Keep printing the same line. `#the-output-contract` fixes its shape —
`allocations: <n> frees: <m> outstanding: <k>` — and every check from here to the end of the
course reads it.

### Why not `std::vector`

Because you would not be able to read its interface yet. `std::vector` is exactly this
class, written by someone with twenty years to get it right, and you are going to delete
your version in favour of it in `12-it-was-in-the-box`. What you are buying with the next
four lessons is the ability to open its documentation and recognise every member function as
an answer to a problem you have personally had. Build the problem first.

## Concepts to teach

Class and struct; member functions and the implicit `this`. Constructors; the member
initialiser list, and why it is not the same as assigning in the body (declaration order,
initialisation before the body, `const` and reference members). Destructors; when they run,
and that the compiler emits the call on every exit path from a scope. RAII as *scope is the
unit of lifetime*. `new`/`delete`, `new[]`/`delete[]`, and the three pairings that may not be
crossed. `delete` on a null pointer being a defined no-op, and why that shapes the
constructor. The destructor of an object whose acquisition did not happen. The
`destroy()`-by-hand anti-pattern and why it reinstates the leak. `operator new` and
`operator delete` as replaceable functions, and what replacing them globally makes visible
(`#the-allocation-counter`). One type owns the bytes and everything else borrows them
(`#owning-and-borrowing`). Why the standard containers are deliberately not the answer yet
(`#handwritten-then-replaced`).

## Constraints

- Exactly one type owns the file bytes. Every function that reads them takes a reference to
  that object (or, from `07-bounds-you-cannot-skip`, a view — a pointer and a length that
  borrow the bytes and own nothing) and frees nothing.
- No `free` or `delete` of the file bytes may appear anywhere except in that type's
  destructor. That includes the success path.
- Cleanup must not depend on a member function you call by hand. If the object can be
  destroyed without releasing its memory, the lesson is not finished.
- Do not use `std::vector`, `std::unique_ptr`, `std::string` or any standard container for
  the buffer. This is the course's shape, not a restriction for its own sake; see
  `#handwritten-then-replaced`.
- The output contract does not change. `dumps-basic-png` must still pass, byte for byte.
- The allocation report is still printed on every exit path, and the counter now sits in
  `operator new`/`operator delete` rather than around `malloc`/`free`.
- Keep the program building as C++17 with the CMake setup from `01-not-a-superset`; the
  project split comes in the next lesson, not this one.

## Suggested progression

Start by naming the thing that owns the bytes. Look at your parser and decide which single
object should hold the file contents and their length — there should be exactly one.

Turn it into a class with a constructor that acquires and a destructor that releases. It is
worth deciding deliberately whether the constructor opens and reads the file itself, or
whether it takes bytes that a separate read function produced; both work, and the second
becomes relevant in `06-moving-not-copying` when that function has to hand the buffer back.
Make the member initialiser list leave the pointer and length in a defined state before
anything can fail.

Now change the allocation: move the file bytes from `malloc` to `new[]`, and the release to
`delete[]`. Check the whole program for other `malloc` calls and decide, for each, which
pairing it belongs to.

Move the counter. Replace the global `operator new` and `operator delete` (and the array
forms), count in them, and confirm the report still prints on both a good file and a bad
one. Compare the numbers against what lesson 02 reported for the same file and account for
the difference — the counter is now seeing allocations it could not see before.

Then delete the `free` calls from the parser's error paths — all of them — and run
`no-leak-on-error-path` on the truncated asset. Run `dumps-basic-png` too: a buffer that
releases too eagerly passes the leak check and breaks the listing.

If at any point you reach for a `destroy()` method, or find yourself writing a cleanup call
before a `return`, run the error-path check at that exact moment rather than after you have
tidied up. What the check says about that version is the point of the lesson.

Finally, read your parser's error branches and satisfy yourself that there is no longer a
release statement in any of them — and that this is why adding a fourth error branch
tomorrow cannot reintroduce the leak.

## Completion conditions

- `build` passes.
- `dumps-basic-png` passes: the chunk listing for `assets/basic.png` is unchanged and the
  tool still exits 0.
- `no-leak-on-error-path` passes: run over `assets/truncated.png`, the allocation report
  shows `outstanding: 0`.
- No `free` or `delete` of the file bytes appears anywhere outside the owning type's
  destructor, and no error path in the parser contains a release statement. This is read
  from the code, not inferred from the checks passing.
- The learner can state when the destructor runs, and name at least two exit paths it covers
  that their lesson-02 `free` did not.
- The learner can say why a `destroy()` method called by hand does not solve the problem,
  in terms of what the error-path check reports.
- The learner can explain why the destructor is correct for an object whose allocation never
  happened, naming the member initialiser list and the defined behaviour of `delete` on a
  null pointer.
- The learner can say where the allocation counter now sits, what replacing `operator new`
  makes visible that wrapping `malloc` did not, and why the numbers differ from lesson 02's.

## On completion, persist

Record in the instance's `STATE.md` that an owning buffer type now exists, its name, whether
its constructor reads the file itself or receives already-read bytes, and that cleanup is in
its destructor with no release on any error path. Record that the allocation counter has
moved to `operator new`/`operator delete` and note the report's numbers for
`assets/basic.png` and `assets/truncated.png` so later lessons have a baseline to compare
against. Note in `DESIGN.md` any decision the learner made about where the file is read —
constructor or free function — because `06-moving-not-copying` depends on it. If the
standard library's own allocations showed up in the count, record how that was handled.

## Optional deeper paths

See the calls the compiler emits for you: take a function with two `return` statements and a
local object, and look at the generated code (`g++ -fdump-tree-gimple`, or
`clang -Xclang -ast-dump`). There is a destructor call on each path, placed by the compiler.

The sized deallocation function `operator delete(void*, std::size_t)`, added in C++14: what
the compiler may call instead of the plain form, and why the default sized version is
defined to forward to the unsized one — which is why replacing only the unsized pair works.

`std::malloc` versus `operator new` versus the `new` expression: three layers that are
routinely conflated. Which one you can replace, which one calls constructors, and where
`new (std::nothrow)` fits.

Destruction order: members are destroyed in reverse declaration order, after the destructor
body has run. Write a small class with two members that announce themselves and watch the
sequence.
