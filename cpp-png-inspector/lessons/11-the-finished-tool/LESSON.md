---
id: 11-the-finished-tool
title: The finished tool
design_refs: [idat-is-out-of-scope, errors-are-values, the-output-contract]
validators: [build, tests, dumps-basic-png, reads-text-metadata, detects-bad-crc, rejects-truncated]
supplies:
  - from: lessons/11-the-finished-tool/crc32.hpp
    to: src/crc32.hpp
    describe: "A CRC32 implementation, supplied: writing one teaches bit manipulation, not C++. Getting the byte range you hand it right is still yours"
---

## Purpose

Finish the inspector: read the text a `tEXt` chunk carries, and check every chunk's stored
checksum against the bytes it actually covers.

## Prerequisites

Lessons `00-write-the-c-walker` through `10-chunks-without-switch` are complete. The tool
lists every chunk of a valid PNG, survives `assets/truncated.png` without crashing or
leaking, returns failures as values carrying a byte offset (`09-errors-without-errno`),
reads big-endian fields through `read<T>()` (`08-templates-eat-the-macros`), reads bytes
through a bounds-checked non-owning view (`07-bounds-you-cannot-skip`), and dispatches to
handler objects rather than switching on a chunk type (`10-chunks-without-switch`).

`src/crc32.hpp` is placed in the workspace when this lesson opens. It is supplied and is
not yours to edit. `PNG-FORMAT.md` has been in the workspace since before lesson 00 and
documents both of this lesson's subjects.

## Learning objectives

- Read a field whose length comes from its framing rather than from a terminator, and
  compute that length correctly
- Say why a C string function is the wrong tool for such a field, and what it does when
  used anyway
- Validate a checksum over a byte range defined by a format, and state that range exactly
- Distinguish a finding that stops the parse from one that is merely reported, and carry
  the difference out to the process exit status
- Use supplied code correctly, including knowing which part of the problem it did not solve
- Say where the tool's scope ends, and why `IDAT` is walked past rather than decoded

## Theory

The tool can say what is in a file and where. It cannot yet say what the file *says*, and
it cannot say whether anything in it is damaged. Both gaps are one lesson's work, and both
turn on the same discipline: a binary format tells you where a field ends, and you believe
the format rather than a convention borrowed from somewhere else.

### The field that does not end where you think

A `tEXt` chunk's payload is a keyword, a zero byte, and a value:

```
| keyword (1-79 bytes) | 00 | value (to the end of the chunk) |
```

The keyword is NUL-terminated. **The value is not.** It runs to the end of the chunk, and
nothing in the bytes marks where it stops. Its length is arithmetic:

    value length = chunk length - keyword length - 1

This is the difference between a C string and a field in a binary format. In C, a string's
length is a property of its *contents* — you find the end by looking for the terminator. In
a framed format, a field's length is a property of its *framing* — the chunk's length field
is the only thing in the file that knows where the value ends. `strlen` on that value does
not answer a question about the value at all. It walks forward out of the chunk, through
the chunk's CRC and the next chunk's length field, through whatever binary follows, until
it happens to meet a zero byte — and in a compressed `IDAT` payload it may not meet one for
a long time, or before the end of the buffer.

The bounds-checked view from `07-bounds-you-cannot-skip` is what stands between that
mistake and a read off the end of the buffer, and it is worth noticing that this is the
lesson where it pays for itself. A read through the view that runs past the payload is
caught and reported; the same read through a raw `char*` is not.

The same trap comes back at the moment you print. Handing a non-terminated value to
anything that prints a C string is the identical bug in a second costume: you must print
exactly the number of bytes you computed, not "until the zero".

Two malformed shapes are possible and both are the file's fault, not a reason to crash:
a payload with no zero byte anywhere in it (so there is no keyword terminator), and a zero
byte at the very last position (so the value is empty, which is legal). Locate the
terminator **within the payload only**. A search that is allowed to run past the payload
has already lost.

How you lay the keyword and value out on screen is yours — `#the-output-contract` fixes
three line shapes and nothing else. What is not yours is the content: the keyword and the
value must appear in the output exactly as the file spells them, unabbreviated and
unescaped, and the chunk's own listing line must stay as it was.

### The checksum, and the range it covers

Every chunk carries a CRC-32 of its own contents, so a reader can tell that the bytes it
just read are the bytes that were written. That is all a CRC does: it detects accidental
corruption — a flipped bit, a truncated transfer, a file copied through something that
mangled it. It is not a signature and it defends against nobody. Anyone who changes a chunk
on purpose recomputes the CRC.

The course hands you the implementation. `src/crc32.hpp` appears in your workspace when
this lesson opens and gives you `png::crc32(const unsigned char*, std::size_t)`. Writing
one yourself is a genuine exercise in bit manipulation and table generation, and it teaches
nothing whatever about C++ — so it would be forty minutes stolen from this lesson's actual
subject. Do not edit the file, and do not reimplement what it does.

What is emphatically still yours is the **range**. A chunk's stored CRC covers the **type
field and the data, together, and nothing else**:

```
+--------+--------+---------------------------+--------+
| length | type   | data                      | crc    |
|        |<------ the CRC covers this ------->|        |
+--------+--------+---------------------------+--------+
```

Not the length field that precedes the type, and not the stored CRC itself. The type and
the data are contiguous in the file, so the range is one pointer and one length — which is
exactly the shape of the borrowed view you already have.

Get the range wrong and the symptom is characteristic and misleading: *every* chunk in
*every* file fails, including files that are perfectly good. It reads like a broken CRC
implementation and it is not; it is four bytes of input that should not be there. The two
checks in this lesson pull in opposite directions on purpose — `dumps-basic-png` requires
`assets/basic.png` to produce no `error:` line at all and exit 0, while `detects-bad-crc`
requires `assets/badcrc.png` to produce one that mentions the CRC and exit non-zero. Only a
correct range satisfies both. `assets/badcrc.png` is `basic.png` with a single bit flipped
in `IHDR`'s stored CRC and nothing else altered, so it is a direct test of the comparison
and of nothing else.

The stored CRC is a four-byte big-endian integer like every other multi-byte field in the
format, so it is read through `read<T>()` (`#byte-order-in-one-place`) and compared as a
number. Comparing raw bytes in file order against a host-order result is a way to fail on
one kind of machine only.

One more thing the range demands: never compute a CRC over bytes you do not have. On
`assets/truncated.png` the final chunk's length field promises more data than the file
contains. The length is not evidence that the bytes exist. Check that the whole of the type
and data range lies inside the file before hashing any of it, and report the truncation
instead.

### Which problems stop the walk, and which are reported

`#errors-are-values` has held since `09-errors-without-errno`: failures are returned as
values carrying the byte offset that caused them. This lesson makes you sort those values
into two kinds, and the sorting is a design decision you should be able to defend.

A **bad CRC is a finding about the file**. The framing is intact — you know the chunk's
length, so you know where the next chunk begins — so the walk can continue and report every
damaged chunk rather than only the first. A **truncated file stops the walk**: the next
chunk's position is unknown, and there is nothing further to read.

Both must reach the exit status, which is a one-bit summary of everything the run found.
The mechanism that carries "something was wrong" from deep in the parse back out to `main`
is the result type you already built, or a count kept beside it — not a global, and not a
`-1` slipped back in at the end. Whatever the tool reports as an `error:` line it must also
reflect in its exit status; a tool that prints a problem and exits 0 has told a script
nothing.

### Where the tool stops

`IDAT` holds the compressed pixel data, and this tool reports its offset and its size and
walks past it. It never decompresses anything: no zlib, no DEFLATE, no PNG filtering, no
pixel data, ever (`#idat-is-out-of-scope`). This is a scope boundary rather than an
oversight — decoding an image is a different subject and a dependency this course does not
carry. A PNG may also split its pixel data across several `IDAT` chunks, which is normal;
the tool lists each of them.

With `tEXt` read and CRCs checked, the inspector is finished. Everything after this lesson
is about replacing what it is built from, not about what it does.

## Concepts to teach

Length-delimited fields versus NUL-terminated strings, and computing a field's length by
subtraction from its framing. Why `strlen` and friends are the wrong tool for a value that
runs to a chunk boundary, and exactly what they read when used. Printing a counted range of
bytes rather than a C string. Locating a terminator within a bounded view. What a CRC is
for and what it is not — accidental corruption, not tampering. Checksum range as part of a
format's contract, and the misleading symptom of getting it wrong. Reading the stored CRC
as a big-endian integer through `read<T>()` and comparing numerically. Refusing to hash
bytes the file does not contain. Fatal versus reported findings, and the exit status as a
summary (`#errors-are-values`). Using supplied code and knowing precisely which part of the
problem it did not solve. The scope boundary at `IDAT` (`#idat-is-out-of-scope`).

## Constraints

- No C string function — `strlen`, `strcpy`, `strdup`, `printf("%s")` or any relative —
  is applied to a `tEXt` value. Its length is computed from the chunk's length field.
- The keyword's terminator is located inside the payload only. A payload with no
  terminator is reported as an error with its offset, not read past and not crashed on.
- The keyword and the value are read through the borrowed view (`#owning-and-borrowing`).
  They are not copied into storage the handler owns.
- `tEXt` support is added as a new handler class in the `10-chunks-without-switch`
  interface. No existing function grows a branch on chunk type.
- CRC validation is **not** per-type, so it does not belong in a handler. It applies to
  every chunk and belongs in the walk, before dispatch. Not everything is a handler.
- `src/crc32.hpp` is supplied and must not be edited, replaced or reimplemented.
- The CRC is computed over the type field and the data together and nothing else, and only
  after confirming that whole range is present in the file.
- The stored CRC is read as a big-endian integer through `read<T>()` and compared as a
  number.
- No decompression of any kind, and no new third-party dependency
  (`#idat-is-out-of-scope`).
- The three fixed line shapes are unchanged (`#the-output-contract`): the chunk lines for
  `assets/basic.png` and `assets/text.png` are exactly what the files contain, error lines
  begin `error:` and name a byte offset, and the allocation report still prints at exit and
  still balances.
