#!/usr/bin/env bash
# Confirms the course's toolchain is present, before lesson 00 rather than during it.

. "$(dirname "$0")/_lib.sh"

command -v cmake >/dev/null 2>&1 \
  || die "cmake is not on your PATH. This course needs CMake 3.20 or newer.
      macOS: brew install cmake   Debian/Ubuntu: apt install cmake
      Windows: winget install Kitware.CMake"

v="$(cmake --version | head -1 | awk '{print $3}')"
major="${v%%.*}"; rest="${v#*.}"; minor="${rest%%.*}"
if [ "$major" -lt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -lt 20 ]; }; then
  die "cmake $v is older than the 3.20 this course needs.
      The course's test check runs 'ctest --test-dir build', and --test-dir
      was added in CMake 3.20."
fi

cxx=""
for c in "${CXX:-}" c++ g++ clang++; do
  [ -n "$c" ] && command -v "$c" >/dev/null 2>&1 && { cxx="$c"; break; }
done
[ -n "$cxx" ] || die "no C++ compiler found. Looked for \$CXX, c++, g++ and clang++.
      macOS: xcode-select --install   Debian/Ubuntu: apt install build-essential"

tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
cat > "$tmp/probe.cpp" <<'PROBE'
#include <optional>
#include <cstdint>
template <typename T> constexpr bool fits() { if constexpr (sizeof(T) >= 4) return true; else return false; }
int main() { std::optional<std::uint32_t> v{7}; auto [a, b] = std::pair{fits<int>(), *v}; return (a && b == 7) ? 0 : 1; }
PROBE
"$cxx" -std=c++17 -o "$tmp/probe" "$tmp/probe.cpp" 2>"$tmp/err" \
  || die "$cxx does not accept C++17. This course needs GCC 8+, Clang 7+ or MSVC 2019+.
$(cat "$tmp/err")"

echo "ok: cmake $v and $cxx, which accepts C++17"
