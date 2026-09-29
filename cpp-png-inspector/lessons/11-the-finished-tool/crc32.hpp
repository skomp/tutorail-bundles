// CRC-32 for PNG chunks. Supplied by the course.
//
// You are not asked to write this. It is the ordinary CRC-32 that zip and gzip use,
// and implementing it teaches bit manipulation rather than C++ — a fine thing to learn
// somewhere other than lesson 11.
//
// What is yours to get right is the RANGE you hand it. A chunk's stored CRC covers the
// TYPE FIELD AND THE DATA, together, and nothing else. Not the length field that
// precedes them, and not the stored CRC itself.
//
//     png::crc32(chunk_start + 4, 4 + length)      // type (4 bytes) + data (length)
//
// See PNG-FORMAT.md, "The CRC".

#pragma once

#include <cstddef>
#include <cstdint>

namespace png {

inline std::uint32_t crc32(const unsigned char* data, std::size_t length) {
    static std::uint32_t table[256];
    static bool built = false;
    if (!built) {
        for (std::uint32_t i = 0; i < 256; ++i) {
            std::uint32_t c = i;
            for (int bit = 0; bit < 8; ++bit)
                c = (c & 1u) ? (0xEDB88320u ^ (c >> 1)) : (c >> 1);
            table[i] = c;
        }
        built = true;
    }
    std::uint32_t c = 0xFFFFFFFFu;
    for (std::size_t i = 0; i < length; ++i)
        c = table[(c ^ data[i]) & 0xFFu] ^ (c >> 8);
    return c ^ 0xFFFFFFFFu;
}

}  // namespace png
