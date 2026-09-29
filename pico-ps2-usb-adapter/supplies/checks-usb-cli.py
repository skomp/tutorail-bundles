#!/usr/bin/env python3
"""The checks that read evidence off the HOST's view of your device.

WHAT THIS CHECKS
    Whatever the first argument names:

        enumerate   lesson 11  the host completed enumeration, with your ids and strings
        descriptor  lesson 12  your HID report descriptor says what lesson 12 requires
        vendor      offered    a second interface is live, and the keyboard one is intact
        nkro        offered    more than six keys can be reported, boot report untouched

WHAT EVIDENCE IT READS
    The host's own record of the device, never your firmware's opinion of itself --
    sysfs on Linux, `system_profiler SPUSBHostDataType` and `ioreg` on macOS,
    `Get-PnpDevice` on Windows. Which device to look for comes from USB_VID/USB_PID
    in `device.env`, defaulting to the pid.codes test pair 1209:0001.

    `descriptor` reads the report descriptor back and PARSES it -- it runs the HID
    item stack language, builds the fields the descriptor declares, and checks the
    structure against what lesson 12 requires. It is not a byte pattern match, so a
    descriptor written differently from the course's own but structurally correct
    passes, and one that pattern-matches but declares the wrong thing does not.

    These checks stop being the source of evidence after lesson 13. A host cannot
    read the input reports of a keyboard collection -- Windows, macOS and Chrome each
    refuse -- so everything about key state is checked on the debug UART instead.

WHAT A FAILURE HERE MEANS
    Your descriptors, nearly always: the bytes the device hands over during
    enumeration. A CANNOT CHECK result means this host cannot answer the question --
    Windows does not return real report descriptors, it reconstructs them -- and that
    is a limit of the machine, not a verdict on your firmware.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _console import EXIT_OK, EXIT_SETUP, fail, note, ok  # noqa: E402
from _usb import (  # noqa: E402
    USAGE_PAGE_GENERIC_DESKTOP,
    USAGE_PAGE_KEYBOARD,
    USAGE_PAGE_LED,
    USAGE_KEYBOARD,
    DescriptorError,
    fail_not_found,
    find_device,
    hexdump,
    hid_interfaces,
    keyboard_interface,
    parse_report_descriptor,
    target_ids,
)

COMMANDS = {}

STOCK_STRINGS = {"tinyusb", "tinyusb device", "tinyusb keyboard", "raspberry pi",
                 "pico", "example device", "generic usb keyboard"}


def command(name):
    def register(function):
        COMMANDS[name] = function
        return function
    return register


def parsed_or_fail(interface):
    try:
        return parse_report_descriptor(interface.descriptor)
    except DescriptorError as exc:
        fail("the report descriptor the host read back does not parse: %s" % exc,
             "",
             "The item stack language is a stream of self-describing items: one prefix",
             "byte says the item's type, its tag and how many data bytes follow. If the",
             "stream runs out mid-item, a length somewhere is wrong -- most often the",
             "array you pass to the HID descriptor callback is longer or shorter than",
             "the length you report alongside it.",
             "",
             "The bytes the host handed over:",
             *hexdump(interface.descriptor))


def show_walk(parsed, interface):
    print("Report descriptor read from %s (%d bytes, %d items, %d fields):"
          % (interface.source, len(interface.descriptor), len(parsed.items),
             len(parsed.fields)))
    for line in parsed.walk():
        print("    " + line)
    if parsed.report_ids:
        print("    report IDs declared: " +
              ", ".join(str(i) for i in parsed.report_ids))
    print("")


# ---------------------------------------------------------------------------
# lesson 11 -- enumerates-as-hid
# ---------------------------------------------------------------------------

@command("enumerate")
def cmd_enumerate():
    vid, pid = target_ids()
    device, everything = find_device(vid, pid)
    if device is None:
        fail(*fail_not_found(vid, pid, everything))

    print("The host sees: %s" % device.describe())
    print("  (via %s)" % device.source)
    print("")

    problems = []
    if not device.product:
        problems.append(
            "no product string. Lesson 11 asks for your own strings, which means a "
            "string descriptor for the product AND a language-ID descriptor at index "
            "0 -- index 0 is not a string, it is the list of languages your strings "
            "are in, and a host that asks for it and gets a string gives up on the "
            "rest of them.")
    elif device.product.strip().lower() in STOCK_STRINGS:
        problems.append(
            "the product string is still the example's (%r). The completion condition "
            "for lesson 11 is the host enumerating with YOUR ids and YOUR strings; "
            "the point is that you wrote the answers the host asked for."
            % device.product)
    if device.manufacturer is not None and not device.manufacturer.strip():
        problems.append("the manufacturer string is present but empty.")

    if (vid, pid) == (0x1209, 0x0001):
        note("VID:PID is the pid.codes test pair 1209:0001, which is what this course",
             "assigns. It is allocated for exactly this and explicitly not for anything",
             "distributed. Ask the learner why making one up is not an option for a",
             "device that leaves the bench.")

    interfaces = []
    if not sys.platform.startswith("win"):
        try:
            interfaces = hid_interfaces(vid, pid)
        except SystemExit:
            raise
        except Exception as exc:  # a HID read failing must not mask enumeration
            note("could not list HID interfaces (%s); enumeration itself is what this "
                 "check is about, so carrying on." % exc)
        if not interfaces:
            problems.append(
                "the device enumerated, but this host has bound no HID interface to "
                "it. That is bInterfaceClass: 3 is HID, and with anything else no "
                "driver claims the interface -- the device appears on the bus and is "
                "nothing in particular. Check bInterfaceClass, bInterfaceSubClass "
                "(1 for boot) and bInterfaceProtocol (1 for keyboard).")
        else:
            for interface in interfaces:
                print("  HID interface: " + interface.label())
            print("")

    if problems:
        lines = ["the device enumerated, but not the way lesson 11 asks for.", ""]
        for problem in problems:
            lines.append("  * " + problem)
        fail(*lines)

    ok("the host enumerated your device from descriptors you wrote.",
       device.describe(),
       "%d HID interface(s) bound." % len(interfaces) if interfaces else
       "(HID interface listing not available on this platform.)")


# ---------------------------------------------------------------------------
# lesson 12 -- report-descriptor-sane
# ---------------------------------------------------------------------------

def keyboard_parsed():
    """The keyboard collection's descriptor, parsed, or a failure explaining why not."""
    vid, pid = target_ids()
    device, everything = find_device(vid, pid)
    if device is None:
        fail(*fail_not_found(vid, pid, everything))
    interfaces = hid_interfaces(vid, pid)   # exits with a clear message on Windows
    if not interfaces:
        fail("the device is on the bus but exposes no HID interface this host can read.",
             "",
             "Enumeration succeeded and HID binding did not. The interface descriptor",
             "is what decides that: bInterfaceClass 3, and for this course subclass 1",
             "and protocol 1, which is boot keyboard. Check also that the HID class",
             "descriptor declares a report descriptor length equal to the length of",
             "the descriptor you actually return.")
    interface = keyboard_interface(interfaces)
    if interface is None:
        fail("none of the %d HID interface(s) is a keyboard." % len(interfaces),
             *["    " + i.label() for i in interfaces],
             "",
             "A keyboard is a top-level Application collection with usage page 0x01",
             "(Generic Desktop) and usage 0x06 (Keyboard). Without that the host will",
             "still bind HID, but nothing about the device says 'keyboard', so no",
             "BIOS will touch it and no OS will route its reports to the text field",
             "that has focus.")
    return interface, parsed_or_fail(interface)


