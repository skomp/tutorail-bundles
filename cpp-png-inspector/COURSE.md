# C++ for C Programmers: Build a PNG Inspector

You are going to write a command-line tool that reads a PNG file and prints what is
inside it — every chunk, where it starts, how long it is, what type it is, what text
metadata it carries, and whether its checksum is good. It never decodes the image. It
tells you how the file is built.

You will write the first version in C.

Then you will spend the rest of the course repairing it.

## The goal

At the end you have a working inspector written in idiomatic C++17, standing on the
standard library, with nothing hand-rolled left in it. That is the artifact.

The thing you actually take away is smaller and more useful: for every C++ feature in
that program you will be able to say which C defect it exists to prevent — because you
wrote that defect yourself, in lesson 00, and took it out by hand.

## How this course teaches

**No feature is introduced before you have been hurt by its absence.**

That is the whole method, and it is why the course opens by having you write C. A
destructor is not interesting until you have watched an early `return` skip your `free`.
A copy constructor is not interesting until passing a struct to a function has freed the
same pointer twice. A template is not interesting until you have four functions that
differ only by a type.

So each lesson starts from something wrong with the program you have, not from a feature
that needs a home. You will be asked what you expect to happen before you run anything,
because the gap between what you expect and what happens is where the learning is.

You write every line of the implementation. The tutor will read your code, run the
checks, and tell you what it sees. It will not write your code for you, and it will not
advance because you said something works — only because a check showed it.

The last lesson deletes most of what you built. That is not a prank; it is the arrival.
You cannot read `std::vector`'s interface as a set of answers until you have met the
questions, and after eleven lessons you will have met all of them.

## Before you start

You need two things installed, and the course checks for both before the first lesson:

- **CMake**, version 3.16 or newer.
- **A C++ compiler that accepts C++17** — GCC 8 or newer, Clang 7 or newer, or MSVC 2019
  or newer. The same compiler will build the C in lesson 00.

You do not need to know CMake. It is taught here, in three pieces, at the three points
where the project actually needs it.

You do not need to download a PNG. The course supplies four of them.

## What the course hands you

Some things are not worth your time, so the bundle puts them in your workspace before
lesson 00 rather than asking you to make them:

- `assets/` — four PNG files: a small valid image, one carrying text metadata, one
  truncated part-way through a chunk, and one whose checksum is deliberately wrong.
- `checks/` — the scripts the course uses to read your program's behaviour back.
- `PNG-FORMAT.md` — one page holding everything about the PNG format this course needs.
  You will not have to read the specification.

Later, in lesson 11, it also hands you a CRC32 implementation. Writing one teaches bit
manipulation, which is a fine thing to learn in some other course.

## The output your program must produce

The check scripts read your program's standard output, so three lines have a fixed shape.
Everything else the tool prints is yours — spacing, headers, colour, how you lay out text
metadata.

```
<offset> <type> <length>                          one line per chunk, in file order
allocations: <n> frees: <m> outstanding: <k>      the allocation report, at exit
error: <message> at offset <n>                    one line per problem found
```

`<offset>` is the byte offset of the chunk's length field. `<length>` is the value of
that field — the payload length, not counting the twelve bytes of framing.

## The map

### Chapter 1 — The C you already have

| | |
|---|---|
| `00-write-the-c-walker` | Write the inspector in C. Open the file, check the signature, walk the chunks, print them. It works, and it leaks. |
| `01-not-a-superset` | Build that same source as C++. It does not compile. Find out what C++ refuses and why. |
| `02-where-the-leaks-are` | Stop guessing. Count every allocation and every free, and put a number on what the error paths lose. |

### Chapter 2 — A type that owns its memory

| | |
|---|---|
| `03-a-class-that-cleans-up` | Give the buffer a destructor. The leak stops being fixed and starts being unwriteable. |
| `04-a-target-of-its-own` | The project is now worth splitting: a library, a binary that links it, and a test suite CMake runs. |
| `05-the-rule-of-three` | Pass the buffer to a function by value and watch it free the same pointer twice. |
| `06-moving-not-copying` | Return the buffer by value without copying what it holds. |

### Chapter 3 — Safety and generics

| | |
|---|---|
| `07-bounds-you-cannot-skip` | The read that runs off the end of the file, and the view that outlives what it points into. |
| `08-templates-eat-the-macros` | Delete the `read_u32` / `read_u16` / `read_u8` family. One definition replaces all of them. |
| `09-errors-without-errno` | Stop returning `-1`. Meet exceptions, learn what RAII has to do with them, and decide against them on purpose. |

### Chapter 4 — Polymorphism and the finished tool

| | |
|---|---|
| `10-chunks-without-switch` | The `switch` over chunk type grows every time the format does. Replace it with dispatch. |
| `11-the-finished-tool` | Text metadata and checksum validation. The inspector is done. |

### Chapter 5 — Arrival

| | |
|---|---|
| `12-it-was-in-the-box` | Delete your buffer, your result type and your owning pointer. The standard library had all three. |

### Lessons the tutor may offer you

These are **optional**. They are not part of the sequence and the course finishes without
them. The tutor offers each at the point where it becomes worth an hour, and you take it
or decline it.

| | |
|---|---|
| `what-the-compiler-writes-for-you` | The six member functions the compiler writes on your behalf, and what makes it stop. Offered around lesson 05. |
| `reading-a-template-error` | How to read a two-hundred-line template error and find the one line that matters. Offered around lesson 08. |

## Milestones

| After | You have |
|---|---|
| lesson 00 | a C program that prints a real PNG's chunk list, and leaks |
| lesson 04 | a project that builds as a library, a binary and a test suite |
| lesson 06 | a buffer type that cannot leak, cannot double-free, and is cheap to return |
| lesson 11 | the complete inspector: metadata, checksum validation, truncation handled |
| lesson 12 | the same tool, on the standard library, with nothing hand-rolled |

## Topics this course must cover

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
- const correctness
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

## Topics this course deliberately leaves out

If you are stuck on one of these, you have wandered outside the course rather than found
a hole in it.

- multiple inheritance and virtual inheritance
- template metaprogramming, SFINAE, `std::enable_if`
- concepts, ranges, coroutines, modules — anything after C++17
- concurrency: threads, atomics, the memory model
- `std::shared_ptr` and reference counting, beyond one paragraph in lesson 12
- custom allocators
- the preprocessor beyond include guards
- image decoding: zlib, DEFLATE, PNG filtering, pixel formats
- build systems other than CMake, and CMake's install, export and packaging machinery
