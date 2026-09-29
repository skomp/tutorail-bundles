"""Shared helper for the checks that look at your device from the HOST. Imported.

WHAT THIS CHECKS
    Nothing on its own. It finds your adapter on whichever machine the check is
    running on, reads back what that machine believes about it, and decodes HID
    report descriptors into items you can read.

WHAT EVIDENCE IT READS
    The host's own view of the USB bus -- never your firmware's opinion of itself:

      Linux    /sys/bus/usb/devices/*        for enumeration and descriptors
               /sys/class/hidraw/*/device/report_descriptor  for report descriptors
      macOS    system_profiler SPUSBHostDataType -json       for enumeration
               ioreg -a -c IOHIDDevice -r -l                 for report descriptors
      Windows  PowerShell Get-PnpDevice / Get-PnpDeviceProperty  for enumeration

    Two notes that are verified facts, not guesses, and must not be "corrected" back:
    `system_profiler SPUSBDataType` returns an EMPTY ARRAY on macOS 26 and is absent
    from -listDataTypes, so this file uses SPUSBHostDataType. And Windows does not
    hand out a device's real report descriptor at all -- it reconstructs one from
    preparsed data -- so the descriptor checks say so plainly on Windows rather than
    passing or failing on a value the OS invented.

    Which device to look for comes from `device.env` in your workspace root:
    USB_VID / USB_PID (VID / PID accepted too), defaulting to the pid.codes test
    pair 1209:0001 that lesson 11 assigns you.

WHAT A FAILURE HERE MEANS
    "Device not found" means the host never completed enumeration -- so this is
    about descriptors, not about your keyboard logic. A platform that cannot answer
    a question says it cannot, and exits 2; it never guesses an answer, because a
    guessed pass here would send you hunting for a bug in the wrong chapter.
"""

from __future__ import annotations

import json
import os
import plistlib
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _console import env_get, load_env, note, setup_error  # noqa: E402

DEFAULT_VID = 0x1209
DEFAULT_PID = 0x0001


# ---------------------------------------------------------------------------
# which device
# ---------------------------------------------------------------------------

def _parse_id(text, default):
    if not text:
        return default
    text = text.strip().lower()
    match = re.search(r"(?:0x)?([0-9a-f]{1,4})", text)
    if not match:
        return default
    return int(match.group(1), 16)


def target_ids():
    """(vid, pid) from device.env, defaulting to the pid.codes test pair."""
    values = load_env(required=False)
    combined = env_get(values, ("USB_VID_PID", "VIDPID"))
    if combined and ":" in combined:
        left, _, right = combined.partition(":")
        return _parse_id(left, DEFAULT_VID), _parse_id(right, DEFAULT_PID)
    vid = _parse_id(env_get(values, ("USB_VID", "VID")), DEFAULT_VID)
    pid = _parse_id(env_get(values, ("USB_PID", "PID")), DEFAULT_PID)
    return vid, pid


class Device:
    """What the host will say about the device, as far as the host can say it."""

    def __init__(self, vid, pid, product=None, manufacturer=None, serial=None,
                 speed=None, source="", extra=None):
        self.vid = vid
        self.pid = pid
        self.product = product
        self.manufacturer = manufacturer
        self.serial = serial
        self.speed = speed
        self.source = source
        self.extra = extra or {}

    def ident(self):
        return "%04x:%04x" % (self.vid, self.pid)

    def describe(self):
        bits = ["%s" % self.ident()]
        if self.manufacturer:
            bits.append("manufacturer %r" % self.manufacturer)
        if self.product:
            bits.append("product %r" % self.product)
        if self.serial:
            bits.append("serial %r" % self.serial)
        if self.speed:
            bits.append("speed %s" % self.speed)
        return ", ".join(bits)


def _run(argv, timeout=25):
    try:
        done = subprocess.run(argv, capture_output=True, timeout=timeout)
    except FileNotFoundError:
        return None, "%s is not on this machine's PATH" % argv[0]
    except subprocess.TimeoutExpired:
        return None, "%s did not finish within %ds" % (argv[0], timeout)
    if done.returncode != 0:
        err = done.stderr.decode("utf-8", "replace").strip()
        return None, "%s exited %d: %s" % (argv[0], done.returncode, err or "(no output)")
    return done.stdout, None


# ---------------------------------------------------------------------------
# enumeration, per platform
# ---------------------------------------------------------------------------

