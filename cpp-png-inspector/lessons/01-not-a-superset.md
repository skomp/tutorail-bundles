---
id: 01-not-a-superset
title: C++ is not a superset
design_refs: [whole-file-in-memory]
validators: [configure, build, dumps-basic-png, explains-the-repair]
---

## Purpose

Compile the C program you just wrote as C++17, find out what the C++ compiler refuses, and
read each refusal as information rather than pedantry.

This is the hinge of the course. Almost everyone arrives believing C++ is C with extra
features bolted on, and almost everyone's first C++ program is a C program that happened to
compile. The fastest cure is the compiler: change one line of `CMakeLists.txt`, rebuild, and
read the errors. Each one marks a place where C's rule was found to be too loose to keep, and
knowing *which* rule was tightened is worth more than the fix.

## Prerequisites

`00-write-the-c-walker` is complete: `pngdump` builds from `CMakeLists.txt`, lists the chunks
of `assets/basic.png` correctly, and exits 0. You still allocate with `malloc` and release with
`free`, and the allocation counts are maintained by hand.

## Learning objectives

- Switch a CMake project from C to C++17, pinning the standard rather than hoping for it
- Predict, then read, the diagnostics a C++ compiler produces for valid C
- Say what an explicit cast asserts, and recognise when adding one is a lie that moves a
  compile error to run time
- Explain why a string literal is not writable and what it means that `const` is part of a type
- Use a namespace, a reference, `auto` and `nullptr` where each one actually earns its place,
  and state when a pointer is still the right choice
- Get the same program, in the same shape, back to passing the basic listing

## Theory

**C++ was designed to accept most C, and deliberately does not accept all of it.** The
divergences are not arbitrary. In each case C allowed something that could not be checked, and
C++ — which leans much harder on the type system, because templates, overloading and
constructors all resolve through it — tightened the rule. So a diagnostic here is not the
compiler being difficult. It is naming a thing your C program was asserting silently, and
asking you to assert it out loud or stop asserting it.

Before you rebuild, predict. Look at your own source and mark the lines you think a C++
compiler will reject. Then build, and compare your list with the compiler's. The gap between
the two lists is the lesson.

**The implicit `void *` conversion.** In C, `void *` converts to any object pointer type
implicitly, which is why `unsigned char *buf = malloc(n);` is not only legal but the
recommended modern C style — casting it is discouraged, because a cast there once hid a
missing `<stdlib.h>`, where an undeclared `malloc` was assumed to return `int`. In C++ that
implicit conversion does not exist, and that line is an error.

The repair is a cast, and the interesting part is what the cast claims. Writing
`static_cast<unsigned char *>(malloc(n))` asserts three things: that the bytes at that address
may be treated as `unsigned char`, that the address is suitably aligned for that type, and
that the region is big enough for what you will do with it. For `malloc` all three are true —
`malloc` returns memory aligned for any fundamental type, and you asked for the size. So the
cast is honest here, and adding it is the right repair.

The trap is the habit it can start. A cast makes a diagnostic go away whether or not the
assertion behind it is true, and the diagnostics that matter most are the ones where it is
false. Casting a `const char *` to `char *` compiles and then writes to read-only memory.
Casting a `struct Foo *` to a `struct Bar *` compiles and then reads garbage. If you find
yourself adding casts until the build goes quiet, you have stopped repairing and started
silencing. A useful discipline for the rest of the course: before you write a cast, say out
loud what it asserts, and only then decide whether it is true. C++ gives you named casts —
`static_cast` for conversions the type system can justify, `const_cast` for removing `const`,
`reinterpret_cast` for reinterpreting bytes — precisely so a reader can tell which claim you
are making. The C-style `(T)x` cast makes them indistinguishable.

**String literals are `const`.** In C, `"IHDR"` has type `char[5]` and `char *p = "IHDR";`
compiles, even though writing through `p` is undefined behaviour — the array usually lives in
a read-only page, so the program dies at run time rather than at compile time. C++ gives the
literal type `const char[5]`, and the conversion to `char *` was removed outright in C++11. The
error you get is the compiler telling you, at compile time, about a bug C could only tell you
about at run time, on a machine that happened to protect the page.

