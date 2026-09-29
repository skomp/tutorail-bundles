# Stripboard layout — level-shifter module build

A worked layout for the circuit already on your breadboard, so that lesson 18 is about
soldering and not about drawing. Nothing here is new electrically: it is the same four
connections to the Pico, the same module, the same four wires to the keyboard.

**This layout is for the level-shifter *module* build.** Lesson 18 offers you a choice, and
`DESIGN.md` `#deliberately-unresolved` leaves it open on purpose: keep the ready-made
4-channel BSS138 module, or build the shifter from two discrete BSS138s and four resistors.
The module is the lower-risk soldering job and it is the one drawn here. **The discrete
build is yours to lay out** — see the last section for what it changes and why no layout is
supplied for it.

---

## 1. Component list

| Qty | Item | Note |
|---|---|---|
| 1 | Stripboard, 0.1 in pitch, **30 columns × 20 rows**, copper strips running **along the rows** | about 76 × 51 mm. Cut down from a larger sheet with a craft knife scored along a hole line, then snapped |
| 1 | Raspberry Pi Pico | soldered directly, or on two 20-way female headers if you want it removable |
| 2 | 20-way female header strip | only if socketing the Pico |
| 1 | 4-channel BSS138 bidirectional level-shifter module, 6 pins each side, rows 0.6 in apart | **check yours before you drill** — see the warning under the grid |
| 1 | 3-way male pin header | the debug UART to the second Pico |
| 1 | PS/2 extension cable, socket end kept | cut to about 150 mm of tail. Easier than a panel socket, and it brings its own strain relief |
| ~4 | 22–24 AWG solid-core hookup wire links | the four jumpers in the wire list |
| — | Heat-shrink, one cable tie or P-clip, enclosure | strain relief and the box |

Only **two** of the module's four channels are used: PS/2 clock and PS/2 data. Channels 3
and 4 are fitted and left unconnected. That is deliberate — an unused channel on a fitted
module costs nothing, and cutting the module down to two channels costs you the spares.

---

## 2. The grid

Strips run **horizontally**, one per lettered row, spanning all thirty columns unless a cut
says otherwise.

> **The drawing is the component side — the top.** The copper is on the *other* face. Every
> cut is made from underneath, and the board is mirrored left-to-right when you turn it over.
> Mark your cuts from the top with a pen through the hole, turn the board over, and cut on the
> mark. Cutting from a top-view drawing by counting columns on the copper side is the single
> most common way to wreck a stripboard, and the mistake is invisible until nothing works.

```
             1         2         3
    123456789012345678901234567890
 A  H..P..X.w.P..X.....X..........   GP0 / VBUS
 B  H..P..X...P..Xw.L..Xw.L...*...   GP1 / VSYS       LV  |  HV  | +5V
 C  H..P......P.....L.....L...*...   GND / GND    <<<<  ONE GROUND STRIP  >>>>
 D  ...P.wX...P..Xw.L..X..L...*...   GP2 / 3V3_EN     LV1 |  HV1 | CLOCK
 E  ...P.wX.w.P..Xw.L..X..L...*...   GP3 / 3V3(OUT)   LV2 |  HV2 | DATA
 F  ...P..X...P..X..L..X..L.......   GP4 / ADC_VREF   LV3 |  HV3   (spare)
 G  ...P..X...P..X..L..X..L.......   GP5 / GP28       LV4 |  HV4   (spare)
 H  ...P......P...................   GND / AGND   <<<<  ground strip  >>>>
 I  ...P..X...P...................   GP6 / GP27
 J  ...P..X...P...................   GP7 / GP26
 K  ...P..X...P...................   GP8 / RUN
 L  ...P..X...P...................   GP9 / GP22
 M  ...P......P...................   GND / GND    <<<<  ground strip  >>>>
 N  ...P..X...P...................   GP10 / GP21
 O  ...P..X...P...................   GP11 / GP20
 P  ...P..X...P...................   GP12 / GP19
 Q  ...P..X...P...................   GP13 / GP18
 R  ...P......P...................   GND / GND    <<<<  ground strip  >>>>
 S  ...P..X...P...................   GP14 / GP17
 T  ...P..X...P...................   GP15 / GP16
```

| Symbol | Meaning |
|---|---|
| `P` | a Raspberry Pi Pico pin. Column 4 is the Pico's left row (pins 1–20, USB at row A); column 11 is its right row (pins 40–21) |
| `L` | a level-shifter module pin. Column 17 is the **LV** row, column 23 is the **HV** row |
| `H` | the 3-way debug UART header, column 1 |
| `w` | a hole where one end of a wire link lands |
| `*` | where a conductor of the PS/2 cable is soldered |
| `X` | **a track cut at this hole** |
| `.` | a free hole |

