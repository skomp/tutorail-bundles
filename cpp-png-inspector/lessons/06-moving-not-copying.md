---
id: 06-moving-not-copying
title: Moving, not copying
design_refs: [owning-and-borrowing]
validators: [build, tests, no-leak-on-error-path, explains-the-repair]
---

## Purpose

Transfer a buffer's ownership instead of duplicating its bytes, so a function can hand one
back without copying the whole file — and so the last of the ways to free the same pointer
twice is closed.

`05-the-rule-of-three` made copying correct. This lesson is about the times you never wanted
a copy: a function that reads a file and returns what it read, a buffer handed on to
something that will outlive the scope it was built in.

## Prerequisites

`05-the-rule-of-three` is complete. The buffer type states its copying decision explicitly,
the test suite covers it, and `no-leak-on-error-path` and `dumps-basic-png` both pass. You
have a test executable you have watched fail.

## Learning objectives

- Distinguish an expression that names an object you will use again from one whose value is
  about to be destroyed, and say why the distinction lets a function steal instead of copy
- Write a move constructor and a move assignment operator for an owning type
- Say what state a moved-from object must be left in, and what happens when it is left
  owning the same pointer as the object that moved from it
- Use `std::move` correctly and explain why it is a cast rather than an action
- State the rule of five and its relationship to the rule of three
- Explain what `noexcept` on a move constructor promises and who reads that promise
- Explain why returning a newly built object never needed a move at all in C++17

## Theory

### The copy you did not want

Suppose a function that reads a file and gives you back the bytes:

```cpp
Buffer read_file(const char* path);   // what does the return cost?
```

With only the rule of three in the class, the honest answer looks alarming: the function
builds a buffer, and returning it by value copies it — allocate again, copy every byte,
release the original. For `assets/basic.png` that is 165 bytes and nobody would notice. For
the four-megabyte PNG this tool is supposed to survive, it is four megabytes of memcpy and a
second four megabytes of address space, to produce a buffer identical to one that was about
to be destroyed anyway.

The waste is obvious. The cure is not a faster copy; it is not copying. The original was
about to die. Its pointer could simply become the new object's pointer, and nothing would
need to be duplicated at all. That is a **move**: not a copy that happens to be quick, but a
transfer of ownership.

### First, the honest part: C++17 already removed one of these copies

Before writing anything, know what the language does for you, because otherwise you will
write a move constructor, measure nothing, and conclude that moves are magic.

Since C++17, returning a newly built object — `return Buffer(path);`, an expression with no
name — is **not** a copy and **not** a move. The object is constructed directly in the
caller's storage. This is guaranteed by the standard, and it works even for a type whose copy
and move are both deleted. Returning a *named* local variable — `Buffer b; ...; return b;` —
is a different case: the compiler is *permitted* to elide the copy and in practice usually
does, and where it does not, the return treats the local as expiring and picks the move
constructor if there is one, and the copy constructor if there is not.

So where does the move actually earn its keep?

- Returning a named local from a type with the copies deleted: without a move constructor
  this does not compile at all.
- Assigning from a temporary, or from something you have finished with: `buf = read_file(p);`
  calls **move assignment**, and no elision rule saves you there.
- Handing ownership out of a local into a longer-lived structure: storing a parsed buffer
  into a member, pushing it onto a list, swapping two of them.
- Any function that takes a buffer by value in order to keep it, called with something the
  caller is done with.

The allocation counter is how you tell which of these happened. An operation that copied
shows an extra allocation; one that moved does not. Do not guess from the source; make the
counter say it.

### Lvalues, rvalues, and a reference that binds to the dying

For a function to be allowed to steal from its argument, it has to know the argument will
not be used again. C++ encodes that in the expression, not the type.

An expression that names an object you can refer to again — a variable, a dereferenced
pointer, something with a name — is an **lvalue**. An expression whose value is a temporary
about to be destroyed — the result of a function returning by value, a literal, an explicit
cast to an rvalue reference — is an **rvalue**. Stealing from an lvalue would be theft.
Stealing from an rvalue is tidying up after something that is leaving anyway.

A new kind of reference binds only to rvalues, written with two ampersands:

```cpp
Buffer(Buffer&& other) noexcept;             // move constructor
Buffer& operator=(Buffer&& other) noexcept;  // move assignment
```

Note what is not there: no `const`. A move modifies its source, which is the entire point.
Overload resolution now has a choice at every call — an lvalue argument picks the
`const Buffer&` copy version, an rvalue argument picks the `Buffer&&` move version — and the
call sites do not change at all. This is why adding moves to a class is a pure optimisation
for its users.

### What a move constructor does, and the one thing it must not forget

Take the source's pointer and length; then leave the source empty.

The second half is not tidiness. If you copy the pointer out of the source and leave the
source holding it as well, you have written exactly the bug `05-the-rule-of-three` removed,
from the other direction: two objects, one allocation, two destructors. It will not crash at
the move. It crashes — or does something worse than crash — at the next scope exit, which
may be in a different function. The counter will show more frees than allocations if the
process survives long enough to print anything.

