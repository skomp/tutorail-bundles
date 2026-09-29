# Shared helper for this course's checks. Sourced, never run directly.
# Finds the binary your build produced and gives every check the same vocabulary.

set -u

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
expected="$root/checks/expected"

die() { echo "FAIL: $*" >&2; exit 1; }

find_pngdump() {
  local c
  for c in build/pngdump build/Debug/pngdump build/Release/pngdump \
           build/pngdump.exe build/Debug/pngdump.exe build/Release/pngdump.exe; do
    if [ -x "$root/$c" ]; then printf '%s\n' "$root/$c"; return 0; fi
  done
  die "no executable called 'pngdump' under build/.
      This check looked in build/, build/Debug/ and build/Release/.
      Your CMakeLists.txt must produce a target named exactly 'pngdump',
      and you must have built it: cmake -S . -B build && cmake --build build"
}

# The three line shapes the course fixes. Everything else your tool prints is yours.
chunk_lines() { grep -E '^[0-9]+ [A-Za-z]{4} [0-9]+$' || true; }
error_lines() { grep -E '^error:' || true; }
outstanding() { sed -n 's/^allocations: [0-9]* frees: [0-9]* outstanding: \([0-9][0-9]*\)$/\1/p'; }
