---
id: what-the-compiler-writes-for-you
title: What the compiler writes for you
design_refs: [the-allocation-counter]
validators: [build, tests]
optional: true
---

## Purpose

Find out which of the six member functions the compiler writes on your behalf, and what
makes it quietly stop writing them.

You have just written a copy constructor and a copy assignment operator by hand. Before
that, the compiler was writing both, plus four more, without being asked — and it stopped
writing two of them the moment you declared a destructor, silently, with no warning and no
error. This is a short detour that makes the rules explicit, so the next time a class
behaves in a way you did not write, you know where to look.

## Prerequisites

This is an optional lesson, offered after `05-the-rule-of-three`. It needs four things,
all of which are true by then: a class of your own that owns a heap allocation and releases
it in a destructor (`03-a-class-that-cleans-up`); a copy constructor and copy assignment
operator you wrote yourself (`05-the-rule-of-three`); a test target CMake builds and CTest
runs (`04-a-target-of-its-own`), because the exercise is a new test file in it; and the
allocation counter from `02-where-the-leaks-are`, which is the only instrument that settles
one of the questions below.

It does **not** require `06-moving-not-copying`. Move operations are named here and
explained only as far as this lesson needs: a move transfers what an object owns instead of
duplicating it, leaving the source safe to destroy. Taken after lesson 06 instead, the move
half reads as a checklist rather than a preview. Nothing here is a prerequisite for anything
on the main path, and the course is completable without it.

## Learning objectives

- Name all six special member functions and say what each one does
- State, for a given class, which of the six exist, which are deleted, and which the
  compiler declined to write
- Explain why declaring a destructor removes the implicit move operations, and what the
  class silently does instead
- Use `= default` and `= delete` deliberately, and say what each one means to overload
  resolution
- State the Rule of Zero and say which of your types could obey it
- Explain why `std::is_move_constructible` is not evidence that a move constructor exists,
  and name a check that is

## Theory

### The six

C++ will write six member functions for a class that does not write them itself: a
**default constructor**, a **destructor**, a **copy constructor**, a **copy assignment
operator**, a **move constructor** and a **move assignment operator**. They are called the
*special member functions* because the compiler is allowed to invent them, and because the
rules for when it does are not the rules for anything else.

Each has a default meaning. The default constructor default-initialises each base and
member. The destructor destroys each member in reverse order of declaration and does nothing
else, which is why a raw pointer member leaks. The copy operations copy each member, which
for a raw pointer copies the pointer and not what it points at — the double-free you met in
`05-the-rule-of-three`. The move operations move each member, which for a raw pointer is
*also* just a copy of the pointer: the compiler does not know that yours owns anything.

### Declaring one changes which others appear

This is the part worth the detour. The six are not independent; declaring one suppresses
others, and "declaring" includes writing `= default`.

- The **default constructor** is written for you only if you declare **no constructor at
  all**. Give your buffer a constructor taking a size and the default constructor is gone.
- The **destructor** is always written for you if you do not write one. It is never virtual
  unless you say so.
- The **copy constructor** and **copy assignment operator** are written for you unless you
  declare a move operation — in which case they are not merely absent, they are defined as
  **deleted**.
- The **move constructor** and **move assignment operator** are written for you only if you
  have declared **none** of: a copy constructor, a copy assignment operator, the other move
  operation, or **a destructor**.

Read that last one twice, because it is the fact this lesson exists for. **Declaring a
destructor suppresses both implicit move operations.** There is no error, no warning, and
no change in behaviour you can see from a call site. The class simply goes back to copying.

Now apply it to the type you have. Your buffer declares a destructor — it had to, that was
`03-a-class-that-cleans-up` — and it declares a copy constructor and a copy assignment
operator, which was `05-the-rule-of-three`. It therefore has **no move constructor and no
move assignment operator**, and it has not had either since lesson 03 wrote the destructor.
Every time it is returned by value or passed by value, the whole allocation is duplicated,
and nothing told you. That is exactly what `06-moving-not-copying` is about, and this is the
mechanism underneath it.

There is a second consequence worth seeing: an object with no move constructor is still
movable *in form*. Two words are used here and explained only as far as the paragraph
needs; `06-moving-not-copying` gives both properly. An **rvalue** is an expression naming a
temporary about to be destroyed, and **overload resolution** is the compiler's choice,
among the functions sharing a name, of the one a particular call reaches.
`std::move` produces an rvalue, overload resolution looks for a constructor that accepts
one, finds only the copy constructor taking `const T&` — and a `const` lvalue reference
binds happily to an rvalue. So the call compiles, silently performs a copy, and looks
exactly like a move at the call site. This is the single most common way a C++ program is
slower than its author believes.

### `= default` and `= delete`

`= default` asks the compiler for the implicit definition explicitly. It is how you get a
move constructor back after a destructor suppressed it, and how you write a destructor that
does nothing while keeping it visible — or virtual, which a base class will need later. Note
what follows from the rules above: writing `virtual ~Base() = default;` is still *declaring*
a destructor, so it suppresses that class's implicit moves as thoroughly as a hand-written
one would.

`= delete` removes a function, but does not make it invisible: a deleted function still
participates in overload resolution, so a call that selects it is a compile error rather than
a fallback to something else. That is the difference between deleting a copy constructor and
simply not having one. Both spellings also say something to a reader that a missing function
cannot: *this was decided*.

### The Rule of Zero

