"""Shared helper for every check that reads your debug console. Imported, never run.

WHAT THIS CHECKS
    Nothing on its own. It is the plumbing the other checks stand on: it opens the
    UART your firmware prints to, reads lines off it, and turns the ones that match
    this course's log contract into records the checks can reason about.

WHAT EVIDENCE IT READS
    The debug UART on your second Pico (the one flashed as `debugprobe`), at the port
    and baud named in `device.env` in the root of your workspace. `device.env` is a
    plain KEY=value file you filled in during lesson 00:

        CONSOLE_PORT=/dev/cu.usbmodem1101      # or COM7, or /dev/serial/by-id/...
        CONSOLE_BAUD=115200
        USB_VID=1209
        USB_PID=0001

    (PORT / BAUD / VID / PID are accepted as aliases. An environment variable of the
    same name wins over the file, which is handy when you move the probe to another
    socket for one run.)

    On that port it looks for lines of the form

        key: value

    where `key` matches [a-z][a-z0-9-]* -- `alive`, `frame`, `queue`, `pio-frames`.
    EVERY OTHER LINE IS IGNORED, on purpose. Your own printf debugging, SDK noise and
    half-lines left in the UART FIFO from before the check started cannot make a check
    pass and cannot make one fail. You stay free to print whatever you like alongside.

WHAT A FAILURE HERE MEANS
    A failure raised by this file is an environment problem, not a verdict on your
    firmware, and it exits 2 rather than 1 to say so. Either `device.env` is missing or
    still has its placeholder in it, or pyserial is not installed, or the port named
    cannot be opened -- usually because something else already has it open (a screen,
    minicom or picocom session is the usual culprit), or because the probe is unplugged.
    Each of those says which one it is and what to do about it.
"""

from __future__ import annotations

import os
import re
import sys
import threading
import time

# ---------------------------------------------------------------------------
# exit codes
#   0  the evidence is there
#   1  the evidence is not there -- a real verdict on the firmware
#   2  the check could not look -- missing port, missing device.env, no pyserial
# ---------------------------------------------------------------------------
EXIT_OK = 0
EXIT_FAIL = 1
EXIT_SETUP = 2

RECORD_RE = re.compile(r"^([a-z][a-z0-9-]*):[ \t]*(.*?)[ \t]*$")

DEFAULT_BAUD = 115200
PLACEHOLDERS = ("change-me", "changeme", "fill-me-in", "xxx", "<", "your-port")


class Record:
    """One `key: value` line, with the moment it was read."""

    __slots__ = ("key", "value", "t", "raw")

    def __init__(self, key, value, t, raw):
        self.key = key
        self.value = value
        self.t = t
        self.raw = raw

    def fields(self):
        """The value split on whitespace. `frame: 1c ok` -> ['1c', 'ok']."""
        return self.value.split()

    def int_at(self, index, base=10):
        """Field `index` as an int, or None if it is not one."""
        parts = self.fields()
        if index >= len(parts):
            return None
        try:
            return int(parts[index], base)
        except ValueError:
            return None

    def as_int(self, base=10):
        """The whole value as an int, or None. Used for `alive`, `edges`, `resync`."""
        try:
            return int(self.value.strip(), base)
        except ValueError:
            return None

    def __repr__(self):
        return "Record(%r, %r)" % (self.key, self.value)


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------

def _emit(prefix, lines, stream):
    sys.stdout.flush()  # so a verdict never lands before the output it is about
    text = "\n".join(str(x) for x in lines)
    for i, line in enumerate(text.splitlines() or [""]):
        stream.write(("%s %s\n" % (prefix, line)) if i == 0 else ("      %s\n" % line))
    stream.flush()


def fail(*lines):
    """Say why, then exit 1. The tutor reads this out; make it worth hearing."""
    _emit("FAIL:", lines, sys.stderr)
    sys.exit(EXIT_FAIL)


def setup_error(*lines):
    """The check could not run at all. Exit 2 -- not a verdict on the firmware."""
    _emit("CANNOT CHECK:", lines, sys.stderr)
    sys.exit(EXIT_SETUP)


def ok(*lines):
    """Say what was seen, then exit 0. Evidence, not applause."""
    _emit("ok:", lines, sys.stdout)
    sys.exit(EXIT_OK)


def note(*lines):
    _emit("  -", lines, sys.stdout)


# ---------------------------------------------------------------------------
# device.env
# ---------------------------------------------------------------------------