So: null the source's pointer, zero its length. Then its destructor releases nothing, which
you already made safe in `03-a-class-that-cleans-up` when you arranged for a destructor that
copes with an object that never allocated.

### What a moved-from object must still satisfy

It must still be a valid object. Its destructor will run — the compiler has no idea it was
moved from — and any member function anyone calls on it must behave. What it must *not* be
relied upon to have is its old value.

The standard's phrase for library types is "valid but unspecified": you may destroy it, you
may assign a new value to it, and you may not assume anything about what it holds. For your
own type you get to choose something stronger, and you should: choose **empty**. A null
pointer and a zero length means the destructor is a no-op, the length is honest, and a
moved-from buffer that someone reads by mistake produces nothing rather than garbage.

Be able to state this rule, because it is the part people get wrong long after they have
learned the syntax.

### Move assignment

Same three jobs as copy assignment, one of them cheaper: release what you hold, take the
source's pointer and length, and leave the source empty. Forget the first and every move
assignment leaks the target's old contents — the counter catches it, and a test should.

Self-assignment comes back here in the form `b = std::move(b)`, which is rarer than the copy
case and nastier: release your own memory, then take a pointer from an object that is you,
and you are holding a freed address. Either guard it, or structure the operation so nothing
is released until the exchange is done — swapping the two objects' contents and letting the
source destroy the old bytes is the usual way, and it is self-move-safe for free.

### `std::move` moves nothing

`std::move`, from `<utility>`, is a cast. It takes an expression and produces an rvalue
reference to it, so that overload resolution picks the move overload. It generates no code,
it does not touch the object, and nothing has been moved when it returns. The move, if any,
happens in whatever constructor or assignment operator the cast made reachable.

The name is a historical mistake that costs every learner an hour. Read `std::move(x)` as
"treat `x` as expiring", and two consequences follow immediately: after you have written it,
you must not rely on `x`'s value again; and if the function you passed it to takes a
`const Buffer&`, absolutely nothing happens — it binds and copies, silently.

There is one place to *not* write it. `return std::move(local);` makes the return value an
rvalue reference expression, which blocks the compiler from eliding the copy altogether and
forces an actual move where you could have had nothing at all. It is a pessimisation, it is
common in code written by people who have just learned about moves, and compilers warn about
it. Return the local.

### The rule of five

Destructor, copy constructor, copy assignment, move constructor, move assignment. If you
write any of them you should think about all five.

There is a trap folded into it that you have already been living with. Declaring a
destructor — which you did in `03-a-class-that-cleans-up` — **suppresses** the implicit move
constructor and move assignment operator. They are not generated. Every operation that could
have moved has been quietly copying ever since, and nothing warned you, because copying is
correct, merely expensive. This is the clearest example in the language of a declaration in
one place changing what the compiler writes in another, and it is why the rule is stated as
all five together. The optional lesson `what-the-compiler-writes-for-you` maps the whole
mechanism if you want it.

### `noexcept`, and who reads it

`noexcept` on a function declares that it will not throw. It is not a hint; if such a
function does throw, the program terminates.

Your move operations copy a pointer and a length and release memory you already own. None of
that can fail, so the promise is both free and true — mark them `noexcept`.

It matters because the standard library reads it. When `std::vector` grows, it must relocate
its elements to new storage, and it wants to do that by moving. But if a move could throw
part-way through the relocation, the vector would be left with some elements moved and some
not, and no way to put things back — so the library checks, and for a type whose move
constructor is not `noexcept` it silently **copies** instead, to keep the operation
recoverable. A missing `noexcept` therefore does not produce an error or a warning. It
produces a program that is quietly as slow as it was before you wrote the move constructor.
You will meet this directly in `12-it-was-in-the-box`, when the vector becomes real; the
promise belongs on the function now.

## Concepts to teach

Lvalue and rvalue as properties of expressions, not of types. Rvalue references (`T&&`) and
why a move parameter is not `const`. Overload resolution picking copy or move from the
argument's value category, with no change at the call site. Move construction: transfer the
pointer, empty the source. Move assignment: release, transfer, empty the source; the leak
from omitting the release; self-move. The moved-from object: valid, destructible,
assignable, its value unspecified — and why leaving it owning the same pointer double-frees
at the next scope exit. `std::move` as a cast that moves nothing; the pessimisation
`return std::move(x)`; the silent no-op when the target parameter is `const&`. Guaranteed
copy elision in C++17 for an unnamed temporary, and NRVO for a named local, so the learner
knows which of their measurements a move actually changed. The rule of five, and that
declaring a destructor suppresses the implicit moves. `noexcept` on moves: what it promises,
that violating it terminates, and why the library's choice between moving and copying
depends on it. The counter as the evidence throughout (`#the-allocation-counter`), and one
owner at a time throughout (`#owning-and-borrowing`).

## Constraints

- The buffer stays hand-written. No `std::vector`, no `std::unique_ptr`
  (`#handwritten-then-replaced`). `std::move` from `<utility>` is a cast, not a container,
  and is expected here.
- Exactly one object owns an allocation at any moment. After a move, the source owns
  nothing.
- A moved-from buffer must be safe to destroy and safe to assign to, and its length must
  report what it actually holds.
