/*
 * ps2_set2_to_hid.h — PS/2 scan code set 2 to USB HID usage translation.
 *
 * Supplied by the course. This is the rest of the table you started in lesson 10.
 *
 * In lesson 10 you derived roughly ten entries from your own captures, because that
 * is where the method is learnt: press a key, read the frame off the trace, look the
 * usage up in the HID Usage Tables, write the row. Doing that another hundred and
 * twenty times teaches nothing it has not already taught. So the bundle ships the
 * rest, and lesson 14 — the first lesson that needs the whole keyboard — is where it
 * arrives.
 *
 * Check a handful of these against the entries you derived yourself before you trust
 * any of them. If one of yours disagrees with one of these, find out which is wrong
 * before you move on; that disagreement is more interesting than either table.
 *
 * ---------------------------------------------------------------------------
 * WHAT IS IN HERE
 *
 *   ps2_set2_make[]     — single-byte make codes
 *   ps2_set2_make_e0[]  — make codes that arrived after an 0xE0 prefix
 *
 * Both are 256 entries. An entry with usage 0 and name NULL is a code this table
 * does not map; treat one as unknown rather than as key 0.
 *
 * Usage IDs are from HID Usage Tables, page 0x07 (Keyboard/Keypad). Those are the
 * values that go into the six-key array and, for 0xE0-0xE7, into the modifier byte
 * of your 8-byte boot report.
 *
 * ---------------------------------------------------------------------------
 * WHAT IS *NOT* IN HERE, AND WHY
 *
 * 1. Break codes. Set 2 signals a release with the prefix 0xF0 followed by the make
 *    code — the SAME make code, unchanged. So there is nothing to look up: 0xF0 sets
 *    a flag, the next byte goes through the table as usual, and the flag decides
 *    whether the event is a down or an up.
 *
 *    Set 2 does NOT set bit 7 of the make code to mean release. That is scan code
 *    set 1. A decoder written for set 1 behaviour on a set 2 keyboard mangles every
 *    key whose make code already has bit 7 set — F7 (0x83), Alt+PrintScreen (0x84),
 *    and the Korean keys — and works perfectly on everything else, which is exactly
 *    what makes it hard to find.
 *
 * 2. Pause and Print Screen. They are sequences, not codes, and no byte-indexed
 *    table can express them. See the block comment above ps2_set2_make_e0[].
 *
 * 3. The multimedia and ACPI keys (E0 4D next track, E0 32 volume up, E0 3F sleep,
 *    and the rest). They are not on a Model M, and more to the point they are not on
 *    HID page 0x07 at all — they live on the Consumer page (0x0C) and the Generic
 *    Desktop page (0x01), which your boot keyboard report cannot carry. Reporting
 *    them needs a second interface or a second report, and that is out of scope.
 *    E0 37 Power is the one exception: HID page 0x07 does define a Power usage
 *    (0x66), so it is in the table.
 *
 * ---------------------------------------------------------------------------
 * USING THE TABLE
 *
 * The table is data. Turning a byte stream into events — holding the 0xF0 and 0xE0
 * flags across bytes, resetting them on an idle timeout, deciding what to do with a
 * code that maps to nothing — is lesson 10's work and stays yours.
 *
 * These arrays are `static const`, so a translation unit that includes this header
 * gets its own copy. That is a few hundred bytes of flash and it keeps the header
 * self-contained; if you would rather have one copy, move the definitions into a .c
 * file and leave `extern` declarations here.
 */

#ifndef PS2_SET2_TO_HID_H
#define PS2_SET2_TO_HID_H

#include <stdint.h>

#if defined(__GNUC__)
#define PS2_TABLE_ATTR __attribute__((unused))
#else
#define PS2_TABLE_ATTR
#endif

/* ------------------------------------------------------------------------- */
/* HID Usage IDs, Usage Page 0x07 (Keyboard/Keypad)                          */
/* ------------------------------------------------------------------------- */

/* Reserved usages. 0x01 is the one your overflow report needs. */
#define HID_KEY_NONE            0x00
#define HID_KEY_ERROR_ROLLOVER  0x01  /* all six array slots on >6KRO overflow */
#define HID_KEY_POST_FAIL       0x02
#define HID_KEY_ERROR_UNDEFINED 0x03