The Pico's two pin rows are 0.7 in apart, which is seven holes: columns 4 and 11. Its ground
pins are symmetric — physical pins 3, 8, 13, 18 on the left and 38, 33, 28, 23 on the right —
so rows **C, H, M and R each carry ground on both sides at once** and need no cut at all.
That symmetry is what makes this layout tidy, and it is worth noticing rather than taking on
trust: check it against a Pico pinout before you commit.

> **Check your level-shifter module before you drill anything.** Modules vary. The common
> 4-channel BSS138 board has its pin rows **0.6 in (six holes) apart**, which is why LV sits
> at column 17 and HV at column 23. Some are 0.5 in or 0.7 in — measure yours and move the HV
> column, moving the column-20 cuts with it. Check the silkscreen for which side is LV and
> which is HV, and check the pin order within each row: this layout assumes
> `LV, GND, LV1, LV2, LV3, LV4` top to bottom on the LV side and `HV, GND, HV1, HV2, HV3, HV4`
> on the HV side. If yours differs, the row assignments change and the wire list changes with
> them. **HV and LV swapped puts 5 V on a 3.3 V pin**, which is the failure `DESIGN.md`
> `#voltage-domains` exists to prevent.

---

## 3. Track cuts

Twenty-eight cuts. Number them and tick them off; a missed cut is a short, and an extra cut
is an open circuit, and neither announces itself.

### Column 7 — separating the Pico's left pins from its right pins

Every non-ground row. Without these, GP2 is wired to 3V3_EN and pulling GP2 low switches off
the Pico's own 3.3 V regulator.

| # | Hole | Separates |
|---|---|---|
| 1 | **A7** | GP0 from VBUS |
| 2 | **B7** | GP1 from VSYS |
| 3 | **D7** | GP2 from 3V3_EN |
| 4 | **E7** | GP3 from 3V3(OUT) |
| 5 | **F7** | GP4 from ADC_VREF |
| 6 | **G7** | GP5 from GP28 |
| 7 | **I7** | GP6 from GP27 |
| 8 | **J7** | GP7 from GP26 |
| 9 | **K7** | GP8 from RUN |
| 10 | **L7** | GP9 from GP22 |
| 11 | **N7** | GP10 from GP21 |
| 12 | **O7** | GP11 from GP20 |
| 13 | **P7** | GP12 from GP19 |
| 14 | **Q7** | GP13 from GP18 |
| 15 | **S7** | GP14 from GP17 |
| 16 | **T7** | GP15 from GP16 |

No cut on **C7, H7, M7 or R7** — those four rows are ground on both sides and are meant to be
continuous.

### Column 14 — separating the Pico's right pins from the LV rail

| # | Hole | Separates |
|---|---|---|
| 17 | **A14** | VBUS from the empty LV-column segment of row A |
| 18 | **B14** | VSYS from the module's LV pin |
| 19 | **D14** | 3V3_EN from LV1 |
| 20 | **E14** | 3V3(OUT) from LV2 |
| 21 | **F14** | ADC_VREF from LV3 |
| 22 | **G14** | GP28 from LV4 |

### Column 20 — separating the LV side of the module from the HV side

| # | Hole | Separates |
|---|---|---|
| 23 | **A20** | — (keeps VBUS copper off the right-hand block) |
| 24 | **B20** | **LV (3.3 V) from HV (5 V)** — the cut that matters most |
| 25 | **D20** | LV1 from HV1 |
| 26 | **E20** | LV2 from HV2 |
| 27 | **F20** | LV3 from HV3 |
| 28 | **G20** | LV4 from HV4 |

No cut on **C14, C20** — row C is the single ground strip, and the module's two GND pins are
*meant* to be joined to each other and to the Pico's ground.

Rows I to T are not cut at columns 14 or 20 because nothing is mounted there. That leaves a
few centimetres of live copper reaching the board edge on those rows. It is harmless, but if
you would rather not have it, cut columns 14 and 20 on every non-ground row as well — twenty
more cuts, no electrical difference to this circuit.

---

## 4. Wire list

Four links. Use solid-core wire, keep them short, and route them flat on the component side
so the board still fits in the box.

| # | From | To | Net | Why a wire and not a strip |
|---|---|---|---|---|
| W1 | **A9** | **B21** | VBUS → HV (5 V) | VBUS is on row A, the module's HV pin is on row B |
| W2 | **E9** | **B15** | 3V3(OUT) → LV (3.3 V) | 3V3(OUT) is on row E, the module's LV pin is on row B |
| W3 | **D6** | **D15** | GP2 → LV1 (clock) | same row, but the column-7 and column-14 cuts are in the way — this link jumps over the 3V3_EN segment without touching it |
| W4 | **E6** | **E15** | GP3 → LV2 (data) | as W3, over the 3V3(OUT) segment |