That works because in C++ `const` is part of the type, not an annotation on a declaration:
`char *` and `const char *` are different types, and a function taking `char *` cannot be
handed a literal. The repair is not to cast it away; it is to make the parameter `const char *`,
which is what you meant — the function does not modify it. This will happen several times in
your file, and each time the fix is the same and improves the declaration. The lesson
`07-bounds-you-cannot-skip` comes back to `const` properly; for now it is enough to know that
it belongs to the type, and that adding it usually makes a signature more accurate rather than
less convenient.

**Enums are their own type.** In C an enumeration is an integer type with named constants, and
any integer converts into it. In C++ an unscoped enum converts *to* an integer but an integer
does not implicitly convert *back*: assigning `3` to a variable of enum type needs a cast, and
that refusal exists because the value being assigned may not be any of the named ones. C++11
added `enum class`, whose enumerators are scoped to the type's name and do not convert to
integers at all; it is the better tool for a fixed set of states and worth knowing exists even
if your program has no use for one yet.

**The other refusals you may meet.** C++ and C have drifted in more than three places, and
which of them you hit depends on how you wrote the walker:

- An identifier that is a C++ keyword: `new`, `delete`, `class`, `this`, `template`,
  `operator`, `namespace`, `try`, `private`, `public`, `export`. A local variable called `new`
  is fine C and unspellable C++.
- C99 designated initialisers — `struct chunk c = {.offset = 8};` — are not C++17. They arrived
  in C++20, with restrictions. Under this course's standard they are an error, which surprises
  people who think of them as a small convenience.
- `void f()` in C declares a function taking an unspecified number of arguments; in C++ it
  declares one taking none. C's `void f(void)` means the same in both, which is why old headers
  are written that way.
- Two file-scope definitions of the same variable — a *tentative definition* in C, where
  `int x;` twice in one translation unit is fine — violate the one-definition rule in C++.
- `'a'` has type `int` in C and `char` in C++, so `sizeof('a')` differs between them.
- `restrict` is a C keyword and is not C++ at all.
- The C standard headers still work, so `<stdio.h>` and `<stdlib.h>` keep compiling. The C++
  spellings `<cstdio>` and `<cstdlib>` declare the same names inside namespace `std`, which is
  the tidier choice in C++ code and the reason you will see `std::printf`.

If your file happens to compile first time, that is not a failure of the lesson and it does not
mean C++ is a superset. It means your C was written in the intersection. Go back to your
prediction list and find, by inspection, the line C++ would have rejected had you written it
the other way — and if you already cast `malloc`'s result out of old habit, you have your
answer.

**What C++ offers in exchange, at the size you need today.** Four things, no more. Everything
else in this course arrives because a defect asked for it.

*Namespaces* are named scopes for declarations, so two libraries can each have a `read` without
colliding, and `::` selects between them. Put your own code in one — the course's later material
uses `png::`, so `namespace png { ... }` around your parsing helpers is a good choice now.
Resist `using namespace std;` as a reflex: at the top of a `.cpp` it is merely untidy, but in a
header it inflicts every name in `std` on everything that includes it, and the collisions
surface as errors in files that never asked for it.

*References.* `T &r = x;` makes `r` another name for `x`. A reference must be initialised, can
never be re-seated to refer to something else, and — barring undefined behaviour that got you
there — is never null. Passing a large object as `const T &` costs a pointer and copies nothing,
which is why C++ code passes so few pointers around. The decision rule you can use for the rest
of the course: use a reference when the thing certainly exists and will not be swapped for
another; use a pointer when absence is meaningful (there may be nothing), when it must be
re-seated, or when you are doing arithmetic across an array — which your buffer walking still
is.

*`auto`* asks the compiler to deduce a variable's type from its initialiser. It earns its place
where the type is long, obvious from the right-hand side, or genuinely unspellable; it costs
you where a reader needed to see the type to follow the code. Two things to know before you use
it: plain `auto` copies, and it drops top-level `const` and any reference, so binding to
something you did not want to copy is written `const auto &`. Deducing `auto` from an integer
expression is also how a signed/unsigned surprise gets in, so name the type where a width
matters — which, in a file parser, is most of the time.