#define HID_KEY_A               0x04
#define HID_KEY_B               0x05
#define HID_KEY_C               0x06
#define HID_KEY_D               0x07
#define HID_KEY_E               0x08
#define HID_KEY_F               0x09
#define HID_KEY_G               0x0A
#define HID_KEY_H               0x0B
#define HID_KEY_I               0x0C
#define HID_KEY_J               0x0D
#define HID_KEY_K               0x0E
#define HID_KEY_L               0x0F
#define HID_KEY_M               0x10
#define HID_KEY_N               0x11
#define HID_KEY_O               0x12
#define HID_KEY_P               0x13
#define HID_KEY_Q               0x14
#define HID_KEY_R               0x15
#define HID_KEY_S               0x16
#define HID_KEY_T               0x17
#define HID_KEY_U               0x18
#define HID_KEY_V               0x19
#define HID_KEY_W               0x1A
#define HID_KEY_X               0x1B
#define HID_KEY_Y               0x1C
#define HID_KEY_Z               0x1D

#define HID_KEY_1               0x1E
#define HID_KEY_2               0x1F
#define HID_KEY_3               0x20
#define HID_KEY_4               0x21
#define HID_KEY_5               0x22
#define HID_KEY_6               0x23
#define HID_KEY_7               0x24
#define HID_KEY_8               0x25
#define HID_KEY_9               0x26
#define HID_KEY_0               0x27

#define HID_KEY_ENTER           0x28
#define HID_KEY_ESCAPE          0x29
#define HID_KEY_BACKSPACE       0x2A
#define HID_KEY_TAB             0x2B
#define HID_KEY_SPACE           0x2C
#define HID_KEY_MINUS           0x2D  /* - _ */
#define HID_KEY_EQUAL           0x2E  /* = + */
#define HID_KEY_LEFT_BRACKET    0x2F  /* [ { */
#define HID_KEY_RIGHT_BRACKET   0x30  /* ] } */
#define HID_KEY_BACKSLASH       0x31  /* \ | on an ANSI board */
#define HID_KEY_NON_US_HASH     0x32  /* # ~ on an ISO board — see the 0x5D note */
#define HID_KEY_SEMICOLON       0x33  /* ; : */
#define HID_KEY_QUOTE           0x34  /* ' " */
#define HID_KEY_GRAVE           0x35  /* ` ~ */
#define HID_KEY_COMMA           0x36  /* , < */
#define HID_KEY_PERIOD          0x37  /* . > */
#define HID_KEY_SLASH           0x38  /* / ? */
#define HID_KEY_CAPS_LOCK       0x39

#define HID_KEY_F1              0x3A
#define HID_KEY_F2              0x3B
#define HID_KEY_F3              0x3C
#define HID_KEY_F4              0x3D
#define HID_KEY_F5              0x3E
#define HID_KEY_F6              0x3F
#define HID_KEY_F7              0x40
#define HID_KEY_F8              0x41
#define HID_KEY_F9              0x42
#define HID_KEY_F10             0x43
#define HID_KEY_F11             0x44
#define HID_KEY_F12             0x45

#define HID_KEY_PRINT_SCREEN    0x46
#define HID_KEY_SCROLL_LOCK     0x47
#define HID_KEY_PAUSE           0x48
#define HID_KEY_INSERT          0x49
#define HID_KEY_HOME            0x4A
#define HID_KEY_PAGE_UP         0x4B
#define HID_KEY_DELETE          0x4C
#define HID_KEY_END             0x4D
#define HID_KEY_PAGE_DOWN       0x4E
#define HID_KEY_ARROW_RIGHT     0x4F
#define HID_KEY_ARROW_LEFT      0x50
#define HID_KEY_ARROW_DOWN      0x51
#define HID_KEY_ARROW_UP        0x52

#define HID_KEY_NUM_LOCK        0x53
#define HID_KEY_KEYPAD_SLASH    0x54
#define HID_KEY_KEYPAD_ASTERISK 0x55
#define HID_KEY_KEYPAD_MINUS    0x56
#define HID_KEY_KEYPAD_PLUS     0x57
#define HID_KEY_KEYPAD_ENTER    0x58
#define HID_KEY_KEYPAD_1        0x59
#define HID_KEY_KEYPAD_2        0x5A
#define HID_KEY_KEYPAD_3        0x5B
#define HID_KEY_KEYPAD_4        0x5C
#define HID_KEY_KEYPAD_5        0x5D
#define HID_KEY_KEYPAD_6        0x5E
#define HID_KEY_KEYPAD_7        0x5F
#define HID_KEY_KEYPAD_8        0x60
#define HID_KEY_KEYPAD_9        0x61
#define HID_KEY_KEYPAD_0        0x62
#define HID_KEY_KEYPAD_PERIOD   0x63