- A run that reports any `error:` line exits non-zero; a run that reports none exits 0.
- The hand-written buffer, view and result type stay hand-written
  (`#handwritten-then-replaced`). `12-it-was-in-the-box` is where they go.

## Suggested progression

Run the tool on `assets/text.png` first and look at what it says. The `tEXt` chunk is
listed like any other and nothing is said about its contents. Open `PNG-FORMAT.md` at the
`tEXt` section, and before writing anything, say how you would find where the keyword ends
and where the value ends — they are not found the same way, and noticing that is the whole
first half of this lesson.

Write the `tEXt` handler as a new class against the lesson-10 interface, and confirm as you
do that you are editing no existing function. Get the keyword out first; it is terminated
and behaves the way you expect. Then the value. Print both, and run `reads-text-metadata`.

Before moving on, write a test with a hand-built payload that has no zero byte in it at
all, and one whose zero byte is the last byte. Both must produce a defined outcome — an
error with an offset, or an empty value — and neither may read outside the payload.

Now open `src/crc32.hpp` and read the comment at the top of it; the file tells you what it
is and what it leaves to you. Start narrow: compute the CRC of a single chunk of
`assets/basic.png` in a test and compare it with the value stored in that chunk. If it does
not match, the range is the first thing to suspect and the implementation is the last —
work out on paper which bytes you passed and which bytes the format says are covered.

With one chunk verified, extend it: a test that walks a valid file and asserts every stored
CRC matches, and a test over a small hand-built chunk whose bytes you control. Then wire
the check into the walk for every chunk, and run `dumps-basic-png` — it must stay silent —
followed by `detects-bad-crc`, which must not.

Decide what each kind of problem does to the walk and to the exit status, and make the two
consistent. Re-run `rejects-truncated` and confirm three things at once: `8 IHDR 13` is
still listed, an `error:` line is reported, the exit status is non-zero — and that nothing
tried to hash the bytes the truncated chunk claims but does not have.

Finish with the full sweep: `build`, `tests`, `dumps-basic-png`, `reads-text-metadata`,
`detects-bad-crc` and `rejects-truncated`.

## Completion conditions

- `build`, `tests`, `dumps-basic-png`, `reads-text-metadata`, `detects-bad-crc` and
  `rejects-truncated` all pass.
- `assets/text.png` lists its four chunks exactly, exits 0, reports no error, and prints
  both the keyword and the value of its `tEXt` chunk in full.
- `assets/badcrc.png` produces an `error:` line naming the CRC and the offset of the chunk
  that failed, and a non-zero exit status.
- `assets/basic.png` still produces no error line and exits 0 — the evidence that the CRC
  range is right rather than merely strict.
- `assets/truncated.png` still lists `8 IHDR 13`, reports an error, exits non-zero, does
  not die on a signal, and computes no CRC over bytes that are not in the file.
- The learner can state, without looking it up, that the `tEXt` value has no terminator and
  how its length is derived, and can say what `strlen` would have read instead.
- The learner can state the CRC's byte range exactly, and describe the symptom of including
  the length field.
- The learner can say which findings stop the walk and which do not, and why, and how the
  distinction reaches the exit status.
- The learner can say what `src/crc32.hpp` solved for them and which part of the problem it
  did not.
- A malformed `tEXt` payload is handled as a reported error rather than undefined
  behaviour, demonstrated by a test.

## On completion, persist

Record in the instance's `DESIGN.md`: that a bad CRC is reported and the walk continues
while a truncation stops it, the rule the tool uses for its exit status, where CRC
validation sits in the walk and why it is not a handler, and the note that
`png::crc32(type_start, 4 + length)` is the range — written down because it is the thing a
future session is most likely to get wrong again.

Record in `STATE.md` that milestone M4 is reached: the inspector is complete — it lists
chunks, reads text metadata, validates checksums and reports truncation without crashing or
leaking. Note that `src/crc32.hpp` is supplied and not learner-owned, so nothing later in
the course should propose changing it. Note also anything the learner decided about output
layout, since `12-it-was-in-the-box` must not disturb it.

## Optional deeper paths

Look at `zTXt` and `iTXt`, the compressed and Unicode relatives of `tEXt`, and work out why
this course stops at `tEXt` — the answer is the same dependency that keeps `IDAT` out of
scope. Notice that the zlib stream inside an `IDAT` chunk carries an Adler-32 of its own,
a different checksum at a different layer, and say what each one protects. Ask what a
CRC-32 does not detect and why a checksum is not a message authentication code. Decode the
thirteen bytes of `IHDR` into width, height, bit depth and colour type, purely as an
exercise in reading a fixed layout. Read the case-bit table in `PNG-FORMAT.md` again and
work out what a decoder should do with an unknown chunk whose first letter is lower case
versus upper case. Finally, look at `#json-output` in the course's `DESIGN.md`: a second
output format is the pressure that makes the lesson-10 handler interface earn its keep, and
it is deliberately left undecided for you to argue.