def workspace_root():
    """The directory device.env and CMakeLists.txt live in (the parent of checks/)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_env(required=True):
    """Parse device.env into a dict. Environment variables override it."""
    path = os.path.join(workspace_root(), "device.env")
    values = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[len("export "):].strip()
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                value = value.split("#")[0].strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                values[key.strip().upper()] = value
    elif required:
        setup_error(
            "there is no device.env in %s." % workspace_root(),
            "",
            "The bundle supplied one as a template. It says which serial port your",
            "debug console is on and which VID/PID your device uses. Restore it with",
            "at least these two lines and fill in the port:",
            "",
            "    CONSOLE_PORT=/dev/cu.usbmodem1101",
            "    CONSOLE_BAUD=115200",
        )
    return values


def env_get(values, names, default=None):
    for name in names:
        if os.environ.get(name):
            return os.environ[name]
    for name in names:
        if values.get(name):
            return values[name]
    return default


def console_port(values=None):
    values = load_env() if values is None else values
    port = env_get(values, ("CONSOLE_PORT", "PICO_CONSOLE_PORT", "SERIAL_PORT", "PORT"))
    if not port:
        setup_error(
            "device.env does not name a serial port.",
            "",
            "Add a CONSOLE_PORT line to %s naming the port your" % os.path.join(workspace_root(), "device.env"),
            "debugprobe appears as, then run this check again. To find it:",
            "",
            _port_hint(),
        )
    if any(marker in port.lower() for marker in PLACEHOLDERS):
        setup_error(
            "CONSOLE_PORT in device.env is still the template placeholder (%r)." % port,
            "",
            "Lesson 00 asks you to replace it with the port your debugprobe actually",
            "appears as on this machine:",
            "",
            _port_hint(),
        )
    if sys.platform == "darwin" and port.startswith("/dev/tty."):
        # Opening a tty.* device on macOS blocks waiting for carrier detect, which a
        # Pico never asserts: the check would hang rather than fail. Refuse early.
        setup_error(
            "CONSOLE_PORT is %s, and on macOS that device will hang rather than open." % port,
            "",
            "Use the cu.* name for the same port instead:",
            "",
            "    %s" % port.replace("/dev/tty.", "/dev/cu.", 1),
            "",
            "A tty.* device waits for a carrier-detect signal before it opens, and a",
            "Pico never asserts one. The cu.* (call-up) device for the same port does",
            "not wait. They are the same hardware; only the open semantics differ.",
        )
    return port


def console_baud(values=None):
    values = load_env() if values is None else values
    raw = env_get(values, ("CONSOLE_BAUD", "BAUD"), str(DEFAULT_BAUD))
    try:
        return int(raw)
    except ValueError:
        setup_error("CONSOLE_BAUD in device.env is %r, which is not a number." % raw)


def _port_hint():
    if sys.platform == "darwin":
        return ("    ls /dev/cu.usbmodem*\n"
                "    (the cu.* name, never the matching tty.* one -- a tty.* device\n"
                "     waits for a carrier signal the Pico never sends, and hangs)")
    if sys.platform.startswith("win"):
        return "    [System.IO.Ports.SerialPort]::GetPortNames()"
    return ("    ls -l /dev/serial/by-id/\n"
            "    (the by-id name stays stable; /dev/ttyACM0 renumbers as you replug)")


# ---------------------------------------------------------------------------
# the serial port
# ---------------------------------------------------------------------------

def _import_serial():
    try:
        import serial  # noqa: F401  (pyserial)
    except ImportError:
        setup_error(
            "pyserial is not installed, so no check can read your debug console.",
            "",
            "It is the one dependency these checks have outside the standard library.",
            "Install it into the interpreter that runs these checks:",
            "",
            "    %s -m pip install pyserial" % os.path.basename(sys.executable or "python3"),
        )
    return sys.modules["serial"]


def _known_ports():
    try:
        from serial.tools import list_ports
    except Exception:
        return []
    try:
        return ["%s  (%s)" % (p.device, p.description) for p in list_ports.comports()]
    except Exception:
        return []


def open_console(values=None):
    """Open the debug UART, or explain precisely why it could not be opened."""
    serial = _import_serial()
    values = load_env() if values is None else values
    port = console_port(values)
    baud = console_baud(values)
    try:
        handle = serial.Serial(port=port, baudrate=baud, timeout=0.2)
    except Exception as exc:  # SerialException, OSError, ValueError
        lines = [
            "could not open %s at %d baud: %s" % (port, baud, exc),
            "",
            "Three things cause this, in order of how often:",
            "  1. something else already has the port open -- a screen, minicom,",
            "     picocom or IDE serial monitor. Close it; only one reader at a time.",
            "  2. the debugprobe Pico is unplugged, or its UART is not wired to",
            "     GP0/GP1 on the adapter Pico.",
            "  3. CONSOLE_PORT in device.env names a port that no longer exists --",
            "     the name can change when you move it to another USB socket.",
            "",
            "On Linux, 'Permission denied' here means the port exists and you are not",
            "in the group that owns it: sudo usermod -aG dialout $USER, then log out",
            "and back in.",
        ]
        ports = _known_ports()
        if ports:
            lines += ["", "Serial ports this machine can see right now:"]
            lines += ["    " + p for p in ports]
        else:
            lines += ["", "This machine reports no serial ports at all."]
        setup_error(*lines)
    try:
        handle.reset_input_buffer()
    except Exception:
        pass
    return handle


class ConsoleReader:
    """Reads the console on a thread so a check can watch the port and the operator
    at the same time -- which is what `press Enter when you are done` needs."""

    def __init__(self, handle):
        self.handle = handle
        self.records = []
        self.lines = 0
        self._buffer = b""
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread = None
        self.error = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def _run(self):
        while not self._stop.is_set():
            try:
                chunk = self.handle.read(256)
            except Exception as exc:
                self.error = exc
                return
            if not chunk:
                continue
            self._buffer += chunk
            while b"\n" in self._buffer:
                raw, _, self._buffer = self._buffer.partition(b"\n")
                self._consume(raw.decode("utf-8", "replace").replace("\r", ""))

    def _consume(self, text):
        now = time.time()
        with self._lock:
            self.lines += 1
            match = RECORD_RE.match(text)
            if match:
                self.records.append(Record(match.group(1), match.group(2), now, text))

    def snapshot(self):
        with self._lock:
            return list(self.records)

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        if self.error is not None:
            setup_error(
                "the serial port stopped responding part way through: %s" % self.error,
                "Did the probe get unplugged?",
            )
        return self.snapshot()


# ---------------------------------------------------------------------------
# the two ways a check gathers evidence
# ---------------------------------------------------------------------------

def collect(seconds, handle=None, quiet=False):
    """Read the console for `seconds` and return every record that arrived."""
    handle = open_console() if handle is None else handle
    if not quiet:
        print("Reading the debug console for %.1f seconds..." % seconds)
        sys.stdout.flush()
    reader = ConsoleReader(handle).start()
    deadline = time.time() + seconds
    while time.time() < deadline:
        time.sleep(0.05)
    records = reader.stop()
    if not quiet:
        print("  read %d lines, %d of them log records." % (reader.lines, len(records)))
    return records


def wait_until(predicate, timeout, handle=None, description="", quiet=False):
    """Read until `predicate(records)` is true or `timeout` expires.

    Returns (records, matched). Use it where waiting longer cannot help once the
    thing has happened -- it makes a passing check fast and a failing one bounded."""
    handle = open_console() if handle is None else handle
    if not quiet and description:
        print("Waiting up to %.0fs for %s..." % (timeout, description))
        sys.stdout.flush()
    reader = ConsoleReader(handle).start()
    deadline = time.time() + timeout
    matched = False
    while time.time() < deadline:
        if predicate(reader.snapshot()):
            matched = True
            break
        time.sleep(0.05)
    records = reader.stop()
    return records, matched


def collect_while(instruction, handle=None, min_seconds=0.0, fallback_seconds=15.0):
    """Print an instruction for a human, read the console while they carry it out,
    and stop when they press Enter.

    This is how a hardware course stays honest: the machine reads the evidence, a
    human causes it. The tutor reads the instruction out to the learner."""
    handle = open_console() if handle is None else handle
    print("")
    print("-" * 72)
    print("ACTION NEEDED -- read this out to the learner:")
    print("")
    for line in instruction.strip().splitlines():
        print("    " + line.strip())
    print("")
    print("Recording from the debug console now. Press Enter here when it is done.")
    print("-" * 72)
    sys.stdout.flush()

    reader = ConsoleReader(handle).start()
    started = time.time()
    if sys.stdin is not None and sys.stdin.isatty():
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            print("")
    else:
        print("(stdin is not a terminal, so recording for %.0fs instead.)" % fallback_seconds)
        sys.stdout.flush()
        time.sleep(fallback_seconds)
    remaining = min_seconds - (time.time() - started)
    if remaining > 0:
        time.sleep(remaining)
    time.sleep(0.4)  # let the last line out of the UART FIFO
    records = reader.stop()
    print("  read %d lines, %d of them log records." % (reader.lines, len(records)))
    return records


# ---------------------------------------------------------------------------
# small conveniences over a list of records
# ---------------------------------------------------------------------------

def by_key(records, key):
    return [r for r in records if r.key == key]


def keys_seen(records):
    seen = []
    for record in records:
        if record.key not in seen:
            seen.append(record.key)
    return seen

def last(records, key):
    found = by_key(records, key)
    return found[-1] if found else None


def counter_delta(records, key):
    """(first, last, delta) for a monotonic counter key, or (None, None, None)."""
    values = [r.as_int() for r in by_key(records, key)]
    values = [v for v in values if v is not None]
    if len(values) < 2:
        return (values[0] if values else None, values[0] if values else None, 0 if values else None)
    return values[0], values[-1], values[-1] - values[0]


def describe_traffic(records):
    """A one-line summary of what did arrive. Goes in every failure message, because
    'nothing matched' and 'the wrong thing matched' need different fixes."""
    if not records:
        return "No log records arrived at all."
    counts = {}
    for record in records:
        counts[record.key] = counts.get(record.key, 0) + 1
    parts = ["%s x%d" % (k, counts[k]) for k in keys_seen(records)]
    return "Records that did arrive: " + ", ".join(parts)


def require_records(records, key, lesson_hint):
    """Fail with the same shape of message everywhere a key is simply absent."""
    found = by_key(records, key)
    if found:
        return found
    fail(
        "no `%s:` records arrived on the debug console." % key,
        "",
        lesson_hint,
        "",
        describe_traffic(records),
        "",
        "Remember the contract: one record per line, `%s: <value>`, printed to" % key,
        "stdout over UART0. A line that does not match is ignored by every check,",
        "so a near miss (`%s = 3`, `[%s] 3`) reads to this check as silence." % (key, key),
    )
