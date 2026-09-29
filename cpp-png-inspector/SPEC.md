# C++ for C Programmers: Build a PNG Inspector

**Bundle id:** `cpp-png-inspector`
**Scale:** long
**Status:** approved
**Date:** 2026-09-29 (approved 2026-09-29)

## The learner

For someone who knows C but has not written any lately — they can read a pointer, a struct
and a `malloc`, and they would have to look up the exact discipline that keeps `free` correct.
They have written no C++ at all. `level: beginner-to-intermediate`: a beginner in C++, not a
beginner in programming.

At the end they have a working command-line tool that reads a real PNG file and prints its
structure — every chunk, its length, its type, its text metadata, and whether its CRC is
good — written in idiomatic C++17 on top of the standard library. More importantly, for
every C++ feature in that tool they can name the C defect it exists to prevent, because they
wrote that defect themselves in lesson 00 and removed it by hand.

**One sentence:** they stop writing C with classes, because they watched each C++ feature
repair a bug of their own.

The course's bet, stated once so every lesson can be checked against it: **no feature is
introduced before the learner has been hurt by its absence.**

## The arc

The learner writes the tool in C first, in lesson 00. Every lesson from 01 to 12 is a repair
of something in that program, and the instructive-failure column is why each row is a lesson
rather than a handover.

### Main path

