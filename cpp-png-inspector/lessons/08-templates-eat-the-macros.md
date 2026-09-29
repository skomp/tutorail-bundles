---
id: 08-templates-eat-the-macros
title: Templates eat the macros
design_refs: [byte-order-in-one-place]
validators: [build, tests, dumps-basic-png]
---

## Purpose

You have three or four byte-reading functions that differ only in a type and a count, and one
definition should replace the lot of them.

Look at `read_u32`, `read_u16` and `read_u8` — or the macros you wrote instead of them. Line
them up and the bodies are the same shape: take a position, take that many bytes, put them
together most significant first, hand back an integer. Only the type and the number of bytes
change, and the number of bytes is a property of the type. In C the available answers were
three near-identical functions or a macro that is not a function at all. C++ has a third
answer, and the reason it matters is not that it saves thirty lines: it is that it leaves
exactly one place where a PNG's byte order is dealt with.

## Prerequisites

Lesson `07-bounds-you-cannot-skip` is complete: the non-owning view exists, parsing functions
take it, and every read is either proved in range or goes through the checked accessor. The
library, binary and test targets from `04-a-target-of-its-own` build, and `ctest` runs the
tests. Headers and include directories work — this lesson puts something new in a header and
the placement is the point.

## Learning objectives

- Write a function template and explain what the compiler does with it at each call
- Say when a template argument is deduced from the call and when it has to be written out,
  and why the return type never deduces
- Use `sizeof(T)` to drive the body, and reject at compile time a `T` the function cannot
  honour
- Explain why a template's definition must be visible wherever it is instantiated, and
  recognise the link error you get when it is not
- Convert file-order bytes to host-order integers in one place, without `reinterpret_cast`
  and without depending on the host's endianness

## Theory

### What is wrong with the family you have

Three functions that differ by a type are three places to fix a bug, and the bug they attract
is the byte-order one: it is entirely possible to get `read_u32` right and `read_u16` subtly
wrong, and nothing points at the discrepancy. If you wrote macros instead, the defects are
the familiar ones — the arguments are evaluated wherever they appear in the expansion, so a
macro called with `p[i++]` does something nobody intended; there is no type checking, because
there is no type; the errors name the expansion, not your call; and a macro obeys no scope
and no namespace.

Neither form is *wrong* in C, which is the point worth holding on to: C offers you a
duplicated function or a textual substitution, and you pick the less bad. C++ offers a third
thing that is a real function, type-checked, scoped, as fast as the hand-written one, and
written once.

### A function template is a pattern, not a function

```cpp
template <typename T>
T read(View bytes, std::size_t offset);
```

`read` is not a function. It is a recipe from which the compiler *makes* functions. When your
code calls `read<std::uint32_t>(...)`, the compiler substitutes `std::uint32_t` for `T`
throughout the body and compiles the result as an ordinary function — this is called
*instantiation*. Call it with `std::uint16_t` somewhere else and you get a second function.
Call it twice with the same type and you get one. Nothing happens at run time; there is no
dispatch, no indirection and no table. The generated code is what you would have written by
hand, which is why this replaces the macro without costing anything.

Two consequences follow immediately, and both surprise C programmers. The body is only
checked properly when it is instantiated, so a template nobody calls can contain nonsense and
still compile. And a mistake inside the body is reported at the instantiation, with the chain
of substitutions attached, which is what makes template errors long.

### Deduction, and why the type has to be spelled here

The compiler will work out `T` for you when it can see it in the *arguments*:

```cpp
template <typename T> void swap_in_place(T& value);   // swap_in_place(x) deduces T from x
```

That is template argument deduction, and it is why you rarely write `<...>` when calling a
standard-library algorithm. The rule is narrow and worth stating exactly: deduction works
from the types of the function arguments, and from nothing else. A `T` that appears only in
the return type cannot be deduced, because the compiler resolves the call before it knows
what the caller intends to do with the result. `read` returns `T` and takes a view and an
offset, so `T` appears nowhere in its parameters and every call spells it out:
`read<std::uint32_t>(bytes, off)`.

That explicitness is a feature here rather than a nuisance. The call says what width is being
read at the point where it matters, and a chunk length is a 32-bit field in the file whether
or not the variable you assign it to is `int`.

### `sizeof(T)` is what makes one body enough