#define HID_KEY_NON_US_BACKSLASH 0x64 /* the extra key on a 102-key ISO board */
#define HID_KEY_APPLICATION     0x65  /* the "menu" key */
#define HID_KEY_POWER           0x66

/* International and language keys. Not present on a US or UK Model M; included so
 * that a learner who plugs in a JIS or Korean PS/2 board is not stuck. These rows
 * come from the published HID/PS-2 translation tables, not from a capture taken for
 * this course — verify against your own hardware before relying on them. */
#define HID_KEY_INTERNATIONAL1  0x87  /* JIS  \ _  (Ro)            */
#define HID_KEY_INTERNATIONAL2  0x88  /* JIS  Katakana/Hiragana    */
#define HID_KEY_INTERNATIONAL3  0x89  /* JIS  Yen                  */
#define HID_KEY_INTERNATIONAL4  0x8A  /* JIS  Henkan               */
#define HID_KEY_INTERNATIONAL5  0x8B  /* JIS  Muhenkan             */
#define HID_KEY_LANG1           0x90  /* Korean Hangul/English     */
#define HID_KEY_LANG2           0x91  /* Korean Hanja              */
#define HID_KEY_LANG3           0x92  /* JIS Katakana              */
#define HID_KEY_LANG4           0x93  /* JIS Hiragana              */

/* Modifiers. These are ordinary HID usages, but they do NOT go in the six-key
 * array — they go in the modifier byte, and putting one in the array instead is a
 * bug the host will render as a key that types nothing. Usage 0xE0 + n is modifier
 * bit n:
 *
 *   bit 0  LeftControl    bit 4  RightControl
 *   bit 1  LeftShift      bit 5  RightShift
 *   bit 2  LeftAlt        bit 6  RightAlt
 *   bit 3  LeftGUI        bit 7  RightGUI
 */
#define HID_KEY_CONTROL_LEFT    0xE0
#define HID_KEY_SHIFT_LEFT      0xE1
#define HID_KEY_ALT_LEFT        0xE2
#define HID_KEY_GUI_LEFT        0xE3
#define HID_KEY_CONTROL_RIGHT   0xE4
#define HID_KEY_SHIFT_RIGHT     0xE5
#define HID_KEY_ALT_RIGHT       0xE6
#define HID_KEY_GUI_RIGHT       0xE7

/* ------------------------------------------------------------------------- */

typedef struct {
    uint8_t     usage; /* HID usage ID on page 0x07; 0 means "not mapped" */
    const char *name;  /* readable name, or NULL; this is what `key:` lines print */
} ps2_hid_key_t;

/* ------------------------------------------------------------------------- */
/* Single-byte make codes.                                                    */
/*                                                                            */
/* Indexed by the scan code byte itself, with no prefix. Preceded by 0xF0 the  */
/* same byte is a release of the same key.                                     */
/* ------------------------------------------------------------------------- */

