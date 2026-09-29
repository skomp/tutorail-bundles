---
id: 05-the-rule-of-three
title: The rule of three
design_refs: [owning-and-borrowing, the-allocation-counter]
validators: [build, tests, no-leak-on-error-path]
---

## Purpose

Pass your buffer to a function by value, watch the same pointer get released twice, and
learn the three functions that have to agree before an owning type is safe to copy.

The destructor you wrote in `03-a-class-that-cleans-up` made the leak unwriteable. It also,
quietly, made a second defect writeable — one the C version could not have had, because in C
nothing copies itself behind your back.

## Prerequisites

`03-a-class-that-cleans-up` and `04-a-target-of-its-own` are complete. An owning buffer type
releases its bytes in its destructor, the project builds as a library plus the `pngdump`
binary plus a test executable, and `tests` runs at least one test you have watched fail when
the code under it was broken.

## Learning objectives

- Predict what the compiler-generated copy does to a class holding a raw owning pointer, and
  confirm the prediction with the allocation counter
- Write a copy constructor and a copy assignment operator for an owning type
- Say why copy assignment has three jobs where copy construction has one, and get their
  order right
- Make assignment correct when the source and the target are the same object
- State the rule of three, and say what makes it a rule rather than a style preference
- Use `= delete` deliberately, and say precisely what it costs the rest of the program

## Theory

### The functions you did not write

Your buffer class has a copy constructor and a copy assignment operator. You did not write
them; the compiler wrote them for you, as it does for every class that does not say
otherwise. What it wrote copies each member in turn.

For a class holding an `int` and a `double` that is exactly right. For a class holding a
pointer to memory it owns, copying "each member in turn" copies the **address**, not the
bytes at that address. You get two objects that each believe they own one allocation, and
one allocation.

Both of them have destructors. Both destructors run.

### Where it happens without you asking

Declare a function parameter by value —

```cpp
void inspect(Buffer b);       // by value: the call copies
void inspect(const Buffer& b) // by reference: the call does not
```

— and every call constructs a new `Buffer` from the caller's one, using that
compiler-written copy constructor. When `inspect` returns, its parameter goes out of scope
and its destructor releases the bytes. Back in the caller, the original buffer is still
holding a pointer to memory that no longer belongs to anybody, and when *it* goes out of
scope it releases the same address a second time.

What a second release does is undefined, which in practice means one of: an immediate abort
from the allocator with a message about a corrupted heap or an invalid pointer; a silent
corruption that ends the program somewhere unrelated much later; or, on a lucky run,
nothing visible at all. All three are worse than a leak, because a leak is a number and this
is a coin toss.

Note what that does to your evidence. If the program aborts inside the second release, the
allocation report at the end of `main` is never printed, and the checks that read it will
tell you there is no report rather than that there is a double free. And if you do reach the
report with more frees than allocations, the outstanding figure goes negative — and
`#the-output-contract` fixes that line as `outstanding: <k>` where `<k>` is a number the
scripts read as digits. A minus sign makes the line unreadable to them, and the check
reports a missing report. If a check tells you the allocation report has gone missing, look
first at whether your program died before printing it, and second at the numbers it printed.

### Copy construction

A copy constructor is the constructor that takes another object of the same class:

```cpp
Buffer(const Buffer& other);
```

Both parts of that signature earn their place. It is a **reference** because taking the
parameter by value would require copying the argument, which would call the copy
constructor, which would copy its argument. It is **`const`** because copying must not
modify the thing being copied, and because a `const Buffer&` binds to things a non-const
reference cannot.

Its job is one thing: leave the new object owning its own equivalent of what the source
owns. Allocate for the new object, copy the bytes across, set the length. Afterwards there
are two allocations and two objects, each responsible for one — and the counter will say
so.

This is a **deep copy**, and it is expensive: for a real PNG of a few megabytes, passing the
buffer by value duplicates a few megabytes. That expense is the subject of
`06-moving-not-copying`. For now, correct and expensive beats fast and wrong.

### Copy assignment, and why it is harder

```cpp
Buffer& operator=(const Buffer& other);
```

`operator=` is an ordinary member function whose name is punctuation; writing `a = b` calls
it. It returns a reference to the object assigned to — `*this` — which is what makes
`a = b = c` work and what matches the behaviour of assignment on built-in types. Returning
`void` compiles and is a small lie about your type.

The difference from construction is that the target **already exists and already owns
something**. Assignment therefore has three jobs where construction had one: release what
the target currently holds, acquire new storage, and copy the source's bytes into it. Every
way of getting this wrong is a bug you will meet:

- Acquire and copy but forget to release the old allocation, and every assignment leaks one
  buffer. Your counter sees it; this is what the counter is for.