@command("descriptor")
def cmd_descriptor():
    interface, parsed = keyboard_parsed()
    show_walk(parsed, interface)

    inputs = parsed.of_kind("input")
    outputs = parsed.of_kind("output")
    problems = []
    passed = []

    # 1. no report ID
    if parsed.report_ids:
        problems.append((
            "report ID present", [
                "the descriptor declares report ID(s) %s."
                % ", ".join(str(i) for i in parsed.report_ids),
                "This interface must have NO report ID. A report ID prepends a byte to",
                "every report, making the input report nine bytes where boot protocol",
                "requires eight, and a BIOS -- which does not parse report descriptors",
                "at all, it assumes the boot layout -- reads nonsense.",
                "The usual cause is a second top-level collection on this interface,",
                "which forces IDs on everything. A debug, vendor or consumer channel",
                "belongs on a SEPARATE INTERFACE, not a second collection here."]))
    else:
        passed.append("no report ID is declared, so reports are the bare boot layout")

    # 2. eight-byte input report
    input_bits = parsed.bits_of("input")
    if input_bits != 64:
        problems.append((
            "input report size", [
                "the input items add up to %d bits (%.2f bytes), not 64."
                % (input_bits, input_bits / 8.0),
                "Boot protocol fixes the input report at eight bytes: one modifier",
                "bitmap, one reserved byte, six key slots. The arithmetic is report",
                "size times report count, summed over every input item:",
                "    8 x 1 bit  (modifiers)  = 8",
                "    1 x 8 bits (reserved)   = 8",
                "    6 x 8 bits (key array)  = 48",
                "                             ---",
                "                              64 bits = 8 bytes",
                "What this descriptor declares, item by item:"] +
            ["    %s" % f.describe() for f in inputs]))
    else:
        passed.append("the input items add up to exactly 64 bits: an eight-byte report")

    # 3. modifiers as a bitmap
    modifier = None
    for field in inputs:
        if (field.usage_page == USAGE_PAGE_KEYBOARD and field.usage_min is not None
                and field.usage_min >= 0xE0 and (field.usage_max or 0) <= 0xE7):
            modifier = field
            break
    if modifier is None:
        candidates = [f for f in inputs if f.report_size == 1 and f.report_count == 8]
        modifier = candidates[0] if candidates else None
    if modifier is None:
        problems.append((
            "modifier bitmap", [
                "no input item declares the modifier keys.",
                "The eight modifiers -- left and right control, shift, alt and GUI --",
                "are usages 0xE0 to 0xE7 on the keyboard page, and they occupy byte 0",
                "as eight single-bit fields."]))
    elif not modifier.is_variable:
        problems.append((
            "modifiers declared as an ARRAY", [
                "the modifier item is an Array, and it must be a Variable (a bitmap):",
                "    " + modifier.describe(),
                "",
                "This is the central conceptual trap of the whole chapter, so it is",
                "worth saying out loud. An ARRAY item means 'here are N slots, each",
                "holding the index of something that is currently on'. A VARIABLE item",
                "means 'here are N fields, one per usage, each saying whether that one",
                "thing is on'. Modifiers must be variable because they are genuinely",
                "simultaneous: Control and Shift and Alt can all be down at once, and a",
                "bitmap says so in one byte. Declared as an array, the host reads byte 0",
                "as a slot holding one usage index, and Shift+Control becomes whichever",
                "of them you wrote last.",
                "",
                "The flags on the Input item carry this: bit 1 set means Variable,",
                "clear means Array. This item's flags are 0x%02x (%s)."
                % (modifier.flags, "/".join(modifier.flag_names()))]))
    elif modifier.report_size != 1 or modifier.report_count != 8:
        problems.append((
            "modifier bitmap shape", [
                "the modifier item is %d x %d bits, and it must be 8 x 1."
                % (modifier.report_count, modifier.report_size),
                "    " + modifier.describe(),
                "Eight modifiers, one bit each, one byte in total."]))
    else:
        passed.append("the eight modifiers are a Variable item, 8 x 1 bit: a bitmap")

    # 4. the reserved byte
    reserved = None
    if modifier is not None and modifier in inputs:
        after = inputs[inputs.index(modifier) + 1:]
        for field in after:
            if field.is_constant and field.bits == 8:
                reserved = field
                break
            break  # only the item immediately after counts
    if reserved is None:
        problems.append((
            "reserved byte", [
                "there is no constant eight-bit input item between the modifiers and",
                "the key array.",
                "Byte 1 of the boot report is reserved. It is declared as a padding",
                "item -- report size 8, report count 1, Constant -- and it is not",
                "optional: leaving it out moves every key slot one byte earlier, and a",
                "BIOS reading the fixed boot layout finds the first key where it",
                "expects the reserved byte. The device works on a desktop, which parses",
                "your descriptor, and fails in firmware setup, which does not.",
                "The input items as declared:"] +
            ["    %s" % f.describe() for f in inputs]))
    else:
        passed.append("a Constant eight-bit item sits where the reserved byte belongs")

    # 5. the six keys as an array
    keys = None
    for field in inputs:
        if field is modifier or field is reserved:
            continue
        if field.usage_page == USAGE_PAGE_KEYBOARD and field.report_size == 8:
            keys = field
            break
    if keys is None:
        for field in inputs:
            if field not in (modifier, reserved) and not field.is_constant:
                keys = field
                break
    if keys is None:
        problems.append((
            "six-key array", [
                "no input item declares the keys themselves.",
                "Six slots of eight bits each, on the keyboard page, holding HID usage",
                "codes for whatever is currently down."]))
    elif not keys.is_array:
        problems.append((
            "the keys declared as a BITMAP", [
                "the key item is a Variable, and for the boot report it must be an Array:",
                "    " + keys.describe(),
                "",
                "This is the same trap as the modifiers, mirrored, and it is the other",
                "half of the chapter's central point. A bitmap over the whole keyboard",
                "page would need one bit per usage -- around 30 bytes -- and boot",
                "protocol has eight. The boot report instead carries six SLOTS, each",
                "holding the usage code of one key that is down: 'A and Shift are down'",
                "is expressed as the number 0x04 sitting in a slot, not as bit 4 being",
                "set somewhere. That is what costs you six-key rollover, and it is",
                "exactly the trade the offered NKRO lesson revisits.",
                "",
                "This item's flags are 0x%02x (%s): bit 1 is set, meaning Variable."
                % (keys.flags, "/".join(keys.flag_names()))]))
    elif keys.report_count != 6 or keys.report_size != 8:
        problems.append((
            "six-key array shape", [
                "the key array is %d x %d bits and it must be 6 x 8."
                % (keys.report_count, keys.report_size),
                "    " + keys.describe(),
                "Six slots, one byte each -- six-key rollover, with 0x01 (ErrorRollOver)",
                "in every slot when a seventh key goes down."]))
    else:
        passed.append("the six keys are an Array item, 6 x 8 bits: usage codes in slots")

    if keys is not None and keys.is_array:
        if (keys.logical_max or 0) < 0x65:
            problems.append((
                "key array logical maximum", [
                    "the key array's logical maximum is %s, which is below 0x65 (101)."
                    % keys.logical_max,
                    "    " + keys.describe(),
                    "For an array item, logical minimum and maximum bound the usage",
                    "index a slot may hold. Stopping short of the highest usage you",
                    "intend to send means the host is entitled to ignore those keys --",
                    "you declared they could not occur. Beware also that HID logical",
                    "values are SIGNED: a one-byte maximum of 0xFF means -1 to a strict",
                    "parser, so where you want 255 write it as the two-byte item",
                    "0x26 0xFF 0x00."]))

    # 6. the LED output report
    output_bits = parsed.bits_of("output")
    led = [f for f in outputs if f.usage_page == USAGE_PAGE_LED]
    if output_bits == 0:
        problems.append((
            "LED output report", [
                "the descriptor declares no output item at all.",
                "The boot keyboard has a one-byte output report: five LED bits (Num,",
                "Caps, Scroll, Compose, Kana) plus three bits of padding. Without it",
                "the host has no way to tell the keyboard that Caps Lock is on, and",
                "lesson 15 has nothing to receive.",
                "The expected shape is:",
                "    5 x 1 bit  LED page, usages 1..5  (Variable)",
                "    1 x 3 bits Constant padding",
                "                                      --- 8 bits = 1 byte"]))
    elif output_bits != 8:
        problems.append((
            "LED output report size", [
                "the output items add up to %d bits, not 8." % output_bits,
                "Five LED bits and three bits of padding make one byte. Padding is not",
                "optional: a report that is not a whole number of bytes is rounded up",
                "by the host anyway, and then the bits you did not declare are whatever",
                "the host felt like putting there.",
                "The output items as declared:"] +
            ["    %s" % f.describe() for f in outputs]))
    elif not led:
        problems.append((
            "LED output usages", [
                "there is a one-byte output report, but nothing in it is on the LED",
                "usage page (0x08).",
                "The bits have to be named or the host does not know which one is Caps",
                "Lock. Usages 0x01 to 0x05 on page 0x08 are Num, Caps, Scroll, Compose",
                "and Kana, in that order."]))
    else:
        passed.append("a one-byte output report with LED usages: eight bits, five named")

    # top-level collection sanity
    if len(parsed.top_level) > 1:
        problems.append((
            "more than one top-level collection", [
                "this interface declares %d top-level collections: %s"
                % (len(parsed.top_level),
                   ", ".join("page 0x%02x usage 0x%02x" % (p or 0, u or 0)
                             for p, u in parsed.top_level)),
                "A second top-level collection on this interface forces report IDs on",
                "every report, which makes the input report nine bytes and breaks boot",
                "protocol silently: the device still works on a running desktop and",
                "fails in firmware setup. Put the extra collection on its own",
                "interface."]))
    elif parsed.top_level:
        page, usage = parsed.top_level[0]
        if page != USAGE_PAGE_GENERIC_DESKTOP or usage != USAGE_KEYBOARD:
            problems.append((
                "top-level collection", [
                    "the one top-level collection is page 0x%02x usage 0x%02x, and a"
                    % (page or 0, usage or 0),
                    "keyboard is page 0x01 (Generic Desktop) usage 0x06 (Keyboard)."]))
        else:
            passed.append("one top-level Application collection: Generic Desktop / Keyboard")

    if problems:
        lines = ["the report descriptor does not describe the report lesson 12 asks for.",
                 "%d of the structural claims fail." % len(problems), ""]
        for name, detail in problems:
            lines.append("  [%s]" % name)
            lines += ["    " + line for line in detail]
            lines.append("")
        if passed:
            lines.append("  What is right:")
            lines += ["    * " + p for p in passed]
            lines.append("")
        lines.append("  The bytes the host read back:")
        lines += hexdump(interface.descriptor)
        fail(*lines)

    print("The bytes the host read back:")
    for line in hexdump(interface.descriptor):
        print(line)
    print("")
    ok("the report descriptor describes a boot-protocol keyboard, item by item.",
       *["  * " + p for p in passed],
       )


