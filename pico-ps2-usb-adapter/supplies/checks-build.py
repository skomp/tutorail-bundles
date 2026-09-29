#!/usr/bin/env python3
"""The build check: does your firmware compile and link for the RP2040.

WHAT THIS CHECKS
    Exactly what you would run by hand, in the same two steps:

        cmake -S . -B build
        cmake --build build

    and then that the build really produced something loadable -- a .uf2 or a .elf
    under build/. A configure step that succeeds and a build that produces no
    artefact is a real and confusing state (a target that was never added to the
    build, most often), and it does not pass here.

WHAT EVIDENCE IT READS
    The exit status of both commands and everything they printed. On failure it
    pulls out the compiler and linker diagnostics -- the lines that actually say
    what is wrong -- and prints those first, because a bare "exit status 2" tells
    you nothing you can act on. CMake's own configure errors are extracted the same
    way.

WHAT A FAILURE HERE MEANS
    Your code, your CMakeLists.txt, or the SDK's view of them. If the failure is
    "PICO_SDK_PATH not set" or "no arm-none-eabi-gcc", that is an environment
    problem and the `toolchain-present` check explains it better -- run that first.

    A note on the build directory: this check does not delete it. CMake caches the
    SDK path and the board in build/CMakeCache.txt, so if you moved the SDK or
    changed PICO_BOARD and the configure step now contradicts itself, delete the
    build directory and let this check configure it again from nothing.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _console import EXIT_FAIL, EXIT_OK, EXIT_SETUP, workspace_root  # noqa: E402

# Lines worth putting in front of a human, in the order they matter.
DIAGNOSTIC = re.compile(
    r"(: (?:fatal )?error:|: undefined reference|ld(?:\.[a-z]+)?: |"
    r"^CMake Error|^\s*No such file or directory|collect2:|"
    r"region `\w+' overflowed|multiple definition of)", re.MULTILINE)
WARNING = re.compile(r": warning:", re.MULTILINE)


def run(argv, cwd):
    print("$ " + " ".join(argv))
    sys.stdout.flush()
    try:
        done = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=1800)
    except FileNotFoundError:
        print("CANNOT CHECK: %s is not on your PATH." % argv[0], file=sys.stderr)
        print("      Run the toolchain-present check; it says how to install it.",
              file=sys.stderr)
        sys.exit(EXIT_SETUP)
    except subprocess.TimeoutExpired:
        print("FAIL: %s did not finish within 30 minutes." % argv[0], file=sys.stderr)
        sys.exit(EXIT_FAIL)
    text = done.stdout.decode("utf-8", "replace") + done.stderr.decode("utf-8", "replace")
    return done.returncode, text


def diagnostics(text):
    """The lines that say what is wrong, each with a little context after it --
    gcc puts the offending source line and the caret on the lines that follow."""
    lines = text.splitlines()
    wanted = set()
    for index, line in enumerate(lines):
        if DIAGNOSTIC.search(line):
            for offset in range(0, 4):
                if index + offset < len(lines):
                    wanted.add(index + offset)
            if index > 0 and "In function" in lines[index - 1]:
                wanted.add(index - 1)
    return [lines[i] for i in sorted(wanted)]


def report_failure(stage, code, text):
    found = diagnostics(text)
    print("", file=sys.stderr)
    print("FAIL: the %s step failed (exit status %d)." % (stage, code), file=sys.stderr)
    if found:
        print("", file=sys.stderr)
        print("      The diagnostics that matter, in order:", file=sys.stderr)
        for line in found[:60]:
            print("      | " + line.rstrip(), file=sys.stderr)
        if len(found) > 60:
            print("      | ... and %d more" % (len(found) - 60), file=sys.stderr)
    else:
        print("", file=sys.stderr)
        print("      Nothing in the output looked like a compiler diagnostic, so here",
              file=sys.stderr)
        print("      are the last 40 lines of it:", file=sys.stderr)
        for line in text.splitlines()[-40:]:
            print("      | " + line.rstrip(), file=sys.stderr)
    warnings = len(WARNING.findall(text))
    if warnings:
        print("", file=sys.stderr)
        print("      (%d warning%s in this build as well. On this chip a warning about"
              % (warnings, "" if warnings == 1 else "s"), file=sys.stderr)
        print("      an unused or discarded volatile is usually a real bug.)", file=sys.stderr)
    sys.exit(EXIT_FAIL)


def artefacts(build_dir):
    found = []
    for base, _dirs, files in os.walk(build_dir):
        for name in files:
            if name.endswith((".uf2", ".elf")):
                found.append(os.path.join(base, name))
    return sorted(found)


def main():
    root = workspace_root()
    build_dir = os.path.join(root, "build")

    if not os.path.isfile(os.path.join(root, "CMakeLists.txt")):
        print("FAIL: there is no CMakeLists.txt in %s." % root, file=sys.stderr)
        print("", file=sys.stderr)
        print("      This course does not supply one: the build file is edited in nearly",
              file=sys.stderr)
        print("      every lesson -- adding the PIO program, adding TinyUSB, switching",
              file=sys.stderr)
        print("      receive backends -- so it is yours to write and to change.",
              file=sys.stderr)
        print("      Lesson 00 is where it starts.", file=sys.stderr)
        return EXIT_FAIL

    env_note = []
    if not os.environ.get("PICO_SDK_PATH"):
        env_note.append(
            "PICO_SDK_PATH is not set in this environment. If your CMakeLists.txt "
            "does not set it itself, configure will fail on the next line.")
    for line in env_note:
        print("note: " + line)

    code, text = run(["cmake", "-S", ".", "-B", "build"], root)
    if code != 0:
        report_failure("configure", code, text)

    code, text = run(["cmake", "--build", "build", "--parallel"], root)
    if code != 0:
        report_failure("build", code, text)

    warnings = len(WARNING.findall(text))
    built = artefacts(build_dir)
    if not built:
        print("", file=sys.stderr)
        print("FAIL: both cmake steps succeeded but produced no .uf2 or .elf under build/.",
              file=sys.stderr)
        print("", file=sys.stderr)
        print("      A configure and a build that produce nothing means no executable",
              file=sys.stderr)
        print("      target was added. In a Pico project two lines do that work:",
              file=sys.stderr)
        print("        add_executable(<name> <your sources>)", file=sys.stderr)
        print("        pico_add_extra_outputs(<name>)   # this is what makes the .uf2",
              file=sys.stderr)
        print("      Without the second one you get an .elf and nothing to drag onto the",
              file=sys.stderr)
        print("      BOOTSEL drive; without the first, nothing at all.", file=sys.stderr)
        return EXIT_FAIL

    uf2 = [p for p in built if p.endswith(".uf2")]
    print("")
    print("ok: the firmware configured and built.")
    for path in built:
        size = os.path.getsize(path)
        print("  - %s (%d bytes)" % (os.path.relpath(path, root), size))
    if not uf2:
        print("  note: an .elf but no .uf2. You can flash over SWD with the debugprobe,")
        print("        but BOOTSEL drag-and-drop needs pico_add_extra_outputs(<target>).")
    if warnings:
        print("  note: %d compiler warning%s. Read them -- on this chip a discarded"
              % (warnings, "" if warnings == 1 else "s"))
        print("        volatile or an unused result is usually a real bug.")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