*`nullptr`.* In C, `NULL` is a macro that expands to an integer constant, and C++ inherits that
problem: a `NULL` argument is indistinguishable from `0`, so it can select an `int` overload
rather than the pointer one. `nullptr` has its own type, converts to any pointer type, and
converts to no integer type at all. Use it everywhere you used `NULL`.

**The CMake half, which is where the quiet mistake lives.** Three changes and one consequence.
The `project` command's `LANGUAGES` list becomes `CXX` — CMake's name for C++ — and the source
file has to be named so the compiler treats it as C++, which means renaming `.c` to `.cpp` and
updating `add_executable`. Then set `CMAKE_CXX_STANDARD` to `17`.

That last setting alone is a request, not a requirement. On its own, if the compiler cannot
provide C++17, CMake will quietly fall back to whatever it does support and carry on. The build
then succeeds on your machine — where the compiler's default may already be C++17 or later —
and fails on someone else's, or worse, succeeds everywhere until the first lesson that uses a
C++17-only construct, at which point the error points at that construct and says nothing about
the standard. Setting `CMAKE_CXX_STANDARD_REQUIRED` to `ON` turns the request into a
requirement, so the failure happens at configure time with a message that names the real
problem. Set both, together, now. `CMAKE_CXX_EXTENSIONS OFF` is a reasonable third line: it
asks for `-std=c++17` rather than `-std=gnu++17`, so a compiler extension cannot creep into
code you believe is portable.

The consequence is the build directory. `build/CMakeCache.txt` was written when the project was
a C project and remembers it. Re-run the configure step; if CMake objects to the change, this is
the moment the out-of-source rule pays for itself — delete `build/` entirely and configure
again, losing nothing, because everything in it was generated.

## Concepts to teach

C++ as a near-superset, and why each divergence exists. The implicit `void *` conversion and
what an explicit cast asserts about type, alignment and size. C++'s named casts (`static_cast`,
`const_cast`, `reinterpret_cast`) and why the C-style cast hides which claim is being made.
String literals as `const char[]`, `const` as part of a type, and repairing by adding `const`
to a parameter rather than casting it away. Unscoped enums versus `enum class`, and the missing
int-to-enum conversion. Keyword collisions, designated initialisers as C-only in C++17,
`void f()` versus `void f(void)`, tentative definitions and the one-definition rule, the type of
a character literal. `<stdio.h>` versus `<cstdio>` and namespace `std`. Namespaces, `::`, and
why `using namespace std;` in a header is a defect. References: initialisation, no re-seating,
never null, `const T &` parameters, and when a pointer is still correct. `auto`: deduction,
copying, dropping `const` and references, `const auto &`. `nullptr` versus `NULL`.
`project(... LANGUAGES CXX)`, `CMAKE_CXX_STANDARD`, `CMAKE_CXX_STANDARD_REQUIRED`,
`CMAKE_CXX_EXTENSIONS`, and the stale cache in a build directory that is safe to delete.

## Constraints

- The program keeps doing exactly what it did. This lesson changes the language it is compiled
  in, not the design. Same file layout, same output, same behaviour.
- Keep `malloc` and `free`. Do not switch to `new`/`delete`, and do not reach for `std::vector`,
  `std::string` or any standard container. `02-where-the-leaks-are` counts those `malloc` calls
  and `03-a-class-that-cleans-up` is what replaces them; taking the shortcut now removes the
  reason the next four lessons exist (see `#whole-file-in-memory`).
- Do not add classes, constructors or destructors yet.
- Do not throw exceptions, and do not add a `try` block.
- Do not fix the leak. It is not measured yet and you would not be able to say what you fixed.
- The whole file is still read into one heap buffer.
- Repair every diagnostic honestly: no cast whose assertion you cannot state, and no
  `const_cast` to silence the string-literal errors.