# ---------------------------------------------------------------------------
# offered lesson -- second-interface-live
# ---------------------------------------------------------------------------

@command("vendor")
def cmd_vendor():
    vid, pid = target_ids()
    device, everything = find_device(vid, pid)
    if device is None:
        fail(*fail_not_found(vid, pid, everything))
    interfaces = hid_interfaces(vid, pid)
    for interface in interfaces:
        print("  " + interface.label())
    print("")

    if len(interfaces) < 2:
        fail("the host binds %d HID interface(s) to this device, and this lesson needs two."
             % len(interfaces),
             "",
             "A composite device declares more than one interface in its configuration",
             "descriptor, and each one gets its own HID descriptor, its own report",
             "descriptor and its own endpoint. Three things to check when the second",
             "one does not appear:",
             "  * bNumInterfaces in the configuration descriptor still says 1;",
             "  * wTotalLength was not increased to cover the new interface, so the",
             "    host stops parsing where the old total ended and never sees it;",
             "  * the second interface reuses the first one's endpoint number.",
             "",
             "And the failure this lesson is about: adding a second top-level",
             "COLLECTION to the keyboard interface is not the same thing, and it is",
             "the wrong answer -- it forces a report ID and breaks boot protocol.")

    keyboard = keyboard_interface(interfaces)
    if keyboard is None:
        fail("there are %d HID interfaces but none of them is still a keyboard."
             % len(interfaces))
    keyboard_parsed_ = parsed_or_fail(keyboard)
    if keyboard_parsed_.report_ids or keyboard_parsed_.bits_of("input") != 64:
        fail("the second interface exists, but the keyboard interface is no longer clean.",
             "",
             "Its input report is %d bits and it declares report ID(s) %s."
             % (keyboard_parsed_.bits_of("input"),
                keyboard_parsed_.report_ids or "none"),
             "",
             "The whole point of putting the debug channel on its own interface is that",
             "the keyboard interface keeps its eight-byte, no-report-ID boot layout.",
             "If that changed, the collection went into the keyboard interface after",
             "all. Run the report-descriptor check for the detail.")

    vendor_like = []
    for interface in interfaces:
        if interface is keyboard:
            continue
        parsed = parsed_or_fail(interface)
        pages = {f.usage_page for f in parsed.fields if f.usage_page is not None}
        top = parsed.top_level
        if any(p >= 0xFF00 for p in pages) or any((p or 0) >= 0xFF00 for p, _u in top):
            vendor_like.append((interface, parsed))
    if not vendor_like:
        others = [i for i in interfaces if i is not keyboard]
        fail("a second interface is there, but nothing on it is a vendor-defined usage page.",
             *["    " + i.label() for i in others],
             "",
             "Usage pages 0xFF00 to 0xFFFF are the vendor-defined range, and that is",
             "where a private channel belongs. It matters for a practical reason and",
             "not a bureaucratic one: a collection on a standard page may be claimed",
             "exclusively by the OS -- which is precisely what stops you reading the",
             "keyboard collection's own reports -- while a vendor page is left alone",
             "and can be opened by your own tooling.")

    interface, parsed = vendor_like[0]
    inputs = parsed.of_kind("input")
    if not inputs:
        fail("the vendor interface declares no input item, so it can report nothing.",
             *["    " + f.describe() for f in parsed.fields])
    ok("a second, vendor-defined interface is live and the keyboard interface is intact.",
       "keyboard: %s" % keyboard.label(),
       "vendor:   %s" % interface.label(),
       "vendor input: %d bits across %d item(s)."
       % (parsed.bits_of("input"), len(inputs)),
       "The keyboard interface is still eight bytes with no report ID, which is what",
       "keeps it working in a BIOS.",
       "Reading live values from this interface is the learner's half of the exercise:",
       "hidapitester, or a short host-side script, opened on the vendor collection.")


