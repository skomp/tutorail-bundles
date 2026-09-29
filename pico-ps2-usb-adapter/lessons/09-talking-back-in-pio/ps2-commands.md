# PS/2 host-to-device commands and responses

Reference material. These byte values are conventions fixed by IBM in the 1980s; you could
not derive them from a capture and nothing would be learnt by trying, so the course hands
them over. What you *do* have to work out yourself is how to put a byte on a bus the other
end clocks — that is lesson 09, and this document deliberately does not do it for you.

Everything below is the keyboard side of the PS/2 command set. Mice share the bus protocol
and almost none of the commands.

---

## 1. The host-to-device transmission sequence

The awkward fact about PS/2 is that **the keyboard generates the clock in both directions**.
The host never clocks the bus. To send a byte the host takes the bus away from the keyboard,
signals that it wants to talk, and then presents one bit at a time for the keyboard to clock
in at its own pace.

Both lines are open-drain, so "drive" below always means *pull low*, and "release" always
means *let the pull-up take it high*. Neither end ever drives a line high.

### The sequence

| Step | What the host does | What the device does |
|---|---|---|
| 1 | Pull **CLOCK** low and hold it for at least **100 µs** | stops transmitting; this is the **inhibit** state |
| 2 | Pull **DATA** low, with CLOCK still low | — |
| 3 | Release **CLOCK** | sees DATA low with CLOCK released — this is the **request-to-send** |
| 4 | wait | starts generating clock pulses |
| 5 | present data bit 0 on **DATA** while CLOCK is low | — |
| 6 | wait | releases CLOCK (rising edge) and **samples DATA here** |
| 7 | wait | pulls CLOCK low again |
| 8 | repeat 5–7 for data bits 1–7, then the **odd parity** bit | clocks each one in |
| 9 | release **DATA** (this presents the stop bit, 1) | — |
| 10 | wait | pulls **DATA** low — this is the **ACK bit** |
| 11 | wait | pulls CLOCK low |
| 12 | wait | releases both DATA and CLOCK; the bus is idle again |

The frame on the wire is the same eleven bits as in the other direction — start bit 0, eight
data bits **LSB first**, **odd** parity, stop bit 1. Only two things change: who drives DATA,
and which clock edge the data is valid on. Device-to-host data is valid on the **falling**
edge, because that is where the host samples. Host-to-device data is valid on the **rising**
edge, because that is where the device samples. See `DESIGN.md` `#wire-format`.

### The step that is easy to get wrong

Step 3 is the one that costs an afternoon. The request-to-send is the *combination* of DATA
low and CLOCK released — the device looks for CLOCK going high while DATA is already low. If
you release CLOCK before you have pulled DATA low, the device sees an ordinary end of
inhibit, decides the host has nothing to say, and starts sending whatever it had buffered.
Now both ends are driving DATA and nobody is right.

### Timing bounds worth encoding

| Bound | Value | What happens if you miss it |
|---|---|---|
| Inhibit hold before request-to-send | ≥ 100 µs | shorter, and the device may not notice the inhibit at all |
| Device starts clocking after request-to-send | within **15 ms** | if nothing clocks by then, the device is absent, asleep or wedged — time out |
| Whole 11-bit host-to-device frame | within **2 ms** | a frame that drags on longer than this has gone wrong; abandon it |
| Host presents its bit after the device pulls CLOCK low | within ~15 µs is comfortable | present it late and the device samples the previous bit again |
| Inhibiting the bus for a long time | keep it short | the device buffers what it wanted to say (typically 16 bytes), and a long inhibit on some keyboards provokes a reset — the keys you pressed during it are gone either way |

### Aborting a device transmission

If the host pulls CLOCK low *while the device is mid-frame*, the device abandons that frame.
Whether the byte is lost depends on how far it got: inhibit before the eleventh clock pulse
and the device will resend the byte when the bus is released; inhibit after it and the device
considers the byte delivered. Do not rely on being able to tell which happened — inhibit at
a moment of your own choosing, not in the middle of a burst of typing.

### What the ACK bit means, and what it does not

The ACK bit at step 10 says only "I clocked in eleven bits and the parity was right". It is
**not** a statement about the command. A command byte with good parity that the keyboard does
not understand is still ACKed at the bit level, and then answered with `0xFA` or `0xFE` (or,
for a few commands, something else) as a whole byte on the bus afterwards. Two different
acknowledgements, on two different layers, and they are easy to conflate.

If the device does **not** pull DATA low at step 10, or answers with `0xFE` Resend, the host
must send the byte again. A host that ignores this loses commands silently.

---

## 2. Commands the host sends

`arg` says whether the command takes a following argument byte. The argument is sent as a
complete second frame, with its own start, parity, stop and ACK bit, and the device answers
it separately.

