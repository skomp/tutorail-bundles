---
id: reading-a-template-error
title: Reading a template error
design_refs: [byte-order-in-one-place]
validators: [build]
optional: true
---

## Purpose

Make a two-hundred-line template error readable, and find the one line in it that names
your mistake.

Templates fail differently from functions. A function with a mistake in it produces an error
on the line with the mistake. A template produces a wall of output in which the first line is
usually not your file, the failing line is usually correct, and the mistake is somewhere you
have to work back to — or it produces no compile error at all and an undefined symbol at link
time instead. Neither is harder than an ordinary error. Both are unreadable until someone
tells you what the parts are.

## Prerequisites

This is an optional lesson, offered around `08-templates-eat-the-macros`. It needs a
function template of your own — the `read<T>()` that replaced the `read_u32` and `read_u8`
pair — a project that builds a library, a binary and a test executable from
`04-a-target-of-its-own`, and the ability to run the build and read its output. It uses no
C++ feature the main path has not reached, and nothing on the main path depends on it.

**If you arrived here with a broken build**, that is the expected second entrance. This
lesson anticipates the failure mode `template-definition-in-a-cpp-file`, and a learner can
easily meet it in the middle of lesson 08 rather than at the offer point. Do not throw your
error away to run the exercise below: your own failure is a better case one than a
manufactured one. Read the theory, diagnose what you already have, and use the second case
only for the compile-time half.

## Learning objectives

- Say where a template is instantiated, and why the compiler needs its definition at that
  point rather than at its declaration
- Explain what an undefined symbol naming a template instantiation actually means, and why
  the same build linked for one type and not another
- Read an instantiation chain: find the frame where the requirement failed and the last
  frame in code you own, and say which of the two holds the mistake
- Bisect a wall of instantiation output down to one question
- Diagnose two broken instantiations from their messages alone, and repair both

## Theory

### A template is not code until someone asks for it

A function template is a pattern for generating functions. Writing `read<T>` produces no
code at all. When the compiler sees a use with concrete arguments — `read<std::uint32_t>`,
or a call it can deduce that from — it *instantiates* the template: it substitutes the
argument for the parameter and compiles the result, as if you had written that one function
out by hand. One instantiation per distinct set of arguments, and none for arguments nobody
used.

Two consequences follow, and between them they explain every template error in this course.
First, **the compiler needs the definition at the point of instantiation**, not at the point
of declaration: a declaration is enough to type-check a call, and not enough to generate a
body from. That is why templates live in headers. Second, **errors in the pattern are found
per instantiation** — the body is checked once when it is defined, for everything that does
not depend on the parameter, and again for each instantiation, for everything that does. A
template body can be entirely valid and still fail to compile, for one type, at one call
site, long after you wrote it.

### The undefined symbol, and why the build half worked

Now put the definition of `read<T>` in a `.cpp` file, the way C separates a declaration from
its definition. The header keeps the declaration. Everything compiles. Then the link fails,
with a message naming a function you can see with your own eyes in a file that is in the
build.

Here is what happened. The `.cpp` holding the definition is a translation unit like any
other, and if it *itself* calls `read<std::uint32_t>` anywhere, the compiler instantiates
that specialisation while compiling it and emits the generated function into that object
file. A different `.cpp` calling `read<std::uint16_t>` sees only the declaration, generates
a call to a function it assumes exists somewhere, and emits nothing. At link time, the
`uint32_t` instantiation is present because one file happened to need it, and the
`uint16_t` one exists nowhere.

That is the shape of the failure and the reason it is confusing: it is a *partial* success.
The same template, the same header, the same build — and one type works. If it had failed
for everything, you would have suspected the mechanism immediately.

The message is more informative than it looks. GCC and the GNU linker say
`undefined reference to` followed by the mangled name; Clang on macOS says
`Undefined symbols for architecture …`, then the symbol, then `referenced from:` and the
object file. In both cases the symbol **contains the template arguments**, so it says exactly
which instantiation was requested, and `c++filt` or `nm -C` over the object files will
demangle it into something readable. Note the one thing it cannot tell you: there is no line
number in the template, because no code was ever generated to have one.

The deliberate version of the same mechanism is an **explicit instantiation definition**:
telling the compiler in that `.cpp` to generate the specialisation for a named type whether
or not the file uses it. Worth knowing it exists, and worth knowing it works by listing every
type in advance, which is why it is the exception rather than the rule.

### The wall of output, and which end of it to read

The other failure is louder. Instantiate a template with a type its body cannot support and
the compiler reports an error *inside the template*, on a line that is correct for every
type the template was written for, followed — or preceded — by a chain of notes that walks
back to your call.

The chain is the useful part, and the compilers print it in opposite orders. GCC leads with
`In instantiation of …`, then one or more `required from here` lines, and puts the error
last; Clang leads with the error and follows it with
`note: in instantiation of function template specialization … requested here`. So **the first
line of the output is not the mistake in either compiler** — it is one end of the chain, and
which end depends on which compiler you are running. Reading the first line and stopping is
the most common way to spend an hour on a five-second problem. Read both ends instead:

- The **deepest frame** is where a requirement failed: an operator that does not exist for
  this type, a member that is not there, a conversion that is not allowed.
- The **last frame in code you own** is where the instantiation was requested — your call
  site, with the deduced arguments printed beside it, usually in the form `[with T = …]`.

The mistake is nearly always at the second point, and the first tells you what the template
needed that your type did not supply. Read the deduced arguments carefully while you are
there: half of these errors are a `T` that is not the `T` you thought you were passing.