Ground needs **no wire at all.** Row C runs uncut from the UART header at C1, through the
Pico's pin 3 at C4 and pin 38 at C11, through both of the module's GND pins at C17 and C23,
to the PS/2 cable's ground at C27.

### The PS/2 cable

Cut the extension cable, keep the **socket** end, and strip the four conductors you identified
in lesson 01. Colours vary between cables and are not to be trusted — verify each conductor
against the socket with a multimeter, exactly as you did then, and do it again now that the
cable has been cut.

| Conductor | Hole | Lands on |
|---|---|---|
| **+5 V** | **B27** | the HV rail — the same net as VBUS, through W1 |
| **GND** | **C27** | the ground strip |
| **CLOCK** | **D27** | HV1 |
| **DATA** | **E27** | HV2 |

The cable's screen or drain wire, if it has one, goes to ground at any free hole on row C —
one end only, at this end.

### The debug UART header

Three pins at column 1, rows A, B and C. No wires: column 1 is on the same strip segment as
the Pico's pins at column 4.

| Header pin | Hole | Pico | To the second Pico (`debugprobe`) |
|---|---|---|---|
| 1 | **A1** | GP0, UART0 TX | its **RX** |
| 2 | **B1** | GP1, UART0 RX | its **TX** |
| 3 | **C1** | GND | its GND |

TX to RX and RX to TX, not straight through. If your console is silent on first power, this
is the first thing to check and it costs nothing to swap.

If you socket the Pico rather than soldering it, the socket body and this header will touch.
That is mechanically fine at 0.1 in pitch; if you dislike it, move the header to rows A, B, C
of columns 28–30 instead and add two more wire links.

---

## 5. Continuity checklist — run this BEFORE first power

Every item is done with the multimeter on continuity or low ohms, the board **not connected
to anything**, and if you socketed the Pico, **with the Pico out of its socket**. The keyboard
stays unplugged throughout.

This list is not ceremony. A short between the HV rail and ground is a dead short across VBUS,
which is a dead short across your host's USB port, and you will find it with the smoke.

### A. The cuts are real

| ☐ | Check | Expect |
|---|---|---|
| ☐ | Hold the board up to a bright light and look along each cut | daylight through bare fibreglass, no copper whisker bridging |
| ☐ | Probe across each of the 28 cuts, one hole either side | **open** every time |

A cut made with a drill bit spun by hand leaves a ring of copper that looks cut and is not.
Probe it, do not eyeball it.

### B. The things that must be connected

| ☐ | From | To | Expect |
|---|---|---|---|
| ☐ | A11 (VBUS) | B23 (HV) | ~0 Ω — W1 |
| ☐ | E11 (3V3 OUT) | B17 (LV) | ~0 Ω — W2 |
| ☐ | D4 (GP2) | D17 (LV1) | ~0 Ω — W3 |
| ☐ | E4 (GP3) | E17 (LV2) | ~0 Ω — W4 |
| ☐ | C1 (header GND) | C27 (cable GND) | ~0 Ω — the whole ground strip |
| ☐ | C4, C11, C17, C23 | each other | ~0 Ω — all four ground landings |
| ☐ | B27 (cable +5 V) | A11 (VBUS) | ~0 Ω |
| ☐ | D27 (cable CLOCK) | D23 (HV1) | ~0 Ω |
| ☐ | E27 (cable DATA) | E23 (HV2) | ~0 Ω |

### C. The things that must NOT be connected

| ☐ | From | To | Expect | Why it matters |
|---|---|---|---|---|
| ☐ | B23 (HV, 5 V) | C (ground) | **open** | this one is the dead short across USB |
| ☐ | B17 (LV, 3.3 V) | C (ground) | **open** | shorts the Pico's regulator |
| ☐ | B17 (LV) | B23 (HV) | **open** | 5 V onto the 3.3 V rail |
| ☐ | A11 (VBUS) | C (ground) | **open** | as above |
| ☐ | D4 (GP2) | E4 (GP3) | **open** | clock shorted to data; the receiver never frames |
| ☐ | D4 (GP2) | D11 (3V3_EN) | **open** | the column-7 cut on row D; miss it and GP2 low kills the 3.3 V rail |
| ☐ | D4 (GP2) | C (ground) | **open** | |
| ☐ | E4 (GP3) | C (ground) | **open** | |
| ☐ | D23 (HV1) | E23 (HV2) | **open** | clock to data on the keyboard side |
| ☐ | D27 (CLOCK) | B27 (+5 V) | **open** | |
| ☐ | E27 (DATA) | B27 (+5 V) | **open** | |
| ☐ | A1 | B1 | **open** | TX shorted to RX at the header |

### D. Adjacent-pin sweep