# ---------------------------------------------------------------------------
# offered lesson -- nkro-reports
# ---------------------------------------------------------------------------

@command("nkro")
def cmd_nkro():
    vid, pid = target_ids()
    device, everything = find_device(vid, pid)
    if device is None:
        fail(*fail_not_found(vid, pid, everything))
    interfaces = hid_interfaces(vid, pid)
    for interface in interfaces:
        print("  " + interface.label())
    print("")

    keyboard = keyboard_interface(interfaces)
    if keyboard is None:
        fail("no keyboard interface is bound to this device at all.")
    boot = parsed_or_fail(keyboard)

    # The boot report must still be there, untouched. Replacing it is the failure
    # this lesson is named after: the adapter stops working in a BIOS.
    boot_ok = (not boot.report_ids and boot.bits_of("input") == 64)
    bitmaps = []
    for interface in interfaces:
        parsed = boot if interface is keyboard else parsed_or_fail(interface)
        for field in parsed.of_kind("input"):
            if (field.usage_page == USAGE_PAGE_KEYBOARD and field.is_variable
                    and field.report_size == 1 and field.report_count >= 16):
                bitmaps.append((interface, parsed, field))

    if not bitmaps:
        fail("nothing in this device's descriptors declares a key bitmap.",
             "",
             "N-key rollover needs an input item that is a VARIABLE over the keyboard",
             "usage page -- one bit per key, so any number of them can be on at once.",
             "The shape is report size 1, report count equal to the span of usages you",
             "cover (0x04 to 0xA4 is 161 keys, usually rounded up to a whole number of",
             "bytes), with usage minimum and usage maximum bounding the range.",
             "",
             "That is the exact opposite of the boot report's six-slot array, which is",
             "the point: six slots can hold six usages, and a bitmap can hold all of",
             "them. What you give up is the BIOS, which understands only the boot",
             "layout -- which is why this is an addition and never a replacement.",
             "",
             "Input items across every interface on this device:",
             *["    " + f.describe()
               for i in interfaces for f in parsed_or_fail(i).of_kind("input")])

    if not boot_ok:
        fail("a key bitmap is declared, but the boot report no longer survives beside it.",
             "",
             "The keyboard interface's input report is %d bits and declares report ID(s)"
             % boot.bits_of("input"),
             "%s." % (boot.report_ids or "none"),
             "",
             "This is the failure the lesson is named for: replacing the boot report",
             "instead of adding to it. A machine in firmware setup does not parse your",
             "report descriptor at all -- it assumes the eight-byte boot layout with no",
             "report ID. Break that and the adapter works everywhere except the one",
             "place you cannot fix it from.",
             "",
             "The usual answer is a second interface carrying the NKRO report, leaving",
             "the boot interface exactly as lesson 12 left it.")

    interface, parsed, field = bitmaps[0]
    span = (field.usage_max or 0) - (field.usage_min or 0) + 1
    if field.report_count < 32:
        note("the bitmap declares %d bits. That is more than six keys, so it passes,"
             % field.report_count,
             "but it covers only usages 0x%02x to 0x%02x -- ask the learner which keys"
             % (field.usage_min or 0, field.usage_max or 0),
             "are outside that range and what happens when one of them is pressed.")

    ok("the device reports more than six keys, and the boot report is untouched.",
       "bitmap: %d x %d bit on the keyboard page, usages 0x%02x..0x%02x (%d keys),"
       % (field.report_count, field.report_size, field.usage_min or 0,
          field.usage_max or 0, span),
       "        carried by %s" % interface.label(),
       "boot:   still 64 bits with no report ID, on %s" % keyboard.label(),
       "The host-side half is the learner's: press more than six keys at once in a",
       "text editor and confirm every one arrives, then confirm the adapter still",
       "types in the machine's firmware setup screen.")


# ---------------------------------------------------------------------------

def usage():
    print(__doc__.strip().splitlines()[0])
    print("")
    print("usage: python3 checks/usb.py <subcommand>")
    print("")
    print("subcommands: " + ", ".join(sorted(COMMANDS)))


def main(argv):
    if len(argv) != 2 or argv[1] in ("-h", "--help", "help"):
        usage()
        return EXIT_SETUP if len(argv) != 2 else EXIT_OK
    name = argv[1]
    if name not in COMMANDS:
        print("CANNOT CHECK: there is no USB check called %r." % name, file=sys.stderr)
        print("      Known checks: " + ", ".join(sorted(COMMANDS)), file=sys.stderr)
        return EXIT_SETUP
    COMMANDS[name]()
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv))
