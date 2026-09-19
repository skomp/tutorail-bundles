#!/usr/bin/env bash
# forwarding-on: IPv4 forwarding is enabled on the board.
. "$(dirname "$0")/_lib.sh"
require_board
v="$(bssh 'cat /proc/sys/net/ipv4/ip_forward' 2>/dev/null || echo 0)"
[ "$v" = "1" ] || fail "net.ipv4.ip_forward is ${v} — forwarding is off"
pass "IPv4 forwarding is enabled on the board"
echo "Note: forwarding alone is not enough. Without NAT the reply cannot get back — that is lesson 06."
