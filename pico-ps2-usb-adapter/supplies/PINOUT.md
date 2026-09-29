# Pinout reference

Two things live in this file, and you will come back to both of them:

1. **The mini-DIN-6 PS/2 connector**, drawn twice — once from the plug side and once
   from the socket side — because reading it from the wrong side is the single most
   common way to destroy a keyboard, a Pico, or an afternoon.
2. **The pin assignment this course uses** on the Pico, which is fixed by the design and
   is not yours to change.

Nothing in this file is a substitute for a multimeter. Lesson 01 has you confirm every
PS/2 pin with your own continuity and voltage readings before a single wire reaches a
GPIO. Read this, then go and prove it.

---

## Part 1 — the mini-DIN-6 PS/2 connector

### The signals

| Pin | Signal | Notes |
|---|---|---|
| 1 | **DATA** | open-drain, idles high at 5 V, pulled up inside the keyboard |
| 2 | not connected | reserved; some laptop Y-splitter ports reuse it, a keyboard does not |
| 3 | **GND** | |
| 4 | **VCC, +5 V** | a PC port budgets 275 mA here; measure what your keyboard actually draws |
| 5 | **CLOCK** | open-drain, idles high at 5 V, pulled up inside the keyboard. The keyboard drives this in **both** directions of traffic |
| 6 | not connected | reserved, as pin 2 |

Four live pins: 1, 3, 4, 5. Pins 2 and 6 are dead on a keyboard cable — on some cheap
plugs they are physically absent, which is a useful clue that you have the numbering the
right way round.

### How to hold the connector

A mini-DIN-6 has a **flat rectangular plastic key** — a blade on the plug, a matching slot
in the socket. That key is the only landmark you need, and it is what stops you inserting
the plug rotated.

**Both diagrams below are drawn with the key at 12 o'clock.** Turn the real connector until
its key is at the top and the diagram will match.

> Plenty of published diagrams draw this connector with the key at 6 o'clock instead. If
> you compare against one of those, **rotate** it through 180° — do not flip it over. A
> rotation preserves the pin order; a flip reverses it, and reversing it is exactly the
> mistake this file exists to prevent.

### View A — the PLUG (male, on the keyboard's cable)

You are looking straight at **the end you push in**: the face with the pins sticking out of
it, pointing back at you. Key at 12 o'clock.

```
                                 key
                               +-----+
                     __________|     |__________
                   /           +-----+           \
   CLOCK ---------|    (5)                 (6)    |--------- n/c
                  |                               |
     GND ---------|  (3)                     (4)  |--------- +5V
                  |                               |
    DATA ---------|     (1)               (2)     |--------- n/c
                   \_____________________________/
```

Reading it row by row, left to right:

- top row: **5 CLOCK**, then **6 not connected**
- middle: **3 GND**, then **4 +5 V**
- bottom: **1 DATA**, then **2 not connected**

### View B — the SOCKET (female: a panel socket, or the port on a PC)

You are looking **into the hole**, at the face the plug goes into. Key slot at 12 o'clock.

```
                                 key
                               +-----+
                     __________|     |__________
                   /           +-----+           \
     n/c ---------|    (6)                 (5)    |--------- CLOCK
                  |                               |
     +5V ---------|  (4)                     (3)  |--------- GND
                  |                               |
     n/c ---------|     (2)               (1)     |--------- DATA
                   \_____________________________/
```

Reading it row by row, left to right:

- top row: **6 not connected**, then **5 CLOCK**
- middle: **4 +5 V**, then **3 GND**
- bottom: **2 not connected**, then **1 DATA**

### The mirror check

The two views are left-right mirror images of each other, and nothing else. If a drawing
you find elsewhere does not mirror like this, one of the two is wrong:

| Position in the drawing | View A — plug | View B — socket |
|---|---|---|
| top left | 5 CLOCK | 6 n/c |
| top right | 6 n/c | 5 CLOCK |
| middle left | 3 GND | 4 +5 V |
| middle right | 4 +5 V | 3 GND |
| bottom left | 1 DATA | 2 n/c |
| bottom right | 2 n/c | 1 DATA |

Every row swaps sides. That is what "mirrored" means, and it is why a plug diagram used as
a socket diagram puts **+5 V where you expected GND** — which is exactly the swap that lets
out the smoke.

### A third view you will actually solder in

If you buy a panel-mount socket, you solder to its **back**, and the back is a mirror of
View B — which makes it read the same way round as View A, the plug view.

Precisely: hold the socket with the key slot at 12 o'clock, then turn it left-to-right about
its own vertical axis so you are looking at the solder tails. The pin positions you now see
are the ones in **View A**.

Do not take that on trust. Panel sockets vary, most have the pin numbers moulded into the
body, and a continuity test between a mating plug's pin and a solder tail takes twenty
seconds. Lesson 01 makes you do it.

### Cable colours mean nothing

**PS/2 cable wire colours are not standardised.** Red is not always +5 V, black is not
always ground, and the braided shield may or may not be tied to pin 3. Manufacturers used
whatever wire they had on the reel. If you cut open a PS/2 extension cable, the only
trustworthy way to find out which wire is which is to put a meter between a wire end and a
numbered pin on the plug, using the views above to know which pin you are touching.

---

## Part 2 — the Pico pin assignment

Fixed by `#pin-assignment` and `#debug-channel` in `tutorial/DESIGN.md`. Physical pin
numbers are the 40 pads on a Raspberry Pi Pico, counting from the corner nearest the USB
connector down the left-hand side and back up the right.