static const ps2_hid_key_t ps2_set2_make[256] PS2_TABLE_ATTR = {
    /* function row -------------------------------------------------------- */
    [0x76] = { HID_KEY_ESCAPE,          "Escape"       },
    [0x05] = { HID_KEY_F1,              "F1"           },
    [0x06] = { HID_KEY_F2,              "F2"           },
    [0x04] = { HID_KEY_F3,              "F3"           },
    [0x0C] = { HID_KEY_F4,              "F4"           },
    [0x03] = { HID_KEY_F5,              "F5"           },
    [0x0B] = { HID_KEY_F6,              "F6"           },
    [0x83] = { HID_KEY_F7,              "F7"           },
    [0x0A] = { HID_KEY_F8,              "F8"           },
    [0x01] = { HID_KEY_F9,              "F9"           },
    [0x09] = { HID_KEY_F10,             "F10"          },
    [0x78] = { HID_KEY_F11,             "F11"          },
    [0x07] = { HID_KEY_F12,             "F12"          },
    [0x7E] = { HID_KEY_SCROLL_LOCK,     "ScrollLock"   },
    /* Alt + PrintScreen. The keyboard sends this single byte instead of the
     * E0 12 E0 7C sequence, and it is a code with bit 7 already set — which is
     * why a set-1-style "bit 7 means release" decoder breaks here first. */
    [0x84] = { HID_KEY_PRINT_SCREEN,    "SysReq"       },

    /* number row ---------------------------------------------------------- */
    [0x0E] = { HID_KEY_GRAVE,           "Grave"        },
    [0x16] = { HID_KEY_1,               "1"            },
    [0x1E] = { HID_KEY_2,               "2"            },
    [0x26] = { HID_KEY_3,               "3"            },
    [0x25] = { HID_KEY_4,               "4"            },
    [0x2E] = { HID_KEY_5,               "5"            },
    [0x36] = { HID_KEY_6,               "6"            },
    [0x3D] = { HID_KEY_7,               "7"            },
    [0x3E] = { HID_KEY_8,               "8"            },
    [0x46] = { HID_KEY_9,               "9"            },
    [0x45] = { HID_KEY_0,               "0"            },
    [0x4E] = { HID_KEY_MINUS,           "Minus"        },
    [0x55] = { HID_KEY_EQUAL,           "Equal"        },
    [0x66] = { HID_KEY_BACKSPACE,       "Backspace"    },

    /* letters and the rest of the alphanumeric block ----------------------- */
    [0x0D] = { HID_KEY_TAB,             "Tab"          },
    [0x15] = { HID_KEY_Q,               "Q"            },
    [0x1D] = { HID_KEY_W,               "W"            },
    [0x24] = { HID_KEY_E,               "E"            },
    [0x2D] = { HID_KEY_R,               "R"            },
    [0x2C] = { HID_KEY_T,               "T"            },
    [0x35] = { HID_KEY_Y,               "Y"            },
    [0x3C] = { HID_KEY_U,               "U"            },
    [0x43] = { HID_KEY_I,               "I"            },
    [0x44] = { HID_KEY_O,               "O"            },
    [0x4D] = { HID_KEY_P,               "P"            },
    [0x54] = { HID_KEY_LEFT_BRACKET,    "LeftBracket"  },
    [0x5B] = { HID_KEY_RIGHT_BRACKET,   "RightBracket" },
    /* On an ANSI (101/104-key) board 0x5D is the backslash key above Enter.
     * On an ISO (102-key) board the very same code comes from the # / ~ key
     * beside Enter, which is HID usage 0x32 (NonUSHash). One code, two keys,
     * and the keyboard does not tell you which layout it is. If yours is a
     * 102-key Model M, change this one row to HID_KEY_NON_US_HASH. */
    [0x5D] = { HID_KEY_BACKSLASH,       "Backslash"    },

    [0x58] = { HID_KEY_CAPS_LOCK,       "CapsLock"     },
    [0x1C] = { HID_KEY_A,               "A"            },
    [0x1B] = { HID_KEY_S,               "S"            },
    [0x23] = { HID_KEY_D,               "D"            },
    [0x2B] = { HID_KEY_F,               "F"            },
    [0x34] = { HID_KEY_G,               "G"            },
    [0x33] = { HID_KEY_H,               "H"            },
    [0x3B] = { HID_KEY_J,               "J"            },
    [0x42] = { HID_KEY_K,               "K"            },
    [0x4B] = { HID_KEY_L,               "L"            },
    [0x4C] = { HID_KEY_SEMICOLON,       "Semicolon"    },
    [0x52] = { HID_KEY_QUOTE,           "Quote"        },
    [0x5A] = { HID_KEY_ENTER,           "Enter"        },

    /* The extra key between LeftShift and Z on a 102-key ISO board. Absent on
     * an ANSI board, which simply never sends 0x61. */
    [0x61] = { HID_KEY_NON_US_BACKSLASH, "NonUSBackslash" },
    [0x1A] = { HID_KEY_Z,               "Z"            },
    [0x22] = { HID_KEY_X,               "X"            },
    [0x21] = { HID_KEY_C,               "C"            },
    [0x2A] = { HID_KEY_V,               "V"            },
    [0x32] = { HID_KEY_B,               "B"            },
    [0x31] = { HID_KEY_N,               "N"            },
    [0x3A] = { HID_KEY_M,               "M"            },
    [0x41] = { HID_KEY_COMMA,           "Comma"        },
    [0x49] = { HID_KEY_PERIOD,          "Period"       },
    [0x4A] = { HID_KEY_SLASH,           "Slash"        },
    [0x29] = { HID_KEY_SPACE,           "Space"        },

    /* modifiers ----------------------------------------------------------- */
    /* Only the LEFT modifiers and the right shift are unprefixed. The right
     * control, the right alt and both GUI keys are 0xE0-prefixed — they were
     * added to the layout after set 2 was defined, and there were no single
     * bytes left. */
    [0x14] = { HID_KEY_CONTROL_LEFT,    "LeftControl"  },
    [0x12] = { HID_KEY_SHIFT_LEFT,      "LeftShift"    },
    [0x11] = { HID_KEY_ALT_LEFT,        "LeftAlt"      },
    [0x59] = { HID_KEY_SHIFT_RIGHT,     "RightShift"   },

    /* keypad -------------------------------------------------------------- */
    /* Note that the keypad digits share no bytes with the number row, and that
     * NumLock (0x77) is a key in its own right — the Num Lock *state* lives in
     * the host, not in the adapter, and this table must not try to be clever
     * about it. Keypad5 with Num Lock off is still Keypad5 on the wire. */
    [0x77] = { HID_KEY_NUM_LOCK,        "NumLock"      },
    [0x7C] = { HID_KEY_KEYPAD_ASTERISK, "KeypadAsterisk" },
    [0x7B] = { HID_KEY_KEYPAD_MINUS,    "KeypadMinus"  },
    [0x79] = { HID_KEY_KEYPAD_PLUS,     "KeypadPlus"   },
    [0x71] = { HID_KEY_KEYPAD_PERIOD,   "KeypadPeriod" },
    [0x70] = { HID_KEY_KEYPAD_0,        "Keypad0"      },
    [0x69] = { HID_KEY_KEYPAD_1,        "Keypad1"      },
    [0x72] = { HID_KEY_KEYPAD_2,        "Keypad2"      },
    [0x7A] = { HID_KEY_KEYPAD_3,        "Keypad3"      },
    [0x6B] = { HID_KEY_KEYPAD_4,        "Keypad4"      },
    [0x73] = { HID_KEY_KEYPAD_5,        "Keypad5"      },
    [0x74] = { HID_KEY_KEYPAD_6,        "Keypad6"      },
    [0x6C] = { HID_KEY_KEYPAD_7,        "Keypad7"      },
    [0x75] = { HID_KEY_KEYPAD_8,        "Keypad8"      },
    [0x7D] = { HID_KEY_KEYPAD_9,        "Keypad9"      },

    /* international — not on a Model M, see the note above ----------------- */
    [0x51] = { HID_KEY_INTERNATIONAL1,  "International1" },
    [0x13] = { HID_KEY_INTERNATIONAL2,  "International2" },
    [0x6A] = { HID_KEY_INTERNATIONAL3,  "International3" },
    [0x64] = { HID_KEY_INTERNATIONAL4,  "International4" },
    [0x67] = { HID_KEY_INTERNATIONAL5,  "International5" },
    [0x63] = { HID_KEY_LANG3,           "Lang3"          },
    [0x62] = { HID_KEY_LANG4,           "Lang4"          },
    /* 0xF1 and 0xF2 are real make codes on a Korean keyboard, and they sit one
     * and two above the 0xF0 break prefix. Nothing about that is ambiguous —
     * 0xF0 0xF2 is a release of Lang1 — but a decoder that special-cases "any
     * byte in the 0xF0 range" instead of exactly 0xF0 will eat them. */
    [0xF2] = { HID_KEY_LANG1,           "Lang1"          },
    [0xF1] = { HID_KEY_LANG2,           "Lang2"          },
};