### Cutting the wall down

Four techniques, in rough order of how often they help.

- **Stop after the first error.** `-fmax-errors=1` on GCC, `-ferror-limit=1` on Clang. The
  second and later errors in a template failure are usually consequences of the first.
- **Instantiate it on purpose, alone.** Force the one instantiation you suspect, in a file
  with nothing else in it. This removes deduction and the surrounding code from the picture,
  and turns a chain into a single error.
- **Bisect the call sites.** Comment out uses until the error disappears; the last one you
  removed requested the instantiation that fails.
- **Assert the requirement yourself.** A `static_assert` at the top of the template body,
  checking what the body actually needs of `T` — that it is an integral type, that its size
  is what the caller expects — replaces a failure deep inside the body with your own sentence
  at the top, with the template arguments beside it. It is the poor relation of what C++20
  concepts do properly, and in C++17 it is the best tool there is.

## Concepts to teach

Instantiation: a template is a pattern, and code exists only for the arguments something
asked for. Why the definition must be visible in every translation unit that instantiates it,
and therefore why templates live in headers. Implicit instantiation in the translation unit
that uses a template, and the partial link success that follows from a definition in a
`.cpp`. Explicit instantiation as the deliberate alternative, and its cost. Demangling a
symbol with `c++filt` or `nm -C`. The structure of an instantiation chain, that GCC and Clang
print it in opposite orders, and that the first line names the instantiation rather than the
mistake. Reading deduced arguments from `[with T = …]`. `static_assert` as a way to move a
diagnosis to a place you chose.

## Constraints

- This lesson breaks your build on purpose. **You** make each break and **you** undo it; the
  tutor does not edit your source. Know how you will get back — a copy of the file, or a
  commit you can return to.
- The tree is green when the detour ends: `build` passes and every check that passed before
  it still passes.
- The repair for the link-time case restores the design decision rather than working around
  it. `byte-order-in-one-place` says the big-endian conversion happens inside `read<T>` and
  nowhere else, so a "fix" that copies the definition into each `.cpp` that needs it, or that
  swaps bytes at a call site to avoid the template, has broken something bigger than it fixed.
- Diagnose from the message before changing anything. The exercise is the reading; a repair
  arrived at by trying things has not done it.

## Suggested progression

Set up two broken instantiations, one at a time, and restore the build between them.

**Case one — the definition in the wrong file.** Move the body of `read<T>` out of the
header and into a `.cpp` file, leaving the declaration behind in the header. Make sure that
`.cpp` itself calls `read<std::uint32_t>` somewhere — reading a chunk length is the natural
one. Then call `read<std::uint16_t>` from a different translation unit: a test is the
cleanest place. Build. The compile will succeed and the link will fail.

Before touching anything, answer from the message alone: which instantiation is missing;
which object file asked for it; why the `uint32_t` instantiation is present and the
`uint16_t` one is not; and what the absence of any line number in the template is telling
you. Then repair it, and be able to say why the repair works in terms of where an
instantiation happens.

**Case two — a type the body cannot serve.** With the build green again, instantiate
`read<T>` from a test with a type its body genuinely cannot handle, and work out from your
own implementation which type that is — that part is the exercise. If the body reassembles
the value by shifting and OR-ing, a floating-point type such as `double` does it, because
neither operator applies. If the body instead copies the bytes and reverses them, a `double`
will compile and quietly return nonsense, so reach for a small class type with no default
constructor instead, which no plausible body can produce. Either way the error lands on a
line of the template that is right for every type the template was designed for.

Answer from the message first: which line the compiler is complaining about; which frame of
the chain is in code you wrote; what the deduced `T` was; and which of the two ends holds the
mistake. Then repair it — and notice that the repair is not necessarily in the template at
all. If your `read<T>` turned out to accept a type it should not, that is a second finding,
and the technique for it is in the theory above.

Finish by restoring the build and re-running the checks that were passing before you started.
For a better diagnosis next time, add the `static_assert` from the theory section to
`read<T>` and reintroduce case two for one build to see what the error looks like now.

## Completion conditions

- `build` passes at the end, with both deliberate breakages repaired and no leftover debris
  from them; every check that passed before the detour still passes.
- For each of the two cases, the learner named the cause **from the error message alone**,
  before editing anything, and their diagnosis matched what the repair turned out to be.
- The learner can state where a template is instantiated and why its definition must be
  visible there, and can explain why the link succeeded for one type and failed for another
  in case one.
- The learner can point at the frame of an instantiation chain that lies in their own code,
  and say why the first line of the output was not it.
- The learner can name at least two of the four ways to cut a template error down, and say
  what a `static_assert` in a template body buys.

## On completion, persist

In the instance's `STATE.md`, record that this optional lesson was taken, and whether it was
taken at the offer point or after hitting the link error for real. If the learner added a
`static_assert` to `read<T>`, that is a change to the shape of their template and belongs in
`DESIGN.md` as a decision, alongside `byte-order-in-one-place`.

## Optional deeper paths

Read about `extern template`, the explicit instantiation *declaration* that promises the
specialisation exists elsewhere and stops every translation unit generating its own copy, and
what that is worth on a large project. Find the same instantiation emitted in several object
files with `nm -C`, and read what the linker does with the duplicates and why that is allowed.
Read about two-phase name lookup and why `typename` and `template` are sometimes required
inside a template body — the errors those produce are the other classic wall. And look at
what C++20 concepts do to the messages in this lesson, which is the reason they exist, while
noting that everything after C++17 is outside this course.