| Signal | GPIO | Physical pin | Why it is here |
|---|---|---|---|
| Debug console TX (UART0 TX) | GP0 | 1 | the console every check reads |
| Debug console RX (UART0 RX) | GP1 | 2 | so you can type at the board later if you want to |
| **PS/2 CLOCK** (3.3 V side) | GP2 | 4 | PIO addresses pins from a base index, so clock is the base |
| **PS/2 DATA** (3.3 V side) | GP3 | 5 | must be base + 1, adjacent to clock, in that order |
| reserved — safety-catch enable | GP4 | 6 | claimed by the offered `a-safety-catch` lesson |
| reserved — timing marker | GP5 | 7 | claimed by lesson 16, to correlate firmware with a capture |
| GND | — | 3, 8, 13, 18, 23, 28, 38 | |
| 3V3(OUT) | — | 36 | the logic rail. **Not** the keyboard's supply |
| VSYS | — | 39 | |
| **VBUS, +5 V** | — | 40 | **this** is what powers the keyboard |
| RUN (pull low to reset) | — | 30 | handy for a reset button |
| On-board LED | GP25 | not on the header | |

**GP23, GP24, GP25 and GP29 are used by the Pico board itself** — SMPS power-save control,
VBUS sense, the LED and VSYS sense. They are not yours, and most of them are not even
brought out to the header.

**GP2 and GP3 are reserved for PS/2 for the whole course.** Do not borrow them for a blink
test in lesson 00; use GP25 or any pin from GP6 upward.

GP4 and GP5 are *reserved*, not used. They are kept clear so that a learner who takes the
offered lessons does not have to move a wire that three earlier lessons assumed.

### The keyboard is powered from VBUS, not from 3V3(OUT)

Pin 40, not pin 36. A Model M draws far more than the Pico's on-board 3.3 V regulator will
give, and it wants 5 V anyway. VBUS is the raw 5 V arriving on the Pico's own USB
connector, so **the adapter Pico must be plugged into a USB port or a USB power supply**
for the keyboard to have any power at all.

### The level shifter

A BSS138-type bidirectional module sits between the keyboard's 5 V open-drain bus and
GP2 / GP3. Its high-voltage side references VBUS and faces the keyboard's clock and data;
its low-voltage side references 3V3(OUT) and faces GP2 and GP3. Both sides share a common
ground with the Pico.

Which of the module's four channels carries clock and which carries data is yours to pick
and to wire — that is lesson 02's build, and this file does not do it for you. What this
file fixes is only where each signal has to *end up*: clock at GP2, data at GP3.

---

## Part 3 — the second Pico, the one running `debugprobe`

The debug console is a real UART on GP0/GP1, going to a second Pico flashed with Raspberry
Pi's `debugprobe` firmware. That second Pico also carries SWD for lesson 16. It appears on
your computer as a USB serial port, and `device.env` is where you record which one.

`debugprobe` built for a Pico host uses this fixed assignment **on the probe**:

| Probe function | Probe GPIO | Probe physical pin |
|---|---|---|
| SWCLK out | GP2 | 4 |
| SWDIO | GP3 | 5 |
| UART TX (the probe talks) | GP4 | 6 |
| UART RX (the probe listens) | GP5 | 7 |

So the wiring between the two boards is:

| Adapter Pico (the target) | | Probe Pico (`debugprobe`) |
|---|---|---|
| GP0, pin 1 — UART0 **TX** | `-->` | GP5, pin 7 — probe UART **RX** |
| GP1, pin 2 — UART0 **RX** | `<--` | GP4, pin 6 — probe UART **TX** |
| GND, pin 3 (or any GND) | `---` | GND, pin 3 (or any GND) |
| SWCLK pad, short edge | `<--` | GP2, pin 4 |
| GND pad, short edge | `---` | GND |
| SWDIO pad, short edge | `<->` | GP3, pin 5 |

Three things worth noticing before you wire it:

- **TX goes to RX and RX goes to TX.** Straight-through TX-to-TX gives you a console that
  never prints a character, and no error anywhere to tell you why.
- **The probe's GP2/GP3 are SWD; the target's GP2/GP3 are PS/2.** Same numbers, different
  boards, no conflict — but it is a genuinely confusing coincidence, so label your jumpers.
- **Share ground, never share power.** Both Picos get their own USB cable. Do not join VBUS
  to VBUS or VSYS to VSYS; that ties two host supplies together through a breadboard.

The three SWD pads (SWCLK, GND, SWDIO) are the small three-pad header on the short edge of
the Pico opposite the USB connector, silkscreened on the underside. You need them only from
lesson 16 onward, but wiring them at the same time as the UART saves taking the bench apart
later.

---

## Quick sanity list before you power anything

- The key on the connector is at 12 o'clock, and you know which of View A and View B you
  are reading.
- Pin 4 is the one going to VBUS. Pin 3 is the one going to GND. You have proved both with
  a meter, not with a cable colour.
- Nothing from the keyboard reaches GP2 or GP3 except through the level shifter's
  low-voltage side.
- The shifter's high-voltage reference is on VBUS and its low-voltage reference is on
  3V3(OUT), and not the other way round.
- Both Picos share a ground and neither shares a supply with the other.

RP2040 GPIO is **not** 5 V tolerant. There is no warning stage, no smoke and no smell — the
pin simply stops working, sometimes not until days later.
