#!/usr/bin/env bash
# lifeline-up: a serial getty is bound to an rfcomm device and Bluetooth is powered.
. "$(dirname "$0")/_lib.sh"
unit="$(bssh 'systemctl list-units --type=service --state=running --no-legend 2>/dev/null | grep -Eo "(serial-getty@rfcomm[0-9]+|rfcomm[^ ]*)\.service" | head -1' || true)"
[ -n "$unit" ] || fail "no running serial getty bound to an rfcomm device — the Bluetooth console is not up"
bssh 'bluetoothctl show 2>/dev/null | grep -q "Powered: yes"' || fail "the Bluetooth controller is not powered"
pass "Bluetooth serial console is up ($unit) and the controller is powered"
echo "Confirm by hand: unplug Ethernet, then open a shell over the Bluetooth serial console."