def _linux_devices():
    found = []
    root = "/sys/bus/usb/devices"
    if not os.path.isdir(root):
        return found

    def read(path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                return handle.read().strip()
        except OSError:
            return None

    for name in sorted(os.listdir(root)):
        base = os.path.join(root, name)
        vid, pid = read(os.path.join(base, "idVendor")), read(os.path.join(base, "idProduct"))
        if not vid or not pid:
            continue
        found.append(Device(
            int(vid, 16), int(pid, 16),
            product=read(os.path.join(base, "product")),
            manufacturer=read(os.path.join(base, "manufacturer")),
            serial=read(os.path.join(base, "serial")),
            speed=read(os.path.join(base, "speed")),
            source="sysfs " + base,
            extra={"sysfs": base},
        ))
    return found


# SPUSBHostDataType does NOT use the key names the retired SPUSBDataType used.
# Verified on macOS 26.6.2: a device carries USBDeviceKeyVendorID / ...ProductID /
# ...VendorName / ...SerialNumber / ...LinkSpeed. Both spellings are accepted here
# so this keeps working on an older macOS and on whatever the next one renames.
MACOS_VID_KEYS = ("USBDeviceKeyVendorID", "vendor_id")
MACOS_PID_KEYS = ("USBDeviceKeyProductID", "product_id")
MACOS_VENDOR_KEYS = ("USBDeviceKeyVendorName", "manufacturer", "vendor_name")
MACOS_SERIAL_KEYS = ("USBDeviceKeySerialNumber", "serial_num")
MACOS_SPEED_KEYS = ("USBDeviceKeyLinkSpeed", "device_speed", "USBKeySpeed")


def _first(node, keys):
    for key in keys:
        if node.get(key):
            return node[key]
    return None


def _macos_items(node, out):
    if isinstance(node, list):
        for item in node:
            _macos_items(item, out)
        return
    if not isinstance(node, dict):
        return
    if _first(node, MACOS_VID_KEYS) and _first(node, MACOS_PID_KEYS):
        out.append(node)
    for key in ("_items", "SPUSBHostDataType"):
        if key in node:
            _macos_items(node[key], out)


def _macos_devices():
    # SPUSBDataType is dead on macOS 26 (empty array, absent from -listDataTypes).
    raw, err = _run(["system_profiler", "SPUSBHostDataType", "-json"])
    if raw is None:
        return [], err
    try:
        blob = json.loads(raw.decode("utf-8", "replace"))
    except ValueError as exc:
        return [], "system_profiler returned something that is not JSON: %s" % exc
    items = []
    _macos_items(blob, items)
    found = []
    for item in items:
        vid = _parse_id(_first(item, MACOS_VID_KEYS), None)
        pid = _parse_id(_first(item, MACOS_PID_KEYS), None)
        if vid is None or pid is None:
            continue
        found.append(Device(
            vid, pid,
            product=item.get("_name"),
            manufacturer=_first(item, MACOS_VENDOR_KEYS),
            serial=_first(item, MACOS_SERIAL_KEYS),
            speed=_first(item, MACOS_SPEED_KEYS),
            source="system_profiler SPUSBHostDataType",
            extra=item,
        ))
    return found, None


POWERSHELL_ENUMERATE = r"""
$ErrorActionPreference = 'Stop'
$out = @()
foreach ($d in Get-PnpDevice -PresentOnly) {
  if ($d.InstanceId -match 'VID_([0-9A-Fa-f]{4})&PID_([0-9A-Fa-f]{4})') {
    $out += [pscustomobject]@{
      vid        = $Matches[1]
      pid        = $Matches[2]
      name       = $d.FriendlyName
      class      = $d.Class
      instance   = $d.InstanceId
      status     = $d.Status
      service    = $d.Service
    }
  }
}
$out | ConvertTo-Json -Depth 3 -Compress
"""


def _powershell(script):
    last = "neither pwsh nor powershell could be run"
    for exe in ("pwsh", "powershell"):
        raw, err = _run([exe, "-NoProfile", "-NonInteractive", "-Command", script], timeout=60)
        if raw is not None:
            return raw, None
        last = err
    return None, last


def _windows_devices():
    raw, err = _powershell(POWERSHELL_ENUMERATE)
    if raw is None:
        return [], err
    text = raw.decode("utf-8", "replace").strip()
    if not text:
        return [], None
    try:
        blob = json.loads(text)
    except ValueError as exc:
        return [], "Get-PnpDevice output was not JSON: %s" % exc
    if isinstance(blob, dict):
        blob = [blob]
    found = []
    for item in blob:
        found.append(Device(
            int(item["vid"], 16), int(item["pid"], 16),
            product=item.get("name"),
            manufacturer=None,
            serial=None,
            speed=None,
            source="Get-PnpDevice",
            extra=item,
        ))
    return found, None


def all_devices():
    """Every USB device the host can see, plus a note if the platform half-answered."""
    if sys.platform.startswith("linux"):
        devices = _linux_devices()
        if not devices:
            return [], "/sys/bus/usb/devices is empty or absent -- is this a container without sysfs?"
        return devices, None
    if sys.platform == "darwin":
        return _macos_devices()
    if sys.platform.startswith("win"):
        return _windows_devices()
    return [], "this check does not know how to enumerate USB on platform %r" % sys.platform


def find_device(vid=None, pid=None):
    """The matching Device, or None. Second return value is every device seen."""
    if vid is None or pid is None:
        want_vid, want_pid = target_ids()
        vid = want_vid if vid is None else vid
        pid = want_pid if pid is None else pid
    devices, err = all_devices()
    if err and not devices:
        setup_error(
            "could not ask this host what is on its USB bus: %s" % err,
            "",
            "That is a problem with the check's view of the machine, not with your",
            "firmware. Run the check on the machine the adapter is plugged into.",
        )
    for device in devices:
        if device.vid == vid and device.pid == pid:
            return device, devices
    return None, devices


def fail_not_found(vid, pid, devices):
    lines = [
        "no device with VID:PID %04x:%04x is on this host's USB bus." % (vid, pid),
        "",
        "The host never completed enumeration with those ids, so either the adapter",
        "is not plugged into THIS machine, or its device descriptor does not carry",
        "the ids device.env names, or enumeration is failing outright.",
        "",
        "When enumeration fails outright the usual causes are, in order:",
        "  * bLength or bDescriptorType wrong on one descriptor, so the host stops",
        "    parsing and gives up on the device;",
        "  * wTotalLength in the configuration descriptor not equal to the real",
        "    total of everything that follows it;",
        "  * the device task never serviced, so the control transfer times out.",
        "",
        "Check the debug console at the same time: if `alive` is still ticking, the",
        "firmware is running and this is a descriptor problem, not a crash.",
    ]
    if devices:
        lines += ["", "Devices this host does see (%d):" % len(devices)]
        for device in devices[:40]:
            lines.append("    " + device.describe())
    return lines


# ---------------------------------------------------------------------------
# HID report descriptors -- the item stack language
# ---------------------------------------------------------------------------

TYPE_MAIN, TYPE_GLOBAL, TYPE_LOCAL = 0, 1, 2

MAIN_TAGS = {8: "Input", 9: "Output", 10: "Collection", 11: "Feature", 12: "End Collection"}
GLOBAL_TAGS = {
    0: "Usage Page", 1: "Logical Minimum", 2: "Logical Maximum",
    3: "Physical Minimum", 4: "Physical Maximum", 5: "Unit Exponent",
    6: "Unit", 7: "Report Size", 8: "Report ID", 9: "Report Count",
    10: "Push", 11: "Pop",
}
LOCAL_TAGS = {
    0: "Usage", 1: "Usage Minimum", 2: "Usage Maximum", 3: "Designator Index",
    4: "Designator Minimum", 5: "Designator Maximum", 7: "String Index",
    8: "String Minimum", 9: "String Maximum", 10: "Delimiter",
}
COLLECTION_KINDS = {0: "Physical", 1: "Application", 2: "Logical", 3: "Report",
                    4: "Named Array", 5: "Usage Switch", 6: "Usage Modifier"}

USAGE_PAGE_GENERIC_DESKTOP = 0x01
USAGE_PAGE_KEYBOARD = 0x07
USAGE_PAGE_LED = 0x08
USAGE_KEYBOARD = 0x06

PAGE_NAMES = {0x01: "Generic Desktop", 0x07: "Keyboard/Keypad", 0x08: "LED",
              0x0C: "Consumer"}


class DescriptorError(Exception):
    pass


class Item:
    __slots__ = ("type", "tag", "data", "size", "offset", "raw")

    def __init__(self, type_, tag, data, size, offset, raw):
        self.type = type_
        self.tag = tag
        self.data = data
        self.size = size
        self.offset = offset
        self.raw = raw

    @property
    def signed(self):
        if self.size == 0:
            return 0
        bits = self.size * 8
        value = self.data
        return value - (1 << bits) if value & (1 << (bits - 1)) else value

    def name(self):
        table = {TYPE_MAIN: MAIN_TAGS, TYPE_GLOBAL: GLOBAL_TAGS, TYPE_LOCAL: LOCAL_TAGS}
        return table.get(self.type, {}).get(self.tag, "tag %d (type %d)" % (self.tag, self.type))


def parse_items(data):
    """Split a report descriptor into short items. Raises DescriptorError if the
    byte stream runs out mid-item -- which is itself a real and common bug."""
    items = []
    index = 0
    length = len(data)
    while index < length:
        prefix = data[index]
        if prefix == 0xFE:  # long item: never used by a keyboard, but parse past it
            if index + 2 >= length:
                raise DescriptorError("long item at offset %d is truncated" % index)
            size = data[index + 1]
            tag = data[index + 2]
            end = index + 3 + size
            if end > length:
                raise DescriptorError("long item at offset %d runs past the end" % index)
            items.append(Item(-1, tag, 0, size, index, data[index:end]))
            index = end
            continue
        size = prefix & 0x03
        if size == 3:
            size = 4
        type_ = (prefix >> 2) & 0x03
        tag = (prefix >> 4) & 0x0F
        end = index + 1 + size
        if end > length:
            raise DescriptorError(
                "item at offset %d claims %d data bytes but only %d remain -- the "
                "descriptor is truncated or its length is wrong"
                % (index, size, length - index - 1))
        value = 0
        for shift, byte in enumerate(data[index + 1:end]):
            value |= byte << (8 * shift)
        items.append(Item(type_, tag, value, size, index, data[index:end]))
        index = end
    return items


class Field:
    """One Input/Output/Feature main item, with the global and local state that
    was in force when it was declared. This is what 'walk the parser output item
    by item' means in lesson 12."""

    def __init__(self):
        self.kind = ""
        self.flags = 0
        self.report_id = None
        self.usage_page = None
        self.usages = []
        self.usage_min = None
        self.usage_max = None
        self.logical_min = None
        self.logical_max = None
        self.report_size = 0
        self.report_count = 0
        self.collections = []
        self.offset = 0

    @property
    def bits(self):
        return self.report_size * self.report_count

    @property
    def is_constant(self):
        return bool(self.flags & 0x01)

    @property
    def is_variable(self):
        return bool(self.flags & 0x02)

    @property
    def is_array(self):
        return not self.is_variable

    def flag_names(self):
        names = ["Constant" if self.is_constant else "Data",
                 "Variable" if self.is_variable else "Array",
                 "Relative" if self.flags & 0x04 else "Absolute"]
        if self.flags & 0x08:
            names.append("Wrap")
        if self.flags & 0x40:
            names.append("Null state")
        return names

    def usage_text(self):
        if self.usage_min is not None or self.usage_max is not None:
            return "usages 0x%02x..0x%02x" % (self.usage_min or 0, self.usage_max or 0)
        if self.usages:
            return "usages " + ", ".join("0x%02x" % u for u in self.usages[:8]) + \
                   ("..." if len(self.usages) > 8 else "")
        return "no usage declared"

    def describe(self):
        page = PAGE_NAMES.get(self.usage_page, "page 0x%02x" % (self.usage_page or 0))
        return "%-6s %2d x %2d bits  %-24s %-22s  logical %s..%s" % (
            self.kind, self.report_count, self.report_size,
            "/".join(self.flag_names()), "%s: %s" % (page, self.usage_text()),
            self.logical_min, self.logical_max)


class Parsed:
    def __init__(self):
        self.fields = []
        self.report_ids = []
        self.top_level = []          # [(usage_page, usage)]
        self.items = []
        self.raw = b""

    def of_kind(self, kind, report_id=None):
        return [f for f in self.fields
                if f.kind == kind and (report_id is None or f.report_id == report_id)]

    def bits_of(self, kind, report_id=None):
        return sum(f.bits for f in self.of_kind(kind, report_id))

    def walk(self):
        return [f.describe() for f in self.fields]


def parse_report_descriptor(data):
    """Run the item stack language and return the fields it declares."""
    parsed = Parsed()
    parsed.raw = bytes(data)
    parsed.items = parse_items(data)

    glob = {"usage_page": None, "logical_min": None, "logical_max": None,
            "report_size": 0, "report_count": 0, "report_id": None}
    stack = []
    local = {"usages": [], "usage_min": None, "usage_max": None}
    collections = []

    def clear_local():
        local["usages"] = []
        local["usage_min"] = None
        local["usage_max"] = None

    for item in parsed.items:
        if item.type == TYPE_GLOBAL:
            if item.tag == 0:
                glob["usage_page"] = item.data
            elif item.tag == 1:
                glob["logical_min"] = item.signed
            elif item.tag == 2:
                # logical maximum is signed, but 0xFF as one byte is meant as 255
                # by nearly every keyboard descriptor in existence; keep both.
                glob["logical_max"] = item.signed if item.signed >= 0 else item.data
            elif item.tag == 7:
                glob["report_size"] = item.data
            elif item.tag == 8:
                glob["report_id"] = item.data
                if item.data not in parsed.report_ids:
                    parsed.report_ids.append(item.data)
            elif item.tag == 9:
                glob["report_count"] = item.data
            elif item.tag == 10:
                stack.append(dict(glob))
            elif item.tag == 11:
                if stack:
                    glob = stack.pop()
        elif item.type == TYPE_LOCAL:
            if item.tag == 0:
                local["usages"].append(item.data)
            elif item.tag == 1:
                local["usage_min"] = item.data
            elif item.tag == 2:
                local["usage_max"] = item.data
        elif item.type == TYPE_MAIN:
            if item.tag == 10:  # Collection
                usage = local["usages"][0] if local["usages"] else None
                collections.append((item.data, glob["usage_page"], usage))
                if len(collections) == 1:  # opened at depth zero: a top-level collection
                    parsed.top_level.append((glob["usage_page"], usage))
                clear_local()
            elif item.tag == 12:  # End Collection
                if collections:
                    collections.pop()
                clear_local()
            elif item.tag in (8, 9, 11):
                field = Field()
                field.kind = {8: "input", 9: "output", 11: "feature"}[item.tag]
                field.flags = item.data
                field.report_id = glob["report_id"]
                field.usage_page = glob["usage_page"]
                field.usages = list(local["usages"])
                field.usage_min = local["usage_min"]
                field.usage_max = local["usage_max"]
                field.logical_min = glob["logical_min"]
                field.logical_max = glob["logical_max"]
                field.report_size = glob["report_size"]
                field.report_count = glob["report_count"]
                field.collections = list(collections)
                field.offset = item.offset
                parsed.fields.append(field)
                clear_local()
            else:
                clear_local()
    return parsed


# ---------------------------------------------------------------------------
# getting a report descriptor off the host
# ---------------------------------------------------------------------------

class HidInterface:
    """One HID top-level collection as the host sees it, with its descriptor."""

    def __init__(self, vid, pid, descriptor, source, usage_page=None, usage=None,
                 name=None):
        self.vid = vid
        self.pid = pid
        self.descriptor = descriptor
        self.source = source
        self.usage_page = usage_page
        self.usage = usage
        self.name = name

    def label(self):
        bits = [self.name or "HID interface"]
        if self.usage_page is not None:
            bits.append("usage page 0x%02x usage 0x%02x" % (self.usage_page, self.usage or 0))
        bits.append("%d descriptor bytes" % len(self.descriptor))
        return ", ".join(bits)


def _linux_hid_interfaces(vid, pid):
    found = []
    root = "/sys/class/hidraw"
    if not os.path.isdir(root):
        return found
    for name in sorted(os.listdir(root)):
        device = os.path.join(root, name, "device")
        uevent = os.path.join(device, "uevent")
        try:
            with open(uevent, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError:
            continue
        match = re.search(r"HID_ID=[0-9A-Fa-f]+:0*([0-9A-Fa-f]{1,8}):0*([0-9A-Fa-f]{1,8})", text)
        if not match:
            continue
        if int(match.group(1), 16) != vid or int(match.group(2), 16) != pid:
            continue
        hid_name = None
        nm = re.search(r"HID_NAME=(.*)", text)
        if nm:
            hid_name = nm.group(1).strip()
        try:
            with open(os.path.join(device, "report_descriptor"), "rb") as handle:
                blob = handle.read()
        except OSError as exc:
            note("could not read %s/report_descriptor: %s" % (device, exc))
            continue
        found.append(HidInterface(vid, pid, blob, "/dev/" + name, name=hid_name or name))
    return found


def _macos_hid_interfaces(vid, pid):
    raw, err = _run(["ioreg", "-a", "-c", "IOHIDDevice", "-r", "-l"])
    if raw is None:
        setup_error("could not run ioreg to read HID descriptors: %s" % err)
    try:
        blob = plistlib.loads(raw)
    except Exception as exc:
        setup_error("ioreg returned a property list this check cannot parse: %s" % exc)
    entries = []

    def walk(node):
        if isinstance(node, list):
            for child in node:
                walk(child)
            return
        if not isinstance(node, dict):
            return
        if "VendorID" in node and "ProductID" in node:
            entries.append(node)
        for child in node.get("IORegistryEntryChildren", []) or []:
            walk(child)

    walk(blob)
    found = []
    for entry in entries:
        if entry.get("VendorID") != vid or entry.get("ProductID") != pid:
            continue
        descriptor = entry.get("ReportDescriptor")
        if not isinstance(descriptor, (bytes, bytearray)):
            continue
        found.append(HidInterface(
            vid, pid, bytes(descriptor),
            "ioreg IOHIDDevice",
            usage_page=entry.get("PrimaryUsagePage"),
            usage=entry.get("PrimaryUsage"),
            name=entry.get("Product") or entry.get("IORegistryEntryName"),
        ))
    return found


def _dedupe(interfaces):
    """ioreg lists the same collection several times -- once per client of it. Two
    entries with the same usage and the same descriptor bytes are one interface, and
    counting them twice would make a single-interface device look composite."""
    seen = {}
    for interface in interfaces:
        key = (interface.usage_page, interface.usage, interface.descriptor)
        if key not in seen:
            seen[key] = interface
    return list(seen.values())


def hid_interfaces(vid=None, pid=None):
    """Every HID top-level collection this host exposes for the device.

    Windows is honestly refused: it does not return the device's report
    descriptor, it reconstructs one from preparsed data, so a pass or a fail here
    would be a verdict on Windows' reconstruction and not on what you wrote."""
    if vid is None or pid is None:
        vid, pid = target_ids()
    if sys.platform.startswith("linux"):
        return _dedupe(_linux_hid_interfaces(vid, pid))
    if sys.platform == "darwin":
        return _dedupe(_macos_hid_interfaces(vid, pid))
    if sys.platform.startswith("win"):
        setup_error(
            "Windows cannot give this check your real HID report descriptor.",
            "",
            "Windows does not pass a GET_DESCRIPTOR(REPORT) request through to the",
            "device. It hands out a descriptor RECONSTRUCTED from HIDP preparsed",
            "data, so checking it would check Windows' reconstruction rather than",
            "the bytes you wrote. USBTreeView's own documentation says the same.",
            "",
            "Two honest routes:",
            "  * run this check on Linux or macOS, where the raw bytes are readable",
            "    (/sys/class/hidraw/*/device/report_descriptor, or ioreg);",
            "  * or use hidapitester --vidpid %04x:%04x --get-report-descriptor" % (vid, pid),
            "    and read the bytes out against your source by hand.",
            "",
            "Lesson 12 says this: Windows learners are not promised byte-for-byte",
            "fidelity, and that limitation is the lesson, not a workaround.",
        )
    setup_error("this check cannot read HID descriptors on platform %r" % sys.platform)


def keyboard_interface(interfaces):
    """The boot-keyboard collection among them, by its parsed top-level usage."""
    for interface in interfaces:
        if interface.usage_page == USAGE_PAGE_GENERIC_DESKTOP and interface.usage == USAGE_KEYBOARD:
            return interface
    for interface in interfaces:
        try:
            parsed = parse_report_descriptor(interface.descriptor)
        except DescriptorError:
            continue
        if (USAGE_PAGE_GENERIC_DESKTOP, USAGE_KEYBOARD) in parsed.top_level:
            return interface
        if any(f.usage_page == USAGE_PAGE_KEYBOARD for f in parsed.fields):
            return interface
    return None


def hexdump(data, per_line=16):
    lines = []
    for offset in range(0, len(data), per_line):
        chunk = data[offset:offset + per_line]
        lines.append("  %04x  %s" % (offset, " ".join("%02x" % b for b in chunk)))
    return lines