- Move construction and move assignment must be `noexcept`, and must genuinely not be able
  to throw.
- Move assignment must release the target's old contents, and must not corrupt the object
  when the source and target are the same.
- Whatever `05-the-rule-of-three` decided about copying stands. A type whose copies are
  deleted and whose moves exist is a normal and good design; a type with both is also fine.
  What is not fine is a type with a destructor and neither.
- The parser's observable behaviour does not change: `dumps-basic-png` and
  `no-leak-on-error-path` pass exactly as before, and the output contract is untouched.

## Suggested progression

Start by finding out what your program actually does today. Arrange for the file to be read
by a function that returns the buffer by value — if your constructor reads the file itself,
this may mean adding a small function that builds one and returns it — and use the allocation
counter to answer one question: how many allocations does reading `assets/basic.png` take?
Predict before you look. If the answer surprises you, read the note above on what C++17
guarantees about returning a temporary; it is doing work on your behalf.

Then construct a case where elision cannot help: assign one buffer to another from a
function call, or build a buffer in a scope and hand it out to a longer-lived object. Count
again. That is the copy this lesson removes.

Write the move constructor. Before running anything, write down what you expect the counter
to say. Then write a test that performs the transfer and asserts on the allocation count —
one allocation, not two — and run it.

Now go looking for the failure deliberately, because it is the one that matters. Remove the
line that empties the source and run the suite again. Watch what happens and where it
happens — note particularly that the move itself is fine and the damage appears later, at a
scope exit somewhere else. Put the line back and say, in your own words, why the moved-from
object must not be left owning that pointer.

Add move assignment. Test that assigning a moved-in buffer over an existing one leaves the
counter balanced; that test is what catches a missing release. Decide how you are handling
self-move-assignment and test it.

Mark both `noexcept`, and be ready to say what would happen if one of them could throw.

Then look for the two habits this lesson creates: somewhere you have written
`return std::move(x)` where returning `x` is better, and somewhere you have written
`std::move` on an argument that a function takes by `const&`, where nothing at all happens.
Find them, or confirm they are not there.

Finish by running everything: `build`, `tests`, `dumps-basic-png` for the listing, and
`no-leak-on-error-path` for the error run. The milestone this lesson closes is a buffer that
cannot leak, cannot double-free, and is cheap to return — be able to point at the code that
makes each of the three true.

## Completion conditions

- `build` passes.
- `tests` passes, and the suite includes a test that proves a buffer obtained from a
  function is allocated exactly once, and a test that a move assignment leaves the counter
  balanced.
- `no-leak-on-error-path` passes on `assets/truncated.png`, and the chunk listing is
  unchanged.
- The learner has seen the suite fail with the source-emptying line removed from the move
  constructor, and can describe where the failure appeared relative to where the bug was.
- Move construction and move assignment exist, are `noexcept`, and leave the source empty;
  move assignment releases the target's previous contents.
- `explains-the-repair`, judged by the tutor from the learner's own account, requires all of:
  - what a moved-from object must still satisfy, and why leaving it owning the same pointer
    double-frees at the next scope exit rather than at the move;
  - what `std::move` actually does, stated as a cast, and what happens when it is applied to
    an argument that is taken by `const&`;
  - the rule of five, and that declaring a destructor in `03-a-class-that-cleans-up` had
    already removed the implicit moves, so everything had been copying since;
  - what `noexcept` on a move constructor promises, and why a library that relocates objects
    changes its behaviour when the promise is missing;
  - which of their own measurements the move constructor changed, and which one C++17's
    guaranteed elision had already taken care of.
- The learner can point at the three properties of the buffer type that close this chapter —
  no leak, no double free, cheap to hand over — and name the member function responsible for
  each.

## On completion, persist

Record in the instance's `STATE.md` that the buffer type now has the full set of special
member functions it needs, listing which of the five are written, which are `= delete`d and
which are `= default`ed, and note that the moves are `noexcept`. Record the allocation counts
measured before and after, for reading `assets/basic.png` and for whichever transfer case was
used, since those numbers are the evidence for this milestone. In `DESIGN.md`, record the
signature the file-reading function settled on — whether it returns a buffer by value — as
later lessons build call sites on it. Note the moved-from state chosen (empty, with a null
pointer and zero length) as a decision, and record the `explains-the-repair` judgement with a
one-line summary of what the learner said.

## Optional deeper paths

Value categories in full: `prvalue`, `xvalue` and `glvalue`, and why C++11's two-way split
became a three-way one. Worth reading once, and not worth memorising.

`std::forward` and forwarding references (`T&&` in a template, which is not an rvalue
reference at all). This is the next thing people meet after `std::move` and the most common
source of confused code; it needs templates, which arrive in
`08-templates-eat-the-macros`.

Compile with elision disabled — `-fno-elide-constructors` on GCC and Clang — and re-run your
measurements. The numbers change, and seeing which ones change is the fastest way to
understand what the compiler had been doing for you.

Moved-from objects in the standard library: look up what `std::string` and `std::vector`
guarantee about a moved-from value, and notice that "valid but unspecified" is weaker than
the guarantee you chose for your own type.