| Byte | Name | arg | Device answers | Notes |
|---|---|---|---|---|
| `0xFF` | **Reset** | no | `0xFA`, then after 500–750 ms `0xAA` (passed) or `0xFC` (failed) | Full power-on reset. The Model M flashes all three LEDs. Scanning is disabled afterwards and the keyboard returns to scan code set 2 with default typematic. |
| `0xFE` | **Resend** | no | the device repeats the **last byte it sent** | No `0xFA` — the answer *is* the resent byte. Send this when you receive a byte with bad parity. |
| `0xEE` | **Echo** | no | `0xEE` | Not `0xFA`. A liveness probe that changes no state — the cheapest "is anything out there?" you have. |
| `0xED` | **Set/reset LEDs** | **yes** | `0xFA`, then `0xFA` for the argument | Argument is the LED bitmap; see section 4. |
| `0xF0` | **Set scan code set** | **yes** | `0xFA`, then `0xFA` for the argument | Argument `0x01`/`0x02`/`0x03` selects a set; argument `0x00` asks, and the device answers `0xFA` then the current set as a byte. This course never sends it — see the warning in section 3. |
| `0xF2` | **Read ID** | no | `0xFA`, then **two** bytes: `0xAB 0x83` | `0xAB 0x83` is an MF2 keyboard, which is what a Model M answers. Some keyboards are slow with the second byte; do not treat a gap as a failure. |
| `0xF3` | **Set typematic rate and delay** | **yes** | `0xFA`, then `0xFA` for the argument | Argument encodes both; see section 5. |
| `0xF4` | **Enable scanning** | no | `0xFA` | The keyboard starts sending scan codes. It sends nothing until you do this after a reset. |
| `0xF5` | **Disable scanning** | no | `0xFA` | Stops scanning **and** restores default parameters. Not merely the inverse of `0xF4`. |
| `0xF6` | **Set default parameters** | no | `0xFA` | Default typematic, scan code set 2, and the LEDs off. Scanning state is left alone. |
| `0xF7`–`0xFB` | set-3 typematic/make/break controls | no | `0xFA` | Only meaningful in scan code set 3, which this course does not use. Listed so you recognise them. |
| `0xFC`–`0xFD` | set-3 per-key make/break controls | yes | `0xFA` | As above. Note the collision: `0xFC` **from** the device is a self-test failure. |

### The two byte values that mean different things in each direction

This trips people up, so it is called out rather than left to be discovered:

- **`0xFE`** sent by the host means *resend the last byte you sent me*. **`0xFE`** sent by the
  device means *resend the last byte you sent me*. Same meaning, opposite directions — but
  your firmware must not confuse a device-originated `0xFE` with an echo of its own command.
- **`0xF0`** sent by the host is **set scan code set**. **`0xF0`** sent by the device is the
  **break prefix** — the thing that makes the next byte a key release. They are unrelated, and
  a decoder that mixes them up will start switching scan code sets every time you let go of a
  key. If that sounds absurd, it is exactly what happens when a shared "handle a PS/2 byte"
  function is used for both directions.
- **`0xFA`** from the device is ACK. `0xFA` *to* the device is a set-3 command. This adapter
  never sends it.

---

## 3. Responses the device sends

These arrive as ordinary device-to-host frames, indistinguishable at the wire level from a
scan code. Only your firmware's knowledge of what it just asked for tells them apart — which
is precisely why a receive path that is "expecting a reply" needs a state of its own.

| Byte | Meaning | When you see it |
|---|---|---|
| `0xFA` | **ACK** | after nearly every command and every argument byte |
| `0xAA` | **Basic Assurance Test passed** | after `0xFF` Reset, and unprompted about 500–750 ms after power is applied to the keyboard |
| `0xFC` | **BAT failed** | after `0xFF` Reset, on a keyboard with a hardware fault |
| `0xFD` | **BAT failed** (alternative code some keyboards use) | as above |
| `0xFE` | **Resend** | the device did not accept your last byte — bad parity, or it arrived while it was busy. Send it again. |
| `0xEE` | **Echo response** | only after an `0xEE` Echo |
| `0xAB` `0x83` | **Keyboard ID** | the two bytes after `0xFA` in reply to `0xF2` |
| `0x00` | **Error or buffer overrun** | in scan code sets 2 and 3 |
| `0xFF` | **Error or buffer overrun** | in scan code **set 1** only |

`0x00` and `0xFF` are the same event reported with different codes depending on the active
set. Since this adapter stays in set 2, `0x00` is the one you will ever see, and `0xFF` from
the device would be surprising enough to be worth logging.

> **The scan code set stays at 2.** `DESIGN.md` `#wire-format` fixes this: the keyboard powers
> up in set 2, the adapter never asks it to change, and there is exactly one translation
> table. `0xF0` is documented above because you should recognise it in someone else's capture,
> not because you should send it. If you do send it out of curiosity, send it to a keyboard
> you can power-cycle.

### An unprompted `0xAA` is information, not noise

A keyboard that was hot-plugged sends `0xAA` on its own, a fraction of a second after it gets
power, with nothing having asked it for anything. That byte is your hot-plug notification, and
lesson 17 leans on it. Firmware that treats every unexpected byte as a framing error throws
away the most useful byte the keyboard ever sends.