/* ------------------------------------------------------------------------- */
/* Make codes that arrived after an 0xE0 prefix.                              */
/*                                                                            */
/* Index this table with the byte that FOLLOWED the 0xE0. A release is         */
/* 0xE0 0xF0 <code> — note the order: the extended prefix comes first, the     */
/* break prefix second. A decoder that expects 0xF0 0xE0 will resynchronise    */
/* on every release of an arrow key and look, for a while, like a wiring       */
/* fault.                                                                      */
/*                                                                            */
/* ---- The two codes that are not keys ----                                   */
/*                                                                            */
/* E0 12 and E0 59 are "fake shifts". The keyboard injects them around the     */
/* extended navigation and keypad keys so that a 1984 BIOS would compute the   */
/* right character — for example, with Num Lock on and a real shift held,      */
/* pressing Insert sends E0 F0 12 E0 70 rather than E0 70 alone. They are an   */
/* artefact of the keyboard's own compatibility logic and they correspond to   */
/* no physical key press. DISCARD THEM. They are deliberately left unmapped    */
/* below so that they read as "not a key" rather than as a shift.              */
/*                                                                            */
/* If you do not discard them you get phantom LeftShift down/up events with    */
/* no matching physical press, your `held` count drifts, and the               */
/* `no-stuck-keys` check will tell you so.                                     */
/*                                                                            */
/* ---- Print Screen ----                                                      */
/*                                                                            */
/*   press:    E0 12 E0 7C                                                     */
/*   release:  E0 F0 7C E0 F0 12                                               */
/*                                                                            */
/* Discard the fake shift and this reduces to E0 7C down and E0 7C up, which   */
/* the table below handles. With Shift or Control already held the keyboard    */
/* omits the fake shift and sends E0 7C on its own — so the discard rule has   */
/* to be unconditional, not "expect four bytes".                               */
/*                                                                            */
/* With Alt held the key becomes SysReq and sends the single byte 0x84         */
/* instead, which is in the base table above.                                  */
/*                                                                            */
/* ---- Pause ----                                                             */
/*                                                                            */
/*   press:    E1 14 77 E1 F0 14 F0 77                                         */
/*   release:  nothing. Ever.                                                  */
/*                                                                            */
/* Pause is the one key on the board that has no break sequence: the eight     */
/* bytes above are sent once when the key goes down and nothing is sent when   */
/* it comes up, however long you hold it. It is also the only key that uses    */
/* the 0xE1 prefix, and it is the only place 0xE1 ever appears.                */
/*                                                                            */
/* No table can express this, so it is not in one. What a decoder has to do:   */
/* recognise the 0xE1 prefix, consume the fixed sequence, and synthesise BOTH  */
/* a down and an up for HID_KEY_PAUSE, because the state bitmap in             */
/* DESIGN.md #events-vs-state has no way to clear a key that never reports a   */
/* release — and a Pause left down is a key stuck forever.                     */
/*                                                                            */
/* Control + Pause is a different key, Break, and it does have a normal        */
/* release: E0 7E down, E0 F0 7E up. It is in the table below, mapped to the   */
/* same HID Pause usage, which is what every OS expects.                       */
/* ------------------------------------------------------------------------- */