| # | slug | purpose | objective | instructive failure | completion | design_refs | validators |
|---|---|---|---|---|---|---|---|
| 00 | `write-the-c-walker` | build the leaky C program the whole course repairs | binary file layout; `malloc`/`free` discipline; CMake's configure/build split | reading the big-endian length field little-endian and walking off the file; missing the 8-byte signature offset; never terminating because `IEND` was not special-cased; running `cmake` inside the source tree | `configure`, `build` and `dumps-basic-png` pass; the tool prints type and length for every chunk of `assets/basic.png` | `#whole-file-in-memory`, `#idat-is-out-of-scope`, `#the-output-contract` | `configure`, `build`, `dumps-basic-png` |
| 01 | `not-a-superset` | discover that a C++ compiler rejects the C they just wrote | C++ is not a superset of C; references; namespaces; `auto`; `nullptr`; `CMAKE_CXX_STANDARD` | "fixing" the implicit `void*` conversion by casting everywhere instead of understanding what the cast asserts; assuming a `char*` string literal is still writable; changing the CMake language and not the standard, then meeting a C++17-only error | the same source builds as C++17 and still passes `dumps-basic-png`; the learner names three things C++ refused and why | `#whole-file-in-memory` | `configure`, `build`, `dumps-basic-png`, `explains-the-repair` |
| 02 | `where-the-leaks-are` | turn "it probably leaks" into a number | ownership as a countable property; every early return is an exit path | counting `malloc` but not `realloc`; printing the count from a path the error return skips, so the one run that matters reports nothing | `leak-is-visible` passes: on `assets/truncated.png` the counter reports outstanding allocations, and the learner can point at the line that returns without freeing | `#the-allocation-counter`, `#the-output-contract` | `build`, `leak-is-visible`, `explains-the-repair` |
| 03 | `a-class-that-cleans-up` | make the leak unwriteable rather than fixed | constructors, destructors, RAII; scope as the unit of lifetime | writing a `destroy()` method and calling it by hand — C with classes, and the leak returns on the error path; a destructor that faults on a buffer that was never allocated | `no-leak-on-error-path` passes on `assets/truncated.png`; no `free` remains on any error path in the parser | `#owning-and-borrowing`, `#the-allocation-counter` | `build`, `dumps-basic-png`, `no-leak-on-error-path` |
| 04 | `a-target-of-its-own` | the project is now worth splitting, so split it | CMake targets: a library, a binary that links it, `target_include_directories`; `enable_testing`, `add_test`, CTest | putting sources in `add_executable` twice instead of linking the library; `PRIVATE` include directories that the test target then cannot see; a test that passes because it asserts nothing | `configure`, `build` and `tests` pass; the binary and the test executable both link one library target | `#owning-and-borrowing` | `configure`, `build`, `tests` |
| 05 | `the-rule-of-three` | pass the buffer to a function and watch it double-free | copy construction and copy assignment; `= delete`; why the compiler's default copy is wrong for an owning type | returning early from copy assignment and leaking the old buffer; forgetting self-assignment; deleting the copy and being unable to explain what that costs | a test copies a buffer and passes; the allocation counter balances; the learner explains what the compiler-generated copy did | `#owning-and-borrowing`, `#the-allocation-counter` | `build`, `tests`, `no-leak-on-error-path` |
| 06 | `moving-not-copying` | return a buffer by value without copying megabytes | move construction and move assignment; the rule of five; `std::move` as a cast, not a verb | leaving the moved-from object owning the same pointer, which double-frees at the next scope exit; writing `std::move` on a return value and pessimising it; a move constructor that is not `noexcept` | a test proves a returned buffer allocated once; the counter balances; the learner explains what a moved-from object must still satisfy | `#owning-and-borrowing` | `build`, `tests`, `no-leak-on-error-path`, `explains-the-repair` |
| 07 | `bounds-you-cannot-skip` | the `memcpy` that reads past the end of the file | `operator[]` and a checked `at()`; a non-owning view; `const` correctness; dangling | a view that outlives the buffer it points into — the exact bug ownership was supposed to end; returning a non-`const` reference from a `const` method and not seeing why it compiles nowhere useful | `rejects-truncated` passes: the truncated asset is reported, not crashed on; a test proves an out-of-range read is caught; read-only operations compile against a `const` buffer | `#owning-and-borrowing` | `build`, `tests`, `rejects-truncated` |
| 08 | `templates-eat-the-macros` | delete the `read_u32`/`read_u16`/`read_u8` family | function templates; template argument deduction; why templates live in headers; `sizeof(T)` as a constraint | defining the template in a `.cpp` and getting an undefined symbol rather than a compile error — the C habit of splitting declaration from definition; a `read<T>` that copies the bytes without swapping them, which breaks on the first length field | the macro family is gone; `read<uint32_t>` reads a chunk length correctly; a test covers a known big-endian value; `dumps-basic-png` still passes | `#byte-order-in-one-place` | `build`, `tests`, `dumps-basic-png` |
| 09 | `errors-without-errno` | stop returning `-1` and setting a global | a class template with a value and an error state; exceptions — what they are, what RAII has to do with them, and why this course returns values instead | a result type whose value member holds valid-looking garbage on the error path; a result holding a buffer that is not movable, so it cannot be returned; concluding that an exception through the parser would leak, when the destructor written in lesson 03 is precisely what stops it | no parse function returns `-1` or sets a global; every failure carries the byte offset that caused it; `rejects-truncated` and `tests` pass | `#errors-are-values`, `#owning-and-borrowing` | `build`, `tests`, `rejects-truncated`, `explains-the-repair` |
| 10 | `chunks-without-switch` | the `switch` over chunk type that grows with every type | abstract base classes; `virtual`, `override`; the virtual destructor; interface inheritance, not implementation inheritance | a base class with no virtual destructor, deleted through a base pointer — and the lesson-02 counter is what catches it; making the chunk *data* polymorphic instead of the handler, so every chunk in the file needs a heap allocation; omitting `override` and silently defining a new function because the signature differs by a `const` | adding a chunk type touches one new class and no existing function; the `switch` is gone; the counter balances; `tests` and `dumps-basic-png` pass | `#chunk-data-vs-chunk-handlers`, `#owning-and-borrowing` | `build`, `tests`, `dumps-basic-png`, `no-leak-on-error-path` |
| 11 | `the-finished-tool` | text metadata and CRC validation; the tool is done | reading a length-delimited field that is not NUL-terminated; validating a checksum over the right byte range | treating a `tEXt` value as a C string and calling `strlen` on it — the value runs to the chunk length and is not terminated; computing the CRC over the data only, when it covers the type field as well | `reads-text-metadata`, `detects-bad-crc`, `rejects-truncated`, `dumps-basic-png` and `tests` all pass | `#idat-is-out-of-scope`, `#errors-are-values`, `#the-output-contract` | `build`, `tests`, `dumps-basic-png`, `reads-text-metadata`, `detects-bad-crc`, `rejects-truncated` |
| 12 | `it-was-in-the-box` | delete the code they spent eight lessons writing | `std::vector`, `std::unique_ptr`, `std::optional`, `std::string_view`; reading a standard container's interface as a set of answers to problems they now recognise | reaching for `std::shared_ptr` where `unique_ptr` is correct, and not being able to say what the count buys; expecting `std::optional` to carry the error message, which is exactly the gap `std::expected` fills in a later standard | no hand-written owning buffer, result type or owning raw pointer remains; every test from lessons 04 to 11 passes unchanged; the counter still balances; the learner says, per replacement, what the standard type does that theirs did not | `#handwritten-then-replaced`, `#errors-are-values` | `build`, `tests`, `dumps-basic-png`, `reads-text-metadata`, `detects-bad-crc`, `rejects-truncated`, `explains-the-repair` |