- Return early on some condition after allocating and before releasing, and you leak on
  exactly that path.
- Release first, then acquire — and the day the two objects are the same one, you have read
  from memory you just handed back.

### Assignment to yourself

`b = b` looks like something nobody writes, and nobody writes it deliberately. It arrives
through aliasing: `items[i] = items[j]` where `i` and `j` happen to be equal, or two
references that turn out to name the same object. An implementation that releases the
target's memory first and then copies the source's bytes will, in that case, copy out of a
freed allocation into new storage — reading memory the allocator may already have reused.

There are two standard cures and both are worth knowing.

The **self-assignment check** is the direct one: compare addresses at the top, and if they
are the same object, return `*this` unchanged. Cheap, obvious, and easy to forget.

**Copy-and-swap** is the structural one. Give your class a `swap` member that exchanges the
pointer and the length of two objects — no allocation, no release, it cannot fail. Then
assignment takes a copy of the source, swaps the copy's contents with its own, and lets the
copy's destructor release what used to be yours as it goes out of scope. Nothing is released
until the new storage is safely in hand, so self-assignment is correct without a special
case, and so is the case where the allocation fails. The price is that a self-assignment
does a real copy rather than nothing. Either answer is defensible; be able to say which one
you chose and what it buys.

### The rule of three

If a class needs a destructor, it almost certainly needs a copy constructor and a copy
assignment operator too — and if it needs any one of the three, it needs all three.

It is a rule rather than a preference because the three are not independent. The reason you
needed a destructor is that the class owns a resource; owning a resource is exactly what
makes memberwise copying wrong. Having written one and not the others, you have a type whose
destructor assumes exclusive ownership and whose copy hands out shared ownership, and the
compiler will not say a word about the contradiction. It writes the two you left out, they
compile, and the program is wrong at run time.

Two lessons from now the rule grows to five. The other two are `06-moving-not-copying`'s
subject, and there is an optional lesson — `what-the-compiler-writes-for-you` — on exactly
which member functions the compiler writes, and what makes it stop, if you want the whole
picture rather than the part you need today.

### Saying no: `= delete`

Writing the copies is not the only correct answer. You may declare that your type cannot be
copied:

```cpp
Buffer(const Buffer&) = delete;
Buffer& operator=(const Buffer&) = delete;
```

`= delete` does not remove the function; it declares it and makes any attempt to use it a
compile error. That is the point. Overload resolution still finds it, so an accidental copy
is reported at the line that wrote it, with the argument type in the message, rather than
duplicating a pointer at run time.

For a type owning megabytes this is a defensible design, and for some resources — a file
handle, a lock — it is the only correct one, because there is no meaningful way to duplicate
what is owned.

What it costs is not nothing, and a learner who chooses it has to be able to say what:

- You cannot pass the buffer by value, cannot store it in anything that copies, and cannot
  return it by value from a function until move semantics exist next lesson.
- Every use site must borrow instead: `const Buffer&` for reading, `Buffer&` when the callee
  really does modify it. This is usually what you wanted anyway.
- When you genuinely do need a duplicate, you need an explicit way to ask — a named member
  that copies — and the fact that it is named is a feature: an expensive operation is
  written down where it happens.

Notice what both answers have in common: neither of them is "keep passing the buffer by
value". The parser never wanted a copy of the file. Fixing the copy makes the type honest;
the reason the double free existed is that a `const Buffer&` was the right parameter all
along, and `#owning-and-borrowing` is the decision that makes it the default for the rest of
the course.

## Concepts to teach

The special member functions the compiler writes, and what memberwise copy does to an owning
pointer. Pass-by-value as a copy-constructor call; pass-by-reference and `const&` as the
borrow. Double free as undefined behaviour, and why it is worse evidence than a leak —
including what it does to the allocation report the checks read. Copy construction:
signature, why `const`, why a reference, deep copy. Operator overloading, minimally: `operator=`
as a function whose name is punctuation, and why it returns `Buffer&`. Copy assignment's
three jobs and their order; the leak from forgetting the release. Self-assignment, how it
arrives through aliasing, the self-check and copy-and-swap. A `swap` member that cannot fail.
The rule of three, and why the three are not independent. `= delete` as a design decision,
what it prevents and what it costs. The cost of a deep copy, as motivation for the next
lesson. That the counter is the evidence for all of this (`#the-allocation-counter`).

## Constraints

- The buffer type stays hand-written. No `std::vector`, no `std::unique_ptr`, no
  `std::string` standing in for it (`#handwritten-then-replaced`).
- Whatever you decide about copying, the decision must be **written in the class**. Leaving
  the compiler's version in place because "we never copy it" is the defect this lesson is
  about; a future call site will copy it.
