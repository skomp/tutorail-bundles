# Design

Durable decisions about the inspector and about how this course teaches it. Each section
is a decision a later lesson depends on, and the paragraph headed *contradiction cost*
says what goes wrong if a lesson quietly decides otherwise.

## Whole file in memory {#whole-file-in-memory}

The tool reads the entire file into one owning buffer before it parses anything. It does
not stream, it does not `mmap`, and it does not read chunk headers and seek past payloads.

This is not the best design for a PNG inspector. A streaming inspector would use constant
memory and handle a file larger than RAM. It is the right design for *this course*,
because the buffer is the object every ownership lesson operates on: something is
allocated, something must free it, something wants to copy it, and something wants to
return it without copying it.

**Contradiction cost.** A streaming parser owns nothing large. Lesson 03 has no leak worth
a destructor, lesson 05 has no expensive copy to be alarmed by, and lesson 06 has no reason
for move semantics to exist. The whole of chapter 2 loses its motivation. If a learner
proposes streaming — and a good one will — the answer is that they are right about PNG
inspectors and that the course is buying something with the choice. Say what it is buying.

## The allocation counter {#the-allocation-counter}

Allocation is counted for the whole course by a counting wrapper the learner writes in
lesson 02: around `malloc` and `free` at first, and around `operator new` and
`operator delete` from lesson 03 onward. It stays in the program to the end.

It is the evidence for lessons 03, 05, 06, 10 and 12. In lesson 10 it is what catches a
missing virtual destructor — a leak with no visible symptom otherwise — but only under a
precondition that lesson has to arrange. Deleting a derived object through a non-virtual
base destructor still makes exactly one deallocation call, so the counts balance and the
counter sees nothing. The omission is observable only when the derived object owns a
*further* heap allocation whose destructor never runs: that allocation is never released
and the count goes positive. Lesson 10 therefore requires at least one handler to own heap
state, and lesson 12 runs the same experiment again once `std::unique_ptr` holds the
handlers.

A sanitizer would be the professional answer and is deliberately not used.
LeakSanitizer does not detect leaks on macOS, and valgrind does not run on Apple silicon,
so on a large share of learners' machines the check for lesson 02 would silently pass while
finding nothing. That is the worst failure available to a lesson whose entire job is to make
a leak visible. The counter behaves identically everywhere, and counting allocations is
itself the ownership discipline being taught.

Its weakness is worth naming to the learner when they ask: it counts, so it sees leaks and
double-frees, and it does not see a use-after-free at all.

**Contradiction cost.** Remove it, or replace it with a sanitizer, and five lessons lose
their completion condition on at least one common platform.

## Owning and borrowing {#owning-and-borrowing}

Exactly one type owns bytes. Everything that reads bytes borrows them through a non-owning
view — a pointer and a length — which copies freely, frees nothing, and must not outlive
what it points into.

The owning type appears in lesson 03. The view appears in lesson 07, and the separation is
the point of that lesson: the learner has just spent four lessons making a type that owns
correctly, and the next thing they need is a type that deliberately does not.

**Contradiction cost.** A view that owns reintroduces the double-free lesson 05 removed,
and forces every chunk handler in lesson 10 to hold a copy of its payload. A buffer that
does not own leaves nothing for the destructor to do.

## Errors are values {#errors-are-values}

Parse failures are returned as values carrying the byte offset that caused them. Nothing
sets a global, nothing returns `-1` as a sentinel, and the parser throws no exceptions.

Exceptions are **taught** in lesson 09 and not used. That is the decision, and teaching
them is half of it: a C programmer's first instinct is that exceptions are a costly foreign
thing to be avoided, and the useful correction is not "use them" but "understand what makes
them survivable". The answer is the destructor they wrote in lesson 03. An exception thrown
through a function holding an owning buffer does not leak, and that is the strongest
possible argument for RAII — made at the moment they can already see why.

The course then returns values anyway, for reasons a learner can weigh: an error carrying a
byte offset is data the caller wants, the control flow is visible at every call site, and a
parser's failures are expected rather than exceptional.

**Contradiction cost.** A lesson that throws makes every later function signature wrong and
lesson 09's exercise meaningless.

## Byte order in one place {#byte-order-in-one-place}

Every multi-byte field in a PNG is big-endian. The conversion from file order to host order
happens in exactly one place: inside the `read<T>()` template written in lesson 08.

**Contradiction cost.** Byte-swapping at call sites is the macro family lesson 08 exists to
delete, wearing a template's clothes. If the learner writes `read<T>` and then swaps bytes
outside it, the lesson has produced a generic function and taught nothing.

## Chunk data, chunk handlers {#chunk-data-vs-chunk-handlers}