### Optional track (offered, not sequenced)

Both are authored in full. Neither is a prerequisite for any main-path lesson, and the
course is completable by a learner who declines both.

| slug | purpose | objective | instructive failure | completion | offer after | design_refs | validators |
|---|---|---|---|---|---|---|---|
| `what-the-compiler-writes-for-you` | the six special member functions, and when the compiler stops writing them | default construction, copy, move, destruction; `= default` and `= delete`; how declaring one suppresses others | declaring a destructor and losing the implicit moves without noticing, so everything silently copies again | the learner predicts, for three class shapes, which special members exist, and a test confirms each prediction | 05 | `#owning-and-borrowing` | `build`, `tests` |
| `reading-a-template-error` | make a 200-line template error readable | where a template is instantiated; what an undefined symbol from a template means; how to bisect an instantiation error | assuming the first line of the error names the mistake, when it names the instantiation | the learner takes two deliberately broken instantiations, names the cause of each from the message alone, and fixes both | 08 | `#byte-order-in-one-place` | `build` |

### Anticipated failure

`reading-a-template-error` anticipates one failure mode, because it is the single most
predictable mistake a C programmer makes with their first template.

| failure mode id | summary | signals |
|---|---|---|
| `template-definition-in-a-cpp-file` | A template defined in a `.cpp` file links only for the types that file happens to instantiate, so the build fails with an undefined symbol rather than a compile error. | `validator:build`, `diagnosis` |

`repair_in: lessons/08-templates-eat-the-macros.md`. No `required_for` gate: the tutor can
coach the repair inline, and lesson 08 is finishable without the detour.

## Chapters and milestones

| Chapter | Lessons | What it is |
|---|---|---|
| 1. The C you already have | 00, 01, 02 | write it, discover C++ rejects it, measure what it leaks |
| 2. A type that owns its memory | 03, 04, 05, 06 | RAII, a real project layout, and value semantics done properly |
| 3. Safety and generics | 07, 08, 09 | bounds, views, `const`, function templates, class templates |
| 4. Polymorphism and the finished tool | 10, 11 | virtual dispatch, and the tool actually finished |
| 5. Arrival | 12 | the standard library, understood rather than taken on trust |

| Milestone | After | The learner has |
|---|---|---|
| M1 | 00 | a C program that prints a real PNG's chunk list, and leaks |
| M2 | 04 | a project that builds as a library, a binary and a test suite |
| M3 | 06 | a buffer type that cannot leak, cannot double-free, and is cheap to return |
| M4 | 11 | the complete inspector: metadata, CRC validation, truncation handled |
| M5 | 12 | the same tool, on the standard library, with nothing hand-rolled |

## Teaching stance

```yaml
workspace_kind: new-repository
tutor_owned:    [tutorial/STATE.md, tutorial/DESIGN.md]
learner_owned:  [src/**, include/**, tests/**, CMakeLists.txt]
ownership_policy: tutor-must-not-edit-learner-owned
one_task_at_a_time: true
solution_code: on-request-only
advance_on: validated-evidence-only

validators:
  configure:             { kind: command, command: [cmake, -S, ., -B, build] }
  build:                 { kind: command, command: [cmake, --build, build] }
  tests:                 { kind: command, command: [ctest, --test-dir, build, --output-on-failure] }
  toolchain-present:     { kind: command, command: [bash, checks/toolchain.sh] }
  dumps-basic-png:       { kind: command, command: [bash, checks/dump.sh, basic] }
  reads-text-metadata:   { kind: command, command: [bash, checks/dump.sh, text] }
  detects-bad-crc:       { kind: command, command: [bash, checks/dump.sh, badcrc] }
  rejects-truncated:     { kind: command, command: [bash, checks/dump.sh, truncated] }
  leak-is-visible:       { kind: command, command: [bash, checks/error-path.sh, expect-leak] }
  no-leak-on-error-path: { kind: command, command: [bash, checks/error-path.sh, expect-clean] }
  explains-the-repair:   { kind: manual }

setup_validators:
  - name: toolchain-present
    describe: confirms cmake and a compiler that accepts C++17 are on your PATH before the first lesson
```

