#!/usr/bin/env bash
# upstream-follows: the upstream is a networkd DHCP client and something reacts to carrier changes.
. "$(dirname "$0")/_lib.sh"
require_board
: "${WAN_IF:?set WAN_IF in board.env — the upstream interface you discovered in lesson 01}"
bssh "networkctl status $WAN_IF 2>/dev/null | grep -qi dhcp" || fail "$WAN_IF is not a DHCP client under networkd"
if bssh 'systemctl is-active --quiet networkd-dispatcher' 2>/dev/null; then
  reactor="networkd-dispatcher"
elif bssh 'systemctl list-unit-files 2>/dev/null | grep -qi upstream'; then
  reactor="a custom upstream unit"
else
  fail "no carrier-reacting mechanism found (networkd-dispatcher or a custom upstream unit)"
fi
pass "$WAN_IF is a networkd DHCP client and ${reactor} reacts to carrier changes"
echo "Then prove it: unplug and replug $WAN_IF, and confirm clients keep reaching the internet."