A parsed chunk is a plain value: its offset, its type, its length, a view of its payload,
and its stored CRC. It is not a base class and it has no virtual functions.

Polymorphism lives in the **handlers** that interpret a chunk. A handler is an object with
a virtual method that is given a chunk value and reports on it, and the dispatch table maps
a four-character type to a handler.

This distinction is the substance of lesson 10, and it is the one most likely to be got
wrong, because "replace the switch with polymorphism" reads as "make the chunks
polymorphic". Both designs remove the switch. Only one of them is any good.

**Contradiction cost.** A hierarchy of chunk data types puts every chunk in the file on the
heap behind a base pointer. Lesson 12 then cannot replace the chunk list with a
`std::vector` of values, because the values are polymorphic and would slice — so the
arrival lesson ends in a `vector<unique_ptr<Chunk>>` and the course's closing argument is
lost.

## Hand-written, then replaced {#handwritten-then-replaced}

The owning buffer, the result type and the owning raw pointer are written by hand, and
lesson 12 replaces each with what the standard library offers. Two of them go outright:
`std::vector` for the buffer, `std::unique_ptr` for the pointer. The result type is the
partial case, and deliberately so — C++17 has no `std::expected`, and `std::optional`
carries no error payload, so it can replace only the returns that need to say "nothing
here". A failure that must carry a byte offset keeps a hand-written shape, and which shape
is a decision the learner argues rather than one this course dictates.

This is the shape of the course, not an accident of ordering, and it has to survive contact
with a learner who knows `std::vector` exists and asks why they are not using it. The answer
is direct: because you would not be able to read its interface yet. You are going to build
the problems it solves, and then throw your answers away for better ones.

**Contradiction cost.** A lesson that reaches for `std::vector` before lesson 12 removes the
reason lessons 03 to 06 exist. If a learner insists, the honest move is to let them use the
standard library for something *outside* the buffer — a `std::string` for a filename, a
`std::vector` for the handler list — and keep the buffer hand-written.

## The output contract {#the-output-contract}

The supplied check scripts read the tool's standard output, so three line shapes are fixed
for the whole course, and stated to the learner in `COURSE.md`:

- `<offset> <type> <length>` — one per chunk, in file order.
- `allocations: <n> frees: <m> outstanding: <k>` — the allocation report, printed at exit.
- `error: <message> at offset <n>` — one per problem found.

The checks match these three literally, so the spacing inside them is part of the shape
and not presentation. A chunk line is `^[0-9]+ [A-Za-z]{4} [0-9]+$` — a decimal offset,
one space, four letters, one space, a decimal length, with nothing before it and nothing
after it. Aligned columns, a leading space and a trailing space all fail to match;
zero-padded numbers do match the pattern but then fail `checks/expected/*.chunks`, which
the listing is compared against character for character. The allocation report is matched
the same way, single spaces and nothing trailing, and must be printed exactly once in a
run — the check reads one value and cannot read two. An error line is matched only on its
`error:` prefix in column one; the rest is read as text, so the message and the offset are
required by this contract rather than enforced by a pattern — with the one exception that
the bad-CRC check looks for the word CRC in it. The patterns live in `checks/_lib.sh`.

Everything else is the learner's: headers, colour, how text metadata is laid out, and any
other formatting printed as extra lines beside these three.

**Contradiction cost.** Every validator from `dumps-basic-png` to `no-leak-on-error-path`
reads these lines. A lesson that changes a shape breaks the checks of the lessons around it,
and the learner sees a failing check with no defect behind it — the most demoralising thing
a course can do. If a learner wants a different format, the answer is to add it beside these
lines, not instead of them.

## IDAT is out of scope {#idat-is-out-of-scope}

The tool reports `IDAT` chunks by offset and size and never decompresses them. No zlib, no
DEFLATE, no PNG filtering, no pixel data, no image output ever.

This is a scope boundary rather than a design preference, and it is in the coverage list so
that a learner who gets stuck trying to decode an image is told they have left the course
rather than coached through it.

**Contradiction cost.** Decompression pulls in a dependency the bundle cannot supply and a
second subject the course cannot teach in the space it has.

## Output modes beyond the listing {#json-output}

**Deliberately unresolved.** Whether the finished tool grows a machine-readable output mode
— JSON beside the human listing — is not decided, and no lesson depends on the answer.

It is recorded because it is the natural place a learner takes the tool after lesson 12,
and because it is where the lesson-10 decision gets argued a second time: a second output
format is exactly the pressure that makes a handler interface earn its keep. A learner who
proposes it after lesson 10 has understood the lesson. Note what they decided here if they
build it.