Inside the template, `sizeof(T)` is a compile-time constant — 4 when `T` is `std::uint32_t`,
2 for `std::uint16_t`, 1 for `std::uint8_t`. So the loop that consumes bytes and the bounds
check that guards it are both written in terms of `sizeof(T)` and neither mentions a literal
4. One body then serves the whole family, and adding a fourth width costs nothing.

It also lets you say what the template refuses. `static_assert` takes a compile-time condition
and a message and fails the build when the condition is false:

```cpp
static_assert(sizeof(T) <= 4, "read<T>: PNG has no field wider than four bytes");
```

That is an error at the mistake, in your words, instead of a mystery a hundred lines deeper.
One or two of these is the right amount for this program; the machinery for expressing
elaborate constraints on `T` is outside this course.

### Where the definition has to live, and the error when it does not

Here is the question to answer by experiment rather than by being told. A C programmer's
habit is a declaration in the header and a definition in the `.cpp`, so that every caller
sees the signature and exactly one translation unit holds the body. Put your template there
and see what the build says. It will compile — every file compiles cleanly — and then
something else will go wrong, and the message will come from a different program than the one
you have been reading errors from all course.

The reason is in the previous sections. The compiler cannot generate `read<std::uint32_t>`
without the body; it meets the call in `parser.cpp`, has only a declaration, and assumes the
function exists somewhere else, exactly as it would for an ordinary function. Nothing
instantiates it in the `.cpp` that holds the definition, because nothing there calls it. So
no such function is ever generated, and the *linker* is the first tool in the chain that
notices. An undefined symbol with a mangled name containing the type argument is the
signature of this mistake, and recognising it on sight is worth as much as anything else in
this lesson.

Hence the rule: **a template's definition goes where every user of it can see it**, which in
practice means a header. That looks like it violates the one-definition rule, since every
translation unit including the header now has the definition — and templates, like `inline`
functions, are exempt: identical definitions may appear in many translation units and the
linker keeps one. (There is a second answer, explicit instantiation, which pins the generated
functions to one translation unit. It exists, it is occasionally right, and it is not the
answer here.)

The tutor may offer `reading-a-template-error` around this point. It is optional and this
lesson finishes without it.

### Byte order, in exactly one place

Every multi-byte integer in a PNG is big-endian: most significant byte first, no exceptions
anywhere in the format (`PNG-FORMAT.md` says so, and it is worth re-reading that paragraph).
Your machine is almost certainly little-endian. So bytes `00 00 00 0D` in the file are the
number 13, and a program that copies those four bytes into a `std::uint32_t` and calls it a
length reads 218103808 instead — then jumps that far forward and falls off the file. The very
first length field in every PNG is enough to expose it, which is the one mercy: this bug
cannot hide.

Two things follow. First, do the conversion arithmetically — take each byte in file order and
combine it into the result, most significant first, using shifts and a bitwise or. Written
that way the code is correct on a big-endian host too, without an `#ifdef`, because it never
depends on how the host arranges bytes in memory. Copying the bytes wholesale and hoping, or
casting the pointer with `reinterpret_cast<const std::uint32_t*>` and dereferencing it, is
wrong three times over: it is endian-dependent, it may be unaligned, and it breaks the rules
about which pointer types may alias the same storage. The shifting loop has none of those
problems and optimises to the same instruction.

Second, and this is the design decision the lesson exists to enforce: the swap happens
**inside** `read<T>`, and nowhere else. A learner who writes the template and then reverses
bytes at the call sites has written a generic function and learned nothing — the byte order
is still spread across the parser, which is exactly the property the macro family had. See
`#byte-order-in-one-place`. After this lesson, the answer to "where does this program deal
with endianness?" is one function, and any call site that mentions byte order is a defect.

## Concepts to teach

Why a macro is not a function: argument re-evaluation, no type checking, no scope, errors
that name the expansion. Function templates; `template <typename T>`; instantiation as
compile-time code generation, one function per distinct type used, and no run-time cost.
Template argument deduction from the parameters only, and why a `T` in the return type must
be written explicitly at the call. `sizeof(T)` as a compile-time constant driving both the
body and its bounds check. `static_assert` as an error reported at the mistake. Why a
template's definition must be visible at the point of instantiation; the undefined-symbol
link error that results when it is not, and why it arrives from the linker rather than the
compiler; the one-definition rule and the exemption templates and `inline` functions have;
explicit instantiation mentioned and set aside. Big-endian file order versus host order,
conversion by shifting rather than by `reinterpret_cast`, and the rule that the conversion
lives in one function (`#byte-order-in-one-place`).

