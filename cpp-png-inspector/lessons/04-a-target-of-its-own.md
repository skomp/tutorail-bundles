---
id: 04-a-target-of-its-own
title: A target of its own
design_refs: [owning-and-borrowing]
validators: [configure, build, tests]
---

## Purpose

Split the program into a library the rest of the course can test and a thin binary that
links it, and get a test suite that CMake builds and CTest runs.

You now have a type worth testing and no way to test it, because everything lives in one
file with a `main` in it. Every lesson from here on is checked by a test you write, so the
harness is not housekeeping — it is the instrument for the next eight lessons.

## Prerequisites

`03-a-class-that-cleans-up` is complete: an owning buffer type exists, its destructor
releases the bytes, `no-leak-on-error-path` passes on `assets/truncated.png`, and
`dumps-basic-png` still passes. You have `cmake` 3.20 or newer and a C++17 compiler, both
confirmed before lesson 00.

## Learning objectives

- Describe a build as a graph of targets rather than a list of compiler commands
- Create a library target and an executable target, and link one to the other
- Choose `PRIVATE`, `PUBLIC` or `INTERFACE` for an include directory and say what each one
  means for a target that links yours
- Register a test with `enable_testing` and `add_test`, and run the suite with CTest
- State exactly what CTest uses to decide a test passed, and demonstrate that your test
  fails when the code it covers is broken
- Give a test the path to a data file without depending on the directory it was run from

## Theory

### Why split now, rather than at the start

Because you could not have tested anything before, and now you can. A test is a separate
program, and two programs cannot both have a `main`. As long as your buffer type and your
parser live in the same translation unit as `main`, the only way to exercise them is to run
the whole tool and read its output — which is what the `checks/` scripts already do, at the
coarsest possible grain. They tell you the listing was wrong. They cannot tell you that
your copy constructor duplicated a pointer, which is the defect two lessons from now.

So the project acquires three parts: a **library** holding everything that is not `main`, a
**binary** named `pngdump` that links the library and does nothing but handle arguments and
print, and one or more **test binaries** that link the same library and check pieces of it
directly.

### A target is a node with requirements attached

CMake is not a shell script that runs a compiler. A `CMakeLists.txt` describes a graph of
**targets** — libraries, executables — and each target carries two kinds of information:
what it needs to be built, and what it imposes on anything that links it. The second kind
are called **usage requirements**, and they are the reason modern CMake is written the way
it is.

Three commands carry almost all of it:

```cmake
add_library(<name> <sources...>)             # a target that is not a program
add_executable(<name> <sources...>)          # a target that is a program
target_link_libraries(<name> <PRIVATE|PUBLIC|INTERFACE> <other targets...>)
```

`target_link_libraries` does far more than pass `-l` to the linker. When your executable
links your library, it inherits the library's **public** usage requirements: its include
directories, its compile definitions, its required language standard. That inheritance is
the whole design. You state a fact once, on the target it belongs to, and everything
downstream gets it.

A library with no type given is a static library here, which is what you want: one archive,
linked into both the binary and the tests, no installation and no shared-object loader
paths to think about.

### `PRIVATE`, `PUBLIC`, `INTERFACE` — one question, three answers

The keyword answers a single question: **who needs this to compile — me, my consumers, or
both?**

```cmake
target_include_directories(pngcore PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
```

- `PRIVATE` — needed to build this target, and nobody else's business. An implementation
  detail: a directory holding headers that only your `.cpp` files include.
- `INTERFACE` — not needed to build this target at all, but required by anything that links
  it. Rare outside header-only libraries.
- `PUBLIC` — both. Your sources need it, and so does every consumer.

Get this wrong in the obvious direction and the failure is immediate and confusing: mark the
directory holding your public headers `PRIVATE`, and the library compiles perfectly while
the test target — which includes the same header — fails to find it. The error names a
missing file, not a missing usage requirement, so the instinct is to add the directory to
the test target as well. That works, and it is wrong: you have now stated in two places a
fact that belongs to the library. The question to ask at that error is not "where else do I
need this include path" but "who is supposed to own this fact".

The same keywords, with the same meaning, appear on `target_link_libraries`,
`target_compile_definitions` and `target_compile_features`. Speaking of which:
`set(CMAKE_CXX_STANDARD 17)` — which `01-not-a-superset` had you write — is a global
variable that applies to targets created after it. The target-scoped form is
`target_compile_features(pngcore PUBLIC cxx_std_17)`, which says the library requires C++17
*and* propagates that requirement to anything linking it. Either works for this project;
knowing the difference is the point.

### Headers, and what goes in one