| ☐ | Check | Expect |
|---|---|---|
| ☐ | Walk down column 4, probing each row against the row below it (A–B, B–C, C–D … S–T) | **open** except where both rows are the same net |
| ☐ | The same down column 11 | **open** except the ground rows |
| ☐ | The same down columns 17 and 23, rows B–G | **open** except B/C where the module's own GND is |

This is the sweep that catches solder bridges between neighbouring pins, and it is the one
people skip because it is forty measurements. Do it. A bridge between two adjacent GPIOs is
silent until something drives one of them.

### E. First power, in this order

| ☐ | Step | Expect |
|---|---|---|
| ☐ | Fit the Pico if it is socketed. Keyboard still unplugged. | |
| ☐ | Power the Pico from USB, nothing else connected | it enumerates or blinks as your firmware does; no heat anywhere |
| ☐ | Measure at B27 (the cable's +5 V landing) | **4.7–5.2 V** |
| ☐ | Measure at B17 (LV) | **3.2–3.4 V** |
| ☐ | Measure at D23 and E23 (HV1, HV2) with the keyboard still unplugged | near 5 V — the module's own pull-ups holding the bus idle high |
| ☐ | Measure at D17 and E17 (LV1, LV2) | near 3.3 V, for the same reason |

> **Flash your working firmware before you take those last two readings.** `DESIGN.md`
> `#pin-assignment` records that an RP2040 pad resets with its internal pull-down enabled, so
> a Pico sitting in BOOTSEL or running code that has not configured GP2 and GP3 is pulling
> both lines down against the module's pull-ups. You will measure somewhere around 2.8 V
> rather than 3.3 V, conclude the board is faulty, and spend an evening on a board that is
> fine. Programmed firmware first, then measure.
| ☐ | Touch every part of the board with a finger | nothing warm. Anything warm, unplug now and go back to section C |
| ☐ | Only now, plug the keyboard in | the current draw is what you measured in lesson 01 |

If any voltage is wrong, **unplug before you investigate**. Measuring a fault under power is
how a fault becomes two faults.

---

## 6. Mechanical notes

- **Strain relief is not optional.** The PS/2 cable is the only thing on this board that will
  ever be pulled, and a pull lifts a pad and takes the track with it. Pass the cable through a
  hole in the enclosure wall, then anchor it to the board with a cable tie through two spare
  holes at the edge — through the *board*, not just to the enclosure — so the tie takes the
  load and the solder joints take none. A P-clip screwed to the case does the same job.
- **Heat-shrink each of the four conductors** where it leaves the outer jacket, and heat-shrink
  the whole bundle where it enters the board. Bare stranded conductor next to a 5 V pad is a
  short waiting for vibration.
- **Cold joints work on the bench and fail warm.** A good joint is shiny and concave and wets
  both the pad and the wire. A dull, blobby joint that sits on top of the pad is a cold joint
  even if it passes continuity today. Reflow anything you are unsure about; it costs seconds.
- **Support the board in the enclosure** on standoffs or double-sided foam, not on the USB
  connector. The Pico's micro-USB or USB-C socket is surface-mount and is not a structural
  member.
- **Leave the BOOTSEL button reachable**, or you will be opening the box for every reflash. A
  hole in the lid over the button, or a length of stiff wire as a plunger, both work.

---

## 7. If you build the discrete BSS138 version instead

`DESIGN.md` leaves this choice open, and it is a genuine choice rather than a lesser one: the
discrete build is the more satisfying object and it is the one that shows you what the module
actually contains. **No layout is supplied for it, deliberately.** You have a working
schematic in your head from lesson 02, you have just laid out one board by following someone
else's drawing, and drawing the second one is where that becomes a skill you own.

What changes:

- The module's six-pin footprint becomes, per channel, **one BSS138** (SOT-23, so you will
  want a SOT-23-to-DIP adapter or dead-bug wiring on stripboard) and **two 10 kΩ resistors** —
  one from source to the 3.3 V rail, one from drain to the 5 V rail. The gate goes to the
  **3.3 V** rail. Two channels, so two MOSFETs and four resistors.
- You now own both pull-ups on the Pico side of the bus, and their value is yours to justify
  from the RC estimate you made in lesson 02 rather than from whatever the module happened to
  fit. 10 kΩ is the conventional answer; if your measured bus capacitance argues for something
  else, say so and use it.
- Everything else on this board is unchanged: same cuts through column 7, same ground strip on
  row C, same four cable landings, same UART header, same checklist. Sections 3, 5 and 6 above
  apply to your layout as they stand.
- Add to the checklist: with the board unpowered, **gate to source** and **gate to drain** on
  each MOSFET must both read open, and the two resistors must measure 10 kΩ ± tolerance
  in-circuit before anything is powered.

Whichever you build, lesson 18's acceptance test is the same and does not care which one you
chose: cold boot on a machine that has never seen the adapter, correct typing in the host's
firmware setup screen, no driver, and survival through suspend, resume and replug.