Two notes on the validator map, because both are deliberate:

- **`leak-is-visible` and `no-leak-on-error-path` are the same script inverted.** Lesson 02
  passes when the leak is demonstrable; every lesson from 03 on passes when it is gone. A
  single validator could not express both, and the pair is what makes lesson 02 checkable
  at all rather than a matter of the learner's word.
- **`explains-the-repair` is `kind: manual` and that is correct, not a gap.** Five lessons
  turn on the learner being able to say what a feature repaired. No command can check that,
  and pretending otherwise would be worse than the tutor judging it.

## Supplied files

| from | to | describe | scope |
|---|---|---|---|
| `supplies/assets/` | `assets` | The four PNG files this course runs against: a small valid image, one carrying text metadata, one truncated part-way through a chunk, and one whose CRC is deliberately wrong | `tutorial.yaml` |
| `supplies/checks/` | `checks` | The scripts the course uses to read your program's behaviour back. You never edit these | `tutorial.yaml` |
| `supplies/PNG-FORMAT.md` | `PNG-FORMAT.md` | One page: the eight-byte signature, the four fields of a chunk, and the handful of chunk types this tool reports — so you never have to open the PNG specification | `tutorial.yaml` |
| `supplies/gitignore` | `.gitignore` | Keeps the `build/` directory out of git | `tutorial.yaml` |
| `lessons/11-the-finished-tool/crc32.hpp` | `src/crc32.hpp` | A CRC32 implementation, supplied: writing one teaches bit twiddling, not C++ | `11-the-finished-tool` |

Every one of these fails the toil test — the bundle could have shipped the result, and
getting any of them wrong teaches nothing about C++. Two are worth their own sentence:

- **The corrupt and truncated PNGs.** A learner cannot be asked to hand-craft a file with a
  wrong CRC, and a course that asked would spend a lesson on a hex editor.
- **`crc32.hpp`.** Implementing CRC32 is a genuine exercise — in bit manipulation, in a
  different course. Here it would be forty minutes stolen from lesson 11's actual subject.

Everything the bundle *cannot* ship stays the learner's work and is not supplied: installing
CMake and a C++17 compiler is asked for in `COURSE.md`, and the `toolchain-present` setup
validator confirms it before lesson 00 rather than letting it fail mid-lesson.

## Durable decisions

### `#whole-file-in-memory`

The tool reads the entire file into one owning buffer before parsing anything. It does not
stream, and it does not `mmap`.

**What breaks if a lesson contradicts it:** the buffer is the object every ownership lesson
operates on. A streaming parser has nothing to own, no 4 MB copy to avoid, and therefore no
motivation for lessons 03 through 06. Resolved.

### `#the-allocation-counter`

Allocation is counted, for the whole course, by a counting wrapper the learner writes in
lesson 02 — around `malloc`/`free` at first and around `operator new`/`operator delete` from
lesson 03. It stays in the program to the end, and it is the evidence for lessons 03, 05, 06,
10 and 12.

**What breaks if a lesson contradicts it:** removing it, or replacing it with a sanitizer,
takes away the one check that works identically on Linux, macOS and Windows — LeakSanitizer
does not detect leaks on macOS, and valgrind does not run on Apple silicon. Resolved.

### `#owning-and-borrowing`

Exactly one type owns bytes. Everything that reads bytes borrows them through a non-owning
view of pointer and length, which copies freely and frees nothing.

**What breaks if a lesson contradicts it:** a view that owns reintroduces the double-free
lesson 05 removed, and forces every chunk handler in lesson 10 to hold a copy of its payload.
Resolved.

### `#errors-are-values`

Parse failures are returned as values carrying the byte offset that caused them. Nothing sets
a global, nothing returns `-1`, and the parser throws no exceptions.

Exceptions are **taught** in lesson 09 — what they are, why RAII is the thing that makes them
survivable, and why this particular program returns values anyway. Teaching them and not
using them is the decision, not an omission.

**What breaks if a lesson contradicts it:** a lesson that throws makes every later function
signature and the whole of lesson 09's exercise meaningless. Resolved.