## Constraints

- `read_u32`, `read_u16`, `read_u8` and any macro that did their job are deleted, not left
  beside the template as wrappers.
- There is exactly one definition of `read`, it is a template, and it lives in a header that
  both the library and the tests include.
- The number of bytes read comes from `sizeof(T)`. No literal 4 or 2 in the body.
- The big-endian to host conversion happens inside `read<T>` only. No call site reverses,
  shifts or otherwise adjusts byte order after the call.
- No `reinterpret_cast` of the buffer to an integer pointer, and no `#ifdef` on the host's
  endianness.
- The read stays bounds-checked: `read<T>` must not read past the end of the view it is given,
  and the check is in terms of `sizeof(T)`.
- `assets/basic.png` and `assets/text.png` must still list exactly as before, and the
  allocation counter must still balance.

## Suggested progression

Put the three functions side by side first and mark what differs: it is a type and a count,
and the count is `sizeof` the type. Predict, before writing anything, what the file-order
bytes `00 00 00 0D` become under each of the two ways of combining them, and what your parser
would then do with the result.

Write the template with the signature you want, and place the declaration and definition the
way you would have placed an ordinary function's. Build. Read whatever comes back carefully,
including which tool produced it — and if the build succeeds, check that the call site you
expect to be instantiated is really in a different translation unit from the definition.
Having reached a conclusion about the placement, fix it and say in one sentence what the
compiler could not do without the body.

Now convert the call sites, one at a time, deleting the old function as its last caller goes.
Run `dumps-basic-png` after the first conversion rather than at the end: the length field of
the first chunk is read by the very first call, so a byte-order mistake shows up immediately
and unambiguously.

Add tests that pin the conversion down with known bytes: a four-byte sequence whose value you
can compute by hand, a two-byte one, and the one-byte case. Include a value with a high bit
set, because that is where a signed intermediate type goes wrong. Finally, grep your own
source for the deleted names and for any shifting or reversing outside the template.

## Completion conditions

- `build` and `tests` pass, and `dumps-basic-png` still passes.
- No `read_u32`/`read_u16`/`read_u8` function or macro remains in the source, and no call site
  adjusts byte order after calling `read<T>`.
- `read<std::uint32_t>` reads a chunk length correctly, demonstrated by the listing for
  `assets/basic.png` being byte-for-byte what it was before.
- At least one test feeds `read` a known big-endian byte sequence and asserts the value,
  covering more than one width, and at least one case has the top bit of the first byte set.
- The learner can explain what the compiler generates for `read<std::uint32_t>` and when, and
  can say why the type is written at the call site while `swap_in_place(x)` would not need
  one.
- The learner can describe the link error a template defined in a `.cpp` produces, say why the
  compiler did not catch it, and say what makes a header the right place for the definition.
- The learner can state where byte order is handled in the program and defend the answer being
  one place.

## On completion, persist

Record in the instance's `STATE.md` the name and header of the `read` template and its
signature, that the `read_u*` family is gone, and that byte order is converted inside `read`
alone — `10-chunks-without-switch` and `11-the-finished-tool` both add parsing code and must
not reintroduce a swap at a call site. Note whether the learner took `reading-a-template-error`
and whether the undefined-symbol failure actually happened, since a learner who never saw it
will need the explanation repeated when a class template arrives in `09-errors-without-errno`.

## Optional deeper paths

The tutor may offer `reading-a-template-error` here; it takes two deliberately broken
instantiations and reads the messages down to the one line that matters.

For the curious: look at the generated code for `read<std::uint32_t>` in a disassembler or on
a compiler explorer and find the single byte-swapping instruction the shifting loop became.
Ask what `template <typename T>` and `template <class T>` differ in (nothing). Find out what
`inline` actually promises, which is about linkage rather than about inlining. And consider
what would change if `read` also had to work for a signed type — which the PNG format never
asks for, but the answer explains why the intermediate arithmetic should be unsigned.
