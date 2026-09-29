---
id: 00-write-the-c-walker
title: Write the C walker
design_refs: [whole-file-in-memory, idat-is-out-of-scope, the-output-contract]
validators: [configure, build, dumps-basic-png]
---

## Purpose

Write the whole inspector in C — a program that reads a PNG into memory, walks its chunks
and prints them — because every lesson after this one repairs something you wrote here.

This is the longest lesson in the course and the only one that starts from nothing. It does
three jobs at once: it re-establishes the `malloc`/`free` discipline you will be measured
against in `02-where-the-leaks-are`, it produces the program that lessons `01` through `12`
take apart, and it teaches the smallest amount of CMake that will build anything at all.
Nothing in it is C++. That is deliberate: you cannot be shown what a C++ feature repairs
until you are holding the thing that needs repairing.

## Prerequisites

None — this is the first lesson. Your toolchain was confirmed before the course opened, so
CMake 3.16 or newer and a working compiler are on your `PATH`.

Your workspace already contains four things the course supplies and you never edit:

- `assets/` — `basic.png`, `text.png`, `truncated.png`, `badcrc.png`.
- `checks/` — the scripts that read your program's output back.
- `PNG-FORMAT.md` — everything about the format this course needs. Read it before you start;
  it is one page and it is the only format reference you will need for twelve lessons.
- `.gitignore` — which already ignores `build/`, for a reason that appears below.

Everything else in the repository is yours to write.

## Learning objectives

- Read an entire binary file into one heap buffer, in binary mode, knowing its exact size
- Assemble a big-endian 32-bit field from four bytes without depending on your machine's
  byte order, and say why a pointer cast is the wrong tool for it
- Walk a length-prefixed chunk sequence, advancing by the right number of bytes and refusing
  to read a byte the file does not contain
- Produce output in a fixed shape that a script can diff, rather than output that reads well
- Write a minimal `CMakeLists.txt` for a C executable, and configure and build it out of
  source as two separate steps

## Theory

**What you are building.** `pngdump` takes one argument, the path to a PNG file, and prints
one line for each chunk it finds. It never decodes an image. A PNG is a signature followed by
a sequence of chunks, and a chunk is a length, a four-letter type, that many bytes of data,
and a checksum — so the whole program is: read the file, check the signature, then repeat
"read a header, print a line, skip forward" until the file runs out. The format reference has
the exact layout; this lesson is about getting it into memory and walking it without reading
anything you do not own.

**The whole file goes into memory at once** (see `#whole-file-in-memory`). You allocate one
buffer the size of the file, read the file into it, and parse out of that buffer. You do not
stream, you do not read chunk headers and `fseek` past the payloads, and you do not `mmap`.
If that bothers you, you are right that it is not how a production inspector would be built —
a streaming inspector uses constant memory and can read a file larger than RAM. The course is
buying something with the choice: that buffer is the object every later lesson operates on.
Something allocates it, something has to free it, something will want to copy it, and
something will want to return it without copying it. A streaming parser owns nothing, and a
course about ownership would have nothing to talk about.

**Open the file in binary mode.** In C that means `"rb"`, not `"r"`, and it matters far more
than it looks. On Windows a stream opened in text mode translates CRLF to LF as it reads —
silently corrupting binary data — and historically treats byte `0x1A` as end of file. Look at
the first eight bytes of any PNG: `89 50 4E 47 0D 0A 1A 0A`. The signature contains a CRLF
*and* a `0x1A` on purpose, precisely so that a file mangled by a naive transfer or a text-mode
read stops looking like a PNG. Your program is the naive reader the format was defending
against. Open it in binary mode and it is a non-event; forget, and on one platform the file
appears to end after seven bytes.

**Know the size exactly.** You need the length before you allocate. The portable route is to
seek to the end, ask the position, and seek back — `fseek`, `ftell`, `rewind` — which returns
a `long`, so think about what you do with a negative return before you pass it to `malloc`.
Then read, and check what `fread` actually returned: it reports items read, and a short read
is not an error you can ignore, because every later bound in your program is computed from the
size you believed. One allocation, one read, one number you trust.

**Use `unsigned char` for the bytes.** Whether plain `char` is signed is
implementation-defined, and on the common platforms it is signed. Compare a signed `char`
holding the signature's first byte against `0x89` and it will not match, because the byte
sign-extends to a negative `int` while the literal is positive. This is the kind of C bug that
survives review because the code looks obviously correct. The buffer holds bytes, not text:
give it a type that says so.

**The first chunk is at offset 8.** The signature is eight bytes and is not a chunk. The
offsets your program prints are the offset of a chunk's *length* field, so the first line of
every well-formed file starts with `8`. Checking the signature means checking all eight bytes,
not looking for `PNG`.

