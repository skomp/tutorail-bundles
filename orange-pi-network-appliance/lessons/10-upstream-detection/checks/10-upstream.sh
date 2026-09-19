#!/usr/bin/env bash
# upstream-follows: eth0 is a networkd DHCP client and something reacts to carrier changes.
. "$(dirname "$0")/_lib.sh"
require_board
bssh 'networkctl status eth0 2>/dev/null | grep -qi dhcp' || fail "eth0 is not a DHCP client under networkd"
if bssh 'systemctl is-active --quiet networkd-dispatcher' 2>/dev/null; then
  reactor="networkd-dispatcher"
elif bssh 'systemctl list-unit-files 2>/dev/null | grep -qi upstream'; then
  reactor="a custom upstream unit"
else
  fail "no carrier-reacting mechanism found (networkd-dispatcher or a custom upstream unit)"
fi
pass "eth0 is a networkd DHCP client and ${reactor} reacts to carrier changes"
echo "Then prove it: unplug and replug eth0, and confirm clients keep reaching the internet."
