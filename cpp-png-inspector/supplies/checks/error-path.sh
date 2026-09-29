#!/usr/bin/env bash
# usage: error-path.sh expect-leak|expect-clean
#
# Runs your inspector over the truncated PNG — the file that sends it down its
# error path — and reads the allocation report it prints at exit.
#
#   expect-leak   passes when the error path LOSES memory. Lesson 02 uses this:
#                 the point of that lesson is to make the leak a number.
#   expect-clean  passes when it does not. Every lesson from 03 uses this.

. "$(dirname "$0")/_lib.sh"

case "${1:-}" in
  expect-leak|expect-clean) mode="$1" ;;
  *) die "usage: error-path.sh expect-leak|expect-clean" ;;
esac

bin="$(find_pngdump)"
asset="$root/assets/truncated.png"
out="$("$bin" "$asset" 2>&1)"; status=$?

[ "$status" -lt 128 ] || die "pngdump died on a signal (exit $status) instead of reporting the truncation."

reports="$(printf '%s\n' "$out" | outstanding)"
[ -n "$reports" ] || die "no allocation report in the output.

      This check reads one line, printed exactly once when your program exits:
          allocations: <n> frees: <m> outstanding: <k>

      Single spaces, nothing before it on the line and nothing after it.

      If you have written the counter but print it only on the success path,
      that is the defect this lesson is about: the run that leaks is exactly
      the run that never reaches your report.

      Its output was:
$out"

count="$(printf '%s\n' "$reports" | grep -c '.')"
[ "$count" -eq 1 ] || die "the allocation report was printed $count times. This check needs
      exactly one, because it cannot tell which of $count counts is the final one.

      Print the line once, at exit, after the last free — not once per chunk and
      not once per object destroyed.

      The counts it found, in order: $(printf '%s\n' "$reports" | paste -sd ' ' -)"

k="$(printf '%s\n' "$reports" | tail -n 1)"

if [ "$k" -lt 0 ]; then
  die "the counter says outstanding: $k. A negative count means your program
      freed more times than it allocated, which almost always means one block was
      freed twice — a double free. The likely cause is a copy: two objects holding
      the same pointer, each releasing it in its destructor.

      A double free is undefined behaviour, so a run that survives it proves
      nothing. Fix the ownership, then run this check again."
fi

case "$mode" in
  expect-leak)
    [ "$k" -gt 0 ] || die "the counter says outstanding: $k, so nothing leaked on the error path.
      Either the report is not counting every allocation, or you have already
      fixed the leak. Check that the buffer you allocate before parsing is
      counted, and that the early return really is taken for this file."
    echo "ok: the error path leaks — outstanding: $k"
    ;;
  expect-clean)
    [ "$k" -eq 0 ] || die "the error path still loses $k allocation(s).

      truncated.png makes the parser return early. Every allocation live at
      that moment must be released by something that runs whatever path is
      taken — which is what a destructor is for, and what a free() call sitting
      after the return is not."
    echo "ok: nothing outstanding on the error path"
    ;;
esac
