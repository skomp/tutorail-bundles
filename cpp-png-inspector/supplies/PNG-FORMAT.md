# The PNG format, as much of it as this course needs

You will not have to open the PNG specification. Everything the inspector reads is on
this page.

## The file

```
89 50 4E 47 0D 0A 1A 0A        the 8-byte signature
<chunk>                        IHDR, always first
<chunk>                        ... any number of chunks ...
<chunk>                        IEND, always last, always empty
```

The first byte is `0x89` — deliberately not ASCII, so a file transfer that mangles
high bits is detectable. `PNG` follows, then a CRLF, a `^Z`, and an LF. A tool that
checks only `PNG` is not checking the signature.

## A chunk

Every chunk, without exception, has the same four fields:

```
+--------+--------+---------------------------+--------+
| length | type   | data                      | crc    |
| 4 B    | 4 B    | <length> bytes            | 4 B    |
+--------+--------+---------------------------+--------+
```

| Field | Notes |
|---|---|
| `length` | the size of **`data` only**. Not the type, not the CRC, not itself. A chunk therefore occupies `length + 12` bytes. |
| `type` | four ASCII letters. Case carries meaning (below), but for reading a file you can treat it as a four-character name. |
| `data` | `length` bytes. May be zero-length — `IEND` always is. |
| `crc` | CRC-32 of the **type and the data together**. Not of the length field. Getting this range wrong is the classic mistake, and it is why `badcrc.png` exists. |

**Every multi-byte integer in a PNG is big-endian**, most significant byte first. Your
machine is almost certainly little-endian, so every `length` and every `crc` needs its
bytes reversed on the way in. There is no exception anywhere in the format.

The offsets this course prints are the offset of a chunk's **length** field. The first
chunk is therefore always at offset 8.

### What the case of the type letters means

Each letter's fifth bit is a flag. You do not need this to walk a file, but it explains
why `tEXt` is spelled the way it is:

| Letter | Lower case means |
|---|---|
| 1st | ancillary — a decoder may ignore this chunk |
| 2nd | private — not defined by the standard |
| 3rd | reserved, always upper case in a valid file |
| 4th | safe to copy, even by an editor that does not understand it |

So `IHDR` is critical, public and unsafe to copy blindly; `tEXt` is ancillary, public and
safe to copy.

## The chunk types this course reports

| Type | What it is | What the inspector does with it |
|---|---|---|
| `IHDR` | the image header: width, height, bit depth, colour type, and three more bytes. Always 13 bytes, always first. | lists it; you may decode width and height if you want |
| `IDAT` | the compressed pixel data, possibly split across several chunks | lists its offset and size, and **never decompresses it** |
| `IEND` | the end marker. Always zero-length. | lists it and stops |
| `tEXt` | a keyword and a text value | lists it and prints both — see below |

Any other type is listed by name and length like the rest. A PNG in the wild will contain
`gAMA`, `pHYs`, `sRGB` and others; nothing in this course needs to know what they are, and
a parser that walks chunks correctly does not care.

## Inside a `tEXt` chunk

```
+------------------+----+------------------------------+
| keyword          | 00 | value                        |
| 1 to 79 bytes    |    | length - keylen - 1 bytes    |
+------------------+----+------------------------------+
```

The keyword is null-terminated. **The value is not.** It runs to the end of the chunk,
and its length is whatever the chunk's `length` field leaves over. This is the single
most useful trap on this page for a C programmer: reaching for `strlen` on the value
reads past the chunk, into whatever follows it.

## The CRC

The polynomial is the ordinary CRC-32 used by zip and gzip: `0xEDB88320` reflected, initial
value all ones, final value complemented. Lesson 11 supplies you with an implementation,
because writing one teaches bit manipulation rather than C++.

What you have to get right is the **range**: it covers the type field and the data, and
nothing else. Feed it `length` as well and every chunk in every file will look corrupt.

## The four files you were given

| File | What it is |
|---|---|
| `assets/basic.png` | an 8x8 truecolour image. Three chunks: `IHDR`, `IDAT`, `IEND`. |
| `assets/text.png` | the same image with a `tEXt` chunk between `IHDR` and `IDAT`. |
| `assets/truncated.png` | `basic.png` cut off part-way through its `IDAT` payload. The `IHDR` before it is intact and should still be reported. |
| `assets/badcrc.png` | `basic.png` with one bit flipped in `IHDR`'s stored CRC. Everything else about the file is correct. |
