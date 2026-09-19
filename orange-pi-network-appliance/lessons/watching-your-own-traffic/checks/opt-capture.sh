#!/usr/bin/env bash
# capture-works: tcpdump is present and captures traffic on wlan0.
. "$(dirname "$0")/_lib.sh"
bssh 'command -v tcpdump >/dev/null' || fail "tcpdump is not installed on the board"
n="$(bssh 'sudo timeout 6 tcpdump -ni wlan0 -c 3 2>/dev/null | wc -l' || echo 0)"
[ "${n:-0}" -ge 1 ] || fail "tcpdump captured nothing on wlan0 — generate some client traffic and re-run"
pass "tcpdump captured ${n} packet line(s) on wlan0"