**Every multi-byte number in a PNG is big-endian**, most significant byte first, with no
exceptions anywhere in the format. Your machine is almost certainly little-endian, which means
the four bytes on disk are in the opposite order from the way your CPU would load them. There
are three separate reasons not to reach for `*(uint32_t *)(buf + off)` here:

- it reads the bytes in *your machine's* order, so the value is wrong on one endianness and
  right on the other, which is the worst possible kind of wrong;
- it may be a misaligned load, which is undefined behaviour in C and a fault on some
  architectures, and chunk offsets are not usefully aligned;
- it violates the strict aliasing rule, so an optimising compiler is entitled to do something
  surprising with it even where the alignment happens to work.

Build the value out of its bytes instead: the first byte on disk carries the most significant
eight bits, so it is shifted left twenty-four places, the second sixteen, and so on, and the
four are combined. That code depends on nothing about the machine running it. One trap while
you write it: an `unsigned char` promotes to `int` in an arithmetic expression, so shifting it
left by twenty-four can push a bit into the sign bit of a 32-bit `int` — undefined behaviour,
for lengths at or above `0x80000000`. Convert each byte to the unsigned 32-bit type *before*
shifting it. Write yourself small helpers for a 32-bit and an 8-bit read; you will be deleting
them in `08-templates-eat-the-macros`, and it will be more satisfying if there is a family of
them to delete.

**Walking the chunks.** From offset 8, a chunk is twelve bytes of framing — four of length,
four of type, four of CRC — plus `length` bytes of data in the middle. So the next chunk
begins `12 + length` bytes after this one. Getting this arithmetic wrong is not subtle; you
will land in the middle of a payload, read four bytes of image data as a length, and go
somewhere absurd.

Which raises the question this lesson wants you to answer deliberately rather than by
accident: **when does the loop stop?** There are two candidate rules and they are not the
same. One is the format's: `IEND` is the last chunk, so a walker can stop when it has printed
it. The other is arithmetic: stop when the bytes remaining are not enough to hold what comes
next. Decide which one your loop is actually resting on, then ask what your program does with
a file that has no `IEND`, or one whose last chunk claims more bytes than the file contains.
`assets/truncated.png` is exactly that file and you will meet it in the next lesson. A loop
whose only stopping rule is "I have not seen `IEND` yet" does not terminate on that file — it
walks off the end of your buffer and keeps reading whatever it finds.

So your walk must refuse to read a byte the buffer does not hold: before reading a header,
check that at least twelve bytes remain; before accepting a chunk, check that its data and
CRC fit in what is left. Compute that check by *subtraction* — compare the length against the
bytes remaining — rather than by adding the length to the offset and comparing with the size.
The addition can overflow, and a malformed file is exactly where a length of `0xFFFFFFFF`
comes from, which makes the comparison say yes and hand you an out-of-bounds read. When a
chunk does not fit, the file is malformed: stop walking and let the program's exit status say
so. You are *not* being asked to report truncation properly yet — that is
`07-bounds-you-cannot-skip` — only to stop rather than read memory you do not own.

**`IDAT` is compressed pixel data and you will never decompress it** (see
`#idat-is-out-of-scope`). It is listed by offset, type and length like every other chunk and
then skipped. No zlib, no DEFLATE, no filtering, not now and not in lesson 12. If you find
yourself reaching for a decompressor you have left the course.

**The output has a contract** (see `#the-output-contract`). The checks read your program's
standard output with a pattern, so three line shapes are fixed for the whole course and only
one of them concerns you today:

```
<offset> <type> <length>                          one line per chunk, in file order
allocations: <n> frees: <m> outstanding: <k>      the allocation report, at exit
error: <message> at offset <n>                    one line per problem found
```

Read the first shape strictly. The three fields are separated by exactly one space each, the
offset and the length are plain decimal, the type is its four letters, and there is nothing
else on the line — no leading spaces, no column alignment, no `0x`, no commas in the numbers.
A listing padded into neat columns is prettier and matches nothing: the check will tell you
that no line matched at all. Headers, colour, blank lines and any other output you like are
genuinely yours, on *other* lines. The freedom is around the contract, not inside it.

**`malloc` and `free`, and where the promises are.** One allocation, held in `main` or in the
function that read the file, released when the program is done with it. That is the whole
discipline and it is easy while there is one path. The interesting question — the one
`02-where-the-leaks-are` is going to put a number on — is what happens on the paths where
something went wrong: the file would not open, the signature did not match, a chunk did not
fit. Each of those is a `return` from somewhere, and each `return` is an exit from the
function that is holding the buffer.

