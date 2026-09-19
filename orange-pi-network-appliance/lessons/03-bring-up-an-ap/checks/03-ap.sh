#!/usr/bin/env bash
# ap-beaconing: hostapd is running and the AP interface is in AP mode.
. "$(dirname "$0")/_lib.sh"
require_board
bssh 'systemctl is-active --quiet hostapd || pgrep -x hostapd >/dev/null' || fail "hostapd is not running"
mode="$(bssh "iw dev $AP_IF info 2>/dev/null" | awk '/type/{print $2}')"
[ "$mode" = "AP" ] || fail "$AP_IF is not in AP mode (iw reports type=${mode:-none})"
pass "hostapd is running and $AP_IF is in AP mode"
echo "Confirm by hand: your phone sees the SSID and can associate (no internet yet)."