### `#byte-order-in-one-place`

Every multi-byte field in a PNG is big-endian, and the conversion happens in exactly one
place: inside `read<T>()`.

**What breaks if a lesson contradicts it:** swapping bytes at call sites is the macro family
lesson 08 exists to delete, wearing a template's clothes. Resolved.

### `#chunk-data-vs-chunk-handlers`

A parsed chunk is a plain value: type, length, a view of its payload, and its CRC.
Polymorphism lives in the **handlers** that interpret a chunk, never in a hierarchy of chunk
objects.

**What breaks if a lesson contradicts it:** a hierarchy of chunk data types puts every chunk
in the file on the heap behind a base pointer, which lesson 12 then cannot replace with a
`std::vector` of values. Resolved.

### `#handwritten-then-replaced`

The buffer, the result type and the owning pointer are written by hand and then deleted in
lesson 12 in favour of `std::vector`, `std::optional` and `std::unique_ptr`. This is the
course's shape, not an accident of ordering.

**What breaks if a lesson contradicts it:** a lesson that reaches for `std::vector` before 12
removes the only reason lessons 03 to 06 exist. Resolved.

### `#the-output-contract`

The supplied check scripts read the tool's standard output, so the course fixes the shape of
three lines and nothing else:

- one line per chunk, `<offset> <type> <length>`, in file order;
- the allocation report at exit, `allocations: <n> frees: <m> outstanding: <k>`;
- one line per reported problem, beginning `error:` and naming a byte offset.

Everything else the tool prints — spacing, headers, colour, how `tEXt` keywords and values
are laid out — is the learner's.

**What breaks if a lesson contradicts it:** every validator from `dumps-basic-png` to
`no-leak-on-error-path` reads these lines. A lesson that changes the shape silently breaks
the checks of every lesson around it, and the learner sees a red check with no defect behind
it. Resolved, and stated to the learner in `COURSE.md` rather than only in a lesson.

### `#idat-is-out-of-scope`

The tool reports `IDAT` chunks by offset and size and never decompresses them. No zlib, no
DEFLATE, no PNG filtering, no pixel data.

**What breaks if a lesson contradicts it:** decompression is a second course, and it pulls in
a dependency the bundle cannot supply. Resolved, and stated in the coverage list so a stuck
learner is told it is outside the course rather than taught it.

### `#json-output`

Whether the finished tool grows a second output mode — machine-readable JSON beside the human
listing — is **deliberately unresolved**. It is a natural place for a learner to take the tool
further after lesson 12, and it is where a second round of the polymorphism decision would be
argued. No lesson depends on the answer.

## Coverage

Topics this course owes a learner, named as a learner would ask about them:

- the C++ build: CMake targets, configure and build as separate steps, out-of-source builds
- unit testing with CTest
- writing a program whose output a script can check
- what C++ rejects that C accepts
- references versus pointers
- namespaces
- classes, constructors and destructors
- RAII
- value semantics: copy construction and copy assignment
- the rule of three, and the rule of five
- move semantics and `std::move`
- the special member functions the compiler writes for you
- `= delete` and `= default`
- `const` correctness
- operator overloading
- non-owning views, and dangling
- headers and the one-definition rule
- function templates
- class templates
- reading a template error message
- inheritance for interfaces
- virtual dispatch, and the virtual destructor
- `override`
- error handling: error codes, a result type, and exceptions — and why a program picks one
- exception safety, and what RAII has to do with it
- `std::vector`, `std::optional`, `std::unique_ptr`, `std::string_view`

Deliberately **not** covered. A learner blocked on one of these is told it is outside this
course rather than taught it:

- multiple inheritance and virtual inheritance
- template metaprogramming, SFINAE, `std::enable_if`
- concepts, ranges, coroutines, modules — anything after C++17
- concurrency: threads, atomics, the memory model
- `std::shared_ptr` and reference counting beyond one paragraph in lesson 12
- custom allocators
- the preprocessor beyond include guards
- image decoding: zlib, DEFLATE, PNG filtering, pixel formats
- build systems other than CMake, and CMake's install, export and packaging machinery

## Proposed manifest fields

