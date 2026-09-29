# The smallest CMake file that builds a Pico SDK project.
#
# This file is yours from here on. The course does not hand you another one, and almost
# every lesson from 00 to 18 changes it: the stdio route in lesson 00, a PIO header in
# lesson 07, TinyUSB in lesson 11, the receive-backend switch in lesson 08. Read it now,
# because you will be editing it for the rest of the course.
#
# What is deliberately NOT here: anything that routes printf anywhere. Lesson 00 asks you
# to decide where your console lives and to say why, and that decision is two lines you
# add below. A build that prints nothing is the correct starting point.

cmake_minimum_required(VERSION 3.13)

# Must come before project(). It finds the SDK via PICO_SDK_PATH and pulls in the
# machinery that pico_sdk_init() needs.
include(pico_sdk_import.cmake)

project(ps2_usb_adapter C CXX ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

# One executable. Add your own source files to this list as you write them.
add_executable(adapter
    src/main.c
)

# pico_stdlib gets you GPIO, timers, UART and stdio. You will add more libraries as the
# course goes on — hardware_pio, tinyusb_device, and others.
target_link_libraries(adapter
    pico_stdlib
)

# Produces the .uf2 the BOOTSEL bootloader accepts, alongside the .elf.
pico_add_extra_outputs(adapter)

# ---------------------------------------------------------------------------
# Lesson 00 adds two lines here. They decide which physical route printf takes,
# and leaving them out is why a fresh build is silent. Work out what they are and
# why this course puts the console where it does before you add them.
# ---------------------------------------------------------------------------