The contract's second line is the report: print `allocations:`, `frees:` and `outstanding:` in
that exact shape when the program is done. For now, keep the two counts by hand — increment
one where you allocate and one where you free — and print the line once as the program
finishes. On a valid file it will balance, and the balance will tell you nothing at all about
the paths that do not run for a valid file. That is next lesson's subject; today just get the
line into the program in the right shape.

**CMake, in the smallest piece that builds anything.** CMake does not build your program. It
reads `CMakeLists.txt` and *generates* a build system — Makefiles, a Ninja file, a Visual
Studio project — which then builds your program. That is why there are two commands and not
one:

- `cmake -S . -B build` — *configure*. Read `CMakeLists.txt` in the source directory `.`,
  write a build system into the directory `build`, and remember every choice it made in
  `build/CMakeCache.txt`.
- `cmake --build build` — *build*. Run whichever underlying tool was generated, in that
  directory. This is the one you will run hundreds of times.

The build directory is generated output. It is separate from your sources — that is the
*out-of-source* rule, and it is why `.gitignore` already lists `build/`. The payoff is real
and you will use it in the next lesson: `build/` can be deleted at any moment and rebuilt from
nothing, so a build that has gone strange has a reliable reset. If you instead run `cmake .`
in the source directory, CMake scatters its cache and generated files among your code, git
sees them, and the `CMakeCache.txt` left behind pins settings that will fight you the next
time you change something — including the language switch that is the whole of the next
lesson.

Your `CMakeLists.txt` needs three commands and is about eight lines long.
`cmake_minimum_required` takes a `VERSION` and must come first, because it tells CMake which
generation of its own behaviour to use. `project` names the project and takes a `LANGUAGES`
list — today that list is `C`, and if you leave it out CMake assumes C and C++ and will look
for a C++ compiler it does not need. `add_executable` takes the name of the target followed by
the source files that make it. That target name is not cosmetic: the checks look for an
executable called exactly `pngdump`, under `build/`, `build/Debug/` or `build/Release/`, so
name the target `pngdump` and do not redirect the output anywhere else.

## Concepts to teach

Binary versus text mode, and what text mode does to `0x0D` and `0x1A`. Determining a file's
size with `fseek`/`ftell`, and checking `fread`'s return. `malloc`, `free`, and the rule that
one owner frees once. `unsigned char` for bytes, and why plain `char`'s signedness is a bug
waiting to happen. Byte order: big-endian on disk versus the host's order, assembling a value
by shifting, integer promotion of `unsigned char` in a shift expression, and the three reasons
a `uint32_t *` cast is wrong here (order, alignment, aliasing). The PNG signature as eight
bytes, and the first chunk at offset 8. Chunk framing: `length + 12` bytes total, and the
offset printed is the offset of the length field. Loop termination: a bounds rule and a format
rule, and which one has to dominate. Overflow-safe bounds checking by subtraction. Printing a
non-NUL-terminated four-byte type without running off the end of it. The output contract
(`#the-output-contract`) and why a script-checked format is not negotiable. CMake's
configure/build split, `cmake_minimum_required`, `project(... LANGUAGES C)`, `add_executable`,
the cache, out-of-source builds and why `build/` is disposable. `IDAT` as out of scope
(`#idat-is-out-of-scope`).

## Constraints

- The program is written in C, compiled as C, with `project(... LANGUAGES C)`. No C++
  anywhere in this lesson.
- Sources live under `src/`; `CMakeLists.txt` sits at the repository root; the build directory
  is `build/` and is never committed.
- The executable target is named exactly `pngdump` and lands under `build/`. Do not redirect
  it to another directory.
- The program takes the path to a PNG as its first command-line argument, and reports failure
  through its exit status when it cannot do its job.
- The entire file is read into one heap buffer before parsing (`#whole-file-in-memory`). No
  streaming, no `mmap`, no reading chunk-by-chunk from the stream.
- No third-party libraries. The C standard library only.
- `IDAT` payloads are listed and never decompressed (`#idat-is-out-of-scope`).
- Chunk lines match the contract exactly: `<offset> <type> <length>`, one space between
  fields, decimal numbers, no padding or alignment, in file order, nothing else on the line.
- On `assets/basic.png` the program exits 0 and prints no line beginning with `error:`.
- The walk must never read outside the buffer. When the bytes remaining cannot hold the next
  chunk, stop.
- Do not validate CRCs and do not report truncation in the contract's `error:` shape. Those
  are `11-the-finished-tool` and `07-bounds-you-cannot-skip`, and doing them now removes the
  lesson that teaches them.