The rules above are all about classes that manage a resource, and the conclusion runs
backwards: a class that manages **no** resource should declare **none** of the six, and then
all six exist, all are correct, and there is nothing to maintain. That is the Rule of Zero,
and it is the target. The Rule of Three and the Rule of Five are the fallback for the one
class in a program that owns something raw — and a program with several such classes has
usually written the same buffer three times.

### Why the type traits are not quite the answer

`<type_traits>` offers `std::is_default_constructible_v`, `std::is_copy_constructible_v`,
`std::is_copy_assignable_v`, `std::is_move_constructible_v`, `std::is_move_assignable_v` and
`std::is_destructible_v`. `static_assert(condition, message)` fails the build, with the
message, when a condition the compiler can evaluate for itself comes out false;
`08-templates-eat-the-macros` puts it to a different use later. A `static_assert` over these
traits is therefore a test that runs at compile time and costs nothing, and for the deleted
cases it is exactly right: a type whose copy constructor is deleted reports
`is_copy_constructible_v` as `false`, and a prediction saying otherwise will not compile.

But `std::is_move_constructible_v<T>` asks whether a `T` can be *constructed from an rvalue
`T`* — not whether a move constructor exists. For a copy-only type the copy constructor takes
`const T&`, that binds to an rvalue, and the trait answers `true`. Your buffer, which has had
no move constructor since `03-a-class-that-cleans-up`, reports `true` right now, and a
prediction "confirmed" by that assertion has confirmed nothing.
`std::is_nothrow_move_constructible_v` gets closer, because a move that allocates nothing is
usually `noexcept` while a copy that allocates is not — but that is a convention, not a rule.
The honest instrument is the one you already built (`#the-allocation-counter`): construct
from an rvalue with the allocation counter watching. A move does not allocate. A copy does.

## Concepts to teach

The six special member functions and the default meaning of each. The suppression rules —
in particular that any user-declared destructor, `= default` and virtual ones included,
removes both implicit move operations, and that a user-declared move operation defines the
copies as deleted. That `= default` restores an implicit definition and `= delete` removes a
function while leaving it in overload resolution. That a `const T&` parameter binds to an
rvalue, so a missing move constructor silently becomes a copy. The Rule of Zero, and its
relationship to the Rules of Three and Five. The traits in `<type_traits>`, and the specific
limit of `std::is_move_constructible`.

## Constraints

- **Predict, then observe. Do not repair.** If this lesson is taken at its offer point,
  restoring your buffer's move operations is the subject of `06-moving-not-copying`; doing
  it here removes that lesson's motivation. Write down what is missing and leave it missing.
- The exercise goes in a **new** test file in the existing test target. Do not edit the
  tests written in earlier lessons, and do not change the inspector's behaviour.
- The prediction is written down **before** the assertions are compiled. A prediction made
  after reading the compiler's answer is not a prediction.
- The tree is green when this detour ends: `build` and `tests` pass, and the checks that
  passed before it still pass.

## Suggested progression

Take three class shapes and write down, for each, which of the six the compiler provides —
present and usable, present but deleted, or never declared. Suggested shapes, all of which
you already have or can write in three lines:

1. **A plain value** — a struct of scalars with no user-declared members, of the kind the
   parser uses to describe one chunk.
2. **Your owning buffer as it stands** — a constructor taking a size, a destructor, a copy
   constructor and a copy assignment operator, all user-declared.
3. **A class whose only user-declared member is `~X() = default;`**, holding one ordinary
   member. It looks like it declares nothing at all.

Then write the assertions. Use the compile-time traits where they genuinely answer the
question — default construction, copy construction, copy assignment, destruction, and every
deleted case — and let a wrong prediction fail the build. Add the runtime probe for the move
question: construct from an rvalue with the allocation counter watching, and assert on
whether an allocation occurred. Then compare shape 3 with shape 1: they differ by one line
that appears to change nothing, and you should be able to say what it changed. Finally, ask
which types in your own project could obey the Rule of Zero if the buffer were not written by
hand.

## Completion conditions

- `build` and `tests` pass with the new test file in place, and every check the project
  passed before this lesson still passes.
- For each of the three shapes a written prediction exists for all six special members, and
  an assertion confirms it. A wrong prediction was corrected *after* the compiler disagreed,
  and the learner can say why it was wrong.
- The learner can state the destructor rule without prompting: declaring a destructor —
  including `= default` and including a virtual one — suppresses both implicit move
  operations, and the class silently copies instead.
- The learner can explain why `std::is_move_constructible_v` is `true` for their own buffer
  despite it having no move constructor, and can name the check that settles it instead.
- The learner can say what `= delete` does that omitting a function does not.

## On completion, persist

In the instance's `STATE.md`, record that this optional lesson was taken and what the
learner predicted wrongly, if anything — a wrong prediction about the move operations is
worth carrying into `06-moving-not-copying`, which starts from exactly this gap. Record any
decision about which project types should declare none of the six in `DESIGN.md`.

## Optional deeper paths

Work out what happens when a *member* cannot be copied: a class holding a member whose copy
constructor is deleted has its own copy operations defined as deleted too, without declaring
anything. Read why defaulting a special member inside the class differs from defaulting it
outside — the out-of-line version counts as user-provided, which changes triviality — and
what `std::is_trivially_copyable` licenses a program to do. And read why the implicit copy
operations are formally deprecated when a destructor is user-declared, yet still generated.