```yaml
bundle_format: 1
id: cpp-png-inspector
title: "C++ for C Programmers: Build a PNG Inspector"
description: >
  Learn C++ classes and templates by writing a PNG structure inspector in C first
  and then repairing it, one C++ feature at a time, until nothing hand-rolled is
  left. For a programmer who knows C and has written no C++.
teaching_method: >
  You write the C version yourself in the first lesson, leaks and all. Every lesson
  after it removes a defect you wrote, and no feature is introduced before you have
  been hurt by its absence. The last lesson deletes most of what you built, because
  the standard library was always going to do it better — and now you can read it.
subjects: [cpp, c, systems-programming, binary-formats, cmake]
aliases: [c++, cpp17, modern c++, classes, templates, raii, move semantics, png, c to c++]
level: beginner-to-intermediate
style: [project-driven, interactive, long-form]

covers:
  raii:
    summary: >
      A resource is owned by an object whose destructor releases it, so scope exit
      frees it on every path including the error paths.
    aliases: [destructors, resource-acquisition-is-initialization]
  value-semantics:
    summary: >
      Copying an owning object must copy what it owns, so the rule of three names
      the three functions that have to agree.
    aliases: [rule-of-three, copy-constructor, copy-assignment]
  move-semantics:
    summary: >
      Ownership can be transferred instead of duplicated, which turns returning a
      large object by value from a copy into a pointer swap.
    aliases: [rule-of-five, std-move]
  function-templates:
    summary: >
      One definition parameterised by type replaces a family of near-identical
      functions or macros, instantiated by the compiler per type used.
    aliases: [templates, generic-functions]
  class-templates:
    summary: >
      A type parameterised by another type, used here for a result carrying either
      a value or an error.
    aliases: [generic-types, result-type]
  virtual-dispatch:
    summary: >
      A call through a base-class interface selects the derived implementation at
      run time, replacing a switch over a type tag — and the base needs a virtual
      destructor.
    aliases: [polymorphism, virtual-destructor, interface-inheritance, override]
  const-correctness:
    summary: >
      Const is part of a type, so a read-only handle to an object permits exactly
      the operations that do not modify it.
  non-owning-views:
    summary: >
      A pointer-and-length view borrows bytes it does not own, copies freely, frees
      nothing, and must not outlive what it points into.
    aliases: [dangling, string-view, span]
  error-handling-as-values:
    summary: >
      Failures are returned as values rather than signalled through a global or
      thrown, and the trade against exceptions is made deliberately.
    aliases: [error-codes, exceptions, exception-safety]
  cmake-targets:
    summary: >
      A build is a graph of targets — a library, a binary that links it, tests
      registered with CTest — configured once and built from a separate directory.
    aliases: [cmake, build-system, ctest]
  standard-library-containers:
    summary: >
      std::vector, std::optional and std::unique_ptr are the standard answers to
      the ownership problems a hand-written buffer and result type run into.
    aliases: [std-vector, std-optional, unique-ptr]

assumes:
  c-programming:
    level: conceptual
    summary: >
      Read C and explain what a pointer, a struct, malloc and free do, without
      necessarily having written any recently or remembering the exact discipline
      that keeps free correct. This course re-establishes that discipline in
      lessons 00 and 02 before contrasting it.
  command-line-tools:
    level: working
    summary: >
      Run a compiler and a program from a shell, edit files in a project
      directory, and read a compiler error message without instruction.
```

`recommended_follow_ups` and `recommended_previous_bundles`: none proposed. Nothing in this
repository is a natural neighbour, and naming a course that does not exist helps no learner.

## Depth decision

**All thirteen main-path lessons and both optional lessons are authored in full now.** None
is left as a map entry in `COURSE.md`.

The cost this avoids is specific: a chapter the manifest does not carry is drafted separately,
and differently, by every learner's tutor. For this course that would be worst at the end — a
tutor improvising lesson 12 has no way to know which of the learner's hand-written types it is
supposed to delete, because that depends on decisions made nine lessons earlier.

## Open questions

1. **`#json-output` is deliberately unresolved** and recorded as such in `DESIGN.md`. It needs
   no answer before generation.
2. **The lesson-00 C program is the learner's, so its shape varies.** Lessons 01 through 03
   are written to repair a *shape* — a file read into a malloc'd buffer, a loop over chunks,
   early returns on malformed input — not an exact file. This was accepted when you chose
   "learner writes it"; it is recorded here because it is a real constraint on how those three
   lessons are worded, and a future author who changes lesson 00 to a supplied file must
   revisit them.
