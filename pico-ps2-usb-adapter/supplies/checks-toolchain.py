#!/usr/bin/env python3
"""The setup check: is the environment ready, before you write anything.

WHAT THIS CHECKS
    Three things the build will need, and nothing about your code:

      1. cmake, at 3.13 or newer, which is what the Pico SDK's own build files
         require;
      2. arm-none-eabi-gcc, the cross compiler that produces code for the RP2040's
         Cortex-M0+ -- your host's gcc or clang cannot, and the failure it gives if
         you try is obscure;
      3. the Pico SDK itself, found the way CMake will look for it: $PICO_SDK_PATH,
         or a pico-sdk directory beside or above your workspace.

    It deliberately does NOT build anything. It runs at course start, before lesson
    00, when there is no firmware to build and no CMakeLists.txt to build it with.
    A setup check that needed your code would report a fresh, healthy workspace as
    broken.

WHAT EVIDENCE IT READS
    The programs on your PATH and their --version output, the PICO_SDK_PATH
    environment variable, and the presence of pico_sdk_init.cmake inside whatever
    that points at -- a directory called pico-sdk with nothing in it is the most
    common way this goes wrong, and an empty clone (git clone without --recursive,
    so TinyUSB is missing) is the second.

WHAT A FAILURE HERE MEANS
    Something is not installed or not findable. It is never a verdict on your
    firmware. Each line tells you the install command for your platform. Fix them in
    the order reported: cmake and the compiler are independent, but the SDK check is
    only meaningful once the others pass.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _console import EXIT_FAIL, EXIT_OK, workspace_root  # noqa: E402

CMAKE_MINIMUM = (3, 13)


def run(argv):
    try:
        done = subprocess.run(argv, capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, str(exc)
    text = (done.stdout + done.stderr).decode("utf-8", "replace")
    return text, None


def version_tuple(text):
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text or "")
    if not match:
        return None
    return tuple(int(x) for x in match.groups(default="0"))


class Report:
    def __init__(self):
        self.problems = []
        self.lines = []

    def good(self, what, detail):
        self.lines.append("  found    %-20s %s" % (what, detail))

    def bad(self, what, detail, remedy):
        self.lines.append("  MISSING  %-20s %s" % (what, detail))
        self.problems.append((what, detail, remedy))

    def warn(self, what, detail):
        self.lines.append("  note     %-20s %s" % (what, detail))


def check_cmake(report):
    path = shutil.which("cmake")
    if not path:
        report.bad("cmake", "not on your PATH", [
            "This course drives the build with CMake; the Pico SDK is a CMake project.",
            "  macOS:          brew install cmake",
            "  Debian/Ubuntu:  sudo apt install cmake",
            "  Fedora:         sudo dnf install cmake",
            "  Windows:        winget install Kitware.CMake",
        ])
        return
    text, err = run([path, "--version"])
    version = version_tuple(text)
    if version is None:
        report.bad("cmake", "at %s, but `cmake --version` said nothing usable (%s)" % (path, err or text),
                   ["Reinstall cmake, or check that `cmake --version` runs by hand."])
        return
    if version[:2] < CMAKE_MINIMUM:
        report.bad("cmake", "%s at %s -- too old" % (".".join(str(x) for x in version), path), [
            "The Pico SDK needs CMake %d.%d or newer; you have %s."
            % (CMAKE_MINIMUM[0], CMAKE_MINIMUM[1], ".".join(str(x) for x in version)),
            "Upgrade it with your package manager, or from cmake.org/download.",
        ])
        return
    report.good("cmake", "%s at %s" % (".".join(str(x) for x in version), path))


def check_generator(report):
    for name in ("ninja", "make", "mingw32-make", "nmake"):
        path = shutil.which(name)
        if path:
            report.good("build tool", "%s at %s" % (name, path))
            return
    report.bad("build tool", "no ninja and no make on your PATH", [
        "CMake configures a project but something else has to run the compiler.",
        "  macOS:          xcode-select --install   (gives you make)",
        "  Debian/Ubuntu:  sudo apt install build-essential ninja-build",
        "  Windows:        winget install Ninja-build.Ninja",
    ])


def check_arm_gcc(report):
    path = shutil.which("arm-none-eabi-gcc")
    if not path:
        report.bad("arm-none-eabi-gcc", "not on your PATH", [
            "The RP2040 is a Cortex-M0+. Your machine's own gcc or clang builds code",
            "for your machine, not for the chip, and the error you get from trying is",
            "not obvious. You need the bare-metal ARM cross compiler:",
            "  macOS:          brew install --cask gcc-arm-embedded",
            "  Debian/Ubuntu:  sudo apt install gcc-arm-none-eabi libnewlib-arm-none-eabi",
            "  Fedora:         sudo dnf install arm-none-eabi-gcc-cs arm-none-eabi-newlib",
            "  Windows:        winget install Arm.GnuArmEmbeddedToolchain",
            "'none-eabi' is the point: no operating system, embedded ABI.",
        ])
        return
    text, err = run([path, "--version"])
    version = version_tuple((text or "").splitlines()[0] if text else "")
    if version is None:
        report.bad("arm-none-eabi-gcc", "at %s but would not report a version (%s)" % (path, err or ""),
                   ["Try running `arm-none-eabi-gcc --version` by hand and see what it says."])
        return
    report.good("arm-none-eabi-gcc", "%s at %s" % (".".join(str(x) for x in version), path))
    if version[0] < 8:
        report.warn("arm-none-eabi-gcc", "version %s is old; 10 or newer is what the SDK is tested against"
                    % ".".join(str(x) for x in version))


def sdk_candidates():
    root = workspace_root()
    parent = os.path.dirname(root)
    home = os.path.expanduser("~")
    seen = []
    for candidate in (
        os.environ.get("PICO_SDK_PATH"),
        os.path.join(root, "pico-sdk"),
        os.path.join(parent, "pico-sdk"),
        os.path.join(home, "pico-sdk"),
        os.path.join(home, "pico", "pico-sdk"),
        "/usr/share/pico-sdk",
        "/opt/pico-sdk",
    ):
        if candidate and candidate not in seen:
            seen.append(candidate)
    return seen


def check_sdk(report):
    tried = []
    for candidate in sdk_candidates():
        tried.append(candidate)
        init = os.path.join(candidate, "pico_sdk_init.cmake")
        if not os.path.isfile(init):
            continue
        source = "PICO_SDK_PATH" if candidate == os.environ.get("PICO_SDK_PATH") else "found on disk"
        version = "unknown version"
        version_file = os.path.join(candidate, "pico_sdk_version.cmake")
        if os.path.isfile(version_file):
            with open(version_file, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
            major = re.search(r"PICO_SDK_VERSION_MAJOR\s+(\d+)", text)
            minor = re.search(r"PICO_SDK_VERSION_MINOR\s+(\d+)", text)
            if major and minor:
                version = "SDK %s.%s" % (major.group(1), minor.group(1))
        report.good("Pico SDK", "%s, %s (%s)" % (candidate, version, source))
        tinyusb = os.path.join(candidate, "lib", "tinyusb", "src", "tusb.h")
        if os.path.isfile(tinyusb):
            report.good("TinyUSB", "present inside the SDK at lib/tinyusb")
        else:
            report.bad("TinyUSB", "the SDK at %s has an empty lib/tinyusb" % candidate, [
                "The SDK vendors TinyUSB as a git submodule, and a plain `git clone`",
                "leaves it empty. Chapter M6 (lessons 11 to 13) cannot build without it.",
                "Fix it inside the SDK checkout:",
                "    git -C %s submodule update --init --recursive" % candidate,
            ])
        return
    report.bad("Pico SDK", "not found", [
        "CMake finds the SDK through the PICO_SDK_PATH environment variable, and this",
        "check looked there and in the usual places. Clone it and point at it:",
        "    git clone -b master --recursive https://github.com/raspberrypi/pico-sdk",
        "    export PICO_SDK_PATH=$PWD/pico-sdk        # add this to your shell profile",
        "--recursive matters: it brings in TinyUSB, which lessons 11 to 13 need.",
        "",
        "Places this check looked:",
    ] + ["    " + path for path in tried])


def check_pyserial(report):
    try:
        import serial  # noqa: F401
    except ImportError:
        report.warn("pyserial", "not installed -- every console check needs it from "
                                "lesson 00 onward. Install it with: %s -m pip install pyserial"
                    % os.path.basename(sys.executable or "python3"))
        return
    report.good("pyserial", "importable, so the console checks can open your debug UART")


def main():
    report = Report()
    check_cmake(report)
    check_generator(report)
    check_arm_gcc(report)
    check_sdk(report)
    check_pyserial(report)

    print("Toolchain for pico-ps2-usb-adapter, on %s:" % sys.platform)
    for line in report.lines:
        print(line)
    print("")
    sys.stdout.flush()

    if not report.problems:
        print("ok: everything this course builds with is installed and findable.")
        return EXIT_OK

    print("FAIL: %d of the things this course builds with %s not ready."
          % (len(report.problems), "is" if len(report.problems) == 1 else "are"),
          file=sys.stderr)
    for what, detail, remedy in report.problems:
        print("", file=sys.stderr)
        print("  %s -- %s" % (what, detail), file=sys.stderr)
        for line in remedy:
            print("      " + line, file=sys.stderr)
    print("", file=sys.stderr)
    print("  None of this is a verdict on your firmware; there is no firmware yet.",
          file=sys.stderr)
    return EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
