# Bill of materials

**Read this before lesson 00, not before lesson 01.**

Everything else in this course is under your control. Delivery time is not. If you start
lesson 00 and discover on lesson 02 that the level shifter is three weeks away, you lose
three weeks, because lesson 02 is the gate to everything after it.

So: skim the "order these first" list below, place the order, and *then* start lesson 00.
Lessons 00 needs only the two Picos and two USB cables, so you can be working while the
rest arrives.

Prices are indicative only, for orientation on what each thing should roughly cost. They
are not quotes.

---

## Order these first

| Item | Why it is on the critical path |
|---|---|
| A **second** Raspberry Pi Pico | needed from **lesson 00**. Nothing in this course is checkable without it |
| BSS138-type 4-channel bidirectional level shifter | needed from **lesson 02**, and the whole electrical design is built around it |
| A PS/2 extension cable, or a mini-DIN-6 panel socket | needed from **lesson 01**. Genuinely obsolete parts; stock is patchy and shipping is often slow |
| 8-channel logic analyser (if you do not own one) | needed from **lesson 03** |

Everything else on this page is either something you probably own or something that ships
from anywhere.

---

## The two load-bearing choices

Two items on this list are not "whatever you have in the drawer". Substituting either one
breaks the course in a way that will not be obvious until several lessons later.

### 1. A second Raspberry Pi Pico, flashed as `debugprobe`

**What it does.** It is the debug console. Your firmware prints structured log lines out of
UART0 on GP0/GP1; the second Pico turns that into a USB serial port on your computer; the
course's checks open that port and read your evidence out of it. The same board carries SWD,
which is how lesson 16 puts you in a debugger.

**Why a substitute fails.** The tempting substitute is "I will just print over USB from the
adapter Pico itself, it already has a USB connector". That works beautifully until
lesson 11, when your firmware claims USB for the keyboard interface — and then your console
is either gone or is itself a variable in the experiment you are running. Lessons 11 to 15
are exactly where enumeration is failing and you most need to see inside the device. This
is written down as `#debug-channel` in `tutorial/DESIGN.md` and it is not negotiable: every
console-reading check in the course depends on a console that is not USB.

**What genuinely does substitute.** Raspberry Pi's own **Debug Probe** accessory (about
$12) does the same two jobs with nicer cables, and the course works with it unchanged.

**What half-substitutes.** A plain 3.3 V USB-to-UART adapter (CP2102, CH340, FT232) gives
you the console for lessons 00 to 15, but gives you no SWD, so lesson 16 has nothing to
debug with. If you go that way, buy one that is switchable to **3.3 V** — a 5 V adapter's
TX will sit on GP1 at 5 V and damage it.

**Typical price.** About $4 for a Pico, $12 for the official Debug Probe.

### 2. A BSS138-type 4-channel bidirectional level shifter

**What it does.** It sits between the keyboard's 5 V bus and the Pico's 3.3 V GPIO, on both
the clock line and the data line. It is the reason the RP2040 survives being connected to a
Model M.

Look for the very common little red or purple breakout board with four channels, `HV`/`LV`
reference pins and a row of `HV1..HV4` / `LV1..LV4` pairs — SparkFun BOB-12009, Adafruit
757, or any of the identical clones sold as "4 channel IIC I2C logic level converter
bi-directional". They are all one BSS138-type N-channel MOSFET per channel with a 10 kΩ
pull-up to each side's reference rail.

**Why a substitute fails.** PS/2 clock and data are **open-drain**: nobody ever drives them
high, both ends may pull them low, and the pull-up resistors do the rest. That rules out the
two things a newcomer reaches for:

- **A resistor divider** is a one-way attenuator. It handles 5 V going down to 3.3 V and has
  no answer at all for the moment the 3.3 V side has to pull the line down — which lesson 09
  requires on both lines.
- **A unidirectional buffer** (74LVC245, 74AHCT125, anything with a direction pin) works
  perfectly for lessons 04 through 08, where only the keyboard ever drives. Then lesson 09
  asks you to transmit, and you find out you bought the wrong part five lessons ago.

Two *other* level-shifter chips are commonly sold on similar-looking boards and are also
wrong here:

- **TXB0104** — TI's own datasheet says it must not be used with open-drain drivers. Its
  output buffers fight anything that pulls the line low externally.
- **TXS0108E** — designed for open-drain, but its internal accelerators and 10 kΩ pull-ups
  misbehave against a strong external pull-up, and a PS/2 keyboard's internal pull-up is
  strong. Expect edges that look wrong on the analyser for reasons that have nothing to do
  with your firmware.

If the board does not say BSS138 (or an equivalent small-signal MOSFET) on it, and does not
have separate `HV`/`LV` reference pins, it is not the part this course assumes.

**Typical price.** About $3, usually sold in packs of five. Buy the pack; you will want a
spare the first time you get a wire wrong.

---

## The full list

### The adapter