- Do not try to make the program leak-proof by inspection. Write it the way you would write
  it; `02-where-the-leaks-are` measures what you actually wrote.

## Suggested progression

Read `PNG-FORMAT.md` first, then look at the file you are about to parse. A hex dump of the
first forty bytes — `xxd` or `od -A d -t x1` — shows the signature, the `IHDR` header and the
length bytes, and seeing `00 00 00 0d 49 48 44 52` on the screen makes the rest of the lesson
concrete. Work out by hand, from the dump, what the three lines of output for that file should
be before you write a line of code — you will then know whether your program is right without
having to ask anyone.

Build the skeleton first: `CMakeLists.txt`, a `src/` with a `main` that prints its argument
and exits, then `cmake -S . -B build` and `cmake --build build`. Getting the two-step build
working on a program that does nothing takes five minutes; getting it working while also
debugging a parser does not. Confirm the binary is at `build/pngdump` and runs.

Then read the file into memory: open in binary mode, find the size, allocate, read, check what
you got, and print the size. Compare it with `wc -c assets/basic.png`. Free the buffer.

Then the signature: compare all eight bytes and fail if they differ. Test it against something
that is not a PNG — `CMakeLists.txt` will do — and check that your program says so and exits
non-zero rather than continuing.

Then the length reader. Before you use it in the walk, print what it returns for the four bytes
at offset 8 and satisfy yourself it is 13 and not 218103808 — that number is what a
little-endian machine reads when the bytes are taken in the wrong order, and recognising it on
sight will save you an hour at some point in your life.

Now the walk itself. Start at offset 8, read the length and type, print the contract line,
advance, and repeat. Decide explicitly what stops the loop, and write the bounds check before
you first run it against anything. Predict, before running it, what your program will do with
`assets/truncated.png`; run it and see whether you were right.

Finally, add the allocation report line in the contract shape, and run the checks: configure,
build, and the basic listing. When the listing check disagrees with you, read what it printed
carefully — it prints what it expected and what it got, and "got: `<no line matched>`" means
your line shape is wrong rather than your parser.

Run the program against `assets/text.png` too. It should list four chunks, and it needs no new
code: a walker that reads the framing does not care what a chunk means. That is worth noticing
now, because `11-the-finished-tool` will come back for what is inside that chunk.

## Completion conditions

- The `configure` validator passes: `cmake -S . -B build` succeeds from a clean checkout.
- The `build` validator passes: `cmake --build build` produces `build/pngdump`.
- The `dumps-basic-png` validator passes: the chunk listing for `assets/basic.png` matches the
  file exactly, in file order, with exit status 0 and no `error:` line.
- The program prints the allocation report line once, in the contract's shape.
- Deleting `build/` and running configure and build again reproduces the binary. The learner
  can say why that is safe and what would have been lost had they configured in-source.
- The learner can explain, from their own code: why the file is opened in binary mode; why the
  first chunk is at offset 8; how a length field is turned into a number without depending on
  the host's byte order, and why casting the buffer to `uint32_t *` would not do; how many
  bytes separate one chunk from the next and where that 12 comes from; and which condition
  ends their loop.
- The learner can point at every `return` between the `malloc` and the `free`, and say what
  happens to the buffer on each one — without yet being asked to fix anything.

## On completion, persist

In the instance's `STATE.md`: that the C walker is written and passes the basic listing; the
source layout chosen (file names under `src/`), how the file size is obtained, the names of
the byte-reading helpers (lesson 08 deletes them by name), and what ends the chunk loop. Note
that the allocation counts are maintained by hand at present.

In the instance's `DESIGN.md`: record the whole-file-in-memory decision as adopted
(`#whole-file-in-memory`), the fixed output contract (`#the-output-contract`), and the
out-of-source build directory `build/`. If the learner argued for a streaming parser, record
the argument and the reason the course declined it, so lesson 12 can return to it honestly.

## Optional deeper paths

Decode the `IHDR` payload — width, height, bit depth, colour type — and print it; the four
values are in the format reference and `assets/basic.png` is 8x8, bit depth 8, colour type 2.
Run the walker against `assets/badcrc.png` and notice it looks perfect, because nothing in the
program checks a checksum yet. Run it against a large PNG from your own machine and watch the
whole thing go into memory at once. Look at what `cmake -S . -B build` actually wrote: open
`build/CMakeCache.txt` and find the compiler it picked. Try a different generator with
`cmake -S . -B build -G Ninja` and see that `cmake --build build` is unchanged — that
indirection is the point of the configure step. Turn warnings up (`-Wall -Wextra`, or
`/W4` on MSVC) and read what your compiler already suspected about your code.
