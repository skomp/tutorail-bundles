# The build for this course. You will change it twice:
#   01-not-a-superset       switches the language to C++17
#   04-a-target-of-its-own  splits it into a library, a binary and a test suite
#
# The target name `pngdump` is not cosmetic. Every check looks for an executable
# called exactly that, under build/, build/Debug/ or build/Release/.
#
# 3.20 is the floor because the tests check runs `ctest --test-dir build`, and
# --test-dir arrived in CMake 3.20.

cmake_minimum_required(VERSION 3.20)

project(pngdump LANGUAGES C)

add_executable(pngdump src/main.c)