static const ps2_hid_key_t ps2_set2_make_e0[256] PS2_TABLE_ATTR = {
    /* modifiers that only exist in extended form -------------------------- */
    [0x14] = { HID_KEY_CONTROL_RIGHT,   "RightControl" },
    [0x11] = { HID_KEY_ALT_RIGHT,       "RightAlt"     },
    [0x1F] = { HID_KEY_GUI_LEFT,        "LeftGUI"      },
    [0x27] = { HID_KEY_GUI_RIGHT,       "RightGUI"     },
    [0x2F] = { HID_KEY_APPLICATION,     "Application"  },

    /* navigation cluster -------------------------------------------------- */
    [0x70] = { HID_KEY_INSERT,          "Insert"       },
    [0x6C] = { HID_KEY_HOME,            "Home"         },
    [0x7D] = { HID_KEY_PAGE_UP,         "PageUp"       },
    [0x71] = { HID_KEY_DELETE,          "Delete"       },
    [0x69] = { HID_KEY_END,             "End"          },
    [0x7A] = { HID_KEY_PAGE_DOWN,       "PageDown"     },
    [0x75] = { HID_KEY_ARROW_UP,        "UpArrow"      },
    [0x6B] = { HID_KEY_ARROW_LEFT,      "LeftArrow"    },
    [0x72] = { HID_KEY_ARROW_DOWN,      "DownArrow"    },
    [0x74] = { HID_KEY_ARROW_RIGHT,     "RightArrow"   },

    /* keypad keys that are extended --------------------------------------- */
    /* Only these two. Every other keypad key is unprefixed, which is why the
     * keypad is split across both tables. */
    [0x4A] = { HID_KEY_KEYPAD_SLASH,    "KeypadSlash"  },
    [0x5A] = { HID_KEY_KEYPAD_ENTER,    "KeypadEnter"  },

    /* the sequence keys, in the forms a table can hold --------------------- */
    [0x7C] = { HID_KEY_PRINT_SCREEN,    "PrintScreen"  },
    [0x7E] = { HID_KEY_PAUSE,           "Pause"        }, /* Control + Pause */

    /* system ---------------------------------------------------------------
     * E0 37 Power is on HID page 0x07 and so can be reported. E0 3F Sleep and
     * E0 5E Wake are Generic Desktop (page 0x01) System Control usages, not
     * keyboard usages, and are deliberately left unmapped — your boot keyboard
     * report has nowhere to put them. */
    [0x37] = { HID_KEY_POWER,           "Power"        },

    /* 0x12 and 0x59 are the fake shifts described above, and are deliberately
     * NOT mapped. Leave them that way. */
};

#endif /* PS2_SET2_TO_HID_H */