- The executable is still named `pngdump` and the chunk lines still match the contract exactly.
- No third-party libraries.

## Suggested progression

Before touching anything, read your own source and write down which lines you expect a C++
compiler to reject, and why. Keep the list; it is half of what this lesson is checking.

Change `CMakeLists.txt` to C++17 — language, standard, and the standard-required flag — rename
the source file, and update `add_executable`. Configure and build, and let it fail. Read the
first error only, fix that one, and rebuild; a C++ compiler's later errors are often cascades
from the first, and fixing them in order is faster than reading all of them. Keep going until it
links.

As each diagnostic appears, name the rule before you write the fix. For the `malloc` line, say
what the cast asserts and why it is true. For a string-literal error, decide between adding
`const` to a parameter and casting the literal, and be able to argue why casting would be the
wrong repair. Compare the finished list against the prediction you wrote at the start.

Now run the basic listing check. The program should behave exactly as it did in the previous
lesson; if the output changed, something in the repair changed meaning rather than syntax, and
that is worth finding.

With the build green, adopt the four C++ facilities in small, deliberate edits, one at a time,
rebuilding after each: put your parsing helpers in a namespace; replace `NULL` with `nullptr`;
change one function that takes a pointer to something that certainly exists so it takes a
reference instead, and notice what disappears from the call site and from the body; use `auto`
in one place where it makes the code clearer and leave it out of one place where it would not.
Then say, for the reference you introduced, what a reader now knows that the pointer version did
not tell them.

Finally, try one experiment: set `CMAKE_CXX_STANDARD` to `11`, reconfigure, and build. What
happens depends on your code, and either result is informative — it tells you whether anything
you wrote is actually C++17. Put it back to `17` when you are done.

## Completion conditions

- The `configure` validator passes with the project declared as `CXX`, `CMAKE_CXX_STANDARD` set
  to `17`, and `CMAKE_CXX_STANDARD_REQUIRED` `ON`.
- The `build` validator passes: the same program, compiled as C++17, with no remaining
  diagnostics that were suppressed rather than repaired.
- The `dumps-basic-png` validator passes, unchanged from `00-write-the-c-walker`.
- `explains-the-repair`: the learner names at least three distinct things C++ refused in *their
  own* source, and for each one says what rule was tightened and what the refusal was
  protecting against. For the `void *` conversion specifically, they state what their cast
  asserts and what it would have hidden had the assertion been false.
- The learner can say what `CMAKE_CXX_STANDARD_REQUIRED ON` prevents, and why the failure it
  prevents is one that would otherwise appear far from its cause.
- The learner can state the difference between a reference and a pointer in terms of what each
  one can express, and name a place in their own program where a pointer is still correct.
- The learner can say why `nullptr` exists when `NULL` already did.
- `malloc` and `free` are still what allocates and releases the buffer.

## On completion, persist

In the instance's `STATE.md`: the project now builds as C++17; the source file's new name; the
list of diagnostics the learner actually hit and the repair made to each; which of the four
facilities they adopted and where. Record any C construct they had to change that is *not* in
this lesson's list, because it is worth the next author knowing about.

In the instance's `DESIGN.md`: the namespace name chosen for the project's own code; the
language standard pinned at C++17 with the standard-required flag; and the deliberate decision
to keep `malloc`/`free` for now, noting that `03-a-class-that-cleans-up` replaces them, so a
later session does not read it as an oversight.

## Optional deeper paths

Read the same erroneous line's diagnostic from two compilers — GCC and Clang, if both are
installed — and see how differently the same rule is reported. Turn on `-Wold-style-cast` and
watch it find every C cast left in the file. Look up what happens to function names in C++:
compile a function, run `nm` on the object file, and see the mangling that makes overloading
possible — then find out what `extern "C"` turns off and why every C header you have ever read
is wrapped in it. Compare `enum` and `enum class` for a small state type and see which
conversions each one permits. Read what `static_cast`, `reinterpret_cast` and `const_cast` are
each allowed to do, and work out which of them a C-style cast would have selected in each place
your file uses one.