---

## 4. The `0xED` LED bitmap — and why it is not the HID one

`0xED` takes one argument byte. Bits 3 to 7 are reserved and must be zero.

### PS/2, in the `0xED` argument byte

| Bit | Mask | LED |
|---|---|---|
| 0 | `0x01` | **Scroll Lock** |
| 1 | `0x02` | **Num Lock** |
| 2 | `0x04` | **Caps Lock** |
| 3–7 | — | reserved, send as 0 |

### USB HID, in the 1-byte LED output report

This is Usage Page `0x08` (LED), as declared in the report descriptor you write in lesson 12
and receive in lesson 15.

| Bit | Mask | LED |
|---|---|---|
| 0 | `0x01` | **Num Lock** |
| 1 | `0x02` | **Caps Lock** |
| 2 | `0x04` | **Scroll Lock** |
| 3 | `0x08` | Compose |
| 4 | `0x10` | Kana |
| 5–7 | — | padding |

### They are not the same, and the difference is not a rotation

Put them side by side:

| LED | PS/2 `0xED` bit | HID output report bit |
|---|---|---|
| Num Lock | 1 | **0** |
| Caps Lock | 2 | **1** |
| Scroll Lock | 0 | **2** |

Num Lock and Scroll Lock swap ends and Caps Lock moves. There is no shift, mask or rotate
that turns one into the other — it is a three-entry lookup, and writing it as one is the
honest implementation.

The reason this is worth a section of its own: **the failure is invisible for the LED you are
most likely to test first.** If you pass the HID byte straight through to `0xED`, pressing
Caps Lock on the host sets HID bit 1, which PS/2 reads as Num Lock. You press Caps Lock and
the Num Lock light comes on. That at least is obviously wrong. But a host that has Num Lock on
at boot — which most do — sets HID bit 0, which PS/2 reads as Scroll Lock, and a Scroll Lock
light that is always on looks like a keyboard quirk rather than a bug. Lesson 15 is built
around this.

### Two more things about `0xED`

- It is a **two-frame** exchange. Command, ACK, argument, ACK. Each frame is a full
  host-to-device sequence with its own inhibit and request-to-send, and the whole thing takes
  on the order of two milliseconds. That is far too long to do inside a USB callback — which
  is the other trap lesson 15 sets.
- The keyboard **stops scanning** while it is processing the command. Keys pressed during those
  two milliseconds are buffered, not lost, but the LED update is not a free operation and
  sending one per host report is wasteful. Send one only when the bitmap actually changes.

---

## 5. The `0xF3` typematic argument

One argument byte, bit 7 must be zero.

| Bits | Field | Values |
|---|---|---|
| 0–4 | **repeat rate** | `0x00` = 30.0 characters per second (fastest) … `0x1F` = 2.0 cps (slowest) |
| 5–6 | **delay before repeat** | `0` = 250 ms, `1` = 500 ms, `2` = 750 ms, `3` = 1000 ms |
| 7 | reserved | must be 0 |

The rate field is not linear in either cps or period; it is a table in the keyboard's
firmware. `0x00` is 30 cps, `0x0B` is about 10.9 cps, `0x1F` is 2 cps, and the values in
between are spaced to feel even rather than to compute cleanly.

The power-on default is 10.9 cps with a 500 ms delay, which is argument `0x2B`.

**You almost certainly do not want to send this.** Typematic repeat is the keyboard repeating
a make code on its own while a key is held, and under `DESIGN.md` `#events-vs-state` a repeated
make code for a key already down changes nothing: the state bitmap already says the key is
down, the report does not change, and no report is sent. The host does its own repeat from the
key-down report. So the keyboard's typematic rate is invisible to the host through this
adapter, and turning it down does not make the adapter feel different — it just reduces PS/2
traffic. Setting it is a legitimate experiment; expecting it to change the typing experience is
not.

---

## 6. A suggested reset conversation

Not code, and not the only correct order — a sketch of what a sane bring-up asks for and what
it should hear back. Lesson 09's completion condition is the first two lines of it.

| Host sends | Expect back | If not |
|---|---|---|
| `0xFF` | `0xFA` within a few ms | no ACK bit, or no `0xFA`: no keyboard, or the request-to-send is wrong |
| — | `0xAA` within about 1 s | `0xFC`/`0xFD`: the keyboard failed its own self-test. Silence: it is not there. |
| `0xF2` | `0xFA`, then `0xAB 0x83` | something else: not an MF2 keyboard, and the set 2 table may not apply |
| `0xED` + `0x00` | `0xFA`, `0xFA` | LEDs off, as a known starting state |
| `0xF4` | `0xFA` | scanning on — nothing arrives until this is sent |

Retry on `0xFE` and on a missing ACK bit. Bound the retries: a keyboard that NAKs three times
running is not going to accept the fourth, and firmware that loops forever on it looks
identical to firmware that has crashed.
