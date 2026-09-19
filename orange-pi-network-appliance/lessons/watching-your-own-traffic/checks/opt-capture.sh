#!/usr/bin/env bash
# capture-works: tcpdump is present and captures traffic on the AP interface.
. "$(dirname "$0")/_lib.sh"
require_board
bssh 'command -v tcpdump >/dev/null' || fail "tcpdump is not installed on the board"
n="$(bssh "sudo timeout 6 tcpdump -ni $AP_IF -c 3 2>/dev/null" | wc -l)"
[ "${n:-0}" -ge 1 ] || fail "tcpdump captured nothing on $AP_IF — generate some client traffic and re-run"
pass "tcpdump captured ${n} packet line(s) on $AP_IF"