Splitting into targets forces the split you have been avoiding: declarations in a header,
definitions in a `.cpp`. A header may be included by many translation units, so anything it
defines must not become a duplicate symbol at link time — this is the **one-definition
rule**, and it is why headers hold class definitions and function declarations but not
function bodies (with exceptions: `inline` functions, and templates, which is
`08-templates-eat-the-macros`'s subject). Guard every header, with include guards or
`#pragma once`.

### What CTest actually checks

Two lines put a test into the build:

```cmake
enable_testing()                                  # in the TOP-LEVEL CMakeLists.txt
add_test(NAME buffer_basics COMMAND buffer_tests) # the target name works as a command
```

`enable_testing()` must appear in the top-level `CMakeLists.txt`, not only in a
subdirectory, or CTest will find nothing at the top of the build tree. `add_test` takes a
name and a command; naming an executable target as the command is enough — CMake substitutes
its real path, wherever the generator put it.

Now the part that decides whether this lesson gave you anything: **CTest decides a test
passed by looking at its exit status.** Zero is a pass. Anything else is a failure. There is
no magic, no framework, no discovery of test functions. A test is a program you wrote that
returns non-zero when it is unhappy.

Which means a test that asserts nothing passes. A test whose checks are all written but
whose failures print a message and then `return 0` passes. A test that constructs your
buffer, reads nothing and falls off the end of `main` passes, and it will keep passing for
eight lessons while covering nothing. This is the most common way a test suite becomes
decorative, and it is not detectable by reading the CTest output, because the output of a
suite that tests nothing and a suite that tests everything are identical.

The only cure is to **verify the test by breaking the thing it tests**. Change the buffer's
length to return the wrong value, or comment out the line the test depends on, run the
suite, and confirm it goes red. Then put the code back and confirm it goes green. A test you
have never seen fail is a test you have no evidence about.

One practical trap while you do that: `assert` from `<cassert>` is compiled out entirely when
`NDEBUG` is defined, which CMake defines in its `Release` and `MinSizeRel` configurations. A
suite built on bare `assert` therefore checks nothing in a release build while still
reporting every test as passed. Either do not use `assert` for this, or know that your test
build must not define `NDEBUG`.

### Where a test finds its data

If your test wants to read `assets/basic.png`, it needs the path — and a test binary's
working directory is decided by CTest, not by where the file happens to live. Do not build
paths relative to the current directory and hope. Two clean answers: pass the path as an
argument from `add_test`, using `${CMAKE_CURRENT_SOURCE_DIR}` to make it absolute; or give
`add_test` a `WORKING_DIRECTORY` and know what it is. A test that only exercises the buffer
with bytes it made up itself avoids the question entirely, and is a perfectly good first
test.

### Two ways to get the split wrong

**Listing the same sources twice.** Having written `add_library(pngcore src/buffer.cpp ...)`,
it is tempting to also list `src/buffer.cpp` in `add_executable(pngdump ...)` — the binary
needs that code, after all. It does, and it gets it by *linking*, not by recompiling. Listing
it twice compiles the same file once per target and, depending on what those objects define,
ends in a linker complaining about a symbol defined more than once. If you find yourself
adding a source file to a second target, the answer is almost always
`target_link_libraries`.

**A replaced `operator new` that does not get linked.** This one is specific to what you
built in `03-a-class-that-cleans-up`, and it is worth knowing before it happens. A static
library is an archive of object files, and the linker pulls out only the objects it needs to
resolve symbols someone referenced. Your global `operator new` replacement is not referenced
by name from anywhere — that is the point of it — so if it sits alone in a translation unit
inside the library, the linker can leave that object in the archive and your program
silently goes back to the standard library's allocator. The symptom is an allocation report
full of implausibly small numbers, or zeroes, after a split that was supposed to change
nothing. The cure is to make something in that translation unit referenced: put the counter
and the function that prints the report in the same `.cpp`, and have `main` call the report
function. Check the report after the split rather than assuming it survived it.

## Concepts to teach

CMake targets as a graph; `add_library`, `add_executable`, `target_link_libraries`. Usage
requirements and the `PRIVATE`/`PUBLIC`/`INTERFACE` keywords, on include directories and on
links. `target_include_directories`. `target_compile_features` versus the global
`CMAKE_CXX_STANDARD`. Static libraries as archives, and what the linker pulls out of one.
Header and source separation; include guards; the one-definition rule as the reason. The
configure/build split and the out-of-source `build/` directory, already used since lesson 00
and now worth naming. `enable_testing`, `add_test`, and CTest's pass criterion being the
process exit status. Why a test that asserts nothing passes, and verifying a test by breaking
the code under it. `assert` and `NDEBUG`. Test data paths and the working directory. The
executable must still be named exactly `pngdump` because every check looks for it.

## Constraints

- The executable target keeps the name `pngdump`. Every `checks/` script looks for
  `build/pngdump`, `build/Debug/pngdump` or `build/Release/pngdump`.
- Exactly one library target holds the code that is not `main`. Both the binary and the test
  executable get that code by linking it, not by listing its sources again.
- The test executable is built by the ordinary `cmake --build build`, so the `build` check
  covers it.
- `enable_testing()` goes in the top-level `CMakeLists.txt`.
- The checks from `03-a-class-that-cleans-up` must still pass after the split. The
  reorganisation may not change behaviour, and in particular the allocation report must
  still be printed and still be counting.
- The build stays out-of-source, in `build/`. `.gitignore` already keeps it out of git.
- No test framework is downloaded or vendored. A test is a program that returns non-zero on
  failure; that is enough for this whole course.
- Still no `std::vector` or `std::unique_ptr` for the buffer (`#handwritten-then-replaced`).

## Suggested progression

Decide the layout first, on paper: which files hold what, and which of your headers are the
library's public interface. A common shape is `include/` for headers the binary and the
tests both include, `src/` for implementation plus `main.cpp`, and `tests/` for test
programs — but the shape is yours, and the only thing the course requires is that the binary
is called `pngdump`.

Move the buffer type out of the file that has `main` in it: a header with the class
definition, a `.cpp` with the member function bodies. Build once with just that change and
before any targets exist, so that any compile error you see is about the split and not about
CMake.

Now rewrite `CMakeLists.txt`: a library target over the non-`main` sources, an executable
`pngdump` over `main.cpp` only, and a `target_link_libraries` joining them. Add
`target_include_directories` for the header directory and choose the keyword deliberately.
Configure and build.

Then deliberately find out what the keyword did. If you chose `PUBLIC`, switch it to
`PRIVATE` once the test target exists and read the error; if you chose `PRIVATE`, you will
meet it without trying. Either way, be able to say afterwards what the error was really
telling you.

Add `enable_testing()` and a first test executable linking the library. Write one test over
the buffer type from `03-a-class-that-cleans-up`: construct one, check that its length is
what you gave it and its bytes are what you put in, let it go out of scope, and check the
allocation counter balances. Return non-zero from `main` if any check failed. Register it
with `add_test`.

Run the suite — the `tests` check runs `ctest --test-dir build --output-on-failure` from the
project root, which is the same thing as running `ctest` inside `build/`.

Now do the step that makes the suite worth having: break the code the test covers, on
purpose, and run the suite again. If it still passes, your test is decorative and the real
work of this lesson has not started. Fix the test until the break turns it red, restore the
code, and confirm it goes green.

Finally re-run the checks from the previous lesson. Look hard at the allocation report: if
the numbers changed when the only thing you did was move code between files, read the note
above about static libraries and replaced `operator new`.

## Completion conditions

- `configure` passes.
- `build` passes, and it builds both `pngdump` and the test executable.
- `tests` passes: CTest runs at least one registered test and reports it green.
- The suite is **demonstrably** real: with a deliberate break in the code under test, the
  learner has seen `tests` fail, and seen it pass again after restoring the code. A suite
  that has never been observed failing does not satisfy this lesson.
- Exactly one library target exists; no source file is listed in more than one target; the
  binary and the test executable both reach the library through `target_link_libraries`.
- The executable is named `pngdump` and the checks from `03-a-class-that-cleans-up` still
  pass unchanged, allocation report included.
- The learner can say what `PUBLIC` and `PRIVATE` mean on `target_include_directories`, in
  terms of a consumer target rather than by reciting the words, and can describe the error a
  wrong choice produced.
- The learner can state what CTest uses to decide a test passed, and why a test that asserts
  nothing is indistinguishable from a good one in the CTest output.

## On completion, persist

Record in the instance's `STATE.md` the project layout that was chosen — the library
target's name, which directories hold headers, sources and tests, and which files moved —
because every later lesson adds to it. Record the name of the first test and what it covers.
Note the `PUBLIC`/`PRIVATE` decision for the include directory as a decision in `DESIGN.md`,
with the reason. Record that the test suite has been verified by breaking the code under it,
and note anything that had to be done to keep the allocation counter linked in after the
split.

## Optional deeper paths

Generator expressions: `$<BUILD_INTERFACE:...>` and `$<INSTALL_INTERFACE:...>` on include
directories, and why a library that is ever installed needs both. Installation and packaging
are outside this course, but the shape of the problem is worth seeing once.

`ctest -N` to list tests without running them, `ctest -R <regex>` to run a subset, and
`ctest --rerun-failed`. `set_tests_properties` for a `WILL_FAIL` test, a `TIMEOUT`, or a
`LABELS` value you can filter on.

`OBJECT` libraries and `INTERFACE` libraries: what each is for, and why a plain static
library is the right default here.

Multi-configuration generators — Visual Studio and Xcode — which build `Debug` and `Release`
side by side and put the binary in a subdirectory. That is why the check scripts look in
three places for `pngdump`, and why `--config` exists on `cmake --build` and `ctest`.

What a compile database is (`CMAKE_EXPORT_COMPILE_COMMANDS`), and why editors and clang-tidy
want one.