| Item | What it is for | Notes | Typical price |
|---|---|---|---|
| Raspberry Pi Pico (RP2040) | the adapter itself | An RP2350 / Pico 2 works unchanged. RP2040 is what this course assumes, because when you are stuck at 1 a.m. the weight of community material about the RP2040 is what rescues you. | ~$4 |
| **A second Pico**, flashed as `debugprobe` | debug console + SWD | See above. Not optional. | ~$4 |
| BSS138-type 4-channel bidirectional level shifter | the 5 V / 3.3 V interface | See above. Not optional. | ~$3 |
| 2 × micro-USB cable | one per Pico | **Data** cables, not charge-only. A charge-only cable gives you a Pico that powers up, never enumerates, and looks broken. | ~$4 |
| Pin headers, 2 × 20-way, 0.1 in | only if your Picos came without them | A plain "Pico" ships bare; a "Pico H" ships with headers already soldered. If you have never soldered, buy the **H** version of both boards and save yourself a first-day problem that is not part of this course. | ~$1 |

### The keyboard side

| Item | What it is for | Notes | Typical price |
|---|---|---|---|
| PS/2 extension cable (mini-DIN-6 male to female) to cut open | getting at the four signals | **The easier option.** Cut it in half, strip the four wires, and you have a flying lead with a female socket for the keyboard and built-in strain relief for lesson 18. Buy two: the first one you cut is a learning experience. | ~$5 |
| *or* mini-DIN-6 panel socket | a tidier finished object | Harder to solder, six close-spaced tails, and you have to work out which tail is which pin from the back. `docs/PINOUT.md` covers that view. | ~$3 |
| Assorted resistors, 1 kΩ to 10 kΩ, 1/4 W | the pull-up experiment in lesson 02 | 1 k, 2.2 k, 4.7 k and 10 k, a handful of each. A cheap assortment box is fine and useful forever. | ~$8 for a box |

### The bench

| Item | What it is for | Notes | Typical price |
|---|---|---|---|
| Solderless breadboard, full size (830 tie point) | lessons 01 to 17 live here | A half-size board is cramped once two Picos, a shifter and a keyboard lead are on it. | ~$5 |
| Jumper wires: male-male and male-female, 20 cm | wiring the above | Get both kinds. Male-female is what reaches the level shifter's header. | ~$6 |
| Multimeter | **assumed present** | Continuity beep, DC volts, DC current. Any $15 meter does everything this course asks. Lesson 01 measures current, so it needs a current range and its fused current jack. | ~$15 if you need one |
| Logic analyser, 8 channel, sigrok / PulseView compatible | **assumed present**, needed from lesson 03 | A cheap "24 MHz 8 channel" clone is entirely sufficient — PS/2 clocks at roughly 10–17 kHz, so you have four orders of magnitude of headroom. Install [PulseView](https://sigrok.org/wiki/PulseView) and check it enumerates before lesson 03. | ~$10 |

### Lesson 18 — turning it into an object

| Item | What it is for | Notes | Typical price |
|---|---|---|---|
| Perfboard or stripboard | the permanent build | `docs/perfboard-layout.md` is supplied at lesson 18 and assumes stripboard with the level-shifter module kept as a module. | ~$5 |
| Soldering iron, solder, flux | lesson 18, and headers before that | A temperature-controlled iron is far easier for a beginner than a fixed-temperature one. | ~$30 |
| Heat-shrink tubing, assorted | strain relief and insulation | | ~$5 |
| Small enclosure | the finished adapter | Anything that fits the board and has room for the cable gland or grommet. | ~$5 |
| Side cutters, wire strippers | | | ~$10 |

### Not assumed

| Item | Who needs it | Notes |
|---|---|---|
| Oscilloscope | **only** the offered `see-the-edges-on-a-scope` lesson | The main path never requires one. The logic analyser shows you *what* the bits are; a scope shows you what the *edge* looks like, which is the point of that one optional lesson. |
| A **third** Pico | **only** the offered `watch-the-enumeration` lesson, and only on a macOS host | USB packet capture does not work on current macOS with SIP enabled. The route that does work is a third Pico acting as a passive full-speed sniffer. On Linux (usbmon) or Windows (USBPcap) you do not need it. |

### Assumed you already have

| Item | Notes |
|---|---|
| **An IBM Model M**, or any PS/2 keyboard | The course is written around a Model M — its buckling-spring matrix, its rollover limits and its lock LEDs all come up by name. Any PS/2 keyboard that speaks scan code set 2 will get you through every lesson; a cheap modern PS/2 board is a fine stand-in for the early lessons and a useful second data point later. If your Model M has the detachable SDL cable, you also need its **SDL-to-mini-DIN-6** cable. |
| A computer with a USB port you are willing to have typed into | See the safety note below. |
| A soldering-capable surface and decent light | Lesson 18. |

---

## One safety note the course states rather than enforces

**Buggy firmware on an input device types into whatever window has focus.** A missing
key-release report types one character forever, and the only way to stop it is to unplug the
adapter — which is fine, but it happens in the middle of whatever you were doing.

Two mitigations, neither required:

- Develop against a machine you do not mind being typed into, or against a spare machine, or
  with a text editor focused and nothing else open.
- Take the offered `a-safety-catch` lesson at lesson 13. It adds a firmware gate on GP4
  that suppresses HID output until you deliberately ground the pin. It costs you one jumper
  and one lesson, and it is the more interesting answer.

The course does not require either, and no check assumes either.

---

## Roughly what the whole thing costs

If you already own a multimeter, a logic analyser and a soldering iron, the parts that are
specific to this course come to **about $30**. If you own none of those, budget **$90 to
$110** — and all three are tools you keep.