- If copying is allowed, it is a deep copy: after a copy there are two allocations, and the
  counter says so.
- If copying is deleted, every call site borrows through a reference, and the type must
  still be usable everywhere the parser needs it.
- Assignment must be correct when the source and the target are the same object, and must
  not leak the target's old contents.
- The allocation report keeps its exact shape, and `outstanding` never goes negative.
- `no-leak-on-error-path` must still pass: the error path through `assets/truncated.png`
  stays clean.
- The parser's behaviour does not change. The chunk listing is the same as it was in
  `03-a-class-that-cleans-up`.

## Suggested progression

Before changing anything, make the defect happen. Take a function in your parser that reads
the buffer and declare its parameter by value rather than by reference, build, and run the
tool over `assets/basic.png`. Predict first, out loud or in writing: how many allocations,
how many frees, and what the outstanding figure will be. Then look at what actually happened
— which may be an abort, a corrupted-heap message, a report with impossible numbers, or
nothing at all, and the variety is itself the lesson.

Write a test that captures it, in the test target you built in `04-a-target-of-its-own`:
construct a buffer, copy it, let both go out of scope, and check the counter's allocations
and frees against what you expect. Watch it fail.

Now decide, deliberately, whether your buffer is copyable. Write down the reason before you
implement either answer.

If it is copyable, write the copy constructor first and make the test pass. Then write copy
assignment, and think through its three jobs before you write the body. Add a test that
assigns one buffer to another and checks that the counter balances afterwards — that test is
what catches the missing release. Add a test that assigns a buffer to itself and then reads
its contents; decide whether you are guarding with a self-check or with copy-and-swap.

If it is not copyable, delete both, and let the compiler show you every place that was
copying. Fix each one to borrow. Your test for this lesson then proves the type is not
copyable — `std::is_copy_constructible_v<Buffer>` from `<type_traits>` is `false` — and that
the buffer still behaves correctly when passed by reference and destroyed once. If there is
anywhere you genuinely need a duplicate, add a named member for it and test that.

Either way, put the parser's parameters back to references and re-run everything:
`dumps-basic-png` for the listing, `no-leak-on-error-path` for the error path, and `tests`
for the suite. Then break one of your new functions on purpose — a copy constructor that
copies the pointer instead of the bytes, say — and confirm the suite goes red. A test that
cannot fail proves nothing.

## Completion conditions

- `build` passes.
- `tests` passes, and the suite includes at least one test that exercises the copying
  decision: a test that copies a buffer and checks the allocation counter balances, or — if
  copying is deleted — a test that the type is not copy-constructible together with a test
  that it still works when borrowed.
- `no-leak-on-error-path` passes on `assets/truncated.png`.
- The learner has seen the suite fail with a deliberately wrong copy, and pass again with it
  corrected.
- The class states its copying decision explicitly. No owning type is left relying on the
  compiler-generated copy.
- Where copying is implemented: after a copy the counter shows two allocations and two
  frees; assignment releases the target's old contents; and assigning an object to itself
  leaves it intact.
- The learner can describe what the compiler-generated copy constructor did to their buffer,
  member by member, and why two destructors then released one allocation.
- The learner can state the rule of three and explain why the three functions are not
  independent of each other.
- A learner who chose `= delete` can name at least two things it costs them and say how they
  would produce a genuine duplicate if they needed one.

## On completion, persist

Record in the instance's `DESIGN.md` the copying decision for the buffer type — copyable
with a deep copy, or non-copyable — and the reason, because `06-moving-not-copying`,
`07-bounds-you-cannot-skip` and `12-it-was-in-the-box` all build on it. If copy assignment
was written, record which self-assignment strategy was chosen. In `STATE.md`, record the
tests added and what each one covers, and note the allocation counts observed before and
after the repair. If the double free was observed as a crash rather than as a number, record
what the program did, because that is the evidence this lesson turned on.

## Optional deeper paths

The optional lesson `what-the-compiler-writes-for-you` is offered here: the six special
member functions, when each is generated, and how declaring one suppresses another.

`= default`: asking the compiler for the version it would have written, explicitly. Why
`Buffer(const Buffer&) = default;` and writing nothing at all are not quite the same thing.

The `explicit` keyword: why a single-argument constructor that is not `explicit` lets the
compiler convert types at call sites you did not intend, and what that has to do with a
buffer constructible from a size.

The exception-safety argument for copy-and-swap, which becomes concrete in
`09-errors-without-errno`: an assignment that releases before it acquires leaves the object
holding a dangling pointer if the acquisition fails part-way.

Read the documentation for `std::vector`'s copy constructor and assignment operator, and
notice that it faces every question you just faced, including self-assignment. You are not
meant to use it yet — but it is the same problem, and the interface is about to become
readable to you.
